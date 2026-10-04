# HumanWill hook client (0.2 Public Beta)

A small Python client for VS Code Local and Copilot CLI hooks. It sends only the
supported prompt or tool fields to an authenticated HumanWill policy service and
returns the host's allow/deny output. Company policies and Jev credentials stay on
the service. Inspected content still reaches the service and its hosted evaluator.

This distribution uses the same hook, JSON, schema and event code as the full
package, under a separate namespace. It contains no policy loader, YAML parser,
Jev transport, web server or gateway connector. It needs Python 3.11–3.14 and the
locked HTTP/schema-validation dependencies. It is not a native binary.

Build from the repository root with the pinned development environment:

```sh
python scripts/build_hook_client.py --outdir dist/hook-client
```

The build produces a wheel and a standalone source archive. Extract the source
archive to obtain `requirements.txt`, then install into a fresh environment:

```sh
python3 -m venv .venv-hook
.venv-hook/bin/python -m pip install -r /path/to/extracted/requirements.txt
.venv-hook/bin/python -m pip install --no-deps /path/to/humanwill_hook_client-0.2.0b2-py3-none-any.whl
.venv-hook/bin/python -m pip check
.venv-hook/bin/humanwill-hook --version
```

In an existing HumanWill hook configuration, replace
`/path/bin/humanwill-policies hook` with `/path/.venv-hook/bin/humanwill-hook`.
Keep all other arguments, runtime/event names, authentication environment variables
and host timeout settings unchanged. For example:

```sh
/path/.venv-hook/bin/humanwill-hook --runtime copilot_local \
  --event UserPromptSubmit --url https://policies.company.example \
  --token-env HUMANWILL_LOCAL_TOKEN --timeout-ms 6000
```

Supply the service token through the host environment; never embed it in committed
hook files. Remote origins require HTTPS and normal certificate verification.
There is no proxy-environment inheritance, redirect following or transport retry.
This client uses the same explicit `--on-error` behavior, validates service replies,
checks their request/coverage binding, and rejects simulated enforced verdicts.
It does not read transcript paths, policy files or referenced repository files.

Existing `humanwill-policies hook` commands remain supported. The two distributions
use different module and executable names and can coexist. This client has no
`serve`, policy-authoring or provider commands. Uninstall only its own hooks/package
to revert, or restore the previous executable path.

Copilot CLI prompt hooks remain assessment-only. VS Code Local and CLI tool hooks
retain their existing boundaries; host timeout/disabled-hook bypasses remain.
This refactor does not add Cloud Agent, Agent Host, Windows qualification, ARM64
Linux qualification, response inspection, or stronger endpoint enforcement.
See the repository's `docs/service-and-connectors.md` for deployment guidance.
