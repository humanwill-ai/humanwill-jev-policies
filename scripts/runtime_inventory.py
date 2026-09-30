"""Record the pinned Python runtime dependencies and their installed license texts.

Run using a fresh environment containing requirements.txt; excludes build tools,
optional hosts, OS/base-image packages and hosted services. No network access.
"""

import argparse
import hashlib
import json
import re
import tomllib
from importlib.metadata import distribution
from pathlib import Path

LICENSES = {
    "pyyaml": "MIT",
    "jsonschema": "MIT",
    "attrs": "MIT",
    "jsonschema-specifications": "MIT",
    "referencing": "MIT",
    "rpds-py": "MIT",
    "typing-extensions": "PSF-2.0",
    "httpx": "BSD-3-Clause",
    "httpcore": "BSD-3-Clause",
    "anyio": "MIT",
    "h11": "MIT",
    "certifi": "MPL-2.0",
    "idna": "BSD-3-Clause",
    "starlette": "BSD-3-Clause",
    "uvicorn": "BSD-3-Clause",
    "click": "BSD-3-Clause",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()
    project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
    components, inventory = [], []
    for line in (root / "requirements.txt").read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        name, version = line.split("==")
        name = re.sub(r"[-_.]+", "-", name.lower())
        dist = distribution(name)
        if dist.version != version:
            raise ValueError(f"Installed version differs from lock: {name}")
        license_id = LICENSES[name]
        declared = dist.metadata.get("License-Expression")
        if declared and declared != license_id:
            raise ValueError(f"Review changed license expression: {name}")
        files = []
        for file in dist.files or []:
            source = str(file)
            if ".dist-info/" not in source or not any(
                key in source.lower() for key in ("license", "copying", "notice")
            ):
                continue
            data = dist.locate_file(file).read_bytes()
            target = root / "third_party/licenses" / name / Path(source).name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            files.append(
                {
                    "path": str(target.relative_to(root)),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            )
        if not files:
            raise ValueError(f"No license text found: {name}")
        purl = f"pkg:pypi/{name}@{version}"
        inventory.append({"name": name, "version": version, "license": license_id, "files": files})
        components.append(
            {
                "type": "library",
                "bom-ref": purl,
                "name": name,
                "version": version,
                "purl": purl,
                "licenses": [{"license": {"id": license_id}}],
            }
        )
    ref = f"pkg:pypi/{project['name']}@{project['version']}"
    bom = {
        "$schema": "http://cyclonedx.org/schema/bom-1.6.schema.json",
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "bom-ref": ref,
                "name": project["name"],
                "version": project["version"],
                "purl": ref,
                "licenses": [{"license": {"id": project["license"]}}],
            },
            "properties": [
                {
                    "name": "humanwill:scope",
                    "value": "Pinned Python runtime lock; excludes tools, hosts and OS/container",
                }
            ],
        },
        "components": sorted(components, key=lambda c: c["name"]),
        # The lock is a flattened inventory; do not invent a transitive dependency graph.
    }
    target = root / "docs/evidence"
    target.mkdir(exist_ok=True)
    for name, value in [
        ("runtime-sbom.cdx.json", bom),
        ("runtime-licenses.json", sorted(inventory, key=lambda c: c["name"])),
    ]:
        (target / name).write_text(json.dumps(value, indent=2) + "\n")
    table = "\n".join(
        f"| {r['name']} | {r['version']} | {r['license']} | "
        f"[License text]({r['files'][0]['path']}) |"
        for r in sorted(inventory, key=lambda r: r["name"])
    )
    (root / "THIRD_PARTY_NOTICES.md").write_text(
        "# Third-party dependencies and notices\n\n"
        "The project does not relicense its dependencies. The following Python runtime\n"
        "packages are pinned in requirements.txt; their unmodified installed license\n"
        "texts are retained under third_party/licenses. No implementation is vendored.\n\n"
        "| Dependency | Version | License | Preserved notice |\n"
        "| --- | --- | --- | --- |\n" + table + "\n\n"
        "[CycloneDX inventory](docs/evidence/runtime-sbom.cdx.json) and\n"
        "[license-file hashes](docs/evidence/runtime-licenses.json) are reproducible with\n"
        "`python scripts/runtime_inventory.py` in the locked runtime environment.\n"
        "This flattened inventory does not claim an audited transitive relationship graph.\n\n"
        "Certifi includes Mozilla CA certificate material under MPL-2.0; retaining this\n"
        "license does not turn HumanWill code into MPL-licensed software. Preserve the\n"
        "dependency's license/source obligations when redistributing it. Python typing\n"
        "extensions retain the full PSF license/history and included notices.\n\n"
        "Build/test tools, optional gateway/editor/CLI hosts, hosted Jev/OpenRouter, and\n"
        "the container's Python/OS base are outside this runtime inventory and retain\n"
        "their own terms. Generate an image-specific inventory and review those notices\n"
        "when the final container is built. No upstream integration implementation or\n"
        "benchmark question pack is vendored by this project.\n"
    )
    print(f"Inventoried {len(inventory)} pinned runtime packages; no network requests")


if __name__ == "__main__":
    main()
