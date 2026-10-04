"""Build a standalone hook wheel/sdist from an explicit allowlist of shared source.

No second protocol implementation or runtime dependency on humanwill-policies.
Only the package initializer and __main__ are distribution-specific. Builds never
include local artifacts, company policies, credentials, or provider transports.
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

MODULES = ("contracts", "errors", "hook_cli", "hook_events", "hooks", "json_codec")
SCHEMAS = ("request", "result", "result-v2", "result-v3", "result-v4")


def stage(root, destination):
    config = root / "clients/hook"
    version = tomllib.loads((config / "pyproject.toml").read_text())["project"]["version"]
    package = destination / "src/humanwill_hook_client"
    (package / "schemas").mkdir(parents=True)
    manifest = {}
    for source, target in [
        *((root / f"src/humanwill_policies/{name}.py", package / f"{name}.py") for name in MODULES),
        *(
            (root / f"src/humanwill_policies/schemas/{name}.json", package / f"schemas/{name}.json")
            for name in SCHEMAS
        ),
        *(
            (config / name, destination / name)
            for name in ("pyproject.toml", "README.md", "requirements.txt")
        ),
        *((root / name, destination / name) for name in ("LICENSE", "NOTICE", "LICENSING.md")),
    ]:
        shutil.copyfile(source, target)
        manifest[str(source.relative_to(root))] = hashlib.sha256(source.read_bytes()).hexdigest()
    (package / "__init__.py").write_text(
        f'"""Remote policy hook client; no local policy engine."""\n\n__version__ = "{version}"\n'
    )
    (package / "__main__.py").write_text("from .hook_cli import main\n\nraise SystemExit(main())\n")
    dependencies = [
        line.split("==")[0].lower()
        for line in (config / "requirements.txt").read_text().splitlines()
        if "==" in line
    ]
    for name in dependencies:
        shutil.copytree(
            root / f"third_party/licenses/{name}", destination / f"third_party/licenses/{name}"
        )
    (destination / "MANIFEST.in").write_text(
        "include requirements.txt SOURCE_MANIFEST.json LICENSING.md\n"
        "recursive-include third_party/licenses *\n"
    )
    (destination / "SOURCE_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    out = args.outdir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if list(out.iterdir()):
        parser.error("Use an empty output directory; preserve earlier artifacts")
    with tempfile.TemporaryDirectory(prefix="humanwill-hook-build-") as directory:
        project = Path(directory)
        stage(root, project)
        subprocess.run(
            [sys.executable, "-m", "build", "--no-isolation", "--outdir", str(out), str(project)],
            check=True,
        )


if __name__ == "__main__":
    main()
