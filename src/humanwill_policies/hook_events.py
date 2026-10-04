"""Supplied-field normalization and host output contracts for Local/CLI hooks."""

from uuid import uuid4

from .contracts import validate_contract
from .errors import PolicyError
from .json_codec import decode_json

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
