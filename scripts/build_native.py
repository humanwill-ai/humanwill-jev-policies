"""Build a native hook with pinned static third-party libraries on the target OS."""

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "clients/hook-c"


def run(*command, cwd, env=None):
    subprocess.run([str(c) for c in command], cwd=cwd, env=env, check=True)


def unpack(dependency, work):
    archive = work / dependency["url"].rsplit("/", 1)[-1]
    if not archive.exists():
        with urlopen(dependency["url"], timeout=120) as response:
            archive.write_bytes(response.read())
    if hashlib.sha256(archive.read_bytes()).hexdigest() != dependency["sha256"]:
        raise ValueError("Dependency checksum mismatch: " + archive.name)
    with tarfile.open(archive) as source:
        first = Path(source.getnames()[0]).parts[0]
        if not (work / first).exists():
            source.extractall(work, filter="data")
    return work / first


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workdir", required=True, type=Path)
    parser.add_argument("--jobs", default=4, type=int)
    args = parser.parse_args()
    work = args.workdir.resolve()
    work.mkdir(parents=True, exist_ok=True)
    deps = json.loads((SOURCE / "dependencies.json").read_text())
    system, machine = platform.system(), platform.machine().lower()
    if system == "Darwin":
        target = "macos-arm64" if machine == "arm64" else "macos-x86_64"
    elif system == "Windows":
        target = "windows-x86_64"
    elif system == "Linux":
        if not list(Path("/lib").glob("ld-musl-x86_64.so.1")):
            raise ValueError("Linux release build requires x86_64 Alpine/musl container")
        target = "linux-x86_64"
    else:
        raise ValueError("Unsupported build target")
    curl_source = unpack(deps["curl"], work)
    config = [
        "-DCMAKE_BUILD_TYPE=Release",
        "-DPython3_EXECUTABLE=" + sys.executable,
        "-DFETCHCONTENT_SOURCE_DIR_CURL=" + str(curl_source),
    ]
    env = dict(os.environ)
    openssl_source = None
    if system != "Windows":
        openssl_source = unpack(deps["openssl"], work)
        prefix = work / "openssl-static"
        if system == "Darwin":
            env["MACOSX_DEPLOYMENT_TARGET"] = "12.0"
            openssl_target = "darwin64-arm64-cc" if machine == "arm64" else "darwin64-x86_64-cc"
            config += ["-DCMAKE_OSX_DEPLOYMENT_TARGET=12.0"]
        else:
            openssl_target = "linux-x86_64"
            config += ["-DHUMANWILL_FULL_STATIC=ON"]
        if not (prefix / "lib/libssl.a").exists():
            run(
                "perl",
                "Configure",
                openssl_target,
                "no-shared",
                "no-tests",
                "no-module",
                "no-dso",
                "no-engine",
                "no-legacy",
                "no-comp",
                "--libdir=lib",
                "--prefix=" + str(prefix),
                "--openssldir=/etc/ssl",
                cwd=openssl_source,
                env=env,
            )
            run("make", "-j" + str(args.jobs), "build_libs", cwd=openssl_source, env=env)
            run("make", "install_dev", cwd=openssl_source, env=env)
        config += ["-DOPENSSL_ROOT_DIR=" + str(prefix), "-DOPENSSL_USE_STATIC_LIBS=TRUE"]
    else:
        config += ["-A", "x64"]
    build = work / "build"
    run("cmake", "-S", SOURCE, "-B", build, *config, cwd=ROOT, env=env)
    run(
        "cmake",
        "--build",
        build,
        "--config",
        "Release",
        "--parallel",
        str(args.jobs),
        cwd=ROOT,
        env=env,
    )
    out = work / "bin"
    out.mkdir(exist_ok=True)
    for name in ("humanwill-hook-c", "canonical-probe"):
        filename = name + (".exe" if system == "Windows" else "")
        built = build / ("Release" if system == "Windows" else "") / filename
        shutil.copy2(built, out / filename)
    licenses = work / "licenses"
    licenses.mkdir(exist_ok=True)
    shutil.copy2(curl_source / "COPYING", licenses / "curl-LICENSE.txt")
    if openssl_source:
        shutil.copy2(openssl_source / "LICENSE.txt", licenses / "openssl-LICENSE.txt")
    shutil.copy2(SOURCE / "vendor/yyjson/LICENSE", licenses / "yyjson-LICENSE.txt")
    (work / "build-manifest.json").write_text(
        json.dumps(
            {
                "target": target,
                "system": platform.platform(),
                "dependencies": deps,
                "third_party_linkage": "static",
                "openssl_included": system != "Windows",
                "source_commit": subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
                ).strip(),
                "binary_sha256": hashlib.sha256(
                    (
                        out
                        / ("humanwill-hook-c.exe" if system == "Windows" else "humanwill-hook-c")
                    ).read_bytes()
                ).hexdigest(),
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
