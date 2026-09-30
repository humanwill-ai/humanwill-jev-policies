"""Interactive, real VS Code Local smoke; all model/evaluator responses are synthetic.

Run from a checkout with the package installed. Requires a dedicated signed-in
Copilot profile; never point --state-dir at a personal editor profile/workspace.
Only sanitized outcome fields are reported; VS Code's own local logs may contain
account/session data. Keep the entire state directory private and ignored.
"""

import argparse
import copy
import json
import os
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from support import TOKEN, policy_app, server

# name, submitted marker, tool argument, marker expected, model calls, inspected stages
CASES = [
    ("allow", "allow", "allowed", True, 2, ["prompt", "tool_action"]),
    ("prompt-deny", "HW_DENY", "allowed", False, 0, ["prompt"]),
    ("tool-deny", "allow", "HW_DENY", False, 2, ["prompt", "tool_action"]),
    ("provider-error", "allow", "HW_ERROR", False, 2, ["prompt", "tool_action"]),
    ("provider-timeout", "allow", "HW_TIMEOUT", False, 2, ["prompt", "tool_action"]),
    ("service-down-tool", "allow", "allowed", False, 2, ["prompt"]),
    ("service-down-prompt", "allow", "allowed", False, 0, []),
    ("malformed-tool", "allow", "allowed", False, 2, ["prompt"]),
    ("malformed-prompt", "allow", "allowed", False, 0, []),
    ("monitor", "HW_DENY", "HW_DENY", True, 2, ["prompt", "tool_action"]),
    ("host-timeout-tool", "allow", "HW_DENY", True, 2, ["prompt"]),
    ("host-timeout-prompt", "HW_DENY", "allowed", True, 2, ["tool_action"]),
    ("disabled", "HW_DENY", "HW_DENY", True, 2, []),
    ("restored-deny", "allow", "HW_DENY", False, 2, ["prompt", "tool_action"]),
]


def write_json(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2))
    temporary.replace(path)


def records(path):
    if not path.exists():
        return []
    # Ignore an incomplete final line while the extension appends.
    lines = path.read_text().splitlines(keepends=True)
    return [json.loads(line) for line in lines if line.endswith("\n")]


def timeout_count(root, event):
    return sum(
        "Hook command timed out after 1s: sleep 3;" in line and f"--event {event}" in line
        for path in (root / "profile/logs").rglob("*Hooks.log")
        for line in path.read_text().splitlines()
    )


def run_cases(root, base, port, monitor_port, captures, monitor_captures):
    workspace = root / "workspace"
    hook_file = workspace / ".github/hooks/humanwill.json"
    report = []
    try:
        for case, prompt, value, marker, calls, stages in CASES:
            hooks = copy.deepcopy(base)
            event = "UserPromptSubmit" if case.endswith("prompt") else "PreToolUse"
            timeouts_before = timeout_count(root, event)
            target = hooks["hooks"][event][0]
            if case.startswith("service-down"):
                target["command"] = target["command"].replace(f":{port}", ":1")
            if case.startswith("malformed"):
                target["command"] = "printf '{}' | " + target["command"]
            if case.startswith("host-timeout"):
                target["command"] = "sleep 3; " + target["command"]
                target["timeout"] = 1
            if case == "monitor":
                for entries in hooks["hooks"].values():
                    entries[0]["command"] = entries[0]["command"].replace(
                        f":{port}", f":{monitor_port}"
                    )
            if case == "disabled":
                hooks = {"hooks": {}}
            write_json(hook_file, hooks)
            time.sleep(2)  # Let the editor observe the configuration change.
            observed = monitor_captures if case == "monitor" else captures
            before = len(observed)
            write_json(
                workspace / "fixture.json",
                {
                    "case": case,
                    "prompt": prompt + " synthetic Local fixture.",
                    "toolValue": value,
                },
            )
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                done = [
                    r
                    for r in records(workspace / "report.jsonl")
                    if r.get("case") == case and (r.get("done") or r.get("error"))
                ]
                if done:
                    break
                time.sleep(0.2)
            else:
                raise RuntimeError(f"Case did not finish: {case}; inspect the test window")
            result = done[-1]
            summary = {
                "case": case,
                "marker": result.get("marker"),
                "model_calls": result.get("calls"),
                "agent": result.get("agent"),
                "stages": [p["state"]["stage"] for p in observed[before:]],
            }
            assert not result.get("error"), f"Fixture error in {case}; inspect local report"
            assert summary == {
                "case": case,
                "marker": marker,
                "model_calls": calls,
                "agent": "github.copilot.editsAgent",
                "stages": stages,
            }, summary
            if case.startswith("host-timeout"):
                # Require explicit host timeout evidence, not just missing hook events.
                assert timeout_count(root, event) > timeouts_before, "No host timeout evidence"
            summary["passed"] = True
            report.append(summary)
            write_json(root / "acceptance.json", report)
            print(json.dumps(summary), flush=True)
    finally:
        write_json(hook_file, base)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--copilot-extension", required=True, type=Path)
    parser.add_argument("--state-dir", type=Path, help="Dedicated short test-profile path")
    args = parser.parse_args()
    root = (
        args.state_dir
        if args.state_dir is not None
        else Path(tempfile.mkdtemp(prefix="hw-vscode-", dir="/tmp"))
    ).resolve()
    # Leave room for VS Code's versioned IPC socket under macOS's 103-byte limit.
    if sys.platform == "darwin" and len(os.fsencode(root / "profile")) > 80:
        parser.error("Test profile path is too long for macOS IPC; use a short --state-dir")
    print(f"Private test state: {root}", flush=True)
    workspace = root / "workspace"
    (workspace / ".github/hooks").mkdir(parents=True, exist_ok=True)
    (root / "profile/User").mkdir(parents=True, exist_ok=True)
    write_json(
        root / "profile/User/settings.json",
        {
            "telemetry.telemetryLevel": "off",
            "update.mode": "none",
            "extensions.autoUpdate": False,
            "security.workspace.trust.enabled": False,
            "chat.useHooks": True,
            "chat.tools.autoApprove": True,
            "chat.disableAIFeatures": False,
        },
    )
    write_json(workspace / "fixture.json", {})
    (workspace / "report.jsonl").unlink(missing_ok=True)
    captures, monitor_captures = [], []
    with server(policy_app(root / "policies", "copilot_local", captures=captures)) as port:
        with server(
            policy_app(
                root / "monitor-policies",
                "copilot_local",
                mode="monitor",
                captures=monitor_captures,
            )
        ) as monitor_port:
            base = {
                "hooks": {
                    event: [
                        {
                            "type": "command",
                            "timeout": 15,
                            "command": shlex.join(
                                [
                                    sys.executable,
                                    "-m",
                                    "humanwill_policies",
                                    "hook",
                                    "--runtime",
                                    "copilot_local",
                                    "--event",
                                    event,
                                    "--url",
                                    f"http://127.0.0.1:{port}",
                                    "--token-env",
                                    "HOST_FIXTURE_TOKEN",
                                ]
                            ),
                        }
                    ]
                    for event in ("UserPromptSubmit", "PreToolUse")
                }
            }
            write_json(workspace / ".github/hooks/humanwill.json", base)
            env = {
                k: v
                for k, v in os.environ.items()
                if k in ("PATH", "HOME", "TMPDIR", "USER", "SHELL", "LANG")
            }
            env.update(
                COPILOT_HOME=str(root / "copilot-home"),
                HOST_FIXTURE_TOKEN=TOKEN,
            )
            with (root / "code.log").open("w") as log:
                process = subprocess.Popen(
                    [
                        str(args.binary.resolve()),
                        "--user-data-dir",
                        str(root / "profile"),
                        "--extensions-dir",
                        str(root / "extensions"),
                        "--extensionDevelopmentPath="
                        + str(Path(__file__).with_name("vscode_fixture").resolve()),
                        "--extensionDevelopmentPath=" + str(args.copilot_extension.resolve()),
                        "--skip-welcome",
                        "--skip-release-notes",
                        "--disable-updates",
                        str(workspace),
                    ],
                    env=env,
                    stdout=log,
                    stderr=log,
                )
                try:
                    input(
                        "Complete Copilot sign-in in the separate test window, then press Enter: "
                    )
                    run_cases(root, base, port, monitor_port, captures, monitor_captures)
                finally:
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)


if __name__ == "__main__":
    main()
