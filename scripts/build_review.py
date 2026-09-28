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
    data = json.dumps(
        {
            "packs": packs,
            "policies": policies,
            "legacy_fingerprint": legacy_fingerprint,
            "source_catalog": catalog_path.read_text(),
            "source_catalog_sha256": hashlib.sha256(catalog_path.read_bytes()).hexdigest(),
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
    print(f"Built {output}: {sum(len(p['cases']) for p in packs)} cases")


if __name__ == "__main__":
    build()
