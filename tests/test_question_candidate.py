"""Question wording changes alone must preserve inputs, labels and decision plumbing."""

import asyncio
import copy
import json
import unittest
from unittest.mock import patch

import yaml
from test_question_context import CaptureBackend

from evals.step6.backends import choice_answer
from evals.step6.question_context import ContextBackend, sha256
from evals.step6.reviewed_live import BASE, CATALOG, CONFIG, DATASET, POLICIES, ROOT
from evals.step6.run import load_case_bundle, select_configuration
from evals.step6.source_approval import load_catalog, source_evidence_for
from evals.step6.threshold_replay import decision_view
from humanwill_policies import load_configuration
from humanwill_policies.serialization import canonical

CANDIDATE = BASE / "questions-v1/config.yaml"


class QuestionCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = yaml.safe_load(CONFIG.read_text())
        cls.candidate = yaml.safe_load(CANDIDATE.read_text())
        cls.cases = json.loads(DATASET.read_text())["cases"]
        cls.bundle = load_case_bundle(cls.cases, POLICIES)
        cls.catalog = load_catalog(CATALOG)
        cls.contexts = {
            c["id"]: c for c in json.loads((BASE / "context-v1/contexts.json").read_text())["cases"]
        }

    def test_frozen_inputs_policies_context_and_candidate(self):
        snapshot = json.loads((CANDIDATE.parent / "snapshot.json").read_text())
        for path, expected in snapshot["sha256"].items():
            self.assertEqual(sha256(ROOT / path), expected, path)
        self.assertEqual(self.bundle.sha256, snapshot["bundle_sha256"])
        self.assertEqual(len(self.cases), 175)
        self.assertEqual(snapshot["status"], "prepared_not_live_evaluated")
        approved = json.loads((BASE / "release/owner-review-v1.json").read_text())
        self.assertEqual([c["id"] for c in self.cases], approved["approved_case_ids"])

    def test_only_four_source_scope_questions_change(self):
        old = self.baseline["policies"]["EVAL-SRC-001"]["scope_by_stage"]
        new = self.candidate["policies"]["EVAL-SRC-001"]["scope_by_stage"]
        self.assertEqual(set(new), {"prompt", "model_request", "response", "tool_action"})
        self.assertTrue(all(new[stage] != old[stage] for stage in old))
        restored = copy.deepcopy(self.candidate)
        restored["policies"]["EVAL-SRC-001"]["scope_by_stage"] = old
        self.assertEqual(restored, self.baseline)
        load_configuration(self.bundle, self.candidate)

    def test_all_175_scripted_outcomes_and_payload_isolation(self):
        from humanwill_policies.evaluation import Evaluator

        changed_questions = 0
        for case in self.cases:
            with self.subTest(case=case["id"]):
                # Gold scope is a scripted backend output, never part of model state/questions.
                answers = {
                    pid: choice_answer(
                        scope or "insufficient_evidence",
                        ["applicable", "not_applicable", "insufficient_evidence"],
                    )
                    for pid, scope in case["scope_by_policy"].items()
                }
                payloads, results = [], []
                for config in (self.baseline, self.candidate):
                    backend = CaptureBackend(answers)
                    engine = Evaluator(
                        self.bundle,
                        load_configuration(
                            self.bundle,
                            select_configuration(
                                config, case["policy_id"], case.get("also_policy_ids", [])
                            ),
                        ),
                        ContextBackend(backend, case["request"], self.contexts[case["id"]]),
                    )
                    with patch(
                        "humanwill_policies.providers.JevBackend.evaluate",
                        side_effect=AssertionError("Offline test cannot invoke Jev"),
                    ):
                        results.append(
                            asyncio.run(
                                engine.evaluate(
                                    case["request"],
                                    evidence=source_evidence_for(case, self.catalog),
                                )
                            )
                        )
                    payloads.append(backend.payloads)
                self.assertEqual(results[0]["decision"], case["expected_composed"])
                self.assertEqual(decision_view(results[0]), decision_view(results[1]))
                self.assertEqual(len(payloads[0]), len(payloads[1]))
                for old, new in zip(*payloads, strict=True):
                    self.assertLessEqual(len(canonical(new).encode()), 24000)
                    normalized = copy.deepcopy(new)
                    if "EVAL-SRC-001" in new["questions"]:
                        changed_questions += 1
                        old_rule = old["questions"]["EVAL-SRC-001"]["instructions"]["rule"]
                        new_rule = new["questions"]["EVAL-SRC-001"]["instructions"]["rule"]
                        self.assertNotEqual(old_rule, new_rule)
                        self.assertEqual(
                            new_rule,
                            self.candidate["policies"]["EVAL-SRC-001"]["scope_by_stage"][
                                case["request"]["stage"]
                            ],
                        )
                        normalized["questions"]["EVAL-SRC-001"]["instructions"]["rule"] = old_rule
                    self.assertEqual(normalized, old)
        self.assertGreater(changed_questions, 0)


if __name__ == "__main__":
    unittest.main()
