"""Run a pinned gateway PROCESS against actual service and controlled downstream.

Usage: python tests/hosts/gateways.py litellm --binary /path/to/litellm
       python tests/hosts/gateways.py agentgateway --binary /path/to/agentgateway
"""

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

import httpx
from support import TOKEN, downstream, dump_yaml, policy_app, port, server, wait_http


def config(host, hostport, policyport, modelport):
    if host == "litellm":
        return {
            "model_list": [
                {
                    "model_name": "synthetic",
                    "litellm_params": {
                        "model": "openai/synthetic",
                        "api_base": f"http://127.0.0.1:{modelport}/v1",
                        "api_key": "synthetic-unused",
                    },
                }
            ],
            "litellm_settings": {
                "callbacks": ["humanwill_policies.connectors.litellm_profile.profile"],
                "set_verbose": False,
            },
            "guardrails": [
                {
                    "guardrail_name": "humanwill",
                    "litellm_params": {
                        "guardrail": "generic_guardrail_api",
                        "mode": ["pre_call", "post_call"],
                        "api_base": f"http://127.0.0.1:{policyport}",
                        "api_key": "os.environ/HOST_FIXTURE_TOKEN",
                        "default_on": True,
                        "fail_on_error": True,
                        "unreachable_fallback": "fail_closed",
                    },
                }
            ],
            "general_settings": {"master_key": "sk-synthetic-host-client"},
        }
    webhook = {
        "target": {"host": f"127.0.0.1:{policyport}"},
        "headers": {"authorization": '"Bearer ' + TOKEN + '"'},
        "failureMode": "failClosed",
    }
    return {
        "binds": [
            {
                "port": hostport,
                "listeners": [
                    {
                        "routes": [
                            {
                                "backends": [
                                    {
                                        "ai": {
                                            "name": "synthetic",
                                            "provider": {"openAI": {"model": "synthetic"}},
                                            "hostOverride": f"127.0.0.1:{modelport}",
                                        }
                                    }
                                ],
                                "policies": {
                                    "ai": {
                                        "promptGuard": {
                                            "request": [{"webhook": webhook}],
                                            "response": [{"webhook": webhook}],
                                        }
                                    }
                                },
                            }
                        ]
                    }
                ],
            }
        ]
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("host", choices=("litellm", "agentgateway"))
    parser.add_argument("--binary", required=True)
    args = parser.parse_args()
    binary = str(Path(args.binary).resolve())
    cases = []
    out = Path("artifacts/hosts")
    out.mkdir(parents=True, exist_ok=True)
    for mode in ("enforce", "monitor"):
        with tempfile.TemporaryDirectory(prefix="humanwill-gateway-") as tmp:
            root = Path(tmp)
            calls = []
            captures = []
            with (
                server(policy_app(root / "policies", args.host, mode, captures)) as policyport,
                server(downstream(calls)) as modelport,
            ):
                hostport = port()
                conf = root / "config.yaml"
                dump_yaml(conf, config(args.host, hostport, policyport, modelport))
                command = (
                    [binary, "--config", str(conf), "--port", str(hostport)]
                    if args.host == "litellm"
                    else [binary, "-f", str(conf)]
                )
                env = {
                    **os.environ,
                    "PYTHONPATH": str(Path("src").resolve()),
                    "LITELLM_LOCAL_MODEL_COST_MAP": "True",
                    "DO_NOT_TRACK": "1",
                    "DEBUG": "false",
                }
                with (out / f"{args.host}-{mode}.log").open("w") as log:
                    process = subprocess.Popen(command, stdout=log, stderr=log, env=env, cwd=root)
                    try:
                        wait_http(f"http://127.0.0.1:{hostport}/health/liveliness", process)
                        for label, text, want_calls, status_ok in [
                            ("allow", "hello", 1, True),
                            (
                                "request_deny",
                                "HW_DENY_REQUEST",
                                0 if mode == "enforce" else 1,
                                mode == "monitor",
                            ),
                            ("response_deny", "MAKE_BAD_OUTPUT", 1, mode == "monitor"),
                            (
                                "provider_error",
                                "HW_ERROR",
                                0 if mode == "enforce" else 1,
                                mode == "monitor",
                            ),
                            (
                                "provider_timeout",
                                "HW_TIMEOUT",
                                0 if mode == "enforce" else 1,
                                mode == "monitor",
                            ),
                        ]:
                            before = len(calls)
                            response = httpx.post(
                                f"http://127.0.0.1:{hostport}/v1/chat/completions",
                                headers={"Authorization": "Bearer sk-synthetic-host-client"},
                                json={
                                    "model": "synthetic",
                                    "messages": [{"role": "user", "content": text}],
                                },
                                timeout=20,
                                trust_env=False,
                            )
                            assert (response.status_code == 200) == status_ok, (
                                label,
                                mode,
                                response.status_code,
                                response.text[:1000],
                            )
                            assert len(calls) - before == want_calls, (
                                label,
                                "downstream_calls",
                                calls,
                            )
                            if label == "response_deny" and mode == "enforce":
                                assert "HW_DENY_RESPONSE" not in response.text
                            cases.append(
                                {
                                    "host": args.host,
                                    "mode": mode,
                                    "case": label,
                                    "status": response.status_code,
                                    "downstream_calls": len(calls) - before,
                                    "passed": True,
                                }
                            )
                    finally:
                        process.terminate()
                        try:
                            process.wait(10)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()
    (out / f"{args.host}.json").write_text(json.dumps(cases, indent=2))
    print(json.dumps(cases, indent=2))


if __name__ == "__main__":
    main()
