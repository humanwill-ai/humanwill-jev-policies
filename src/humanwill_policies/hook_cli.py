"""Minimal command interface for the separately installable HTTP hook client."""

import argparse

from . import __version__


def add_hook_arguments(parser):
    parser.add_argument("--runtime", required=True, choices=("copilot_local", "copilot_cli"))
    parser.add_argument(
        "--event",
        required=True,
        choices=("UserPromptSubmit", "PreToolUse", "userPromptSubmitted", "preToolUse"),
    )
    parser.add_argument("--url", default="http://127.0.0.1:8088")
    parser.add_argument("--token-env", default="HUMANWILL_HOOK_TOKEN")
    parser.add_argument(
        "--timeout-ms", type=int, choices=range(100, 60001), default=6000, metavar="100..60000"
    )
    parser.add_argument("--on-error", choices=("block", "allow_monitor"), default="block")


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="humanwill-hook", description="Check a Copilot hook event through a policy service."
    )
    parser.add_argument("--version", action="version", version=__version__)
    add_hook_arguments(parser)
    args = parser.parse_args(argv)
    from .hooks import run

    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
