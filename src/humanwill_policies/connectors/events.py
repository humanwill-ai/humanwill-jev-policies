"""Normalize only documented, supplied event fields. Never read agent-supplied paths."""

from uuid import uuid4

from ..contracts import validate_contract
from ..errors import PolicyError
from ..providers import decode_json

ROLES = {"system", "developer", "user", "assistant", "tool"}
HOOKS = {
    "copilot_local": {"UserPromptSubmit": "prompt", "PreToolUse": "tool_action"},
    "copilot_cli": {"userPromptSubmitted": "prompt", "preToolUse": "tool_action"},
}


def unsupported():
    raise PolicyError("unsupported_payload", "Payload is outside the supported text/event profile")


def event(stage, parts):
    if not parts:
        unsupported()
    content = [{"id": f"part-{i}", **part} for i, part in enumerate(parts)]
    result = {
        "format": "humanwill.request/1",
        "request_id": "event-" + uuid4().hex,
        "stage": stage,
        "content": content,
        # Complete means all fields in the supported event surface, never all agent context.
        "coverage": {"inspected": [p["id"] for p in content], "omitted": [], "complete": True},
    }
    validate_contract("request", result)
    return result


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


def hook(payload, runtime, name):
    if runtime not in HOOKS or name not in HOOKS[runtime]:
        unsupported()
    stage = HOOKS[runtime][name]
    if runtime == "copilot_local" and payload.get("hook_event_name") != name:
        unsupported()
    if stage == "prompt":
        if not isinstance(payload.get("prompt"), str):
            unsupported()
        return event(stage, [{"kind": "text", "role": "user", "text": payload["prompt"]}])
    local = runtime == "copilot_local"
    tool = payload.get("tool_name" if local else "toolName")
    args = payload.get("tool_input" if local else "toolArgs")
    if not local and isinstance(args, str):
        args = decode_json(args.encode())
    if not isinstance(tool, str) or not isinstance(args, dict):
        unsupported()
    return event(stage, [{"kind": "tool_action", "name": tool, "arguments": args}])


def hook_output(runtime, name, blocked, reason="HumanWill policy check denied this operation"):
    if not blocked or (runtime == "copilot_cli" and name == "userPromptSubmitted"):
        return {}  # Preserve the host's normal permission/approval flow.
    if runtime == "copilot_local":
        if name == "UserPromptSubmit":
            return {"continue": False, "stopReason": reason}
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
    return {"permissionDecision": "deny", "permissionDecisionReason": reason}
