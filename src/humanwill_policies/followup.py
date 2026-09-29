"""One runtime-selected Q04 continuation; no dataset or policy-specific routing."""

import asyncio
import copy
import time

from .errors import PolicyError
from .providers import response_usage, validate_response
from .questions import scoped_variant
from .serialization import canonical


def assessment_trace(profile):
    return dict(
        profile=profile,
        status="disabled" if profile == "q05" else "not_needed",
        batch_index=None,
        eligible=[],
        accepted=[],
        rejected={},
        primary_answers={},
        secondary_answers={},
        error=None,
    )


async def follow_up(
    *, rows, planned, payload, backend, limits, start, batches, thresholds, apply_answer, trace
):
    # Preserve accepted decisions and errors masked by a block, across ALL primary batches.
    if any(row["judgment"] == "violation" for row in rows.values()):
        return
    eligible = sorted(
        key
        for key, row in rows.items()
        if row["status"] == "error"
        and row["reasons"] == ["low_confidence"]
        and row["evidence"].get("choice") in ("applicable", "not_applicable")
    )
    trace["eligible"] = eligible
    if not eligible:
        return
    # A single extra call per event. Preserve original batch boundaries and size limits.
    batch = next(b for b in planned if set(b).intersection(eligible))
    ids = sorted(set(batch).intersection(eligible))
    trace["rejected"] = {key: "call_limit" for key in eligible if key not in ids}
    trace["primary_answers"] = {
        key: {
            f: copy.deepcopy(rows[key]["evidence"][f])
            for f in ("choice", "confidence", "probabilities")
        }
        for key in ids
    }
    trace["status"] = "skipped"
    if len(batches) >= limits.max_batches:
        trace["error"] = "batch_limit"
        return
    request = payload({key: scoped_variant(q, "q04") for key, q in batch.items()})
    if len(canonical(request).encode()) > limits.max_batch_bytes:
        trace["error"] = "batch_limit"
        return
    remaining = limits.timeout_ms / 1000 - (time.monotonic() - start)
    if remaining <= 0:
        trace["error"] = "evaluation_timeout"
        return
    attempt = dict(returned_model=None, input_tokens=None, output_tokens=None, cost_usd=None)
    trace.update(status="attempted", batch_index=len(batches))
    batches.append(attempt)
    try:
        async with asyncio.timeout(remaining):
            response = await backend.evaluate(
                request, timeout=remaining, max_bytes=limits.max_response_bytes
            )
        if len(canonical(response).encode()) > limits.max_response_bytes:
            raise PolicyError("response_limit", "Evaluator response exceeds byte limit")
        attempt.update(response_usage(response, backend.accepted_models))
        answers, _ = validate_response(response, request["questions"], backend.accepted_models)
    except asyncio.CancelledError:
        trace.update(status="failed", error="evaluation_interrupted")
        raise
    except TimeoutError:
        trace.update(status="failed", error="evaluation_timeout")
        return
    except PolicyError as exc:
        trace.update(status="failed", error=exc.code)
        return
    except Exception:
        trace.update(status="failed", error="backend_error")
        return
    trace["status"] = "completed"
    for key in ids:
        answer = answers[key]
        trace["secondary_answers"][key] = copy.deepcopy(answer)
        choice = answer["choice"]
        maximum = max(answer["probabilities"].values())
        if choice == "insufficient_evidence":
            trace["rejected"][key] = "still_indeterminate"
        elif choice != trace["primary_answers"][key]["choice"]:
            trace["rejected"][key] = "conflicting_scope"
        elif (
            answer["confidence"] < thresholds[choice]
            or sum(v == maximum for v in answer["probabilities"].values()) != 1
        ):
            trace["rejected"][key] = "low_confidence"
        else:
            apply_answer(key, answer)
            trace["accepted"].append(key)
