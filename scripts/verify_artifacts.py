"""Install exact wheel/sdist outside checkout; run packaged demo and offline contracts.

This downloads locked dependencies but never invokes a hosted evaluator. Run with
Python 3.11–3.14. Artifacts are inputs, never rebuilt from the developer checkout.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import venv
from pathlib import Path


def run(command, cwd, env, *, output=False):
    result = subprocess.run(
        [str(arg) for arg in command],
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE if output else None,
        check=True,
        timeout=240,
    )
    return result.stdout if output else None


def extract(source, destination):
    # Reject links and non-regular members; do not trust archive paths.
    with tarfile.open(source) as archive:
        for member in archive.getmembers():
            path = Path(member.name)
            if path.is_absolute() or ".." in path.parts or not (member.isdir() or member.isfile()):
                raise ValueError("Unsafe source archive member")
        archive.extractall(destination, filter="data")
    roots = list(destination.iterdir())
    if len(roots) != 1 or not roots[0].is_dir():
        raise ValueError("Expected one source archive root")
    return roots[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", required=True, type=Path)
    parser.add_argument("--sdist", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    wheel, sdist = args.wheel.resolve(strict=True), args.sdist.resolve(strict=True)
    if args.report.exists():
        parser.error("Report already exists; use a new evidence path")
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    environment.pop("PYTHONOPTIMIZE", None)
    environment["PYTHONNOUSERSITE"] = "1"
    environment["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    report = {"python": sys.version, "artifacts": {}, "checks": {}}
    for artifact in (wheel, sdist):
        report["artifacts"][artifact.name] = hashlib.sha256(artifact.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix="humanwill-artifacts-") as directory:
        root = Path(directory).resolve()
        environment["PIP_CACHE_DIR"] = str(root / "pip-cache")
        unpack = root / "source"
        unpack.mkdir()
        source = extract(sdist, unpack)
        for name in (
            "Dockerfile",
            ".dockerignore",
            "scripts/verify_artifacts.py",
            "scripts/artifact_runtime.py",
            "docs/quickstart.md",
            "CHANGELOG.md",
        ):
            if not (source / name).is_file():
                raise ValueError(f"Source distribution missing {name}")
        # All verification scripts/fixtures come from the source artifact.
        tests = root / "tests"
        shutil.copytree(source / "tests", tests)
        for kind, artifact in (("wheel", wheel), ("sdist", sdist)):
            work = root / kind
            work.mkdir()
            venv.EnvBuilder(with_pip=True, symlinks=True).create(work / "env")
            python = work / "env/bin/python"
            cli = work / "env/bin/humanwill-policies"
            run(
                [python, "-m", "pip", "install", "-r", source / "requirements.txt"],
                work,
                environment,
            )
            if kind == "sdist":
                # Fixed build backend, with no editable checkout or build-isolation dependency.
                import tomllib

                requirements = tomllib.loads((source / "pyproject.toml").read_text())[
                    "build-system"
                ]["requires"]
                run([python, "-m", "pip", "install", *requirements], work, environment)
            run(
                [python, "-m", "pip", "install", "--no-deps", "--no-build-isolation", artifact],
                work,
                environment,
            )
            run([python, "-m", "pip", "check"], work, environment)
            origin = run(
                [python, "-c", "import humanwill_policies; print(humanwill_policies.__file__)"],
                work,
                environment,
                output=True,
            ).strip()
            if not Path(origin).resolve().is_relative_to((work / "env").resolve()):
                raise ValueError("Imported developer checkout instead of installed artifact")
            run([cli, "init-demo", "demo"], work, environment)
            run(
                [cli, "validate", "demo", "--config", "demo/config.yaml", "--json"],
                work,
                environment,
            )
            run(
                [
                    cli,
                    "preview",
                    "demo",
                    "--config",
                    "demo/config.yaml",
                    "--stage",
                    "prompt",
                    "--json",
                ],
                work,
                environment,
                output=True,
            )
            run([cli, "schema", "request"], work, environment, output=True)
            result = json.loads(
                run(
                    [
                        cli,
                        "evaluate",
                        "demo",
                        "--config",
                        "demo/config.yaml",
                        "--request",
                        "demo/request.json",
                        "--mock-answers",
                        "demo/mock-answers.json",
                        "--json",
                    ],
                    work,
                    environment,
                    output=True,
                )
            )
            if result["decision"] != "allow" or not result["simulated"]:
                raise ValueError("Offline demo did not produce its scripted allow")
            # Existing meaningful contracts include gateway pre/post, both hook dialects,
            # monitor/deny/error, authentication, unsupported coverage and metadata trust.
            run(
                [python, "-m", "unittest", "discover", "-s", tests, "-p", "test_service.py", "-v"],
                work,
                environment,
            )
            runtime = json.loads(
                run(
                    [python, source / "scripts/artifact_runtime.py", "--cli", cli, "--root", work],
                    work,
                    environment,
                    output=True,
                )
            )
            report["checks"][kind] = {
                "installed_version": run(
                    [cli, "--version"], work, environment, output=True
                ).strip(),
                "offline_demo": "pass",
                "service_and_hook_contracts": "pass",
                "service_process": runtime,
            }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
