"""Small offline CLI. JSON errors never echo YAML source or provider credentials."""

import argparse
import asyncio
import json
import shutil
import sys
import tempfile
from importlib.resources import as_file, files
from pathlib import Path

from . import __version__
from .config import load_project, preview
from .contracts import SCHEMAS, STAGES, schema
from .errors import PolicyError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="humanwill-policies", description="Validate and preview policy bundles offline."
    )
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "preview"):
        command = commands.add_parser(name)
        command.add_argument("root", type=Path)
        command.add_argument("--entrypoint", default="policies.md")
        command.add_argument("--config", type=Path)
        command.add_argument("--json", action="store_true")
        if name == "preview":
            command.add_argument("--stage", choices=STAGES)
    commands.add_parser("schema").add_argument("name", choices=SCHEMAS)
    commands.add_parser("init-demo").add_argument("destination", type=Path)
    evaluate = commands.add_parser("evaluate", help="Assess an event; mock by default")
    evaluate.add_argument("root", type=Path)
    evaluate.add_argument("--entrypoint", default="policies.md")
    evaluate.add_argument("--config", required=True, type=Path)
    evaluate.add_argument("--request", required=True, type=Path)
    evaluate.add_argument("--backend", choices=("mock", "configured"), default="mock")
    evaluate.add_argument("--mock-answers", type=Path)
    evaluate.add_argument(
        "--allow-external",
        action="store_true",
        help="Authorize disclosing this event and policy bundle to the hosted evaluator",
    )
    evaluate.add_argument("--json", action="store_true")
    serve = commands.add_parser("serve", help="Run the authenticated policy service")
    serve.add_argument("root", type=Path)
    serve.add_argument("--entrypoint", default="policies.md")
    serve.add_argument("--config", required=True, type=Path)
    serve.add_argument("--service-config", required=True, type=Path)
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8088)
    hook = commands.add_parser("hook", help="Read a Copilot hook event from stdin")
    hook.add_argument("--runtime", required=True, choices=("copilot_local", "copilot_cli"))
    hook.add_argument(
        "--event",
        required=True,
        choices=("UserPromptSubmit", "PreToolUse", "userPromptSubmitted", "preToolUse"),
    )
    hook.add_argument("--url", default="http://127.0.0.1:8088")
    hook.add_argument("--token-env", default="HUMANWILL_HOOK_TOKEN")
    hook.add_argument(
        "--timeout-ms", type=int, choices=range(100, 60001), default=6000, metavar="100..60000"
    )
    hook.add_argument("--on-error", choices=("block", "allow_monitor"), default="block")
    mcp = commands.add_parser("agentgateway-mcp", help="Run the loopback ExtMCP policy connector")
    mcp.add_argument("--url", default="http://127.0.0.1:8088")
    mcp.add_argument("--token-env", default="HUMANWILL_MCP_TOKEN")
    mcp.add_argument("--gateway-token-env", default="HUMANWILL_AGENTGATEWAY_MCP_TOKEN")
    mcp.add_argument("--target", action="append", required=True)
    mcp.add_argument("--port", type=int, choices=range(1, 65536), default=9001, metavar="1..65535")
    mcp.add_argument("--timeout-ms", type=int, default=6000)
    mcp.add_argument("--max-in-flight", type=int, default=8)
    return parser


def _read_json(path: Path) -> dict:
    import os
    import stat

    from .providers import decode_json

    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise PolicyError("invalid_file", "JSON input must be a regular file")
        data = stream.read(262145)
    if len(data) > 262144:
        raise PolicyError("payload_limit", "JSON input exceeds 262144 bytes")
    return decode_json(data)


def _evaluate(args, bundle, configuration):
    from .evaluation import Evaluator
    from .providers import JevBackend, MockBackend
    from .runtime import EgressPermit
    from .serialization import digest

    request = _read_json(args.request)
    if args.backend == "mock":
        if args.mock_answers is None or args.allow_external:
            raise PolicyError(
                "invalid_options", "Mock evaluation requires answers and no external opt-in"
            )
        backend = MockBackend(_read_json(args.mock_answers))
        permit = None
    else:
        if not args.allow_external or args.mock_answers is not None:
            raise PolicyError(
                "invalid_options",
                "Configured evaluation requires external opt-in and no mock answers",
            )
        provider = configuration.to_dict().get("provider")
        if not provider:
            raise PolicyError("missing_provider", "Configure an explicit evaluator provider")
        backend = JevBackend(provider)
        permit = EgressPermit(digest(request), bundle.sha256, backend.transport)
    result = asyncio.run(Evaluator(bundle, configuration, backend).evaluate(request, egress=permit))
    print(json.dumps(result, indent=2))
    return 0 if result["decision"] == "allow" else 3 if result["decision"] == "block" else 4


def _init_demo(destination: Path) -> None:
    if destination.exists() or destination.is_symlink():
        raise PolicyError("destination_exists", "Demo destination must not already exist")
    if not destination.parent.is_dir():
        raise PolicyError("invalid_destination", "Demo parent directory must already exist")
    # Copy into a sibling temp directory first; a failed copy leaves no partial demo.
    with tempfile.TemporaryDirectory(prefix=".humanwill-demo-", dir=destination.parent) as tmp:
        staged = Path(tmp) / "demo"
        # as_file(directory) is not available until Python 3.12; traverse resource files.
        staged.mkdir()
        resource = files("humanwill_policies").joinpath("demo")
        for child in resource.iterdir():
            if child.is_file():
                with as_file(child) as source:
                    shutil.copyfile(source, staged / child.name)
            elif child.name == "rules":
                (staged / "rules").mkdir()
                for rule in child.iterdir():
                    with as_file(rule) as source:
                        shutil.copyfile(source, staged / "rules" / rule.name)
        # mkdir is exclusive even if another process created the destination after the check.
        destination.mkdir()
        try:
            for child in staged.iterdir():
                shutil.move(str(child), destination / child.name)
        except OSError:
            shutil.rmtree(destination)
            raise


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "agentgateway-mcp":
            try:
                from .connectors.agentgateway_mcp import run
            except ImportError:
                raise PolicyError(
                    "missing_extra", "Install humanwill-policies[agentgateway-mcp]"
                ) from None
            return run(args)
        if args.command == "hook":
            from .hooks import run

            return run(args)
        if args.command == "serve":
            import logging

            import uvicorn

            from .evaluation import Evaluator
            from .providers import JevBackend
            from .service import create_app, read_settings

            bundle, configuration = load_project(args.root, args.config, args.entrypoint)
            provider = configuration.to_dict().get("provider")
            if not provider:
                raise PolicyError("missing_provider", "Configure an evaluator provider")
            app = create_app(
                Evaluator(bundle, configuration, JevBackend(provider)),
                read_settings(args.service_config),
            )
            logging.basicConfig(level=logging.INFO, format="%(message)s")
            uvicorn.run(
                app,
                host=args.host,
                port=args.port,
                access_log=False,
                server_header=False,
                proxy_headers=False,
            )
            return 0
        if args.command == "schema":
            print(json.dumps(schema(args.name), indent=2))
            return 0
        if args.command == "init-demo":
            _init_demo(args.destination)
            print(f"Created offline demo: {args.destination}")
            return 0
        bundle, configuration = load_project(args.root, args.config, args.entrypoint)
        if args.command == "evaluate":
            return _evaluate(args, bundle, configuration)
        if args.command == "validate":
            result = {
                "valid": True,
                "bundle_id": bundle.id,
                "bundle_sha256": bundle.sha256,
                "policy_count": len(bundle.policies),
                "source_count": len(bundle.sources),
                "configuration_sha256": configuration.sha256 if configuration else None,
                "scope": "bundle_and_configuration" if configuration else "bundle_only",
                "runtime_available": False,
            }
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(
                    f"Valid {result['scope']}: {bundle.id}; {len(bundle.policies)} policies; "
                    f"sha256={bundle.sha256}"
                )
                print("Offline validation only. No model calls or enforcement.")
        else:
            result = preview(bundle, configuration, args.stage)
            if args.json:
                print(json.dumps(result, indent=2, ensure_ascii=True))
            else:
                print(f"Bundle {bundle.id} ({bundle.sha256})")
                for row in result["policies"]:
                    print(f"\n{row['id']} v{row['version']} [{row['status']}] {row['path']}")
                    print(f"Stages: {', '.join(row['stages'])}")
                    if row["issues"]:
                        print(f"Configuration issues: {', '.join(row['issues'])}")
                    print(row["body"].strip())
                print(f"\n{result['note']}")
        return 0
    except PolicyError as exc:
        if getattr(args, "json", False):
            print(json.dumps({"valid": False, "error": exc.to_dict()}), file=sys.stderr)
        else:
            print(str(exc), file=sys.stderr)
        return 2
    except OSError:
        print("io_error: Unable to complete filesystem operation", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
