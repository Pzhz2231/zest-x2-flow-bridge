# Zest Flow Agent MCP Bridge

This stdio MCP package exposes exactly two tools and hard-codes only the two verified published app IDs:

- `x2_text_simple` → X²Agent 1.1 Test (`ba86217448de4d49bafa80c956eec8ae`)
- `x2_text_complex` → Test3_ZJXJDMX_20260519 / X² 1.0 (`578f133457ba468b82eec09d21e6c0b9`)

The bridge sends a compact prompt brief to the selected Flow App completion API. It does not create a third text tier, call both apps for one request, inspect conversation history, or change either app's RAG configuration. It rejects oversized inputs and empty outputs. The session environment must contain the Vault placeholder `${DASHSCOPE_API_KEY}`. The request uses it as a Bearer token so Bailian's Managed Agent credential gateway can substitute the saved credential for the allowlisted host; the bridge never reads or stores the actual key.

## Run locally

Run the server only as a Bailian Managed Agent MCP service with a session bound to the Vault containing `DASHSCOPE_API_KEY`. Bailian injects the literal placeholder into the process environment; the outbound gateway replaces it only in the Authorization header for an allowed host. A local model call will not resolve the placeholder and must not be used as a credential test.

## Bailian deployment

Bailian's custom MCP script deployment installs a public `uvx` package. This source is published in the `v0.1.0` GitHub release; the Bailian service still needs to be deployed and attached to Zest. Add only this service to Zest and expose its two allowlisted tools. Bind the Vault containing `DASHSCOPE_API_KEY` to each session that may use this MCP. The credential value is never included in MCP configuration, source code, or a prompt.

## Cost behavior

The service makes no startup or health-check model calls. One tool call makes one Flow App API request, which can incur the selected app's model/RAG charges. Zest should dispatch once and should not retry an empty result more than once.
