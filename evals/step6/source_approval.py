"""Offline reference matcher for operator-owned synthetic source fixtures.

No command parsing, network resolution, identity authentication or host enforcement.
Descriptors must come from a trusted resolver, never from request/model assertions.
"""

import copy
import json
from pathlib import Path
from urllib.parse import urlsplit

import yaml

from humanwill_policies.contracts import validate_contract
from humanwill_policies.runtime import EvidenceContext
from humanwill_policies.serialization import digest

from .run import evidence_for

ROOT = Path(__file__).parent
OPERATIONS = {"download", "install", "update", "execute"}
KINDS = {"git", "npm", "python", "oci", "https_file"}
REGISTRIES = {"npm", "python", "oci"}


def endpoint(value):
    """Require canonical explicit HTTPS identifiers; do not normalize ambiguous input."""
    if not isinstance(value, str) or not value or not value.isascii():
        raise ValueError("Source endpoint must be an ASCII HTTPS identifier")
    if any(c.isspace() or c in "\\%*" for c in value):
        raise ValueError("Ambiguous source endpoint")
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.netloc != parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.hostname.endswith(".")
        or any(part in {".", ".."} for part in parsed.path.split("/"))
        or "//" in parsed.path
        or parsed.path.endswith("/")
        or value != "https://" + parsed.hostname + parsed.path
    ):
        raise ValueError("Use exact canonical HTTPS endpoints without credentials or aliases")
    return value


def validate_catalog(data):
    if not isinstance(data, dict) or set(data) != {"format", "id", "version", "default", "sources"}:
        raise ValueError("Invalid approved-source catalog")
    if data["format"] != "humanwill.approved-sources/1" or data["default"] != "deny":
        raise ValueError("Source catalog must default to deny")
    if not all(isinstance(data[k], str) and data[k].strip() for k in ("id", "version")):
        raise ValueError("Catalog needs an ID and string version")
    if not isinstance(data["sources"], list):
        raise ValueError("Sources must be a list")
    ids = set()
    for entry in data["sources"]:
        if not isinstance(entry, dict):
            raise ValueError("Invalid source entry")
        required = {"id", "kind", "endpoint", "operations"}
        if set(entry) - (required | {"packages"}) or required - set(entry):
            raise ValueError("Invalid source fields")
        if not isinstance(entry["id"], str) or not entry["id"].strip() or entry["id"] in ids:
            raise ValueError("Source IDs must be nonempty and unique")
        ids.add(entry["id"])
        if entry["kind"] not in KINDS:
            raise ValueError("Unknown source kind")
        endpoint(entry["endpoint"])
        ops = entry["operations"]
        if not isinstance(ops, list) or not ops or any(o not in OPERATIONS for o in ops):
            raise ValueError("Invalid permitted operations")
        packages = entry.get("packages")
        if entry["kind"] in REGISTRIES:
            if packages != "all" and (
                not isinstance(packages, list)
                or not packages
                or any(not isinstance(p, str) or not p.strip() or "*" in p for p in packages)
            ):
                raise ValueError("Registries need exact package names or explicit 'all'")
        elif packages is not None:
            raise ValueError("Package restrictions apply only to registries")
    return data


def load_catalog(path=ROOT / "sources-v1/approved-sources.yaml"):
    # Fixture loader only; production configuration needs bounded duplicate-key-safe parsing.
    return validate_catalog(yaml.safe_load(path.read_text()))


def load_source_cases(path=ROOT / "sources-v1/candidates.json"):
    """Keep source-aware review fixtures separate from the frozen live runner."""
    data = json.loads(path.read_text())
    if data.get("format") != "humanwill.eval-dataset/1" or data.get("synthetic") is not True:
        raise ValueError("Expected a synthetic review dataset")
    ids, seen = set(), {}
    for case in data["cases"]:
        validate_contract("request", case["request"])
        if (
            case["id"] in ids
            or case["id"] != case["request"]["request_id"]
            or case["split"] != "review_candidate"
            or case["expected"] not in {"allow", "block", "evaluation_error"}
            or case["expected_scope"]
            not in {"applicable", "not_applicable", "insufficient_evidence"}
            or not case["rationale"]
            or not case["family"]
        ):
            raise ValueError("Invalid source review case")
        ids.add(case["id"])
        request = copy.deepcopy(case["request"])
        request.pop("request_id")
        key = digest(
            {
                "request": request,
                "policy": case["policy_id"],
                "facts": case["trusted_facts"],
                "source_context": case["source_context"],
                "disclosure_context": case.get("disclosure_context"),
            }
        )
        if key in seen and seen[key] != case["expected"]:
            raise ValueError("Identical source evidence has conflicting labels")
        seen[key] = case["expected"]
    return data["cases"]


def source_facts(context, catalog):
    """All resources must match. A completed empty lookup never grants approval."""
    validate_catalog(catalog)
    if not isinstance(context, dict) or set(context) != {"resolution", "resources"}:
        raise ValueError("Invalid trusted source-resolution context")
    if context["resolution"] not in {"complete", "unavailable"}:
        raise ValueError("Unknown source-resolution state")
    if not isinstance(context["resources"], list):
        raise ValueError("Resources must be a list")
    matched = []
    for resource in context["resources"]:
        if not isinstance(resource, dict) or set(resource) != {
            "kind",
            "endpoint",
            "operation",
            "package",
        }:
            raise ValueError("Invalid resolved resource")
        if resource["kind"] not in KINDS or resource["operation"] not in OPERATIONS:
            raise ValueError("Invalid resolved kind or operation")
        endpoint(resource["endpoint"])
        if resource["kind"] in REGISTRIES:
            if not isinstance(resource["package"], str) or not resource["package"].strip():
                raise ValueError("Resolved package identity is required")
        elif resource["package"] is not None:
            raise ValueError("Non-registry resource must have null package")
        matched.append(
            any(
                e["kind"] == resource["kind"]
                and e["endpoint"] == resource["endpoint"]
                and resource["operation"] in e["operations"]
                and (
                    resource["kind"] not in REGISTRIES
                    or e["packages"] == "all"
                    or resource["package"] in e["packages"]
                )
                for e in catalog["sources"]
            )
        )
    if context["resolution"] == "unavailable":
        return {}
    return {"authorization.software_sources_approved": bool(matched) and all(matched)}


def source_evidence_for(case, catalog):
    """Bind derived synthetic source approvals to an exact event alongside existing facts."""
    prepared = copy.deepcopy(case)
    prepared["trusted_facts"].pop("authorization.software_sources_approved", None)
    if "source_context" in case:
        prepared["trusted_facts"].update(source_facts(case["source_context"], catalog))
    context = evidence_for(prepared)
    return EvidenceContext.from_verified(case["request"], json.loads(context.facts_json))
