# Architecture diagrams

These PNGs accompany the [architecture guide](../../architecture.md). Each is
rendered at 2× resolution, with the same numbered references used in the text.

| Diagram | PNG |
| --- | --- |
| Shared policy core and Jev | [policy-core.png](policy-core.png) |
| LiteLLM model and MCP flows | [litellm.png](litellm.png) |
| Agentgateway model relay | [agentgateway-model.png](agentgateway-model.png) |
| Agentgateway MCP processor | [agentgateway-mcp.png](agentgateway-mcp.png) |
| Copilot Local and CLI hooks | [copilot.png](copilot.png) |

The editable Mermaid definitions remain in collapsed source sections in
`docs/architecture.md`. PNGs were rendered with Mermaid 11.17.2; refresh the images
when changing the diagram definitions. The images contain original project
diagrams, not screenshots of external products.

The Markdown guide displays these PNGs directly on GitHub; no HTML page, Mermaid
support or web server is required to see them. Keep the numbered references in
the diagrams and explanation tables consistent when editing. PNG files are
included in source distributions through `MANIFEST.in`.
