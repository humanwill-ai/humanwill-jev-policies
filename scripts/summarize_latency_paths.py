"""Summarize recorded gateway paths without new API calls or reinterpretation of labels."""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from evals.step6.preview_latency import stats


def summarize(report):
    groups, pooled = {}, defaultdict(list)
    all_rows = []
    for key, rows in report["groups"].items():
        workload, arm = key.split("/")
        baseline = report["groups"][workload + "/baseline"]
        assert len(rows) == len(baseline)
        records = []
        for row in rows:
            comparison = baseline[row["index"]]
            assert comparison["index"] == row["index"]
            assessments = row["assessments"]
            followups = sum(len(a["evaluation"]["batches"]) > 1 for a in assessments)
            record = {
                "index": row["index"],
                "cold": row["cold"],
                "duration_ms": row["duration_ms"],
                "added_ms": row["duration_ms"] - comparison["duration_ms"],
                "provider_calls": len(row["provider_calls"]),
                "followups": followups,
                "decisions": [a["decision"] for a in assessments],
                "followup_status": [a["policy_assessment"]["status"] for a in assessments],
                "status": row["status"],
            }
            records.append(record)
            all_rows.append(record)
            if not row["cold"] and arm != "baseline":
                kind = (
                    "placeholder" if workload == "legacy_placeholder_diagnostic" else "meaningful"
                )
                pooled[kind + "/" + arm].append(record)
                pooled[kind + "/" + arm + ("/followup" if followups else "/no_followup")].append(
                    record
                )
        groups[key] = {
            "warm_total": stats([r["duration_ms"] for r in records if not r["cold"]]),
            "warm_added": stats([r["added_ms"] for r in records if not r["cold"]]),
            "rows": records,
        }
    return {
        "source_commit": report["source_commit"],
        "simulated": report["simulated"],
        "cost_before_usd": report["cost_before_usd"],
        "cost_after_usd": report["cost_after_usd"],
        "new_cost_usd": report["new_cost_usd"],
        "physical_calls": report["physical_calls"],
        "accounting_stopped": report["accounting_stopped"],
        "request_count": len(all_rows),
        "assessment_decisions": dict(Counter(d for r in all_rows for d in r["decisions"])),
        "groups": groups,
        "pooled_warm_paths": {
            key: {
                "added": stats([r["added_ms"] for r in rows]),
                "total": stats([r["duration_ms"] for r in rows]),
                "provider_call_counts": dict(Counter(r["provider_calls"] for r in rows)),
                "followup_requests": sum(bool(r["followups"]) for r in rows),
                "assessment_decisions": dict(Counter(d for r in rows for d in r["decisions"])),
            }
            for key, rows in sorted(pooled.items())
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    summary = summarize(json.loads(args.report.read_text()))
    args.output.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary["pooled_warm_paths"], indent=2))


if __name__ == "__main__":
    main()
