"""Offline fixtures only; do not weaken or call a historical paid-run hash guard."""

import json

import yaml

from evals.step6.effect_question import context_for
from evals.step6.question_context import BASE
from evals.step6.reviewed_live import CATALOG, DATASET, POLICIES
from evals.step6.run import load_case_bundle
from evals.step6.source_approval import load_catalog


def reviewed_inputs():
    cases = json.loads(DATASET.read_text())["cases"]
    bundle = load_case_bundle(cases, POLICIES)
    config = yaml.safe_load((BASE / "direct-policy-v2/config.yaml").read_text())
    original = {
        c["id"]: c for c in json.loads((BASE / "context-v1/contexts.json").read_text())["cases"]
    }
    contexts = {c["id"]: context_for(c, original[c["id"]], "question_and_context") for c in cases}
    return {}, cases, bundle, config, load_catalog(CATALOG), contexts


def comparison_inputs():
    frozen, cases, bundle, config, catalog, contexts = reviewed_inputs()
    base = BASE / "q04-comparison-v1"
    cases += json.loads((base / "fresh-cases.json").read_text())["cases"]
    contexts.update(
        {c["id"]: c for c in json.loads((base / "fresh-contexts.json").read_text())["cases"]}
    )
    return frozen, cases, bundle, config, catalog, contexts
