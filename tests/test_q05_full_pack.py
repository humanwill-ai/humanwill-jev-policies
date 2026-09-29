"""Brief templates change only declared wording, preserving policy/evidence composition."""

import asyncio
import copy
import json
import unittest

import yaml
from test_question_context import CaptureBackend

from evals.step6.backends import choice_answer
from evals.step6.effect_question import context_for
from evals.step6.focused_policy_live import CONFIG
from evals.step6.question_context import ContextBackend
from evals.step6.reviewed_live import BASE, CATALOG, DATASET, POLICIES
from evals.step6.run import load_case_bundle, select_configuration
from evals.step6.short_questions import VariantBackend
from evals.step6.source_approval import load_catalog, source_evidence_for
from humanwill_policies import load_configuration
from humanwill_policies.evaluation import Evaluator
from humanwill_policies.serialization import canonical


class Q05FullPackTests(unittest.TestCase):
    def test_all_175_cases_preserve_policy_context_and_gold_composition(self):
        all_cases = json.loads(DATASET.read_text())["cases"]
        cases = all_cases
        self.assertEqual(len(cases), 175)
        bundle = load_case_bundle(all_cases, POLICIES)
        config, catalog = yaml.safe_load(CONFIG.read_text()), load_catalog(CATALOG)
        contexts = {
            c["id"]: c for c in json.loads((BASE / "context-v1/contexts.json").read_text())["cases"]
        }
        calls = 0
        for case in cases:
            record = context_for(case, contexts[case["id"]], "question_and_context")
            answers = {
                pid: choice_answer(
                    scope or "insufficient_evidence",
                    ["applicable", "not_applicable", "insufficient_evidence"],
                )
                for pid, scope in case["scope_by_policy"].items()
            }
            loaded = load_configuration(
                bundle,
                select_configuration(config, case["policy_id"], case.get("also_policy_ids", [])),
            )
            original = None
            for name in ["control", "q05"]:
                with self.subTest(case=case["id"], variant=name):
                    capture = CaptureBackend(answers)
                    backend = ContextBackend(
                        VariantBackend(capture, name, "test"), case["request"], record
                    )
                    result = asyncio.run(
                        Evaluator(bundle, loaded, backend).evaluate(
                            case["request"], evidence=source_evidence_for(case, catalog)
                        )
                    )
                    self.assertEqual(result["decision"], case["expected_composed"])
                    self.assertLessEqual(len(capture.payloads), 1)
                    if not capture.payloads:
                        continue
                    calls += 1
                    payload = capture.payloads[0]
                    self.assertLessEqual(len(canonical(payload).encode()), 24000)
                    if name == "control":
                        original = payload
                        continue
                    restored = copy.deepcopy(payload)
                    for pid, q in restored["questions"].items():
                        before = original["questions"][pid]
                        q["instructions"]["task"] = before["instructions"]["task"]
                        q["instructions"]["boundary"] = before["instructions"]["boundary"]
                        q["instructions"]["trusted_conditions"]["meaning"] = before["instructions"][
                            "trusted_conditions"
                        ]["meaning"]
                        q["criteria"] = before["criteria"]
                    self.assertEqual(restored, original)
        self.assertEqual(calls, 296)
