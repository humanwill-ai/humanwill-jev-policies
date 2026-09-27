"""Use only verified event-bound evidence; never inspect request metadata as authority."""

import json
from datetime import datetime

from .errors import PolicyError
from .runtime import EvidenceContext
from .serialization import canonical, digest, json_value


def predicate_result(predicate: dict, value: object) -> bool:
    # Canonical JSON equality distinguishes true from 1; membership is never substring matching.
    def same(a, b):
        return canonical(a) == canonical(b)

    op = predicate["op"]
    if op == "exists":
        return value is not None
    if op == "equals":
        if isinstance(value, (dict, list)) or type(value) is not type(predicate["value"]):
            if type(value) not in (int, float) or type(predicate["value"]) not in (int, float):
                raise PolicyError(
                    "invalid_metadata_type", "Equality requires matching scalar types"
                )
        return same(value, predicate["value"])
    if op == "contains":
        if not isinstance(value, list):
            raise PolicyError("invalid_metadata_type", "Membership requires a complete list")
        return any(same(item, predicate["value"]) for item in value)
    if op == "in":
        if isinstance(value, (dict, list)):
            raise PolicyError("invalid_metadata_type", "Set membership requires a scalar")
        if not any(type(value) is type(item) for item in predicate["value"]):
            raise PolicyError(
                "invalid_metadata_type", "Set membership requires a matching scalar type"
            )
        return any(same(value, item) for item in predicate["value"])
    raise PolicyError("unsupported_predicate", "Unsupported metadata predicate")


def check_metadata(request, binding, metadata, context: EvidenceContext | None, now, max_age):
    if not metadata["enabled"]:
        raise PolicyError("metadata_disabled", "Required metadata is disabled")
    if context is None or context.request_sha256 != digest(request):
        raise PolicyError("missing_trusted_metadata", "No verified evidence bound to this event")
    try:
        facts = json.loads(context.facts_json)
        json_value(facts)
        if not isinstance(facts, list) or len(facts) > 256:
            raise ValueError
        values = {}
        for field in binding["requires_metadata"]:
            source = metadata["sources"].get(field.split(".")[0])
            if not source or not source["enabled"]:
                raise PolicyError("metadata_source_disabled", "Required source is disabled")
            matching = [f for f in facts if isinstance(f, dict) and f.get("field") == field]
            if len(matching) != 1:
                raise PolicyError("missing_trusted_metadata", "Missing or ambiguous verified fact")
            fact = matching[0]
            if fact.get("source") != source["source"] or fact.get("complete") is not True:
                raise PolicyError(
                    "untrusted_metadata", "Source or completeness was not established"
                )
            if not isinstance(fact.get("subject_ref"), str) or not fact["subject_ref"].strip():
                raise ValueError
            observed = datetime.fromisoformat(fact["observed_at"])
            if observed.tzinfo is None:
                raise ValueError
            age = (now - observed).total_seconds()
            if age < -5 or age > max_age:
                raise PolicyError("stale_metadata", "Evidence is stale or future-dated")
            if "value" not in fact or fact["value"] is None:
                raise PolicyError("missing_trusted_metadata", "Required fact has no known value")
            values[field] = fact["value"]
        return [predicate_result(p, values[p["field"]]) for p in binding["predicates"]]
    except PolicyError:
        raise
    except (ValueError, TypeError, KeyError, RecursionError):
        raise PolicyError("invalid_metadata", "Invalid verified evidence") from None
