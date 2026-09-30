"""Stage-aware opt-in keeps the bounded continuation and connector contracts."""

import json
from pathlib import Path

import test_assessment_followup as existing
from test_evaluation import event
from test_foundation import write_policy

from humanwill_policies import load_bundle, load_configuration
from humanwill_policies.config import preview
from humanwill_policies.questions import ASSESSMENT_POINTS, scoped_variant


class StageAwareTests(existing.FollowupTests):
    # Re-run the existing failure, deadline, metadata, usage and connector contracts
    # with the new profile, as well as explicit all-stage routing checks below.
    def configured(self, **extra):
        extra.setdefault("policy_assessment", "q05_stage_aware")
        return super().configured(**extra)

    def test_all_stage_questions_match_frozen_experiment_and_preview(self):
        from evals.step6.tool_probe import followup_payload

        write_policy(self.root, stages=list(ASSESSMENT_POINTS))
        config = self.configured()
        bundle = load_bundle(self.root)
        shown = preview(bundle, load_configuration(bundle, config))["policies"][0]
        for stage in ASSESSMENT_POINTS:
            with self.subTest(stage=stage):
                backend = existing.SequenceBackend(
                    [
                        {"RULE": existing.scope(confidence=0.5)},
                        {"RULE": existing.scope(confidence=0.8)},
                    ]
                )
                request = event(stage)
                if stage == "tool_action":
                    request["content"] = [
                        {
                            "id": "text-1",
                            "kind": "tool_action",
                            "name": "shell",
                            "arguments": {"command": "pwd"},
                        }
                    ]
                result = self.run_evaluation(backend, config, request=request)
                self.assertEqual(result["decision"], "allow")
                self.assertEqual(result["policy_assessment"]["profile"], "q05_stage_aware")
                self.assertEqual(len(backend.calls), 2)
                self.assertEqual(
                    backend.calls[1],
                    followup_payload(
                        backend.calls[0], "tool_wording" if stage == "tool_action" else "q04", {}
                    ),
                )
                self.assertEqual(
                    backend.calls[1]["questions"]["RULE"], shown["followup_questions"][stage]
                )

    def test_tool_stage_contract(self):
        write_policy(self.root, stages=["tool_action"])
        request = event("tool_action")
        request["content"] = [
            {
                "id": "text-1",
                "kind": "tool_action",
                "name": "shell",
                "arguments": {"command": "pwd"},
            }
        ]
        backend = existing.SequenceBackend(
            [{"RULE": existing.scope(confidence=0.5)}, {"RULE": existing.scope()}]
        )
        result = self.run_evaluation(backend, self.configured(), request=request)
        self.assertEqual(result["decision"], "allow")
        self.assertEqual(result["policy_assessment"]["profile"], "q05_stage_aware")
        self.assertEqual(result["policy_assessment"]["accepted"], ["RULE"])
        self.assertEqual(len(backend.calls), 2)
        self.assertTrue(
            backend.calls[1]["questions"]["RULE"]["instructions"]["task"].startswith(
                "Considering only the actual proposed tool use and its supplied arguments,"
            )
        )

    def test_tool_wording_does_not_touch_content_only_rules(self):
        question = {
            "type": "choice",
            "instructions": {"task": "Content policy"},
            "criteria": {"compliant": "yes", "violation": "no", "insufficient_evidence": "unknown"},
        }
        self.assertEqual(scoped_variant(question, "tool_action"), question)

    def test_measured_wording_is_preserved_verbatim(self):
        from humanwill_policies.questions import SHORT_VARIANTS

        source = Path(__file__).resolve().parents[1] / "evals/step6/tool-probe-v1/questions.json"
        frozen = json.loads(source.read_text())
        self.assertEqual(SHORT_VARIANTS["tool_action"]["task"], frozen["tool_task"])
        self.assertEqual(SHORT_VARIANTS["tool_action"]["criteria"], frozen["tool_criteria"])

    def test_historical_stage_tool_live_guard_rejects_changed_runtime(self):
        from evals.step6.stage_tool import validate_experiment

        with self.assertRaisesRegex(ValueError, "Frozen"):
            validate_experiment()
