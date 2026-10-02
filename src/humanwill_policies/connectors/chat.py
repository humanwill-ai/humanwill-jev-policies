"""Bounded non-streaming function-call surface; never infer execution from history."""

from ..contracts import MAX_REQUEST_BYTES
from ..providers import decode_json
from ..serialization import canonical
from .events import event, unsupported

MAX_TOOL_CALLS = 32


def name(value):
    return isinstance(value, str) and 0 < len(value) <= 512 and bool(value.strip())


def tool_calls(value):
    """Validate a complete OpenAI function-call list and parse strict JSON objects."""
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_TOOL_CALLS:
        unsupported()
    parsed, ids = [], set()
    for call in value:
        if (
            not isinstance(call, dict)
            or set(call) != {"id", "type", "function"}
            or call["type"] != "function"
            or not name(call["id"])
            or call["id"] in ids
        ):
            unsupported()
        ids.add(call["id"])
        function = call["function"]
        if (
            not isinstance(function, dict)
            or set(function) != {"name", "arguments"}
            or not name(function["name"])
            or not isinstance(function["arguments"], str)
            or len(function["arguments"].encode()) > MAX_REQUEST_BYTES
        ):
            unsupported()
        parsed.append(
            {
                "kind": "tool_action",
                "name": function["name"],
                "arguments": decode_json(function["arguments"].encode()),
            }
        )
    return parsed


def definitions(tools):
    if not isinstance(tools, list) or len(tools) > MAX_TOOL_CALLS:
        unsupported()
    names = set()
    for tool in tools:
        if not isinstance(tool, dict) or set(tool) != {"type", "function"}:
            unsupported()
        fn = tool["function"]
        if (
            tool["type"] != "function"
            or not isinstance(fn, dict)
            or set(fn) - {"name", "description", "parameters", "strict"}
            or not name(fn.get("name"))
            or fn["name"] in names
            or ("description" in fn and not isinstance(fn["description"], str))
            or ("parameters" in fn and not isinstance(fn["parameters"], dict))
            or ("strict" in fn and not isinstance(fn["strict"], bool))
        ):
            unsupported()
        names.add(fn["name"])
    return names


def request_parts(rows, tools):
    """History is model input, never a fresh tool_action assessment."""
    definitions(tools)
    if not isinstance(rows, list) or not rows or len(rows) > 256:
        unsupported()
    parts = []
    for row in rows:
        if (
            not isinstance(row, dict)
            or row.get("role") not in {"system", "developer", "user", "assistant", "tool"}
            or set(row) - {"role", "content", "name", "tool_call_id", "tool_calls"}
            or ("name" in row and not name(row["name"]))
        ):
            unsupported()
        calls = row.get("tool_calls")
        if "tool_calls" in row:
            if row["role"] != "assistant":
                unsupported()
            tool_calls(calls)
        if "tool_call_id" in row:
            if row["role"] != "tool" or not name(row["tool_call_id"]):
                unsupported()
        elif row["role"] == "tool":
            unsupported()
        if not isinstance(row.get("content"), str) and not (row.get("content") is None and calls):
            unsupported()
        # Preserve structured history/IDs losslessly in the model-request surface.
        text = row["content"] if set(row) <= {"role", "content"} else canonical(row)
        parts.append({"kind": "text", "role": row["role"], "text": text})
    if tools:
        parts.append(
            {
                "kind": "text",
                "role": "unknown",
                "text": "Available tool definitions (not executions): " + canonical(tools),
            }
        )
    return parts


def validate_request(body):
    if not isinstance(body, dict) or (
        body.get("stream") is not None and body["stream"] is not False
    ):
        unsupported()
    if any(k in body for k in ("functions", "function_call", "audio", "modalities")):
        unsupported()
    tools = body.get("tools", [])
    parts = request_parts(body.get("messages"), tools)
    names = definitions(tools)
    choice = body.get("tool_choice", "auto")
    if isinstance(choice, dict):
        if (
            set(choice) != {"type", "function"}
            or choice["type"] != "function"
            or not isinstance(choice["function"], dict)
            or set(choice["function"]) != {"name"}
            or choice["function"]["name"] not in names
        ):
            unsupported()
    elif choice not in ("auto", "none", "required"):
        unsupported()
    if "parallel_tool_calls" in body and not isinstance(body["parallel_tool_calls"], bool):
        unsupported()
    return parts


def validate_response(body):
    """Validate the complete host response before any proposal can leave the host."""
    if (
        not isinstance(body, dict)
        or not isinstance(body.get("choices"), list)
        or not body["choices"]
    ):
        unsupported()
    texts, calls = [], []
    for choice in body["choices"]:
        if not isinstance(choice, dict) or not isinstance(choice.get("message"), dict):
            unsupported()
        row = {k: v for k, v in choice["message"].items() if v is not None}
        # LiteLLM 1.102.1 adds this empty envelope even to ordinary OpenAI replies.
        provider_fields = row.get("provider_specific_fields")
        if isinstance(provider_fields, dict) and all(v is None for v in provider_fields.values()):
            del row["provider_specific_fields"]
        if row.get("role") != "assistant" or set(row) - {"role", "content", "tool_calls"}:
            unsupported()
        current = row.get("tool_calls", [])
        if current:
            tool_calls(current)
            if choice.get("finish_reason") != "tool_calls":
                unsupported()
            calls.extend(current)
        elif "tool_calls" in row and not isinstance(current, list):
            unsupported()
        if "content" in row:
            if not isinstance(row["content"], str):
                unsupported()
            texts.append(row["content"])
        elif not current:
            unsupported()
    if calls:
        tool_calls(calls)
    return texts, calls


def response_events(texts, calls):
    if not isinstance(texts, list) or not all(isinstance(t, str) for t in texts):
        unsupported()
    parsed = tool_calls(calls) if calls else []
    parts = [{"kind": "text", "role": "assistant", "text": t} for t in texts]
    if parsed:
        parts.append(
            {
                "kind": "text",
                "role": "assistant",
                "text": "New tool-call proposals (not executed): " + canonical(calls),
            }
        )
    # Response policies cover everything disclosed, including names/arguments.
    # Each action gets its own trusted-evidence resolution and policy decision.
    return [event("response", parts)] + [event("tool_action", [call]) for call in parsed]


def litellm_events(payload):
    if payload.get("litellm_version") != "1.102.1" or payload.get("images"):
        unsupported()
    tools = [] if payload.get("tools") is None else payload["tools"]
    calls = [] if payload.get("tool_calls") is None else payload["tool_calls"]
    if not isinstance(tools, list) or not isinstance(calls, list):
        unsupported()
    texts = payload.get("texts")
    if not isinstance(texts, list) or not all(isinstance(t, str) for t in texts):
        unsupported()
    if payload.get("input_type") == "response":
        if tools:
            unsupported()
        return response_events(texts, calls)
    if payload.get("input_type") != "request":
        unsupported()
    rows = payload.get("structured_messages")
    parts = request_parts(rows, tools)
    if texts != [row["content"] for row in rows if isinstance(row.get("content"), str)]:
        unsupported()
    if calls != [call for row in rows for call in row.get("tool_calls", [])]:
        unsupported()
    return [event("model_request", parts)]
