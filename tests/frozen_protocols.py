"""Test-only source fixtures for exercising old data with the current decision engine.

Live runners must still reject changed evaluator code. Composition/review unit tests
substitute only the historical source inventory, leaving data/config/context hashes
and review validation active. This is not a measured replay of the frozen protocol.
"""

import json
from unittest.mock import patch


def source_fixture(target, protocol):
    return patch(target, return_value=json.loads(protocol.read_text())["source_sha256"])
