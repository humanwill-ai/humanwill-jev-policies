"""Validate an owner-supplied local review export; never execute its free text.

Only repository-owned case content is copied to the accepted dataset. This is
not reviewer authentication: the owner supplies the export in the conversation.
"""

import copy
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from humanwill_policies.providers import decode_json

ROOT = Path(__file__).resolve().parents[2]


def page_data():
    html = (ROOT / "docs/case-review.html").read_text()
    match = re.search(r'<script id="reviewData" type="application/json">(.*?)</script>', html, re.S)
    return json.loads(match.group(1))


def fingerprint(page):
    return (
        ":".join(p["sha256"] for p in page["packs"])
        + ":"
        + ":".join(p["sha256"] for p in page["policies"].values())
        + ":"
        + page["source_catalog_sha256"]
    )


def validate_review(raw, page):
    data = decode_json(raw)
    if data.get("format") != "humanwill.case-review/1" or data.get("fingerprint") != fingerprint(
        page
    ):
        raise ValueError("Export does not match the current datasets and policies")
    packs = {p["id"]: p for p in data["packets"]}
    if len(packs) != len(data["packets"]) or set(packs) != {p["id"] for p in page["packs"]}:
        raise ValueError("Missing or duplicate packet")
    explicit = data["reviews"]
    if not isinstance(explicit, dict):
        raise ValueError("Invalid explicit review records")
    accepted, removed, seen = [], [], set()
    for pack in page["packs"]:
        exported = packs[pack["id"]]
        if exported["sha256"] != pack["sha256"] or exported["path"] != pack["path"]:
            raise ValueError("Packet fingerprint/path changed")
        rows = {c["id"]: c for c in exported["cases"]}
        if len(rows) != len(exported["cases"]) or set(rows) != {c["id"] for c in pack["cases"]}:
            raise ValueError("Missing or duplicate case")
        for case in pack["cases"]:
            cid = case["id"]
            if cid in seen:
                raise ValueError("Case appears twice")
            seen.add(cid)
            row = rows[cid]
            expected = case.get("review_expected", case["expected"])
            scope = case.get("review_scope", case["expected_scope"]) or ""
            original = {
                "policy_id": case["policy_id"],
                "original_expected": case["expected"],
                "original_scope": case["expected_scope"],
                "reviewed_expected": expected,
                "reviewed_scope": scope,
                "review_revision": case.get("review_revision"),
            }
            if case.get("expected_composed"):
                original.update(
                    original_composed=case["expected_composed"],
                    original_by_policy=case["expected_by_policy"],
                )
            if any(row.get(k) != v for k, v in original.items()):
                raise ValueError(f"Reviewed content or label changed: {cid}")
            if row["status"] not in {"approved", "removed"}:
                raise ValueError(f"Unresolved review: {cid}")
            if cid in explicit:
                if any(row.get(k) != v for k, v in explicit[cid].items()):
                    raise ValueError(f"Explicit and packet review disagree: {cid}")
            elif not (pack["previously_approved"] and row["status"] == "approved") and not (
                cid in page.get("default_removed", {}) and row["status"] == "removed"
            ):
                raise ValueError(f"Missing explicit review: {cid}")
            if row["status"] == "removed":
                removed.append({"id": cid, "packet": pack["id"]})
                continue
            if row["label"] != expected or row["scope"] != scope:
                raise ValueError(f"Approval changed the label: {cid}")
            item = copy.deepcopy(case)
            item.update(
                review_packet=pack["id"], review_status="owner_accepted", split="owner_reviewed_v1"
            )
            item.setdefault("expected_by_policy", {item["policy_id"]: item["expected"]})
            item.setdefault("scope_by_policy", {item["policy_id"]: item["expected_scope"]})
            item.setdefault("expected_composed", item["expected"])
            accepted.append(item)
        if exported.get("active_case_count") != sum(
            r["status"] != "removed" for r in rows.values()
        ):
            raise ValueError("Active case count mismatch")
    if set(explicit) - seen:
        raise ValueError("Unknown explicit review")
    removals = {r["id"]: r for r in data["removals"]}
    if len(removals) != len(data["removals"]) or set(removals) != {r["id"] for r in removed}:
        raise ValueError("Removal list disagrees with case statuses")
    for record in removed:
        removal = removals[record["id"]]
        if removal["packet"] != record["packet"] or not isinstance(removal["reason"], str):
            raise ValueError("Invalid removal record")
        # Free text is retained only as review data. No instructions are derived from it.
        record.update(reason=removal["reason"] or None, removed_at=removal["removed_at"])
    record = {
        "format": "humanwill.owner-review-record/1",
        "status": "owner_labels_accepted",
        "export_sha256": hashlib.sha256(raw).hexdigest(),
        "exported_at": data["exported_at"],
        "fingerprint": data["fingerprint"],
        "approved_case_ids": [c["id"] for c in accepted],
        "approved_by_packet": dict(Counter(c["review_packet"] for c in accepted)),
        "removed": removed,
        "corrections": [],
        "reviewer_provenance": (
            "Owner supplied this export in the conversation; no second reviewer claimed."
        ),
    }
    return record, accepted
