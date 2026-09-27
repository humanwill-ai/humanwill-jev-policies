# Synthetic provider smoke procedure

**Pending credentials, not executed yet.** The owner approved up to **$5 total** for synthetic smoke calls on both routes. Configure credentials locally before running. Use only the packaged synthetic policy/event; do not substitute private company material. One attempt per route is sufficient for this smoke gate; no automatic retries or route substitution. The CLI bounds bytes, batches, and time, but **does not enforce a currency budget**. Response cost may be unavailable, especially after an error; do not infer zero spend.

The keys are environment variables `OPENROUTER_API_KEY` and `TYPESAFE_API_KEY`. Set them locally through your preferred credential mechanism, never in committed files or chat. No separate TypeSafe key is needed for the OpenRouter route.

From the checkout with the package installed:

```sh
humanwill-policies init-demo ./smoke-demo
python - <<'PY'
from pathlib import Path
import yaml
root = Path('smoke-demo')
base = yaml.safe_load((root / 'config.yaml').read_text())
for route, model, returned, key in [
    ('openrouter', 'typesafe/jev-1.13', 'typesafe/jev-1.13-20260917', 'OPENROUTER_API_KEY'),
    ('typesafe', 'jev-1.13.0', 'jev-1.13.0', 'TYPESAFE_API_KEY'),
]:
    config = dict(base)
    config['provider'] = {
        'transport': route, 'model': model,
        'accepted_models': [returned], 'api_key_env': key,
    }
    config['evaluation'] = {
        'timeout_ms': 10000, 'max_batches': 1, 'questions_per_batch': 1,
        'max_batch_bytes': 24000,
    }
    (root / f'{route}.yaml').write_text(yaml.safe_dump(config))
PY
```

Validate both configurations offline first. Only after authorizing the synthetic disclosure and budget, run the selected route explicitly:

```sh
humanwill-policies validate ./smoke-demo --config ./smoke-demo/openrouter.yaml
humanwill-policies evaluate ./smoke-demo --config ./smoke-demo/openrouter.yaml \
  --request ./smoke-demo/request.json --backend configured --allow-external --json
```

For direct TypeSafe, replace `openrouter.yaml` with `typesafe.yaml`. The example returned-model identities come from official references, not observed calls from this project. A model mismatch requires deliberate investigation of the actual provider contract; do not wildcard the allowlist or erase the failed attempt.

Record the exact commit, route, requested/returned model, request/bundle/configuration digests, normalized result, measured duration, usage/cost if reported, and any failures in a dated report. Inspect account billing for attempts whose usage is unknown. Keep keys and raw headers out of output and reports. A valid transport result may still assess the synthetic prompt differently; investigate rather than silently changing thresholds to manufacture a pass. Two transport checks do not establish semantic quality, latency distributions, adversarial robustness, or runtime enforcement.
