"""Compile a root-contained Markdown include graph into an immutable snapshot."""

import hashlib
import os
import posixpath
import stat
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath

from .contracts import validate_contract
from .errors import PolicyError
from .serialization import digest, parse_yaml

COMPILER = "humanwill.bundle/1"


@dataclass(frozen=True)
class Limits:
    file_bytes: int = 65_536
    bundle_bytes: int = 1_048_576
    files: int = 128
    policies: int = 100
    depth: int = 16
    includes: int = 128

    def __post_init__(self):
        # Upper bounds prevent configuration from bypassing parser/resource ceilings.
        ceilings = {
            "file_bytes": 1_048_576,
            "bundle_bytes": 8_388_608,
            "files": 512,
            "policies": 500,
            "depth": 32,
            "includes": 512,
        }
        for key, value in asdict(self).items():
            if type(value) is not int or not 1 <= value <= ceilings[key]:
                raise PolicyError("invalid_limit", f"Invalid limit: {key}")


@dataclass(frozen=True)
class Source:
    path: str
    sha256: str
    text: str


@dataclass(frozen=True)
class Policy:
    id: str
    version: str
    title: str
    stages: tuple[str, ...]
    path: str
    sha256: str
    body: str


@dataclass(frozen=True)
class Bundle:
    id: str
    version: str
    entrypoint: str
    sources: tuple[Source, ...]
    policies: tuple[Policy, ...]
    sha256: str
    limits: Limits

    def snapshot(self) -> dict:
        return {
            "format": COMPILER,
            "id": self.id,
            "version": self.version,
            "entrypoint": self.entrypoint,
            "sha256": self.sha256,
            "sources": [asdict(source) for source in self.sources],
            "policies": [asdict(policy) for policy in self.policies],
        }


def _relative(parent: str, target: str) -> str:
    if (
        not target
        or "\\" in target
        or ":" in target
        or "\x00" in target
        or target.startswith("/")
        or "#" in target
        or "?" in target
    ):
        raise PolicyError("invalid_path", "Expected a relative Markdown path", parent)
    result = posixpath.normpath(posixpath.join(posixpath.dirname(parent), target))
    if result == ".." or result.startswith("../"):
        raise PolicyError("path_escape", "Include leaves the policy root", parent)
    if PurePosixPath(result).suffix != ".md":
        raise PolicyError("invalid_path", "Only .md includes are supported", parent)
    return result


def _read(root_fd: int, relative: str, limit: int) -> bytes:
    """Open every path component beneath a stable root fd; reject all symlinks."""
    current = os.dup(root_fd)
    try:
        parts = PurePosixPath(relative).parts
        for part in parts[:-1]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current)
            os.close(current)
            current = next_fd
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=current)
        with os.fdopen(fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise PolicyError("invalid_file", "Policy source must be a regular file", relative)
            data = stream.read(limit + 1)
            after = os.fstat(stream.fileno())
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise PolicyError("source_changed", "Source changed during loading", relative)
            if len(data) > limit:
                raise PolicyError(
                    "file_limit", "Policy source exceeds the file byte limit", relative
                )
            return data
    except OSError:
        raise PolicyError(
            "unreadable_source", "Missing, unreadable, or symlinked source", relative
        ) from None
    finally:
        os.close(current)


def _document(data: bytes, path: str) -> tuple[dict, str, str]:
    try:
        text = data.decode("utf-8")
    except UnicodeError:
        raise PolicyError("invalid_encoding", "Policy files must be UTF-8", path) from None
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        raise PolicyError("missing_front_matter", "File must start with ---", path)
    end = next((i for i in range(1, len(lines)) if lines[i].rstrip("\r\n") == "---"), None)
    if end is None:
        raise PolicyError("missing_front_matter", "Missing closing ---", path)
    header = parse_yaml("".join(lines[1:end]), path)
    kind = header.get("kind")
    if kind not in ("policy", "collection"):
        raise PolicyError("unknown_kind", "Expected policy or collection", path)
    validate_contract(kind, header, path)
    body = "".join(lines[end + 1 :])
    if kind == "policy" and not body.strip():
        raise PolicyError("empty_policy", "Policy body cannot be empty", path)
    return header, body, text


def load_bundle(
    root: str | Path, entrypoint: str = "policies.md", limits: Limits | None = None
) -> Bundle:
    limits = limits or Limits()
    entry = _relative("", entrypoint)
    sources: dict[str, Source] = {}
    policies: list[Policy] = []
    headers: dict[str, dict] = {}
    active: list[str] = []
    ids: dict[str, str] = {}
    total_bytes = 0
    try:
        root_fd = os.open(Path(root).resolve(strict=True), os.O_RDONLY | os.O_DIRECTORY)
    except OSError:
        raise PolicyError("invalid_root", "Policy root must be an existing directory") from None

    def visit(path: str, depth: int):
        nonlocal total_bytes
        if depth > limits.depth:
            raise PolicyError("depth_limit", "Include nesting exceeds configured depth", path)
        if path in active:
            raise PolicyError("include_cycle", "Include cycle: " + " -> ".join([*active, path]))
        if path in sources:
            return
        if len(sources) >= limits.files:
            raise PolicyError("file_count_limit", "Too many source files")
        data = _read(root_fd, path, limits.file_bytes)
        total_bytes += len(data)
        if total_bytes > limits.bundle_bytes:
            raise PolicyError("bundle_limit", "Bundle exceeds total byte limit")
        header, body, text = _document(data, path)
        if header["id"] in ids:
            raise PolicyError("duplicate_id", f"ID already defined in {ids[header['id']]}", path)
        ids[header["id"]] = path
        headers[path] = header
        source_hash = hashlib.sha256(data).hexdigest()
        sources[path] = Source(path, source_hash, text)
        active.append(path)
        if header["kind"] == "collection":
            if len(header["includes"]) > limits.includes:
                raise PolicyError("include_limit", "Too many includes in collection", path)
            for target in header["includes"]:
                visit(_relative(path, target), depth + 1)
        else:
            if len(policies) >= limits.policies:
                raise PolicyError("policy_limit", "Too many policies")
            policies.append(
                Policy(
                    header["id"],
                    header["version"],
                    header["title"],
                    tuple(sorted(header["stages"])),
                    path,
                    source_hash,
                    body,
                )
            )
        active.pop()

    try:
        visit(entry, 0)
    finally:
        os.close(root_fd)
    if headers[entry]["kind"] != "collection":
        raise PolicyError("invalid_entrypoint", "Entrypoint must be a collection", entry)
    if not policies:
        raise PolicyError("empty_bundle", "Bundle must include at least one policy", entry)
    ordered_sources = tuple(sources[path] for path in sorted(sources))
    bundle_hash = digest(
        {
            "format": COMPILER,
            "entrypoint": entry,
            "sources": [{"path": s.path, "sha256": s.sha256} for s in ordered_sources],
        }
    )
    return Bundle(
        headers[entry]["id"],
        headers[entry]["version"],
        entry,
        ordered_sources,
        tuple(sorted(policies, key=lambda policy: policy.id)),
        bundle_hash,
        limits,
    )
