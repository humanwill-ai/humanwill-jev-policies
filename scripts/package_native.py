"""Audit runtime linkage, package a tested binary, and retain its exact evidence."""

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def output(*command):
    return subprocess.check_output([str(x) for x in command], text=True, stderr=subprocess.STDOUT)


def audit(binary):
    system = platform.system()
    if system == "Darwin":
        text = output("otool", "-L", binary)
        libraries = [line.strip().split(" (")[0] for line in text.splitlines()[1:]]
        assert all(p.startswith(("/usr/lib/", "/System/Library/")) for p in libraries), text
        assert not any("libcurl" in p or "libssl" in p or "libcrypto" in p for p in libraries), text
    elif system == "Windows":
        vswhere = (
            Path(os.environ["ProgramFiles(x86)"]) / "Microsoft Visual Studio/Installer/vswhere.exe"
        )
        install = output(vswhere, "-latest", "-property", "installationPath").strip()
        dumpbin = sorted((Path(install) / "VC/Tools/MSVC").glob("*/bin/Hostx64/x64/dumpbin.exe"))[
            -1
        ]
        text = output(dumpbin, "/DEPENDENTS", binary)
        libraries = re.findall(r"^\s+([\w.-]+\.dll)\s*$", text, re.MULTILINE | re.IGNORECASE)
        allowed = {
            "kernel32.dll",
            "ws2_32.dll",
            "bcrypt.dll",
            "crypt32.dll",
            "secur32.dll",
            "advapi32.dll",
            "normaliz.dll",
            "user32.dll",
            "iphlpapi.dll",
            "ntdll.dll",
        }
        assert libraries and all(
            p.lower() in allowed or p.lower().startswith("api-ms-win-") for p in libraries
        ), text
    else:
        text = output("readelf", "-l", binary) + output("readelf", "-d", binary)
        assert "INTERP" not in text and "(NEEDED)" not in text, text
        libraries = []
    return {"libraries": libraries, "audit_output": text, "non_system_shared_dependencies": []}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workdir", required=True, type=Path)
    parser.add_argument("--outdir", required=True, type=Path)
    args = parser.parse_args()
    work, out = args.workdir.resolve(), args.outdir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((work / "build-manifest.json").read_text())
    filename = "humanwill-hook-c" + (".exe" if platform.system() == "Windows" else "")
    binary = work / "bin" / filename
    manifest["linkage"] = audit(binary)
    version = output(binary, "--version").strip()
    name = "humanwill-hook-c-" + version + "-" + manifest["target"]
    package = work / "package" / name
    if package.exists():
        raise ValueError("Use a fresh package directory")
    package.mkdir(parents=True)
    shutil.copy2(binary, package / filename)
    for source in ("LICENSE", "NOTICE", "THIRD_PARTY_NOTICES.md"):
        shutil.copy2(ROOT / source, package / source)
    shutil.copy2(ROOT / "clients/hook-c/README.md", package / "README.md")
    shutil.copytree(work / "licenses", package / "licenses")
    evidence = package / "evidence"
    evidence.mkdir()
    for file in sorted(work.glob("*verification*.json")):
        shutil.copy2(file, evidence / file.name)
    if not list(evidence.iterdir()):
        raise ValueError("Contract verification report missing")
    manifest["version"] = version
    manifest["binary_sha256"] = hashlib.sha256(binary.read_bytes()).hexdigest()
    (package / "build-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (package / "SHA256SUMS").write_text(manifest["binary_sha256"] + "  " + filename + "\n")
    if platform.system() == "Windows":
        archive = out / (name + ".zip")
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
            for file in sorted(package.rglob("*")):
                if file.is_file():
                    z.write(file, file.relative_to(package.parent))
    else:
        archive = out / (name + ".tar.gz")
        with tarfile.open(archive, "w:gz") as t:
            t.add(package, arcname=name)
    (out / (archive.name + ".sha256")).write_text(
        hashlib.sha256(archive.read_bytes()).hexdigest() + "  " + archive.name + "\n"
    )
    # The exact archive must extract and start outside the build tree, even in a path with spaces.
    extracted = work / "extracted package"
    extracted.mkdir(exist_ok=False)
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as z:
            z.extractall(extracted)
    else:
        with tarfile.open(archive) as t:
            t.extractall(extracted, filter="data")
    installed = extracted / name / filename
    assert hashlib.sha256(installed.read_bytes()).hexdigest() == manifest["binary_sha256"]
    assert output(installed, "--version").strip() == version
    manifest["extracted_archive_smoke"] = "pass"
    (out / (name + "-verification.json")).write_text(json.dumps(manifest, indent=2) + "\n")
    print(archive)


if __name__ == "__main__":
    main()
