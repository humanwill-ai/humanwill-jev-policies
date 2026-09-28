"""Actual authored rules, shared templates, trusted checks and no hidden scope rewrite."""

import copy

import test_evaluation
from test_evaluation import ScriptedBackend, answer, event
from test_foundation import Workspace, write_policy
from test_outcome_thresholds import v4

from humanwill_policies import load_bundle, load_configuration
from humanwill_policies.config import preview
from humanwill_policies.errors import PolicyError
from humanwill_policies.questions import POLICY_RUBRIC


def v5(config):
    result = v4(config)
    result["format"] = "humanwill.config/5"
    for binding in result["policies"].values():
        binding.pop("scope", None)
        binding.pop("scope_by_stage", None)
    return result


class DirectPolicyTests(Workspace):
    config = test_evaluation.EvaluationTests.config
    enforcing = test_evaluation.EvaluationTests.enforcing
    metadata_config = test_evaluation.EvaluationTests.metadata_config
    fact = test_evaluation.EvaluationTests.fact
    run_evaluation = test_evaluation.EvaluationTests.run_evaluation

    def test_all_stages_send_exact_body_and_preview_matches(self):
        body = (
            "# Company rule\n\nDo not insult customers. Quoting an insult for analysis is allowed."
        )
        stages = ["prompt", "model_request", "response", "tool_action"]
        write_policy(self.root, body=body, stages=stages)
        bundle = load_bundle(self.root)
        config = v5(self.config())
        loaded = load_configuration(bundle, config)
        shown = preview(bundle, loaded)["policies"][0]["evaluation_questions"]
        for stage in stages:
            request = event(stage)
            if stage == "tool_action":
                request["content"] = [
                    {"id": "text-1", "kind": "tool_action", "name": "test", "arguments": {}}
                ]
            backend = ScriptedBackend()
            result = self.run_evaluation(backend, config, request=request)
            q = backend.calls[0]["questions"]["RULE"]
            self.assertEqual(q, shown[stage])
            self.assertEqual(q["instructions"]["policy"]["text"], bundle.policies[0].body)
            self.assertEqual(q["instructions"]["stage"], stage)
            self.assertNotIn("rule", q["instructions"])
            self.assertEqual(result["format"], "humanwill.result/4")
            self.assertEqual(result["rubric"], POLICY_RUBRIC)
            self.assertEqual(result["decision"], "allow")
        self.assertEqual(
            set(preview(bundle, loaded, "prompt")["policies"][0]["evaluation_questions"]),
            {"prompt"},
        )

    def test_editing_only_markdown_changes_the_evaluation_input_and_hash(self):
        config = v5(self.config())
        texts, hashes = [], []
        for body in (
            "Only neutral descriptions are permitted.",
            "Friendly jokes are also permitted.",
        ):
            write_policy(self.root, body=body)
            backend = ScriptedBackend()
            result = self.run_evaluation(backend, config)
            texts.append(backend.calls[0]["questions"]["RULE"]["instructions"]["policy"]["text"])
            hashes.append(result["configuration_sha256"])
        self.assertNotEqual(texts[0], texts[1])
        self.assertNotEqual(hashes[0], hashes[1])

    def test_scope_still_requires_trusted_permission_and_retains_uncertainty(self):
        write_policy(
            self.root,
            body=(
                "Only verified finance staff may approve payments. Read-only inquiries are allowed."
            ),
        )
        config = v5(self.metadata_config("scoped_predicates"))
        for choice, facts, decision in [
            ("applicable", None, "evaluation_error"),
            ("applicable", [self.fact([])], "block"),
            ("applicable", [self.fact()], "allow"),
            ("not_applicable", None, "allow"),
            ("insufficient_evidence", [self.fact([])], "evaluation_error"),
        ]:
            backend = ScriptedBackend({"RULE": answer(choice, scoped=True)})
            result = self.run_evaluation(backend, config, facts=facts)
            self.assertEqual(result["decision"], decision)
            instructions = backend.calls[0]["questions"]["RULE"]["instructions"]
            self.assertEqual(
                instructions["trusted_conditions"]["required_fields"], ["identity.groups"]
            )
            self.assertNotIn("verified-directory", str(backend.calls))
            self.assertNotIn("predicates", str(backend.calls))
            self.assertNotIn("all_of", instructions["trusted_conditions"])
            self.assertEqual(set(backend.calls[0]["state"]), {"stage", "content", "coverage"})

    def test_old_scope_fields_rejected_in_new_format(self):
        bundle = load_bundle(self.root)
        for field, value in [
            ("scope", "Manual scope"),
            ("scope_by_stage", {"prompt": "Manual scope"}),
        ]:
            config = v5(self.metadata_config("scoped_predicates"))
            config["policies"]["RULE"][field] = value
            self.fails("schema_error", lambda config=config: load_configuration(bundle, config))

    def test_shared_template_has_no_policy_identifier_special_cases(self):
        original = v5(self.config())
        first = ScriptedBackend()
        self.run_evaluation(first, original)
        write_policy(self.root, policy_id="CUSTOM-RULE")
        second = ScriptedBackend({"CUSTOM-RULE": answer()})
        changed = copy.deepcopy(original)
        changed["policies"]["CUSTOM-RULE"] = changed["policies"].pop("RULE")
        self.run_evaluation(second, changed)
        before = copy.deepcopy(first.calls[0]["questions"]["RULE"])
        after = copy.deepcopy(second.calls[0]["questions"]["CUSTOM-RULE"])
        before["instructions"]["policy"].pop("id")
        after["instructions"]["policy"].pop("id")
        self.assertEqual(before, after)

    def test_long_policy_is_not_silently_truncated_or_sent_over_limit(self):
        write_policy(self.root, body="Rule text " * 2000)
        config = v5(self.config())
        config["evaluation"] = {"max_batch_bytes": 1024}
        backend = ScriptedBackend()
        result = self.run_evaluation(backend, config)
        self.assertEqual(result["decision"], "evaluation_error")
        self.assertFalse(backend.calls)
        self.assertEqual(result["errors"][0]["code"], "batch_limit")

    def test_metadata_disabled_and_egress_guards_still_apply(self):
        config = v5(self.metadata_config("scoped_predicates"))
        config["metadata"]["enabled"] = False
        with self.assertRaises(PolicyError):
            load_configuration(load_bundle(self.root), config)
        backend = ScriptedBackend()
        result = self.run_evaluation(backend, v5(self.enforcing()), permit=False)
        self.assertEqual(result["errors"][0]["code"], "egress_not_authorized")
        self.assertFalse(backend.calls)
