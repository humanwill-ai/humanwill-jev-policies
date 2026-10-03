"""Project-scoped transcript preparation and non-blocking Codex prompt capture.

No API calls occur in prepare/capture. The reviewed packet and explicit egress
receipt are required by the separate live runner. Raw content stays local.
"""

import argparse
import fcntl
import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT / "artifacts/dogfood-v1"
MAX_CONTEXT_BYTES = 10000
MAX_PARTS = 5
MAX_CAPTURE = 100


def fingerprint(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    data = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    fd, name = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(data)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def messages(path, project):
    """Read one explicitly selected transcript; accept only native user.text/final replies.

    Never export tool output, reasoning, developer/system messages, injected context,
    compaction summaries or attachments. Unknown transcript shapes are not guessed.
    """
    records = []
    verified = False
    with Path(path).open() as stream:
        for number, line in enumerate(stream, 1):
            row = json.loads(line)
            item = row.get("payload", {})
            if row.get("type") == "session_meta":
                if Path(item.get("cwd", "")).resolve() != Path(project).resolve():
                    raise ValueError("Transcript is not scoped to the selected project")
                verified = True
            if not verified:
                raise ValueError("Missing project session metadata")
            if row.get("type") != "response_item" or item.get("type") != "message":
                continue
            role = item.get("role")
            if role == "user":
                metadata = item.get("internal_chat_message_metadata_passthrough") or {}
                if metadata.get("content_item_kinds") != ["user.text"]:
                    continue
                text_type = "input_text"
            elif role == "assistant" and item.get("phase") in ("final", "final_answer"):
                text_type = "output_text"
            else:
                continue
            content = item.get("content", [])
            if not content or any(
                c.get("type") != text_type or not isinstance(c.get("text"), str) for c in content
            ):
                continue
            text = "\n\n".join(c["text"] for c in content)
            records.append(
                {"line": number, "timestamp": row.get("timestamp"), "role": role, "text": text}
            )
    if not verified:
        raise ValueError("Missing session metadata")
    return records


def request_for(records, index, request_id):
    """Contiguous recent visible-text suffix only; never truncate or skip an oversized part."""
    selected = []
    used = 0
    for item in reversed(records[: index + 1]):
        size = len(item["text"].encode())
        if selected and (len(selected) == MAX_PARTS or used + size > MAX_CONTEXT_BYTES):
            break
        selected.append(item)
        used += size
        if used > MAX_CONTEXT_BYTES:
            break
    selected.reverse()
    parts = [
        {"id": f"part-{i}", "kind": "text", "role": x["role"], "text": x["text"]}
        for i, x in enumerate(selected)
    ]
    request = {
        "format": "humanwill.request/1",
        "request_id": request_id,
        "stage": "model_request",
        "content": parts,
        "coverage": {
            "complete": False,
            "inspected": [x["id"] for x in parts],
            "omitted": [
                "Not the actual model wire request: bounded visible-text conversation only",
                (
                    "Tools, tool results, attachments, system/developer instructions "
                    "and compaction summaries"
                ),
                "Earlier conversation outside the maximum five-message/10000-byte suffix",
            ],
        },
    }
    return request, [x["line"] for x in selected]


def prepare(transcript, before, output, count=50):
    output = Path(output)
    if output.exists():
        raise ValueError("Use a fresh packet directory")
    records = messages(transcript, ROOT)
    indices = [i for i, x in enumerate(records) if x["role"] == "user" and x["timestamp"] < before][
        -count:
    ]
    if len(indices) != count:
        raise ValueError("Insufficient eligible historical requests")
    cases = []
    for n, i in enumerate(indices, 1):
        request, lines = request_for(records, i, f"dogfood-history-{n:03d}")
        cases.append(
            {
                "id": request["request_id"],
                "timestamp": records[i]["timestamp"],
                "source_lines": lines,
                "request": request,
                "request_sha256": fingerprint(request),
                "review": {
                    "status": "pending",
                    "expected_decision": None,
                    "reason": "",
                    "facts": {
                        "destination.onward_approved": None,
                        "authorization.software_sources_approved": None,
                    },
                },
            }
        )
    packet = {
        "format": "humanwill.dogfood-packet/1",
        "scope": "this project session only",
        "selection": (
            "Last 50 native user.text messages before cutoff, chronological; no outcome selection"
        ),
        "cutoff_exclusive": before,
        "count": count,
        "transcript_prefix_sha256": hashlib.sha256(
            b"".join(
                Path(transcript)
                .read_bytes()
                .splitlines(keepends=True)[: max(c["source_lines"][-1] for c in cases)]
            )
        ).hexdigest(),
        "cases": cases,
    }
    save(output / "packet.json", packet)
    render_review(packet, output / "review.html")
    return packet


def render_review(packet, path):
    # All content enters the DOM through textContent, never transcript-provided HTML.
    data = (
        json.dumps(packet, ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
    page = Path(__file__).with_name("review.html").read_text().replace("DATA", data)
    Path(path).write_text(page)
    Path(path).chmod(0o600)


def capture(event, settings, directory):
    """Capture only; host always continues. Filter before reading or storing the prompt."""
    if event.get("hook_event_name") != "UserPromptSubmit":
        return "ignored_event"
    try:
        cwd = Path(event.get("cwd", "")).resolve()
        cwd.relative_to(Path(settings["project"]).resolve())
    except (ValueError, TypeError):
        return "ignored_project"
    if event.get("session_id") != settings["session_id"]:
        return "ignored_session"
    prompt = event.get("prompt")
    turn = event.get("turn_id")
    if not isinstance(prompt, str) or not isinstance(turn, str) or not turn:
        return "invalid_event"
    if len(prompt.encode()) > 64000:
        return "oversized_event"
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = directory / "capture.lock"
    with lock.open("a") as stream:
        os.chmod(lock, 0o600)
        fcntl.flock(stream, fcntl.LOCK_EX)
        state_path = directory / "capture-state.json"
        state = json.loads(state_path.read_text()) if state_path.exists() else {"events": []}
        identity = fingerprint({"session": event["session_id"], "turn": turn, "prompt": prompt})
        if any(x["identity"] == identity for x in state["events"]):
            return "duplicate"
        if len(state["events"]) >= min(settings["max_prompts"], MAX_CAPTURE):
            return "capture_limit"
        event_id = f"dogfood-future-{len(state['events']) + 1:03d}"
        record = {
            "id": event_id,
            "identity": identity,
            "captured_at": datetime.now(UTC).isoformat(),
            "status": "captured_not_evaluated",
            "request": {
                "format": "humanwill.request/1",
                "request_id": event_id,
                "stage": "prompt",
                "content": [{"id": "prompt", "kind": "text", "role": "user", "text": prompt}],
                "coverage": {"complete": True, "inspected": ["prompt"], "omitted": []},
            },
            "coverage_note": (
                "Submitted text only: no conversation, files, tool calls or model wire payload."
            ),
            "turn_id": turn,
        }
        save(directory / (event_id + ".json"), record)
        state["events"].append({"identity": identity, "id": event_id})
        save(state_path, state)
    return "captured"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--transcript", type=Path, required=True)
    p.add_argument("--before", required=True)
    p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("capture")
    p.add_argument("--settings", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        packet = prepare(args.transcript, args.before, args.output)
        print(
            json.dumps(
                {
                    "cases": len(packet["cases"]),
                    "packet_sha256": fingerprint(packet),
                    "review": str(args.output / "review.html"),
                }
            )
        )
    else:
        # No stdout content enters the model and no nonzero status blocks the host.
        try:
            import sys

            raw = sys.stdin.buffer.read(131073)
            if len(raw) > 131072:
                raise ValueError("oversized input")
            event = json.loads(raw)
            settings = json.loads(args.settings.read_text())
            status = capture(event, settings, args.output)
            save(
                args.output / "last-hook-status.json",
                {"status": status, "timestamp": datetime.now(UTC).isoformat()},
            )
        except Exception:
            try:
                save(args.output / "last-hook-status.json", {"status": "capture_error"})
            except Exception:
                pass


if __name__ == "__main__":
    main()
