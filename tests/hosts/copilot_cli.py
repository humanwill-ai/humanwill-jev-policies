"""Real Copilot CLI 1.0.88, offline BYOK, one controlled file-creation tool call."""

import argparse
import json
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from support import TOKEN, policy_app, server


def model_app(marker, requests):
    async def completion(request):
        body = await request.json()
        requests.append(body)
        tool_results = [m for m in body.get("messages", []) if m.get("role") == "tool"]
        if not tool_results:
            message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "synthetic_call",
                        "type": "function",
                        "function": {
                            "name": "bash",
                            "arguments": json.dumps(
                                {
                                    "command": "printf synthetic > " + shlex.quote(str(marker)),
                                    "description": "Create a synthetic test marker",
                                }
                            ),
                        },
                    }
                ],
            }
            reason = "tool_calls"
        else:
            message = {"role": "assistant", "content": "Synthetic test complete."}
            reason = "stop"
        return JSONResponse(
            {
                "id": "chatcmpl-synthetic",
                "object": "chat.completion",
                "created": 1,
                "model": "synthetic",
                "choices": [{"index": 0, "message": message, "finish_reason": reason}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            }
        )

    return Starlette(
        routes=[
            Route("/v1/chat/completions", completion, methods=["POST"]),
            Route("/chat/completions", completion, methods=["POST"]),
        ]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", required=True)
    parser.add_argument(
        "--hook-binary", type=Path, help="Test this native client instead of Python"
    )
    parser.add_argument("--outdir", type=Path, default=Path("artifacts/hosts"))
    args = parser.parse_args()
    binary = str(Path(args.binary).resolve())
    assert "1.0.88" in subprocess.check_output([binary, "--version"], text=True)
    out = args.outdir
    out.mkdir(parents=True, exist_ok=True)
    report = []
    for case in ["allow", "deny", "prompt_assessment", "service_down", "host_timeout", "disabled"]:
        with tempfile.TemporaryDirectory(prefix="humanwill-cli-") as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir()
            subprocess.run(["git", "init", "-q", str(workspace)], check=True)
            marker = workspace / (
                "HW_DENY_marker"
                if case in ("deny", "host_timeout", "disabled")
                else "allowed-marker"
            )
            captures = []
            requests = []
            with (
                server(
                    policy_app(root / "policies", "copilot_cli", captures=captures)
                ) as policyport,
                server(model_app(marker, requests)) as modelport,
            ):
                hooks = workspace / ".github/hooks"
                hooks.mkdir(parents=True)

                def command(event, case=case, policyport=policyport):
                    return shlex.join(
                        [
                            *(
                                [str(args.hook_binary.resolve())]
                                if args.hook_binary
                                else [sys.executable, "-m", "humanwill_policies", "hook"]
                            ),
                            "--runtime",
                            "copilot_cli",
                            "--event",
                            event,
                            "--url",
                            f"http://127.0.0.1:{policyport if case != 'service_down' else 1}",
                            "--timeout-ms",
                            "600",
                            "--token-env",
                            "HOST_FIXTURE_TOKEN",
                        ]
                    )

                pre = command("preToolUse") + " 2> " + shlex.quote(str(root / "hook-error.log"))
                if case == "host_timeout":
                    pre = "sleep 3; " + pre
                hooks.joinpath("humanwill.json").write_text(
                    json.dumps(
                        {
                            "version": 1,
                            "hooks": {
                                "preToolUse": [
                                    {
                                        "type": "command",
                                        "bash": pre,
                                        "timeoutSec": 1 if case == "host_timeout" else 15,
                                    }
                                ],
                                "userPromptSubmitted": [
                                    {
                                        "type": "command",
                                        "bash": command("userPromptSubmitted"),
                                        "timeoutSec": 15,
                                    }
                                ],
                            },
                        }
                    )
                )
                if case == "disabled":
                    settings = workspace / ".github/copilot"
                    settings.mkdir()
                    (settings / "settings.json").write_text('{"disableAllHooks":true}')
                (root / "copilot-home").mkdir()
                (root / "copilot-home/config.json").write_text(
                    json.dumps({"trusted_folders": [str(workspace), str(workspace.resolve())]})
                )
                env = {
                    k: v
                    for k, v in os.environ.items()
                    if k in ("PATH", "HOME", "TMPDIR", "USER", "SHELL", "LANG")
                }
                env.update(
                    COPILOT_HOME=str(root / "copilot-home"),
                    COPILOT_OFFLINE="true",
                    COPILOT_PROVIDER_BASE_URL=f"http://127.0.0.1:{modelport}/v1",
                    COPILOT_MODEL="gpt-4o",
                    COPILOT_PROVIDER_WIRE_API="completions",
                    COPILOT_PROVIDER_API_KEY="synthetic-unused",
                    HOST_FIXTURE_TOKEN=TOKEN,
                    DO_NOT_TRACK="1",
                )
                prompt = (
                    "HW_DENY_PROMPT"
                    if case == "prompt_assessment"
                    else "Run the synthetic marker test."
                )
                result = subprocess.run(
                    [
                        binary,
                        "-p",
                        prompt,
                        "--allow-all-tools",
                        "--disable-builtin-mcps",
                        "--no-auto-update",
                        "--no-remote",
                        "--no-remote-export",
                        "--no-custom-instructions",
                        "--no-ask-user",
                        "--stream",
                        "off",
                    ],
                    cwd=workspace,
                    env=env,
                    text=True,
                    capture_output=True,
                    timeout=60,
                )
                (out / f"copilot-cli-{case}.log").write_text(result.stdout + result.stderr)
                (out / f"copilot-cli-{case}-requests.json").write_text(
                    json.dumps(requests, indent=2)
                )
                import shutil

                if (root / "hook-error.log").exists():
                    print((root / "hook-error.log").read_text())
                shutil.copytree(
                    root / "copilot-home", out / f"copilot-state-{case}", dirs_exist_ok=True
                )
                assert result.returncode == 0, (case, result.returncode, result.stderr[-2000:])
                expected = case in ("allow", "prompt_assessment", "host_timeout", "disabled")
                assert marker.exists() == expected, (
                    case,
                    "marker",
                    marker.exists(),
                    result.stdout[-1500:],
                    result.stderr[-1000:],
                )
                stages = [p["state"]["stage"] for p in captures]
                if case == "prompt_assessment":
                    assert "prompt" in stages, stages
                if case == "deny":
                    assert "tool_action" in stages, stages
                report.append(
                    {
                        "case": case,
                        "marker_exists": marker.exists(),
                        "evaluated_stages": stages,
                        "model_calls": len(requests),
                        "passed": True,
                    }
                )
                print(json.dumps(report[-1]), flush=True)
    (out / "copilot-cli.json").write_text(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
