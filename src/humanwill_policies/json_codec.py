"""Bounded JSON decoding and stable hashes shared by service and hook client."""

import hashlib
import json
import math

from .errors import PolicyError


def canonical(value: object) -> str:
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def json_value(value: object, depth: int = 0) -> None:
    if depth > 24:
        raise PolicyError("depth_limit", "Structured data exceeds depth 24")
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float and math.isfinite(value):
        return
    if isinstance(value, list):
        for item in value:
            json_value(item, depth + 1)
        return
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        for item in value.values():
            json_value(item, depth + 1)
        return
    raise PolicyError("invalid_value", "Only finite JSON-compatible values are supported")


def decode_json(data: bytes) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError
            result[key] = value
        return result

    try:
        result = json.loads(data, object_pairs_hook=pairs)
        json_value(result)
        if not isinstance(result, dict):
            raise ValueError
        return result
    except (ValueError, UnicodeError, RecursionError, PolicyError):
        raise PolicyError("malformed_json", "Invalid JSON object") from None
