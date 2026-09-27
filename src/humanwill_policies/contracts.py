"""Offline JSON schema validation; schemas contain only local references."""

import json
from datetime import datetime
from importlib.resources import files

from jsonschema import Draft202012Validator

from .errors import PolicyError
from .serialization import canonical, json_value

SCHEMAS = (
    "policy",
    "collection",
    "config",
    "config-v2",
    "config-v3",
    "request",
    "result",
    "result-v2",
    "result-v3",
    "service",
)
STAGES = ("prompt", "model_request", "response", "tool_action")
MAX_REQUEST_BYTES = 262_144


def schema(name: str) -> dict:
    if name not in SCHEMAS:
        raise PolicyError("unknown_schema", "Unknown schema name", name)
    return json.loads(files("humanwill_policies").joinpath(f"schemas/{name}.json").read_text())


def validate_contract(name: str, value: object, location: str = "") -> None:
    json_value(value)
    if name in ("config", "result") and isinstance(value, dict):
        for version in (2, 3):
            if value.get("format") == f"humanwill.{name}/{version}":
                name += f"-v{version}"
                break
    kind = name.removesuffix("-v2").removesuffix("-v3")
    if kind in ("request", "result") and len(canonical(value).encode()) > MAX_REQUEST_BYTES:
        raise PolicyError("payload_limit", "Payload exceeds 262144 canonical JSON bytes", location)
    validator = Draft202012Validator(schema(name))
    error = next(validator.iter_errors(value), None)
    if error:
        path = "/".join(str(part) for part in error.absolute_path)
        raise PolicyError(
            "schema_error", f"Schema rule {error.validator} failed at /{path}", location
        )
    if kind in ("request", "result"):
        if value["coverage"]["complete"] and value["coverage"]["omitted"]:
            raise PolicyError(
                "invalid_coverage", "Complete coverage cannot include omissions", location
            )
    if name == "request":
        ids = [part["id"] for part in value["content"]]
        if len(ids) != len(set(ids)):
            raise PolicyError("duplicate_content_id", "Content IDs must be unique", location)
        if set(value["coverage"]["inspected"]) != set(ids):
            raise PolicyError(
                "invalid_coverage", "Inspected IDs must match supplied content", location
            )
        for fact in value.get("metadata", []):
            try:
                observed = datetime.fromisoformat(fact["observed_at"])
                if observed.tzinfo is None or "T" not in fact["observed_at"]:
                    raise ValueError
            except ValueError:
                raise PolicyError(
                    "invalid_timestamp", "Evidence needs an ISO timestamp with timezone", location
                ) from None
        if value["stage"] == "tool_action" and not any(
            part["kind"] == "tool_action" for part in value["content"]
        ):
            raise PolicyError(
                "missing_action", "A tool_action event needs a proposed action", location
            )
    elif kind == "result":
        ids = [part["policy_id"] for part in value["policies"]]
        if len(ids) != len(set(ids)):
            raise PolicyError("duplicate_policy_id", "Result policy IDs must be unique", location)
