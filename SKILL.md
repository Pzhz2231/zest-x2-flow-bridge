---
name: zest-flow-routing
description: Use when Zest needs a finished Chinese text deliverable and must route it to one of the two existing X² Flow Agents. Simple editing, summaries, short rewrites, translations and short copy use X² 1.1Pro; long original writing, open planning, complex policy or theory, and cross-material synthesis use X² 1.0. The helper runs inside the Managed Agent session so its Vault-bound DashScope credential stays on the session egress path.
---

# Zest X² Flow 双档文字路由

## 路由

- 简单档：错别字与语病修订、润色、压缩、短摘要、常规改写或翻译、短文案。调用 `flow_call.py simple`，对应 X²Agent 1.1Pro。
- 复杂档：开放策划、长篇原创、多约束创作、跨材料综合、复杂政策/理论解释、重要对外稿。调用 `flow_call.py complex`，对应 X² 1.0（Test3）。
- 纯机械格式转换和简单事实问答由 Zest 主控直接处理，不调用 Flow。一次任务只选择一个档位，不并行比较。

## 费用确认

Flow 调用会产生所选 Flow 应用的模型及其内部知识检索费用。只有在用户已经明确同意这一次 Flow 调用时才执行脚本。若用户没有针对本次调用明确授权，先告知将调用哪一档、会产生按量费用且无法在调用前精确结算，并等待同意。一次同意只覆盖一个 Flow API 请求；重试或补救请求必须另行取得同意。

## 最小化传递

- 只发送本次任务、必要的受众/渠道/篇幅/硬约束。
- 默认不附加理论摘要，让所选 Flow 应用沿用自身已配置的 RAG。仅当用户给了必须遵循的材料或本次任务要求采用 Zest 已核对的资料时，才附最多 5 条、约 600 字的摘要，并带来源名称/日期和不确定项。
- 不发送完整聊天记录、无关材料或隐藏推理；不传入 Flow `session_id`，保持单轮调用，避免隐式扩大上下文。

## 调用

使用当前 Managed Agent 会话中的 `bash` 工具。脚本仅在当前 Skill 目录运行，输入为 JSON，从标准输入传入：

```bash
python3 flow_call.py simple <<'ZEST_FLOW_INPUT'
{"task":"任务正文","audience":"受众","channel":"渠道或体裁","length":"篇幅","constraints":"硬约束","theory_summary":"必要时填写，否则留空"}
ZEST_FLOW_INPUT
```

复杂任务将 `simple` 替换为 `complex`。只运行一次，不自动重试。脚本会把完整返回正文输出到工具结果；必须核验其中有实际正文后才能交付。若凭证未绑定、网络/TLS失败、API报错或正文为空，向用户说明具体失败类别并停止，不伪造成稿、不自行降级或改调另一档。

## 凭证与安全

- 当前 Session 必须绑定包含 `DASHSCOPE_API_KEY` 的 Bailian Vault。脚本只接受百炼占位符 `BMA_SECRET_PLACEHOLDER_DASHSCOPE_API_KEY`，并在 `Authorization: Bearer ...` 中发送；百炼出网网关应仅对 Vault `allowed_hosts` 中的 DashScope 主机替换真实凭证。
- 脚本不会读取、打印、存储或请求用户提供真实 API Key。若拿到的不是预期占位符，立即停止，绝不将其发送到网络。
- 保持 TLS 证书校验，不使用 `curl -k`、`verify=False` 或任何其他证书绕过方式。
- 原 Flow 应用 ID 固定在脚本允许列表，不接受用户或模型提供的 URL/App ID。

