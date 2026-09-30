# Install and run the preview candidate

The current experimental developer preview candidate is `0.1.0a1`; no public release or registry package is published. Use Python 3.11–3.14 on Linux/macOS. This guide needs only the source distribution, wheel and locked runtime requirements from the same candidate. Installation downloads dependencies; the demo and contract checks make no evaluator calls.

## Install an exact artifact

Extract `humanwill_policies-0.1.0a1.tar.gz` into a new directory. From that extracted directory, install into a fresh environment, using the wheel supplied alongside the archive:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install --no-deps /absolute/path/humanwill_policies-0.1.0a1-py3-none-any.whl
.venv/bin/python -m pip check
.venv/bin/humanwill-policies --version
```

Alternatively, replace the wheel path with the exact `.tar.gz` path. Pip builds that source archive with the pinned build backend. No editable checkout or HumanWill Benchmark installation is required. Check the artifact SHA-256 against the candidate evidence before installing; an adjacent untrusted checksum alone is not authentication.

## Complete the offline demo

Run these commands from the extracted directory; choose a new `demo` path:

```sh
.venv/bin/humanwill-policies init-demo demo
.venv/bin/humanwill-policies validate demo --config demo/config.yaml --json
.venv/bin/humanwill-policies preview demo --config demo/config.yaml --stage prompt --json
.venv/bin/humanwill-policies evaluate demo --config demo/config.yaml \
  --request demo/request.json --mock-answers demo/mock-answers.json --json
```

Expected: three valid policies, one enabled content rule, two explicitly disabled metadata-dependent rules; evaluation returns `decision: allow`, `simulated: true` and no requested enforcement. Metadata is off. The answer is scripted, so this demonstrates installation and contract behavior, not Jev accuracy. Preview prints policy text and source snapshots; handle its output accordingly.

Next, write your rules using the [policy-author guide](policy-authoring.md), then follow [service and connector setup](service-and-connectors.md). Hosted evaluation requires a provider credential and explicit egress opt-in. Company policy text and covered content leave your environment through OpenRouter or direct TypeSafe. Only synthetic samples have been authorized for this project's live evaluation.

## Reproduce packaging evidence

From an extracted source artifact with its wheel available:

```sh
python3 scripts/verify_artifacts.py \
  --wheel /absolute/path/humanwill_policies-0.1.0a1-py3-none-any.whl \
  --sdist /absolute/path/humanwill_policies-0.1.0a1.tar.gz \
  --report artifacts/packaging/verification.json
```

The script creates temporary environments outside the checkout, installs each exact artifact, checks the imported package location, runs the offline demo and service/hook contract scenarios from the archive, then starts the real installed service process. It verifies unauthenticated denial, disabled egress, invalid configuration rejection and rollback/restart. The output records artifact hashes; use a new report path each time. Contract scenarios exercise both gateway adapters and both hook dialects. They are not fresh tests of the actual LiteLLM, Agentgateway or Copilot hosts: those procedures and pinned evidence are in the [connector guide](service-and-connectors.md) and [integration report](integration-report.md).

## Local container recipe

Docker is an optional local packaging route. Build from the source directory with the selected wheel in `dist/`:

```sh
docker build --build-arg WHEEL=dist/humanwill_policies-0.1.0a1-py3-none-any.whl \
  -t humanwill-policies:0.1.0a1 .
docker run --rm --network none humanwill-policies:0.1.0a1 --version
```

The recipe installs the selected wheel and locked dependencies, runs as numeric UID/GID 65532, and includes no policy folder or credentials. Its context is allowlisted to the recipe, runtime lock and wheels. The default Python image is a mutable development tag; for release evidence set `--build-arg PYTHON_IMAGE=python@sha256:YOUR_APPROVED_DIGEST` and record the image ID/base digest. Do not treat a recipe as a published or verified image.

Mount a readable protected policy folder at `/policies`, a protected configuration directory at `/configuration`, and provide only the token/key environment variables selected by your configuration:

```sh
docker run --rm --read-only --cap-drop ALL --security-opt no-new-privileges \
  --tmpfs /tmp:rw,noexec,nosuid,size=16m -p 127.0.0.1:8088:8088 \
  --mount type=bind,src=/absolute/policies,dst=/policies,readonly \
  --mount type=bind,src=/absolute/configuration,dst=/configuration,readonly \
  --env OPENROUTER_API_KEY --env HUMANWILL_LOCAL_TOKEN \
  humanwill-policies:0.1.0a1 serve /policies \
  --config /configuration/policies.yaml --service-config /configuration/service.yaml \
  --host 0.0.0.0 --port 8088
```

This example assumes the service configuration retains only its Local principal. Add distinct tokens for other enabled principals. Grant UID 65532 read/traverse access to mounted files without making credentials public. On SELinux hosts apply appropriate local volume labels. Container loopback differs from the host: update connector URLs according to your protected network topology. The service health/readiness endpoints do not probe Jev. Follow the [operations guide](operations.md) for upgrades and rollback. No container is automatically deployed or published by these commands.

To preview/evaluate the new full-policy template, use `demo/config-policy-text.yaml` in the same offline commands. See [config/5](direct-policy-evaluation.md) for result/4 compatibility and trusted-data bindings.

For the optional stage-aware profile use `demo/config-stage-aware-followup.yaml`.
It retains monitoring and metadata-off defaults. Content-only rules keep their
semantic question; scoped-predicate follow-ups require trusted metadata bindings.
See [profile limits](bounded-policy-followup.md) and [candidate evidence](preview-status.md).
