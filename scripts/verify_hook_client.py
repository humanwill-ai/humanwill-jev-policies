"""Install baseline and standalone artifacts outside checkout; verify without Jev.

Run separately with each supported Python interpreter. The resulting isolated
Python paths are usable by benchmark_hook_client.py. Dependency installation uses
the reviewed locks; all contract checks use synthetic replies, never a provider.
"""

import argparse
import json
import os
import shutil
import subprocess
import tarfile
import venv
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-wheel", required=True, type=Path)
    parser.add_argument("--client-wheel", required=True, type=Path)
    parser.add_argument("--client-sdist", required=True, type=Path)
    parser.add_argument("--workdir", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    work = args.workdir.resolve()
    work.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONOPTIMIZE", None)
    env["PYTHONNOUSERSITE"] = "1"
    env["PIP_CACHE_DIR"] = str(work / "pip-cache")
    tests = work / "tests"
    (tests / "fixtures").mkdir(parents=True)
    for name in ["test_hook_client.py", "fixtures/result-hook.json"]:
        shutil.copyfile(root / "tests" / name, tests / name)
    with tarfile.open(args.client_sdist) as archive:
        archive.extractall(work / "source", filter="data")
    source = next((work / "source").iterdir())
    # The wheel and sdist are distinct clean environments, with no full service package.
    reports = {}
    for label, artifact, lock in [
        ("baseline", args.baseline_wheel, root / "requirements.txt"),
        ("client", args.client_wheel, source / "requirements.txt"),
        ("sdist", args.client_sdist, source / "requirements.txt"),
    ]:
        target = work / label
        venv.EnvBuilder(with_pip=True, symlinks=os.name != "nt").create(target)
        python = target / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

        def run(*command, **kwargs):
            return subprocess.run(
                [str(x) for x in command], cwd=work, env=env, check=True, **kwargs
            )

        run(python, "-m", "pip", "install", "-r", lock)
        run(python, "-m", "pip", "install", "--no-deps", artifact.resolve())
        run(python, "-m", "pip", "check")
        if label != "baseline":
            env["HUMANWILL_HOOK_TEST_PACKAGE"] = "humanwill_hook_client"
            run(python, "-m", "unittest", "discover", "-s", tests)
            run(
                python,
                "-c",
                "import importlib.util as u; "
                "assert all(u.find_spec(n) is None for n in "
                '["humanwill_policies","yaml","uvicorn","starlette"])',
            )
        reports[label] = {
            "python": str(python),
            "artifact": str(artifact.resolve()),
            "installed": True,
            "standalone_contracts": "pass" if label != "baseline" else "not_applicable",
        }
    (work / "verification.json").write_text(json.dumps(reports, indent=2) + "\n")
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
