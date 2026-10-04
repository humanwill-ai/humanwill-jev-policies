"""Normalize only documented, supplied event fields. Never read agent-supplied paths."""

from ..hook_events import HOOKS as HOOKS
from ..hook_events import event as event
from ..hook_events import hook as hook
from ..hook_events import hook_output as hook_output
from ..hook_events import unsupported as unsupported

ROLES = {"system", "developer", "user", "assistant", "tool"}


def messages(rows):
    if not isinstance(rows, list) or not rows:
        unsupported()
    parts = []
    for row in rows:
        if not isinstance(row, dict) or row.get("role") not in ROLES:
            unsupported()
        if set(row) - {"role", "content", "name", "tool_call_id"}:
            unsupported()
        if not isinstance(row.get("content"), str):
            unsupported()
        # Preserve names/IDs in text when present; do not claim tool execution inspection.
        text = row["content"]
        if row.get("name") or row.get("tool_call_id"):
            unsupported()
        parts.append({"kind": "text", "role": row["role"], "text": text})
    return parts


def litellm(payload):
    stage = {"request": "model_request", "response": "response"}.get(payload.get("input_type"))
    if stage is None or payload.get("litellm_version") != "1.102.1":
        unsupported()
    if any(payload.get(k) for k in ("images", "tools", "tool_calls")):
        unsupported()
    texts = payload.get("texts")
    if not isinstance(texts, list) or not texts or not all(isinstance(t, str) for t in texts):
        unsupported()
    structured = payload.get("structured_messages")
    # Response structured_messages can contain INPUT context, not generated output.
    if stage == "model_request" and structured:
        parts = messages(structured)
        if [p["text"] for p in parts] != texts:
            unsupported()
    else:
        parts = [{"kind": "text", "role": "unknown", "text": t} for t in texts]
    return event(stage, parts)


def agentgateway(payload, stage):
    if set(payload) != {"body"} or not isinstance(payload["body"], dict):
        unsupported()
    body = payload["body"]
    if stage == "model_request":
        if set(body) != {"messages"}:
            unsupported()
        return event(stage, messages(body["messages"]))
    if set(body) != {"choices"} or not isinstance(body["choices"], list):
        unsupported()
    rows = []
    for choice in body["choices"]:
        if not isinstance(choice, dict) or set(choice) - {"index", "message", "finish_reason"}:
            unsupported()
        rows.append(choice.get("message"))
    return event(stage, messages(rows))
