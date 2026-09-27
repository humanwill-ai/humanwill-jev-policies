"""Small offline CLI. JSON errors never echo YAML source or provider credentials."""

import argparse
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
    return parser


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
        if args.command == "schema":
            print(json.dumps(schema(args.name), indent=2))
            return 0
        if args.command == "init-demo":
            _init_demo(args.destination)
            print(f"Created offline demo: {args.destination}")
            return 0
        bundle, configuration = load_project(args.root, args.config, args.entrypoint)
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
