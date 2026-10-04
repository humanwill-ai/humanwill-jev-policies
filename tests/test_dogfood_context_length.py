"""Context experiment provenance checks; no provider calls or private data."""

import copy
import unittest

from evals.dogfood.context_length import extend_case
from evals.dogfood.pilot import fingerprint


class ContextLengthTests(unittest.TestCase):
    def fixture(self):
        records = [
            {"line": n, "timestamp": str(n), "role": role, "text": text}
            for n, role, text in (
                (1, "user", "Original feature definition"),
                (2, "assistant", "Implementation discussion"),
                (3, "user", "Implement it"),
                (4, "assistant", "Future answer must not leak"),
            )
        ]
        request = {
            "request_id": "case",
            "stage": "model_request",
            "content": [{"id": "part-0", "kind": "text", "role": "user", "text": "Implement it"}],
            "coverage": {
                "complete": False,
                "inspected": ["part-0"],
                "omitted": ["Other surfaces", "Older history"],
            },
        }
        return records, {
            "id": "case",
            "timestamp": "3",
            "source_lines": [3],
            "request": request,
            "request_sha256": fingerprint(request),
            "review": {"facts": {"destination.onward_approved": None}},
        }

    def test_original_target_and_missing_facts_survive_without_future_answers(self):
        records, case = self.fixture()
        before = copy.deepcopy(case)
        result = extend_case(case, records, 1)
        self.assertEqual(case, before)
        self.assertEqual(result["source_lines"], [1, 2, 3])
        self.assertEqual(result["request"]["content"][-1], case["request"]["content"][-1])
        self.assertEqual(result["review"], case["review"])
        self.assertEqual(result["request_sha256"], fingerprint(result["request"]))
        self.assertNotIn("Future answer", str(result))
        self.assertFalse(result["request"]["coverage"]["complete"])

    def test_mismatched_transcript_missing_start_or_no_extension_rejected(self):
        records, case = self.fixture()
        for start in (0, 3):
            with self.assertRaises(ValueError):
                extend_case(case, records, start)
        records[2]["text"] = "Changed target"
        with self.assertRaises(ValueError):
            extend_case(case, records, 1)

    def test_excerpt_gap_is_explicit_and_preserves_original_suffix(self):
        records, case = self.fixture()
        result = extend_case(case, records, 1, 1)
        self.assertEqual(result["source_lines"], [1, 3])
        self.assertIn("Intervening visible messages", result["request"]["coverage"]["omitted"][-1])
        self.assertEqual(result["request"]["content"][-1], case["request"]["content"][-1])
        with self.assertRaises(ValueError):
            extend_case(case, records, 1, 3)

    def test_future_dated_content_rejected_and_large_history_never_trimmed(self):
        records, case = self.fixture()
        records[0]["text"] = "x" * 30000
        self.assertEqual(len(extend_case(case, records, 1)["request"]["content"][0]["text"]), 30000)
        records[0]["timestamp"] = "9"
        with self.assertRaises(ValueError):
            extend_case(case, records, 1)


if __name__ == "__main__":
    unittest.main()
