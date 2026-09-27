"""Local-only synthetic policy service for manual Copilot Local acceptance checks.

No provider network call; only use in a disposable synthetic test workspace.
"""

import argparse
import tempfile
from pathlib import Path

import uvicorn
from support import TOKEN, policy_app

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8088)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="humanwill-manual-fixture-") as tmp:
        app = policy_app(Path(tmp), "copilot_local")
        print("Synthetic fixture only. Set HUMANWILL_LOCAL_TOKEN to:", TOKEN)
        uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False)
