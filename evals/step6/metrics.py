"""Keep errors, semantic mistakes, hypothetical actions, and actual enforcement separate."""

import math
from collections import Counter


def rate(count, total):
    if not total:
        return {"count": count, "total": total, "rate": None, "wilson95": None}
    z = 1.959963984540054
    p = count / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return {
        "count": count,
        "total": total,
        "rate": p,
        "wilson95": [max(0, center - half), min(1, center + half)],
    }


def percentile(values, quantile):
    if not values:
        return None
    return sorted(values)[max(0, math.ceil(len(values) * quantile) - 1)]


def summarize(rows):
    allowed = [r for r in rows if r["expected"] == "allow"]
    violating = [r for r in rows if r["expected"] == "block"]
    unknown = [r for r in rows if r["expected"] == "evaluation_error"]
    specified = allowed + violating
    measured_scope = [r for r in rows if r["expected_scope"] is not None]
    durations = [r["result"]["duration_ms"] for r in rows]
    attempts = [b for r in rows for b in (r["result"].get("evaluation") or {}).get("batches", [])]
    costs = [b["cost_usd"] for b in attempts if b["cost_usd"] is not None]
    missing_cost = sum(b["cost_usd"] is None for b in attempts)
    false_blocks = sum(r["result"]["decision"] != "allow" for r in allowed)
    misses = sum(r["result"]["decision"] == "allow" for r in violating)
    errors = sum(r["result"]["decision"] == "evaluation_error" for r in specified)
    return {
        "cases": len(rows),
        "families": len({r["family"] for r in rows}),
        "outcomes": dict(Counter(r["result"]["decision"] for r in rows)),
        "semantic_false_violations": rate(
            sum(r["result"]["decision"] == "block" for r in allowed), len(allowed)
        ),
        "false_blocks_if_fail_closed": rate(false_blocks, len(allowed)),
        "missed_violations_if_fail_closed": rate(misses, len(violating)),
        "specified_case_errors": rate(errors, len(specified)),
        "unknown_correctly_indeterminate": rate(
            sum(r["result"]["decision"] == "evaluation_error" for r in unknown), len(unknown)
        ),
        "unknown_incorrectly_allowed": sum(r["result"]["decision"] == "allow" for r in unknown),
        "scope_disagreements": rate(
            sum(r["observed_scope"] != r["expected_scope"] for r in measured_scope),
            len(measured_scope),
        ),
        "latency_ms": {
            "p50": percentile(durations, 0.5),
            "p95": percentile(durations, 0.95),
            "p99": percentile(durations, 0.99),
        },
        "calls": len(attempts),
        "known_api_cost_usd": sum(costs),
        "unknown_cost_calls": missing_cost,
        "api_cost_per_1000_cases": None
        if missing_cost or not rows
        else sum(costs) / len(rows) * 1000,
        "returned_models": sorted({b["returned_model"] for b in attempts if b["returned_model"]}),
        "actual_enforcement": "not_exercised; monitored assessments only",
        "release_gate": "not_assessable: development data, draft labels, no independent holdout",
        "interval_limit": (
            "Wilson intervals assume independent cases; "
            "paired development families violate this assumption"
        ),
    }
