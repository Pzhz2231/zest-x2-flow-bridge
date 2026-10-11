# Zest Flow Routing Skill

This repository contains an Alibaba Cloud Bailian Managed Agent Skill for routing Zest text tasks to the user's two existing X² Flow Apps:

- `simple` → X²Agent 1.1Pro, App ID `ba86217448de4d49bafa80c956eec8ae`
- `complex` → X² 1.0 / Test3, App ID `578f133457ba468b82eec09d21e6c0b9`

The Skill runs `flow_call.py` from within the Managed Agent session sandbox. It sends one compact task brief to one allowlisted Flow App and returns the actual `output.text`. It does not change either app's RAG settings, call both tiers for one task, or retry a failed/empty result.

## Bailian installation

1. Package `SKILL.md` and `flow_call.py` at the ZIP root.
2. Upload the ZIP through Bailian Skill Manager, wait for its review, then bind the resulting Skill to Zest.
3. Bind a Bailian Vault containing the `DASHSCOPE_API_KEY` credential to the Managed Agent session. The sandbox receives only `BMA_SECRET_PLACEHOLDER_DASHSCOPE_API_KEY`; keep the real credential in Vault.
4. Allow outbound credential substitution only for the required DashScope host. The helper sends the placeholder solely in the HTTPS `Authorization` header and retains default TLS certificate verification.
5. Require user approval before every Flow API request. Do not test by calling a Flow App without separate approval for that specific call.

The helper uses only Python's standard library. It defaults to no theory summary so each Flow App can use its existing RAG. Add a short, sourced summary only when the user explicitly supplies required material that the Flow cannot retrieve itself.

## Important: historical MCP prototype

The `v0.1.0` tag is a historical stdio MCP/Function Compute prototype. **Do not deploy it.** A separately deployed custom MCP process does not inherit the Managed Agent session's Vault, so its credential path was not verified. The supported design is this in-session Skill; the repository no longer publishes an `uvx` MCP server.

## Cost and acceptance

Each Flow API request may incur that Flow App's model and retrieval charges. Charges can apply even when the request fails. This repository does not claim a tested price, successful live call, token reduction measurement, or end-to-end acceptance. Obtain the current price and user approval before a live test.

## Source files

- `SKILL.md` — routing, approval, compact-context, output, retry, and Vault rules.
- `flow_call.py` — fixed App ID allowlist and single-request HTTPS helper.
