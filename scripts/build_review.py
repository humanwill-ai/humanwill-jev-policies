"""Build a standalone offline review page from the frozen evaluation packets."""

import hashlib
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "scripts/review"


def build():
    packs = []
    for key, title, path, approved in [
        ("holdout", "New 100 cases", "evals/step6/release/holdout-v1.json", False),
        ("previous", "Previously approved 36", "evals/step6/prospective/candidates-v1.json", True),
    ]:
        raw = (ROOT / path).read_bytes()
        expected_hash = (
            "06b8baa96cf62d956fbcbc12114ca4bdd1293db763d6945a0d574b71314b8a62"
            if approved
            else json.loads((ROOT / "evals/step6/release/holdout-v1-protocol.json").read_text())[
                "dataset_sha256"
            ]
        )
        if hashlib.sha256(raw).hexdigest() != expected_hash:
            raise ValueError(f"Dataset changed; review its provenance before rebuilding: {path}")
        packs.append(
            {
                "id": key,
                "title": title,
                "path": path,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "previously_approved": approved,
                "approval_date": "2026-09-27" if approved else None,
                "cases": json.loads(raw)["cases"],
            }
        )
    policies = {}
    for path in sorted((ROOT / "evals/step6/policies-v2").glob("*.md")):
        source = path.read_text()
        _, front, body = source.split("---", 2)
        meta = yaml.safe_load(front)
        if meta["kind"] == "policy":
            policies[meta["id"]] = {
                **meta,
                "body": body.strip(),
                "source": source,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
    legacy_fingerprint = (
        ":".join(p["sha256"] for p in packs)
        + ":"
        + ":".join(p["sha256"] for p in policies.values())
    )
    source_path = ROOT / "evals/step6/sources-v1/candidates.json"
    snapshot = json.loads((source_path.parent / "snapshot.json").read_text())
    for path, expected in snapshot["sha256"].items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Source review snapshot changed: {path}")
    packs.append(
        {
            "id": "sources",
            "title": "Approved sources · 46",
            "path": str(source_path.relative_to(ROOT)),
            "sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
            "previously_approved": False,
            "approval_date": None,
            "cases": json.loads(source_path.read_text())["cases"],
        }
    )
    path = ROOT / "evals/step6/policies-sources-v1/approved-sources.md"
    source = path.read_text()
    _, front, body = source.split("---", 2)
    meta = yaml.safe_load(front)
    policies[meta["id"]] = {
        **meta,
        "body": body.strip(),
        "source": source,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    catalog_path = source_path.parent / "approved-sources.yaml"
    catalog_hash = hashlib.sha256(catalog_path.read_bytes()).hexdigest()
    previous_fingerprint = (
        ":".join(p["sha256"] for p in packs)
        + ":"
        + ":".join(p["sha256"] for p in policies.values())
        + ":"
        + catalog_hash
    )
    original_labels = {
        c["id"]: {"expected": c["expected"], "expected_scope": c["expected_scope"]}
        for c in packs[0]["cases"]
    }
    revised = ROOT / "evals/step6/release/holdout-sources-v2.json"
    revised_snapshot = json.loads((revised.parent / "holdout-sources-v2-snapshot.json").read_text())
    for path, expected in revised_snapshot["sha256"].items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Revised 100-case snapshot changed: {path}")
    revised_data = json.loads(revised.read_text())
    # Preserve approvals of unchanged cases from the preceding source-aware packet.
    compatible_fingerprint = (
        ":".join([revised_data["previous_dataset_sha256"], *[p["sha256"] for p in packs[1:]]])
        + ":"
        + ":".join(p["sha256"] for p in policies.values())
        + ":"
        + catalog_hash
    )
    removed = revised_data.get("removed_cases", [])
    packs[0].update(
        title="Updated packet · sources v2.1",
        path=str(revised.relative_to(ROOT)),
        sha256=hashlib.sha256(revised.read_bytes()).hexdigest(),
        cases=revised_data["cases"] + [r["case"] for r in removed],
    )
    default_removed = {r["id"]: {k: v for k, v in r.items() if k != "case"} for r in removed}
    recorded_approvals = []
    recorded_approval_at = None
    review_path = ROOT / "evals/step6/release/owner-review-v1.json"
    if review_path.exists():
        protocol = json.loads((review_path.parent / "reviewed-live-v1-protocol.json").read_text())
        if (
            hashlib.sha256(review_path.read_bytes()).hexdigest()
            != protocol["sha256"][str(review_path.relative_to(ROOT))]
        ):
            raise ValueError("Recorded owner review changed")
        record = json.loads(review_path.read_text())
        recorded_approvals = record["approved_case_ids"]
        recorded_approval_at = record["exported_at"]
        for removal in record["removed"]:
            default_removed[removal["id"]] = {
                **removal,
                "reason": removal["reason"] or "",
                "authority": "owner_review_export",
            }
    context_root = ROOT / "evals/step6/context-v1"
    context_snapshot = json.loads((context_root / "snapshot.json").read_text())
    for name, expected in context_snapshot["sha256"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Context snapshot changed: {name}")
    context_path = context_root / "contexts.json"
    context_pack = json.loads(context_path.read_text())
    context_cases = context_pack["cases"]
    if [c["id"] for c in context_cases] != recorded_approvals:
        raise ValueError("Context cases do not match the accepted review")
    scope_config = yaml.safe_load((ROOT / "evals/step6/config-sources-v1.yaml").read_text())
    release_scope_path = ROOT / "evals/step6/release-scope-v1/manifest.json"
    release_scope = json.loads(release_scope_path.read_text())
    if (
        [c["id"] for c in release_scope["cases"]] != recorded_approvals
        or hashlib.sha256((ROOT / release_scope["dataset"]).read_bytes()).hexdigest()
        != release_scope["dataset_sha256"]
        or hashlib.sha256((ROOT / "evals/step6/release_scope.py").read_bytes()).hexdigest()
        != release_scope["selector_sha256"]
    ):
        raise ValueError("Release-scope manifest changed")
    active_pack = json.loads((ROOT / "evals/step6/release/active-pack.json").read_text())
    for removal in active_pack["removals"]:
        default_removed[removal["id"]] = removal
    active_removals = {r["id"]: r for r in active_pack["removals"]}
    # Preserve prior labels/progress under the owner's explicit policy clarification.
    active_previous_fingerprint = (
        ":".join(p["sha256"] for p in packs)
        + ":"
        + ":".join(p["sha256"] for p in policies.values())
        + ":"
        + catalog_hash
    )
    if "policy_directory" in active_pack:
        for path in sorted((ROOT / active_pack["policy_directory"]).glob("*.md")):
            source = path.read_text()
            _, front, body = source.split("---", 2)
            meta = yaml.safe_load(front)
            if meta["kind"] == "policy":
                policies[meta["id"]] = {
                    **meta,
                    "body": body.strip(),
                    "source": source,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
    data = json.dumps(
        {
            "packs": packs,
            "policies": policies,
            "legacy_fingerprint": legacy_fingerprint,
            "previous_fingerprint": previous_fingerprint,
            "compatible_fingerprint": compatible_fingerprint,
            "active_previous_fingerprint": active_previous_fingerprint,
            "active_previous_fingerprints": active_pack.get("review_previous_fingerprints", []),
            "default_removed": default_removed,
            "active_removals": active_removals,
            "owner_removals_revision": active_pack["revision"],
            "recorded_approvals": recorded_approvals,
            "recorded_approval_at": recorded_approval_at,
            "original_labels": original_labels,
            "source_catalog": catalog_path.read_text(),
            "source_catalog_sha256": catalog_hash,
            "question_contexts": {c["id"]: c["context"] for c in context_cases},
            "question_context_sha256": hashlib.sha256(context_path.read_bytes()).hexdigest(),
            "release_scope": release_scope,
            "release_scope_sha256": hashlib.sha256(release_scope_path.read_bytes()).hexdigest(),
            "scope_questions": {
                pid: binding.get("scope_by_stage", {})
                for pid, binding in scope_config["policies"].items()
            },
        },
        ensure_ascii=False,
    )
    # Keep embedded content inert even if a future fixture contains HTML/script delimiters.
    data = data.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    html = (TEMPLATE / "page.html").read_text()
    for marker, value in [
        ("/* STYLE */", (TEMPLATE / "style.css").read_text()),
        ("/* APP */", (TEMPLATE / "app.js").read_text()),
        ("__DATA__", data),
    ]:
        html = html.replace(marker, value)
    output = ROOT / "docs/case-review.html"
    output.write_text(html)
    print(
        f"Built {output}: {sum(len(p['cases']) for p in packs) - len(default_removed)} active cases"
    )


if __name__ == "__main__":
    build()
