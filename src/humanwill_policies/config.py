"""Validate deployment bindings without contacting providers or identity services."""

import json
import os
import stat
from dataclasses import asdict, dataclass
from pathlib import Path

from .bundle import Bundle, Limits, load_bundle
from .contracts import STAGES, validate_contract
from .errors import PolicyError
from .serialization import canonical, digest, parse_yaml

# Contract targets, not implemented connector capabilities.
ASSESS_STAGES = {
    "litellm": {"model_request", "response"},
    "agentgateway": {"model_request", "response"},
    "copilot_local": {"prompt", "tool_action"},
    "copilot_cli": {"prompt", "tool_action"},
}
ENFORCE_STAGES = {**ASSESS_STAGES, "copilot_cli": {"tool_action"}}


@dataclass(frozen=True)
class Configuration:
    """Canonical JSON keeps nested configuration immutable, too."""

    json: str
    sha256: str
    bundle_sha256: str

    def to_dict(self) -> dict:
        return json.loads(self.json)


def read_configuration(path: str | Path) -> dict:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise PolicyError("invalid_config", "Configuration must be a regular file")
            data = stream.read(65_537)
        if len(data) > 65_536:
            raise PolicyError("config_limit", "Configuration exceeds 65536 bytes")
        document = parse_yaml(data.decode("utf-8"), "configuration")
    except (OSError, UnicodeError):
        raise PolicyError("invalid_config", "Cannot read UTF-8 configuration") from None
    validate_contract("config", document, "configuration")
    return document


def load_configuration(bundle: Bundle, document: dict) -> Configuration:
    validate_contract("config", document, "configuration")
    # Copy into JSON primitives; never mutate the caller's document.
    effective = json.loads(canonical(document))
    v2 = effective["format"] == "humanwill.config/2"
    if v2:
        from .runtime import EvaluationLimits

        effective["evaluation"] = asdict(EvaluationLimits(**effective.get("evaluation", {})))
    expected = {policy.id for policy in bundle.policies}
    supplied = set(effective["policies"])
    if supplied != expected:
        raise PolicyError(
            "policy_bindings",
            "Bindings must name every policy exactly once; "
            f"missing={sorted(expected - supplied)}, unknown={sorted(supplied - expected)}",
        )
    effective.setdefault("connectors", [])
    effective["limits"] = asdict(Limits(**effective.get("limits", {})))
    if effective["limits"] != asdict(bundle.limits):
        raise PolicyError("limits_mismatch", "Reload the bundle with the configuration's limits")
    metadata = effective["metadata"]
    metadata.setdefault("sources", {})
    connectors = effective["connectors"]
    names = [connector["name"] for connector in connectors]
    if len(names) != len(set(names)):
        raise PolicyError("duplicate_connector", "Connector names must be unique")
    for connector in connectors:
        if not set(connector["stages"]) <= ASSESS_STAGES[connector["name"]]:
            raise PolicyError(
                "unsupported_stage",
                "Connector cannot assess the configured stage",
                connector["name"],
            )
        connector["stages"].sort()
    connectors.sort(key=lambda connector: connector["name"])
    for policy in bundle.policies:
        binding = effective["policies"][policy.id]
        binding.setdefault("mode", "monitor")
        binding.setdefault("on_error", "block")
        binding.setdefault("requires_metadata", [])
        binding.setdefault("predicates", [])
        if v2:
            strategy = binding["strategy"]
            binding.setdefault("monitor_min_confidence", 0.8)
            binding.setdefault("require_complete_coverage", True)
            binding.setdefault("when", [])
            if binding["when"] and strategy != "predicates":
                raise PolicyError(
                    "invalid_strategy", "When is only for deterministic predicates", policy.id
                )
            if (strategy == "scoped_predicates") != ("scope" in binding):
                raise PolicyError(
                    "invalid_strategy", "Only scoped predicates require scope", policy.id
                )
            if (strategy != "semantic") != bool(binding["predicates"]):
                raise PolicyError(
                    "invalid_strategy", "Predicate strategies require predicates", policy.id
                )
            if strategy == "semantic" and binding["requires_metadata"]:
                raise PolicyError(
                    "invalid_strategy", "Use predicates for required trusted facts", policy.id
                )
        binding["requires_metadata"].sort()
        required = set(binding["requires_metadata"])
        for predicate in binding["predicates"] + binding.get("when", []):
            if predicate["field"] not in required:
                raise PolicyError(
                    "undeclared_metadata", "Predicate field must be declared required", policy.id
                )
        if not binding["enabled"] or binding["mode"] == "monitor":
            continue
        semantic = not v2 or binding["strategy"] != "predicates"
        if semantic and ("evaluation_profile" not in binding or "provider" not in effective):
            raise PolicyError(
                "missing_profile", "Enforcement requires provider and evaluation profile", policy.id
            )
        if semantic and binding["evaluation_profile"]["model"] != effective["provider"]["model"]:
            raise PolicyError(
                "profile_model_mismatch", "Profile must match the configured model", policy.id
            )
        if required and not metadata["enabled"]:
            raise PolicyError("metadata_disabled", "Enforced policy requires metadata", policy.id)
        for field in required:
            source = metadata["sources"].get(field.split(".")[0])
            if not source or not source["enabled"]:
                raise PolicyError(
                    "metadata_source_disabled", "Enforced policy needs an enabled source", policy.id
                )
        for connector in connectors:
            applicable = set(policy.stages) & set(connector["stages"])
            if not applicable <= ENFORCE_STAGES[connector["name"]]:
                raise PolicyError(
                    "unsupported_enforcement",
                    "Stage is assessment-only on this connector",
                    f"{policy.id}:{connector['name']}",
                )
    return Configuration(
        canonical(effective),
        digest(
            {
                "format": "humanwill.effective-config/1",
                "bundle_sha256": bundle.sha256,
                "configuration": effective,
            }
        ),
        bundle.sha256,
    )


def load_project(
    root: str | Path, config: str | Path | None = None, entrypoint: str = "policies.md"
) -> tuple[Bundle, Configuration | None]:
    document = read_configuration(config) if config is not None else None
    limits = Limits(**document.get("limits", {})) if document is not None else Limits()
    bundle = load_bundle(root, entrypoint, limits)
    configuration = load_configuration(bundle, document) if document is not None else None
    return bundle, configuration


def preview(
    bundle: Bundle, configuration: Configuration | None = None, stage: str | None = None
) -> dict:
    if stage is not None and stage not in STAGES:
        raise PolicyError("unknown_stage", "Unsupported stage", stage)
    if configuration and configuration.bundle_sha256 != bundle.sha256:
        raise PolicyError("bundle_mismatch", "Configuration belongs to a different policy bundle")
    config = configuration.to_dict() if configuration else None
    rows = []
    for policy in bundle.policies:
        row = asdict(policy)
        row["issues"] = []
        binding = config["policies"][policy.id] if config else None
        if binding is None:
            row["status"] = "unconfigured"
        elif not binding["enabled"]:
            row["status"] = "disabled"
        elif stage and stage not in policy.stages:
            row["status"] = "not_applicable"
        else:
            row["status"] = binding["mode"]
            if binding["requires_metadata"]:
                if not config["metadata"]["enabled"]:
                    row["issues"].append("metadata_disabled")
                else:
                    for field in binding["requires_metadata"]:
                        source = config["metadata"]["sources"].get(field.split(".")[0])
                        if not source or not source["enabled"]:
                            row["issues"].append(f"metadata_source_disabled:{field}")
        rows.append(row)
    return {
        "format": "humanwill.preview/1",
        "runtime_available": False,
        "bundle": bundle.snapshot(),
        "configuration": config,
        "configuration_sha256": configuration.sha256 if configuration else None,
        "stage": stage,
        "policies": rows,
        "note": "Offline authoring/configuration validation only; no judgments or enforcement.",
    }
