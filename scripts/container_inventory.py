"""Capture installed Debian/Python packages and license texts in the built image.

Run inside the release container without networking. This is a package/license
inventory, not a dependency graph, vulnerability scan or legal certification.
"""

import argparse
import hashlib
import json
import platform
import subprocess
from importlib.metadata import distributions
from pathlib import Path


def license_record(path):
    data = path.read_bytes()
    return {
        "path": str(path),
        "sha256": hashlib.sha256(data).hexdigest(),
        "text": data.decode("utf-8", errors="replace"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-image", required=True)
    parser.add_argument("--image-id", required=True)
    args = parser.parse_args()
    installed = subprocess.check_output(
        ["dpkg-query", "-W", "-f=${Package}\t${Version}\t${Architecture}\n"],
        text=True,
    )
    debian = []
    for line in installed.splitlines():
        name, version, architecture = line.split("\t")
        copyright_path = Path("/usr/share/doc") / name / "copyright"
        debian.append(
            {
                "name": name,
                "version": version,
                "architecture": architecture,
                "copyright": license_record(copyright_path) if copyright_path.is_file() else None,
            }
        )
    python = []
    for dist in distributions():
        licenses = []
        for file in dist.files or []:
            source = str(file)
            if ".dist-info/" in source and any(
                key in source.lower() for key in ("license", "copying", "notice")
            ):
                path = Path(dist.locate_file(file))
                if path.is_file():
                    licenses.append(license_record(path))
        python.append(
            {
                "name": dist.metadata["Name"],
                "version": dist.version,
                "license_expression": dist.metadata.get("License-Expression"),
                "license_metadata": dist.metadata.get("License"),
                "license_files": licenses,
            }
        )
    report = {
        "schema": "humanwill/container-inventory/1",
        "scope": "Installed packages and license texts; not a vulnerability or legal assessment",
        "base_image": args.base_image,
        "image_id": args.image_id,
        "os_release": Path("/etc/os-release").read_text(),
        "python_version": platform.python_version(),
        "python_license": license_record(Path("/usr/local/lib/python3.11/LICENSE.txt")),
        "common_licenses": [
            license_record(path)
            for path in sorted(Path("/usr/share/common-licenses").iterdir())
            if path.is_file()
        ],
        "debian_packages": sorted(debian, key=lambda item: item["name"]),
        "python_packages": sorted(python, key=lambda item: item["name"].lower()),
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
