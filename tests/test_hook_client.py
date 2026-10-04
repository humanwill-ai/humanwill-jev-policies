"""Security contracts for both the full package and the standalone installed client.

Set HUMANWILL_HOOK_TEST_PACKAGE=humanwill_hook_client outside the checkout to
exercise the exact standalone wheel/source installation. All inputs are synthetic.
"""

import asyncio
import copy
import importlib
import io
import json
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import httpx

PACKAGE = os.environ.get("HUMANWILL_HOOK_TEST_PACKAGE", "humanwill_policies")
client = importlib.import_module(f"{PACKAGE}.hooks")
events = importlib.import_module(f"{PACKAGE}.hook_events")
codec = importlib.import_module(f"{PACKAGE}.json_codec")
PolicyError = importlib.import_module(f"{PACKAGE}.errors").PolicyError
TOKEN = "synthetic-hook-client-test-token-0000000000"
FIXTURE = json.loads((Path(__file__).parent / "fixtures/result-hook.json").read_text())
PROFILES = [
    (
        "copilot_local",
        "UserPromptSubmit",
        {"hook_event_name": "UserPromptSubmit", "prompt": "test"},
    ),
    (
        "copilot_local",
        "PreToolUse",
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "bash",
            "tool_input": {"command": "echo test"},
        },
    ),
    ("copilot_cli", "userPromptSubmitted", {"prompt": "test"}),
    ("copilot_cli", "preToolUse", {"toolName": "bash", "toolArgs": '{"command":"echo test"}'}),
]


def reply(payload, runtime="copilot_local", event="UserPromptSubmit", *, block=False):
    result = copy.deepcopy(FIXTURE)
    normalized = events.hook(payload, runtime, event)
    normalized["request_id"] = result["request_id"]
    result["request_sha256"] = codec.digest(normalized)
    result["coverage"] = normalized["coverage"]
    if block:
        result["decision"] = "block"
        result["enforcement"]["requested"] = "block"
        result["policies"][0]["judgment"] = "violation"
    return result


class HookClientTests(unittest.TestCase):
    def assess(self, handler, profile=PROFILES[0], **kwargs):
        runtime, event, payload = profile
        return asyncio.run(
            client.assess(
                payload,
                runtime,
                event,
                "http://localhost",
                TOKEN,
                100,
                transport=httpx.MockTransport(handler),
                **kwargs,
            )
        )

    def test_all_host_profiles_and_bearer_auth(self):
        for runtime, event, payload in PROFILES:
            with self.subTest(runtime=runtime, event=event):

                def handler(request, runtime=runtime, event=event, payload=payload):
                    self.assertEqual(request.headers["authorization"], "Bearer " + TOKEN)
                    self.assertEqual(request.url.path, f"/v1/hooks/{runtime}/{event}")
                    self.assertEqual(json.loads(request.content), payload)
                    return httpx.Response(200, json=reply(payload, runtime, event))

                self.assertEqual(
                    self.assess(handler, (runtime, event, payload))["decision"], "allow"
                )

    def test_invalid_verdicts_are_never_accepted(self):
        mutations = [
            lambda r: r.update(request_sha256="0" * 64),
            lambda r: r["coverage"].update(complete=False, omitted=["missing"]),
            lambda r: r.update(simulated=True),
            lambda r: r.update(format="humanwill.result/999"),
            lambda r: r["enforcement"].update(requested="unknown"),
            lambda r: r.update(unrecognized=True),
            lambda r: r["policies"].append(copy.deepcopy(r["policies"][0])),
        ]
        for i, mutate in enumerate(mutations):
            with self.subTest(mutation=i):
                result = reply(PROFILES[0][2])
                mutate(result)
                with self.assertRaises(PolicyError):
                    self.assess(lambda _, result=result: httpx.Response(200, json=result))

    def test_protocol_failures_redirects_compression_and_limits(self):
        responses = [
            (302, {}, {"location": "https://unapproved.example.test"}),
            (401, {}, {}),
            (503, {}, {}),
            (200, {}, {"content-encoding": "unexpected"}),
        ]
        for status, body, headers in responses:
            calls = []

            def handler(request, calls=calls, status=status, body=body, headers=headers):
                calls.append(request)
                return httpx.Response(status, json=body, headers=headers)

            with self.assertRaises(PolicyError):
                self.assess(handler)
            self.assertEqual(len(calls), 1)
        for body in [b'{"a":1,"a":2}', b'{"a":NaN}', b"[]", b"{", b" " * (262144 + 1)]:
            with self.subTest(length=len(body)), self.assertRaises(PolicyError):
                self.assess(lambda _, body=body: httpx.Response(200, content=body))

    def test_total_deadline_and_connection_failure(self):
        async def slow(_):
            await asyncio.sleep(0.2)
            return httpx.Response(200, json=reply(PROFILES[0][2]))

        with self.assertRaises(TimeoutError):
            self.assess(slow)

        def unavailable(_):
            raise httpx.ConnectError("synthetic-private-error")

        with self.assertRaises(httpx.ConnectError):
            self.assess(unavailable)

    def test_url_and_token_checks_prevent_egress(self):
        for url in [
            "http://company.example",
            "https://user:pass@company.example",
            "https://company.example/path",
            "https://company.example?x=1",
            "file:///tmp/x",
        ]:
            with self.subTest(url=url), self.assertRaises(PolicyError):
                client.check_url(url)
        for token in ["", "short", "x" * 32 + "\n"]:
            with self.assertRaises(PolicyError):
                asyncio.run(
                    client.assess(
                        PROFILES[0][2],
                        *PROFILES[0][:2],
                        "http://localhost",
                        token,
                        100,
                        transport=httpx.MockTransport(lambda _: self.fail("must not send")),
                    )
                )

    def test_private_host_fields_not_sent_and_errors_are_sanitized(self):
        for runtime, event, payload in PROFILES:
            payload = {
                **payload,
                "transcript_path": "/private/DO_NOT_READ",
                "cwd": "/private/DO_NOT_SEND",
                "extra": "DO_NOT_SEND",
            }
            observed = []

            async def assess(data, *args, observed=observed):
                observed.append(data)
                raise httpx.ConnectError("DO_NOT_LOG")

            for fallback in ["block", "allow_monitor"]:
                args = SimpleNamespace(
                    runtime=runtime,
                    event=event,
                    on_error=fallback,
                    url="http://localhost",
                    token_env="MISSING",
                    timeout_ms=100,
                )
                stdout, stderr = io.StringIO(), io.StringIO()
                with (
                    patch.object(client, "assess", assess),
                    patch(
                        "sys.stdin",
                        SimpleNamespace(buffer=io.BytesIO(json.dumps(payload).encode())),
                    ),
                    redirect_stdout(stdout),
                    redirect_stderr(stderr),
                ):
                    self.assertEqual(client.run(args), 0)
                self.assertEqual(
                    json.loads(stdout.getvalue()),
                    events.hook_output(runtime, event, fallback == "block"),
                )
                self.assertNotIn(
                    "DO_NOT", stdout.getvalue() + stderr.getvalue() + json.dumps(observed)
                )

    def test_hook_path_does_not_import_policy_engine_or_yaml(self):
        script = f'''import importlib,sys
m=importlib.import_module("{PACKAGE}.hook_events")
m.hook({PROFILES[0][2]!r},"copilot_local","UserPromptSubmit")
for name in ("yaml","config","bundle","providers","starlette","uvicorn"):
 assert name not in sys.modules and "{PACKAGE}."+name not in sys.modules
'''
        subprocess.run([sys.executable, "-c", script], check=True, capture_output=True)

    def test_json_depth_and_nonfinite_and_duplicates_rejected(self):
        for raw in [b'{"a":NaN}', b'{"a":1,"a":2}', b'{"x":' + b"[" * 26 + b"0" + b"]" * 26 + b"}"]:
            with self.assertRaises(PolicyError):
                codec.decode_json(raw)


if __name__ == "__main__":
    unittest.main()
