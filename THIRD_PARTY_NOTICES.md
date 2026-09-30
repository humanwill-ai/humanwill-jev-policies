# Third-party dependencies and notices

The project does not relicense its dependencies. The following Python runtime
packages are pinned in requirements.txt; their unmodified installed license
texts are retained under third_party/licenses. No implementation is vendored.

| Dependency | Version | License | Preserved notice |
| --- | --- | --- | --- |
| anyio | 4.15.1 | MIT | [License text](third_party/licenses/anyio/LICENSE) |
| attrs | 26.1.0 | MIT | [License text](third_party/licenses/attrs/LICENSE) |
| certifi | 2026.7.22 | MPL-2.0 | [License text](third_party/licenses/certifi/LICENSE) |
| click | 8.5.0 | BSD-3-Clause | [License text](third_party/licenses/click/LICENSE.txt) |
| h11 | 0.16.0 | MIT | [License text](third_party/licenses/h11/LICENSE.txt) |
| httpcore | 1.0.9 | BSD-3-Clause | [License text](third_party/licenses/httpcore/LICENSE.md) |
| httpx | 0.28.1 | BSD-3-Clause | [License text](third_party/licenses/httpx/LICENSE.md) |
| idna | 3.20 | BSD-3-Clause | [License text](third_party/licenses/idna/LICENSE.md) |
| jsonschema | 4.26.0 | MIT | [License text](third_party/licenses/jsonschema/COPYING) |
| jsonschema-specifications | 2025.9.1 | MIT | [License text](third_party/licenses/jsonschema-specifications/COPYING) |
| pyyaml | 6.0.3 | MIT | [License text](third_party/licenses/pyyaml/LICENSE) |
| referencing | 0.37.0 | MIT | [License text](third_party/licenses/referencing/COPYING) |
| rpds-py | 2026.6.3 | MIT | [License text](third_party/licenses/rpds-py/LICENSE) |
| starlette | 1.7.0 | BSD-3-Clause | [License text](third_party/licenses/starlette/LICENSE.md) |
| typing-extensions | 4.16.0 | PSF-2.0 | [License text](third_party/licenses/typing-extensions/LICENSE) |
| uvicorn | 0.54.0 | BSD-3-Clause | [License text](third_party/licenses/uvicorn/LICENSE.md) |

[CycloneDX inventory](docs/evidence/runtime-sbom.cdx.json) and
[license-file hashes](docs/evidence/runtime-licenses.json) are reproducible with
`python scripts/runtime_inventory.py` in the locked runtime environment.
This flattened inventory does not claim an audited transitive relationship graph.

Certifi includes Mozilla CA certificate material under MPL-2.0; retaining this
license does not turn HumanWill code into MPL-licensed software. Preserve the
dependency's license/source obligations when redistributing it. Python typing
extensions retain the full PSF license/history and included notices.

Build/test tools, optional gateway/editor/CLI hosts, hosted Jev/OpenRouter, and
the container's Python/OS base are outside this runtime inventory and retain
their own terms. Generate an image-specific inventory and review those notices
when the final container is built. No upstream integration implementation or
benchmark question pack is vendored by this project.
