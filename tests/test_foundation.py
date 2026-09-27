import dataclasses
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml
from jsonschema import Draft202012Validator

from humanwill_policies import Limits, PolicyError, load_bundle
from humanwill_policies.cli import _init_demo
from humanwill_policies.config import load_configuration, load_project, preview, read_configuration
from humanwill_policies.contracts import SCHEMAS, schema, validate_contract
from humanwill_policies.serialization import parse_yaml

FIXTURES = Path(__file__).parent / "fixtures"


def write_policy(root, name="rule.md", policy_id="RULE", body="Do not insult customers.", **extra):
    header = {
        "kind": "policy",
        "id": policy_id,
        "version": "1",
        "title": "Test rule",
        "stages": ["prompt"],
        **extra,
    }
    (root / name).parent.mkdir(parents=True, exist_ok=True)
    (root / name).write_text("---\n" + yaml.safe_dump(header) + "---\n" + body)


def write_collection(root, includes, name="policies.md", collection_id="bundle"):
    (root / name).parent.mkdir(parents=True, exist_ok=True)
    (root / name).write_text(
        "---\n"
        + yaml.safe_dump(
            {"kind": "collection", "id": collection_id, "version": "1", "includes": includes}
        )
        + "---\n# Collection\n"
    )


class Workspace(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "root"
        self.root.mkdir()
        write_policy(self.root)
        write_collection(self.root, ["rule.md"])

    def fails(self, code, call):
        with self.assertRaises(PolicyError) as caught:
            call()
        self.assertEqual(caught.exception.code, code, str(caught.exception))


class BundleTests(Workspace):
    def test_nested_includes_and_repeated_reference(self):
        write_collection(self.root, ["../rule.md", "extra.md"], "sub/policies.md", "sub")
        write_policy(self.root, "sub/extra.md", "EXTRA")
        write_collection(self.root, ["sub/policies.md", "./rule.md", "rule.md"])
        bundle = load_bundle(self.root)
        self.assertEqual([p.id for p in bundle.policies], ["EXTRA", "RULE"])
        self.assertEqual(len(bundle.sources), 4)

    def test_hashes_portable_and_snapshot_detached(self):
        bundle = load_bundle(self.root)
        other = Path(self.temp.name) / "copy"
        shutil.copytree(self.root, other)
        self.assertEqual(bundle.sha256, load_bundle(other).sha256)
        snapshot = bundle.snapshot()
        snapshot["sources"][0]["text"] = "changed"
        self.assertNotEqual(snapshot, bundle.snapshot())
        with self.assertRaises(dataclasses.FrozenInstanceError):
            bundle.policies[0].body = "changed"
        for source in bundle.sources:
            self.assertEqual(source.sha256, hashlib.sha256(source.text.encode()).hexdigest())

    def test_content_change_changes_digest_without_version_change(self):
        old = load_bundle(self.root)
        write_policy(self.root, body="Changed rule.")
        new = load_bundle(self.root)
        self.assertEqual(old.version, new.version)
        self.assertNotEqual(old.sha256, new.sha256)
        self.assertNotEqual(old.policies[0].sha256, new.policies[0].sha256)

    def test_include_order_changes_provenance_not_policy_order(self):
        write_policy(self.root, "b.md", "B")
        write_collection(self.root, ["rule.md", "b.md"])
        before = load_bundle(self.root)
        write_collection(self.root, ["b.md", "rule.md"])
        after = load_bundle(self.root)
        self.assertEqual(before.policies, after.policies)
        self.assertNotEqual(before.sha256, after.sha256)

    def test_ordinary_links_are_not_loaded(self):
        write_policy(self.root, body="Read [background](missing.md).")
        self.assertEqual(len(load_bundle(self.root).policies), 1)

    def test_cycle(self):
        write_collection(self.root, ["policies.md"])
        self.fails("include_cycle", lambda: load_bundle(self.root))

    def test_duplicate_ids_in_different_files(self):
        write_policy(self.root, "second.md")
        write_collection(self.root, ["rule.md", "second.md"])
        self.fails("duplicate_id", lambda: load_bundle(self.root))

    def test_missing_file(self):
        write_collection(self.root, ["missing.md"])
        self.fails("unreadable_source", lambda: load_bundle(self.root))

    def test_escape_and_unsupported_path_forms(self):
        for path, code in [
            ("../outside.md", "path_escape"),
            ("/tmp/a.md", "invalid_path"),
            ("https://example.org/a.md", "invalid_path"),
            ("rule.md#section", "invalid_path"),
            ("rule.txt", "invalid_path"),
            ("sub\\rule.md", "invalid_path"),
        ]:
            with self.subTest(path=path):
                write_collection(self.root, [path])
                self.fails(code, lambda: load_bundle(self.root))

    def test_symlink_files_and_directories_rejected(self):
        (self.root / "alias.md").symlink_to(self.root / "rule.md")
        write_collection(self.root, ["alias.md"])
        self.fails("unreadable_source", lambda: load_bundle(self.root))
        (self.root / "alias").symlink_to(self.root, target_is_directory=True)
        write_collection(self.root, ["alias/rule.md"])
        self.fails("unreadable_source", lambda: load_bundle(self.root))

    def test_fifo_does_not_block(self):
        os.mkfifo(self.root / "fifo.md")
        write_collection(self.root, ["fifo.md"])
        self.fails("invalid_file", lambda: load_bundle(self.root))

    def test_limits(self):
        cases = [
            (Limits(file_bytes=4), "file_limit"),
            (Limits(bundle_bytes=5), "bundle_limit"),
            (Limits(files=1), "file_count_limit"),
        ]
        for limit, code in cases:
            with self.subTest(code=code):
                self.fails(code, lambda limit=limit: load_bundle(self.root, limits=limit))
        write_policy(self.root, "b.md", "B")
        write_collection(self.root, ["rule.md", "b.md"])
        self.fails("policy_limit", lambda: load_bundle(self.root, limits=Limits(policies=1)))
        self.fails("include_limit", lambda: load_bundle(self.root, limits=Limits(includes=1)))
        write_collection(self.root, ["rule.md"], "nested.md", "nested")
        write_collection(self.root, ["nested.md"])
        self.fails("depth_limit", lambda: load_bundle(self.root, limits=Limits(depth=1)))

    def test_invalid_limits(self):
        for values in [{"depth": 0}, {"depth": True}, {"depth": 10000}]:
            self.fails("invalid_limit", lambda values=values: Limits(**values))

    def test_policy_schema_rejects_missing_unknown_and_wrong_types(self):
        for extra in [
            {"id": ""},
            {"version": 1},
            {"stages": ["unknown"]},
            {"stages": ["prompt", "prompt"]},
            {"mode": "allow"},
            {"title": " "},
        ]:
            with self.subTest(extra=extra):
                write_policy(self.root, **extra)
                self.fails("schema_error", lambda: load_bundle(self.root))

    def test_empty_policy_and_invalid_encoding(self):
        write_policy(self.root, body=" \n")
        self.fails("empty_policy", lambda: load_bundle(self.root))
        (self.root / "rule.md").write_bytes(b"\xff")
        self.fails("invalid_encoding", lambda: load_bundle(self.root))

    def test_missing_id_rejected(self):
        path = self.root / "rule.md"
        path.write_text(path.read_text().replace("id: RULE\n", ""))
        self.fails("schema_error", lambda: load_bundle(self.root))

    def test_empty_collection_rejected(self):
        write_collection(self.root, [])
        self.fails("schema_error", lambda: load_bundle(self.root))

    def test_front_matter_and_entrypoint(self):
        (self.root / "rule.md").write_text("# Missing header")
        self.fails("missing_front_matter", lambda: load_bundle(self.root))
        (self.root / "rule.md").write_text("---\nkind: policy\n")
        self.fails("missing_front_matter", lambda: load_bundle(self.root))
        write_policy(self.root)
        self.fails("invalid_entrypoint", lambda: load_bundle(self.root, "rule.md"))

    def test_unrecognized_files_are_not_read(self):
        (self.root / "unlisted.md").write_bytes(b"\xff")
        self.assertEqual(len(load_bundle(self.root).sources), 2)

    def test_crlf_bytes_preserved(self):
        path = self.root / "rule.md"
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        bundle = load_bundle(self.root)
        self.assertIn("\r\n", next(s.text for s in bundle.sources if s.path == "rule.md"))


class ParserTests(Workspace):
    def test_unsafe_ambiguous_and_non_json_yaml(self):
        cases = [
            ("key: 1\nkey: 2", "duplicate_key"),
            ("key: &x value\nother: *x", "invalid_yaml"),
            ("key: !!python/object/apply:os.system ['echo bad']", "invalid_yaml"),
            ("key: .nan", "invalid_value"),
            ("key: 2026-09-27", "invalid_value"),
            ("1: value", "invalid_yaml"),
            ("- value", "invalid_yaml"),
            ("key: 1\n---\nkey: 2", "invalid_yaml"),
        ]
        for text, code in cases:
            with self.subTest(text=text):
                self.fails(code, lambda text=text: parse_yaml(text))

    def test_yaml_depth_and_no_source_echo(self):
        self.fails("depth_limit", lambda: parse_yaml("key: " + "[" * 30 + "]" * 30))
        with self.assertRaises(PolicyError) as caught:
            parse_yaml("key: [PRIVATE_SENTINEL")
        self.assertNotIn("PRIVATE_SENTINEL", str(caught.exception))


class ConfigTests(Workspace):
    def config(self, **binding):
        return {
            "format": "humanwill.config/1",
            "metadata": {"enabled": False},
            "policies": {"RULE": {"enabled": True, **binding}},
        }

    def enforced(self):
        config = self.config(
            mode="enforce",
            evaluation_profile={
                "id": "test-only",
                "model": "test",
                "dataset_sha256": "0" * 64,
                "min_confidence": 0.9,
            },
        )
        config["provider"] = {"transport": "openrouter", "model": "test", "api_key_env": "TEST_KEY"}
        return config

    def test_metadata_off_content_policy_and_immutable_config(self):
        bundle = load_bundle(self.root)
        supplied = self.config()
        config = load_configuration(bundle, supplied)
        self.assertEqual(preview(bundle, config)["policies"][0]["status"], "monitor")
        supplied["metadata"]["enabled"] = True
        config.to_dict()["metadata"]["enabled"] = True
        self.assertFalse(config.to_dict()["metadata"]["enabled"])

    def test_defaults_have_stable_digest(self):
        bundle = load_bundle(self.root)
        first = load_configuration(bundle, self.config())
        second = load_configuration(
            bundle,
            self.config(mode="monitor", on_error="block", requires_metadata=[], predicates=[]),
        )
        self.assertEqual(first.sha256, second.sha256)

    def test_config_digest_changes_with_bundle(self):
        first = load_configuration(load_bundle(self.root), self.config()).sha256
        write_policy(self.root, body="New body")
        self.assertNotEqual(first, load_configuration(load_bundle(self.root), self.config()).sha256)

    def test_preview_rejects_configuration_from_another_bundle(self):
        configuration = load_configuration(load_bundle(self.root), self.config())
        write_policy(self.root, body="Different policy body, same ID.")
        self.fails("bundle_mismatch", lambda: preview(load_bundle(self.root), configuration))

    def test_absent_configuration_and_stage_filter(self):
        bundle = load_bundle(self.root)
        self.assertEqual(preview(bundle)["policies"][0]["status"], "unconfigured")
        config = load_configuration(bundle, self.config())
        self.assertEqual(
            preview(bundle, config, "response")["policies"][0]["status"], "not_applicable"
        )
        self.assertFalse(preview(bundle, config)["runtime_available"])

    def test_explicit_disabled_and_missing_metadata_monitor(self):
        bundle = load_bundle(self.root)
        config = load_configuration(bundle, self.config(requires_metadata=["identity.groups"]))
        self.assertEqual(preview(bundle, config)["policies"][0]["issues"], ["metadata_disabled"])
        disabled = load_configuration(bundle, self.config(enabled=False))
        self.assertEqual(preview(bundle, disabled)["policies"][0]["status"], "disabled")

    def test_binding_ids_must_be_exhaustive(self):
        config = self.config()
        config["policies"]["WRONG"] = config["policies"].pop("RULE")
        self.fails("policy_bindings", lambda: load_configuration(load_bundle(self.root), config))

    def test_unknown_settings_review_and_inline_secrets_rejected(self):
        for extra in [{"mode": "review"}, {"typo": True}, {"requires_metadata": ["user_claim"]}]:
            self.fails(
                "schema_error",
                lambda extra=extra: load_configuration(
                    load_bundle(self.root), self.config(**extra)
                ),
            )
        config = self.enforced()
        config["provider"]["api_key"] = "PRIVATE_SENTINEL"
        self.fails("schema_error", lambda: load_configuration(load_bundle(self.root), config))

    def test_enforcement_requires_profile(self):
        self.fails(
            "missing_profile",
            lambda: load_configuration(load_bundle(self.root), self.config(mode="enforce")),
        )
        config = self.enforced()
        config["provider"]["model"] = "other"
        self.fails(
            "profile_model_mismatch", lambda: load_configuration(load_bundle(self.root), config)
        )

    def test_enforcement_requires_metadata_feature_and_sources(self):
        config = self.enforced()
        config["policies"]["RULE"]["requires_metadata"] = ["identity.groups"]
        bundle = load_bundle(self.root)
        self.fails("metadata_disabled", lambda: load_configuration(bundle, config))
        config["metadata"]["enabled"] = True
        self.fails("metadata_source_disabled", lambda: load_configuration(bundle, config))
        config["metadata"]["sources"] = {
            "identity": {"enabled": True, "source": "company-identity"}
        }
        self.assertIsNotNone(load_configuration(bundle, config))

    def test_predicate_dependencies(self):
        config = self.config(
            predicates=[{"field": "identity.groups", "op": "contains", "value": "finance"}]
        )
        self.fails(
            "undeclared_metadata", lambda: load_configuration(load_bundle(self.root), config)
        )
        config["policies"]["RULE"]["requires_metadata"] = ["identity.groups"]
        self.assertIsNotNone(load_configuration(load_bundle(self.root), config))

    def test_assessment_only_and_unsupported_connector_stages(self):
        config = self.enforced()
        config["connectors"] = [{"name": "copilot_cli", "stages": ["prompt"]}]
        self.fails(
            "unsupported_enforcement", lambda: load_configuration(load_bundle(self.root), config)
        )
        config["policies"]["RULE"]["mode"] = "monitor"
        self.assertIsNotNone(load_configuration(load_bundle(self.root), config))
        config["connectors"][0]["stages"] = ["response"]
        self.fails("unsupported_stage", lambda: load_configuration(load_bundle(self.root), config))

    def test_config_byte_and_loader_limits(self):
        path = self.root / "config.yaml"
        path.write_text("#" * 65_537)
        self.fails("config_limit", lambda: read_configuration(path))
        config = self.config()
        config["limits"] = {"files": 1}
        path.write_text(yaml.safe_dump(config))
        self.fails("file_count_limit", lambda: load_project(self.root, path))

    def test_no_network_in_offline_operations(self):
        with patch("socket.socket", side_effect=AssertionError("Network is forbidden")):
            bundle = load_bundle(self.root)
            config = load_configuration(bundle, self.config())
            self.assertEqual(preview(bundle, config)["policies"][0]["status"], "monitor")

    def test_configuration_cannot_bypass_already_loaded_limits(self):
        config = self.config()
        config["limits"] = {"files": 1}
        self.fails("limits_mismatch", lambda: load_configuration(load_bundle(self.root), config))

    def test_configuration_fifo_does_not_block(self):
        path = self.root / "config.yaml"
        os.mkfifo(path)
        self.fails("invalid_config", lambda: read_configuration(path))


class ContractTests(Workspace):
    def test_schema_validity_and_fixture_validation(self):
        for name in SCHEMAS:
            Draft202012Validator.check_schema(schema(name))
        for path in FIXTURES.glob("*.json"):
            validate_contract(path.name.split("-")[0], json.loads(path.read_text()))

    def test_request_metadata_is_optional_but_cannot_assert_trust(self):
        request = json.loads((FIXTURES / "request-content.json").read_text())
        validate_contract("request", request)
        request["metadata"] = [
            {
                "field": "identity.groups",
                "source": "host",
                "subject_ref": "user-1",
                "observed_at": "2026-09-27T10:00:00Z",
                "value": ["finance"],
                "trusted": True,
            }
        ]
        self.fails("schema_error", lambda: validate_contract("request", request))

    def test_invalid_coverage_and_tool_action(self):
        request = json.loads((FIXTURES / "request-content.json").read_text())
        request["coverage"]["inspected"] = ["absent"]
        self.fails("invalid_coverage", lambda: validate_contract("request", request))
        request["coverage"]["inspected"] = ["message-1"]
        request["stage"] = "tool_action"
        self.fails("missing_action", lambda: validate_contract("request", request))

    def test_request_cannot_override_policy_or_threshold(self):
        request = json.loads((FIXTURES / "request-content.json").read_text())
        request["policies"] = []
        self.fails("schema_error", lambda: validate_contract("request", request))

    def test_request_size(self):
        request = json.loads((FIXTURES / "request-content.json").read_text())
        request["content"][0]["text"] = "x" * 262144
        self.fails("payload_limit", lambda: validate_contract("request", request))

    def test_evaluator_cannot_assert_host_block(self):
        result = json.loads((FIXTURES / "result-example.json").read_text())
        result["enforcement"]["actual"] = "blocked"
        self.fails("schema_error", lambda: validate_contract("result", result))

    def test_coverage_cannot_claim_complete_with_omissions(self):
        for name, fixture in [("request", "request-content"), ("result", "result-example")]:
            value = json.loads((FIXTURES / f"{fixture}.json").read_text())
            value["coverage"]["complete"] = True
            value["coverage"]["omitted"] = ["attached files"]
            self.fails(
                "invalid_coverage", lambda name=name, value=value: validate_contract(name, value)
            )

    def test_metadata_timestamp_needs_valid_time_and_timezone(self):
        value = json.loads((FIXTURES / "request-finance.json").read_text())
        for timestamp in [
            "not-a-date",
            "2026-09-27",
            "2026-09-27T10:00:00",
            "2026-02-31T00:00:00Z",
        ]:
            value["metadata"][0]["observed_at"] = timestamp
            self.fails("invalid_timestamp", lambda: validate_contract("request", value))


class CLITests(Workspace):
    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "humanwill_policies", *map(str, args)],
            capture_output=True,
            text=True,
            timeout=15,
        )

    def test_json_success_and_safe_failure(self):
        run = self.run_cli("validate", self.root, "--json")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout)["scope"], "bundle_only")
        (self.root / "rule.md").write_text("---\nsecret: [PRIVATE_SENTINEL\n---\nBody")
        run = self.run_cli("validate", self.root, "--json")
        self.assertEqual(run.returncode, 2)
        self.assertFalse(run.stdout)
        self.assertNotIn("PRIVATE_SENTINEL", run.stderr)
        self.assertNotIn("Traceback", run.stderr)
        self.assertEqual(json.loads(run.stderr)["error"]["code"], "invalid_yaml")

    def test_demo_from_package_and_no_overwrite(self):
        target = Path(self.temp.name) / "demo"
        run = self.run_cli("init-demo", target)
        self.assertEqual(run.returncode, 0, run.stderr)
        run = self.run_cli("preview", target, "--config", target / "config.yaml", "--json")
        self.assertEqual(run.returncode, 0, run.stderr)
        result = json.loads(run.stdout)
        self.assertEqual(len(result["policies"]), 3)
        self.assertEqual([p["status"] for p in result["policies"]].count("disabled"), 2)
        marker = target / "keep.txt"
        marker.write_text("keep")
        self.assertEqual(self.run_cli("init-demo", target).returncode, 2)
        self.assertEqual(marker.read_text(), "keep")

    def test_all_schemas_export(self):
        for name in SCHEMAS:
            run = self.run_cli("schema", name)
            self.assertEqual(run.returncode, 0, run.stderr)
            Draft202012Validator.check_schema(json.loads(run.stdout))

    def test_demo_initialization_offline(self):
        with patch("socket.socket", side_effect=AssertionError("Network is forbidden")):
            _init_demo(Path(self.temp.name) / "offline")


if __name__ == "__main__":
    unittest.main()
