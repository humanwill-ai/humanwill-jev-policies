"""Embed current schemas; reject unsupported validation keywords at build time."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUPPORTED = {
    "$id",
    "$schema",
    "title",
    "format",
    "type",
    "const",
    "enum",
    "oneOf",
    "properties",
    "required",
    "additionalProperties",
    "items",
    "uniqueItems",
    "minItems",
    "maxItems",
    "minLength",
    "maxLength",
    "maxProperties",
    "minimum",
    "maximum",
    "pattern",
}
PATTERNS = {
    r"\S",
    r"^[a-f0-9]{64}$",
    r"^[A-Za-z][A-Za-z0-9._-]{0,127}$",
    r"^(identity|documents|destination|environment|authorization)\.[a-z][a-z0-9_]{0,63}$",
}


def check(schema):
    if set(schema) - SUPPORTED:
        raise ValueError("Unsupported schema keyword")
    if "pattern" in schema and schema["pattern"] not in PATTERNS:
        raise ValueError("Unsupported schema pattern")
    for value in schema.get("properties", {}).values():
        check(value)
    for key in ("items", "additionalProperties"):
        if isinstance(schema.get(key), dict):
            check(schema[key])
    for value in schema.get("oneOf", []):
        check(value)


lines = ["/* Generated from the canonical repository schemas. */"]
for name in ("request", "result-v2", "result-v3", "result-v4"):
    data = json.loads((ROOT / "src/humanwill_policies/schemas" / (name + ".json")).read_text())
    check(data)
    payload = json.dumps(data, separators=(",", ":")).encode()
    values = ",".join(str(v) for v in payload + b"\0")
    lines.append(f"static const char schema_{name.replace('-', '_')}[] = {{{values}}};")
Path(sys.argv[1]).write_text("\n".join(lines) + "\n")
