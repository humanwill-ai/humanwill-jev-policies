"""Standalone artifact staging must use exact shared security code and schemas."""

import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_hook_client import MODULES, SCHEMAS, stage

ROOT = Path(__file__).resolve().parents[1]


class HookClientPackagingTests(unittest.TestCase):
    def test_allowlisted_package_uses_identical_protocol_code(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory)
            stage(ROOT, dest)
            package = dest / "src/humanwill_hook_client"
            for name in MODULES:
                self.assertEqual(
                    (package / f"{name}.py").read_bytes(),
                    (ROOT / f"src/humanwill_policies/{name}.py").read_bytes(),
                )
            for name in SCHEMAS:
                self.assertEqual(
                    (package / f"schemas/{name}.json").read_bytes(),
                    (ROOT / f"src/humanwill_policies/schemas/{name}.json").read_bytes(),
                )
            self.assertEqual(
                {p.stem for p in package.glob("*.py")}, set(MODULES) | {"__init__", "__main__"}
            )
            manifest = json.loads((dest / "SOURCE_MANIFEST.json").read_text())
            self.assertFalse(any("artifacts" in name or "private" in name for name in manifest))
            lock = (dest / "requirements.txt").read_text()
            root_pins = set((ROOT / "requirements.txt").read_text().splitlines())
            self.assertTrue(all(line in root_pins for line in lock.splitlines() if "==" in line))
            for name in ("PyYAML", "starlette", "uvicorn"):
                self.assertNotIn(name, lock)
