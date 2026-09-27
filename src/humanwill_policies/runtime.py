"""Deployment limits and explicit in-process trust boundaries (never wire assertions)."""

from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from .errors import PolicyError
from .serialization import canonical, digest, json_value


@dataclass(frozen=True)
class EvaluationLimits:
    timeout_ms: int = 5000
    max_batch_bytes: int = 24000
    max_response_bytes: int = 262144
    questions_per_batch: int = 16
    max_batches: int = 8
    max_in_flight: int = 4
    metadata_max_age_seconds: int = 300

    def __post_init__(self):
        bounds = {
            "timeout_ms": (1, 60000),
            "max_batch_bytes": (512, 262144),
            "max_response_bytes": (512, 1048576),
            "questions_per_batch": (1, 64),
            "max_batches": (1, 64),
            "max_in_flight": (1, 32),
            "metadata_max_age_seconds": (1, 86400),
        }
        for key, value in asdict(self).items():
            low, high = bounds[key]
            if type(value) is not int or not low <= value <= high:
                raise PolicyError("invalid_limit", f"Invalid evaluation limit: {key}")


@dataclass(frozen=True)
class EvidenceContext:
    """Created by a trusted embedding verifier, not deserialized from request metadata.

    The verifier must authenticate sources, subjects, document versions and completeness.
    The digest binds the verified facts to the exact event (including route/action data).
    No network lookup, authentication protocol, or signature verifier lives in this class.
    """

    request_sha256: str
    facts_json: str

    @classmethod
    def from_verified(cls, request: dict, facts: list[dict]):
        json_value(facts)
        if len(canonical(facts).encode()) > 65536:
            raise PolicyError("evidence_limit", "Verified evidence exceeds 65536 bytes")
        return cls(digest(request), canonical(facts))


@dataclass(frozen=True)
class EgressPermit:
    """A trusted caller's authorization to disclose this request AND bundle on one route."""

    request_sha256: str
    bundle_sha256: str
    transport: str

    def matches(self, request: dict, bundle_sha256: str, transport: str) -> bool:
        return (self.request_sha256, self.bundle_sha256, self.transport) == (
            digest(request),
            bundle_sha256,
            transport,
        )


def utc_now() -> datetime:
    return datetime.now(UTC)
