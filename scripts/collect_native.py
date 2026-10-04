"""Collect tested Actions archives and complete notices without changing binaries."""

import argparse
import hashlib
import json
import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, nargs="+", required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()
    out = args.outdir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    records = []
    for source in args.artifacts:
        downloads = source / "native-downloads"
        archive = next(downloads.glob("*.zip"), None) or next(downloads.glob("*.tar.gz"))
        original_sha = sha(archive)
        assert (downloads / (archive.name + ".sha256")).read_text().split()[0] == original_sha
        audit = json.loads(next(downloads.glob("humanwill-*-verification.json")).read_text())
        contract = json.loads((source / "native/contract-verification.json").read_text())
        assert audit["extracted_archive_smoke"] == "pass"
        assert audit["linkage"]["non_system_shared_dependencies"] == []
        assert contract["passed"] == 108
        assert contract["binary_sha256"] == audit["binary_sha256"]
        target = audit["target"]
        stage = out / "extracted" / target
        stage.mkdir(parents=True, exist_ok=False)
        if archive.suffix == ".zip":
            with zipfile.ZipFile(archive) as z:
                z.extractall(stage)
        else:
            with tarfile.open(archive) as t:
                t.extractall(stage, filter="data")
        package = next(stage.iterdir())
        binary = package / (
            "humanwill-hook-c.exe" if target.startswith("windows") else "humanwill-hook-c"
        )
        assert sha(binary) == audit["binary_sha256"]
        # Only accompanying documentation/evidence changes; the CI-tested executable is exact.
        shutil.copy2(ROOT / "THIRD_PARTY_NOTICES.md", package)
        shutil.copy2(ROOT / "clients/hook-c/README.md", package / "README.md")
        if target == "linux-x86_64":
            for notice in (ROOT / "clients/hook-c/vendor/runtime-licenses").iterdir():
                shutil.copy2(notice, package / "licenses" / notice.name)
            shutil.copy2(source / "native/alpine-inventory.txt", package / "evidence")
            for name in ("ubuntu-contract-verification.json", "ubuntu-service-verification.json"):
                shutil.copy2(downloads / name, package / "evidence" / name)
        shutil.copy2(
            next(downloads.glob("humanwill-*-verification.json")),
            package / "evidence/build-verification.json",
        )
        provenance = {
            "original_ci_archive_sha256": original_sha,
            "binary_sha256_unchanged": sha(binary),
            "binary_source_commit": audit["source_commit"],
            "packaging_source_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "changes": "Accompanying README, notices and verification evidence only",
        }
        (package / "packaging-provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
        final = out / archive.name
        if final.exists():
            raise ValueError("Refusing to overwrite " + str(final))
        if final.suffix == ".zip":
            with zipfile.ZipFile(final, "w", zipfile.ZIP_DEFLATED) as z:
                for file in sorted(package.rglob("*")):
                    if file.is_file():
                        z.write(file, file.relative_to(stage))
            with zipfile.ZipFile(final) as z:
                packaged_binary = z.read(str(binary.relative_to(stage)))
        else:
            with tarfile.open(final, "w:gz") as t:
                t.add(package, arcname=package.name)
            with tarfile.open(final) as t:
                packaged_binary = t.extractfile(str(binary.relative_to(stage))).read()
        assert hashlib.sha256(packaged_binary).hexdigest() == audit["binary_sha256"]
        digest = sha(final)
        (out / (final.name + ".sha256")).write_text(digest + "  " + final.name + "\n")
        records.append(
            {
                "target": target,
                "archive": final.name,
                "archive_sha256": digest,
                "binary_sha256": sha(binary),
                "binary_bytes": binary.stat().st_size,
                "archive_bytes": final.stat().st_size,
                "system": audit["system"],
                "source_commit": audit["source_commit"],
                "contract_checks": contract["passed"],
                "linkage": audit["linkage"]["libraries"],
                "packaging": provenance,
            }
        )
    (out / "SHA256SUMS").write_text(
        "".join(r["archive_sha256"] + "  " + r["archive"] + "\n" for r in records)
    )
    (out / "inventory.json").write_text(json.dumps(records, indent=2) + "\n")
    print(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()
