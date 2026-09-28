"""Source-approval boundaries and scripted policy composition; no model/network calls."""

import asyncio
import copy
import hashlib
import json
import unittest
from pathlib import Path

import yaml

from evals.step6.backends import choice_answer
from evals.step6.run import load_case_bundle, select_configuration
from evals.step6.source_approval import (
    load_catalog,
    load_source_cases,
    source_evidence_for,
    source_facts,
)
from humanwill_policies import load_configuration
from humanwill_policies.evaluation import Evaluator
from humanwill_policies.providers import MockBackend

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "evals/step6"


class SourcePolicyTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_catalog()
        self.resource = {
            "kind": "npm",
            "endpoint": "https://packages.example.test/npm",
            "operation": "install",
            "package": "@company/build-kit",
        }

    def facts(self, *resources, resolution="complete"):
        return source_facts({"resolution": resolution, "resources": list(resources)}, self.catalog)

    def test_package_endpoint_kind_and_operation_are_all_required(self):
        self.assertEqual(
            self.facts(self.resource), {"authorization.software_sources_approved": True}
        )
        for replacement in [
            {"endpoint": "https://packages.example.test.evil.test/npm"},
            {"endpoint": "https://packages.example.test/npm-other"},
            {"package": "@company/build-kit-copy"},
            {"kind": "python"},
        ]:
            with self.subTest(replacement=replacement):
                self.assertFalse(
                    self.facts({**self.resource, **replacement})[
                        "authorization.software_sources_approved"
                    ]
                )
        r = {
            "kind": "https_file",
            "endpoint": "https://tools.example.test/releases/linter-1.2.3.sh",
            "operation": "execute",
            "package": None,
        }
        self.assertFalse(self.facts(r)["authorization.software_sources_approved"])

    def test_all_sources_required_and_empty_is_not_approval(self):
        self.assertFalse(self.facts()["authorization.software_sources_approved"])
        self.assertFalse(
            self.facts(self.resource, {**self.resource, "package": "unlisted"})[
                "authorization.software_sources_approved"
            ]
        )
        self.assertEqual(self.facts(self.resource, resolution="unavailable"), {})

    def test_ambiguous_urls_are_not_treated_as_approval(self):
        for url in [
            "http://packages.example.test/npm",
            "https://user@packages.example.test/npm",
            "https://packages.example.test/npm/../other",
            "https://packages.example.test/npm%2fother",
            "https://packages.example.test/npm?mirror=evil",
            "https://packages.example.test/npm#x",
            "https://packages.example.test:443/npm",
            "https://PACKAGES.example.test/npm",
            "https://packages.example.test/npm/",
            "https://packages.example.test\\evil/npm",
        ]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                self.facts({**self.resource, "endpoint": url})

    def test_registry_wide_approval_requires_explicit_all(self):
        self.catalog["sources"][2]["packages"] = "all"
        self.assertTrue(
            self.facts({**self.resource, "package": "other"})[
                "authorization.software_sources_approved"
            ]
        )
        self.catalog["sources"][2].pop("packages")
        with self.assertRaises(ValueError):
            self.facts(self.resource)

    def test_empty_catalog_denies_and_invalid_catalog_fails(self):
        self.catalog["sources"] = []
        self.assertFalse(self.facts(self.resource)["authorization.software_sources_approved"])
        self.catalog["default"] = "allow"
        with self.assertRaises(ValueError):
            self.facts(self.resource)

    def test_review_snapshot_and_old_bundle_are_preserved(self):
        snapshot = json.loads((BASE / "sources-v1/snapshot.json").read_text())
        for path, expected in snapshot["sha256"].items():
            self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), expected)
        for name in ["software.md", "production.md", "documents.md"]:
            self.assertEqual(
                (BASE / "policies-v2" / name).read_bytes(),
                (BASE / "policies-sources-v1" / name).read_bytes(),
            )

    def test_scripted_scope_labels_compose_with_real_source_matching(self):
        cases = load_source_cases()
        bundle = load_case_bundle(cases, BASE / "policies-sources-v1")
        config = yaml.safe_load((BASE / "config-sources-v1.yaml").read_text())
        self.assertEqual(len(cases), 46)
        self.assertEqual(
            bundle.sha256,
            json.loads((BASE / "sources-v1/snapshot.json").read_text())["bundle_sha256"],
        )
        for case in cases:
            with self.subTest(case=case["id"]):
                scopes = case.get("scope_by_policy", {case["policy_id"]: case["expected_scope"]})
                answers = {
                    key: choice_answer(
                        value, ["applicable", "not_applicable", "insufficient_evidence"]
                    )
                    for key, value in scopes.items()
                }
                selected = select_configuration(
                    config, case["policy_id"], case.get("also_policy_ids", [])
                )
                evaluator = Evaluator(
                    bundle, load_configuration(bundle, selected), MockBackend(answers)
                )
                result = asyncio.run(
                    evaluator.evaluate(
                        case["request"], evidence=source_evidence_for(case, self.catalog)
                    )
                )
                self.assertEqual(
                    result["decision"], case.get("expected_composed", case["expected"])
                )
                for row in result["policies"]:
                    if row["policy_id"] in case.get("expected_by_policy", {}):
                        observed = (
                            "block"
                            if row["judgment"] == "violation"
                            else "evaluation_error"
                            if row["status"] == "error"
                            else "allow"
                        )
                        self.assertEqual(observed, case["expected_by_policy"][row["policy_id"]])

    def test_metadata_feature_remains_optional_without_fake_approval(self):
        cases = load_source_cases()
        case = cases[0]
        bundle = load_case_bundle(cases, BASE / "policies-sources-v1")
        config = select_configuration(
            yaml.safe_load((BASE / "config-sources-v1.yaml").read_text()), "EVAL-SRC-001"
        )
        config["metadata"]["enabled"] = False
        backend = MockBackend(
            {
                "EVAL-SRC-001": choice_answer(
                    "applicable", ["applicable", "not_applicable", "insufficient_evidence"]
                )
            }
        )
        evaluator = Evaluator(bundle, load_configuration(bundle, config), backend)
        result = asyncio.run(
            evaluator.evaluate(case["request"], evidence=source_evidence_for(case, self.catalog))
        )
        self.assertEqual(result["decision"], "evaluation_error")
        disabled = copy.deepcopy(config)
        disabled["policies"]["EVAL-SRC-001"]["enabled"] = False
        load_configuration(bundle, disabled)
