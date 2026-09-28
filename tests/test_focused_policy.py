"""The experiment changes only the intended question fields and one neutral observation."""

import asyncio
import copy
import json
import unittest

import yaml
from test_question_context import CaptureBackend

from evals.step6.backends import choice_answer
from evals.step6.focused_policy_live import CONFIG, PROTOCOL, FocusedBackend
from evals.step6.patch_diagnostics import CRITERIA, TASK
from evals.step6.question_context import ContextBackend
from evals.step6.reviewed_live import BASE, CATALOG, DATASET, POLICIES
from evals.step6.run import load_case_bundle, select_configuration
from evals.step6.source_approval import load_catalog, source_evidence_for
from humanwill_policies import load_configuration
from humanwill_policies.evaluation import Evaluator
from humanwill_policies.serialization import canonical


class FocusedPolicyTests(unittest.TestCase):
    def test_all_175_keep_policies_events_and_scripted_decisions(self):
        cases = json.loads(DATASET.read_text())["cases"]
        bundle = load_case_bundle(cases, POLICIES)
        config = yaml.safe_load(CONFIG.read_text())
        catalog = load_catalog(CATALOG)
        contexts = {
            c["id"]: c for c in json.loads((BASE / "context-v1/contexts.json").read_text())["cases"]
        }
        notes = json.loads(PROTOCOL.read_text())["short_context"]
        calls = 0
        for case in cases:
            with self.subTest(case=case["id"]):
                answers = {
                    pid: choice_answer(scope or "insufficient_evidence", CRITERIA)
                    for pid, scope in case["scope_by_policy"].items()
                }
                loaded = load_configuration(
                    bundle,
                    select_configuration(
                        config, case["policy_id"], case.get("also_policy_ids", [])
                    ),
                )
                captured = []
                for focused in (False, True):
                    backend = CaptureBackend(answers)
                    delegate = FocusedBackend(backend, case["id"]) if focused else backend
                    engine = Evaluator(
                        bundle,
                        loaded,
                        ContextBackend(delegate, case["request"], contexts[case["id"]]),
                    )
                    result = asyncio.run(
                        engine.evaluate(
                            case["request"], evidence=source_evidence_for(case, catalog)
                        )
                    )
                    self.assertEqual(result["decision"], case["expected_composed"])
                    captured.append(backend.payloads)
                self.assertEqual(len(captured[0]), len(captured[1]))
                for before, after in zip(*captured, strict=True):
                    calls += 1
                    self.assertLessEqual(len(canonical(after).encode()), 24000)
                    restored = copy.deepcopy(after)
                    for pid, question in restored["questions"].items():
                        self.assertEqual(question["instructions"]["task"], TASK)
                        self.assertEqual(question["criteria"], CRITERIA)
                        question["instructions"]["task"] = before["questions"][pid]["instructions"][
                            "task"
                        ]
                        question["criteria"] = before["questions"][pid]["criteria"]
                    if case["id"] in notes:
                        self.assertEqual(
                            restored["state"]["assessment_context"].pop("operation_semantics"),
                            notes[case["id"]],
                        )
                    self.assertEqual(restored, before)
        self.assertEqual(calls, 148)
