"""Minimal stdio MCP bridge to the two existing X² Flow Agent apps.

The app IDs are an explicit allowlist. Bailian's Managed Agent outbound
credential gateway replaces the Authorization Bearer placeholder at runtime;
the actual credential is never read into this process or stored in this package.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any


PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "zest-x2-flow-bridge", "version": "0.1.0"}
MAX_TASK_CHARS = 6000
MAX_CONTEXT_CHARS = 3000
APP_ALLOWLIST = {
    "x2_text_simple": {
        "app_id": "ba86217448de4d49bafa80c956eec8ae",
        "name": "X² 1.1Pro 简单文字处理",
    },
    "x2_text_complex": {
        "app_id": "578f133457ba468b82eec09d21e6c0b9",
        "name": "X² 1.0 复杂文字处理",
    },
}


def _text(value: Any, field: str, limit: int, required: bool = False) -> str:
    if value is None and not required:
        return ""
    if not isinstance(value, str):
        raise ValueError(f"{field} 必须是文本")
    value = value.strip()
    if required and not value:
        raise ValueError(f"{field} 不能为空")
    if len(value) > limit:
        raise ValueError(f"{field} 超出 {limit} 字符限制")
    return value


def _flow_prompt(args: dict[str, Any]) -> str:
    task = _text(args.get("task"), "task", MAX_TASK_CHARS, required=True)
    audience = _text(args.get("audience"), "audience", 300)
    channel = _text(args.get("channel"), "channel", 200)
    length = _text(args.get("length"), "length", 200)
    constraints = _text(args.get("constraints"), "constraints", MAX_CONTEXT_CHARS)
    theory_summary = _text(args.get("theory_summary"), "theory_summary", MAX_CONTEXT_CHARS)

    sections = ["请直接完成以下任务，只返回可交付的完整正文；如材料不足，用一句话标出关键疑点。", f"任务：\n{task}"]
    for label, value in (
        ("受众", audience),
        ("渠道/体裁", channel),
        ("篇幅", length),
        ("硬约束", constraints),
        ("理论检索摘要（仅在任务需要时提供，保留来源）", theory_summary),
    ):
        if value:
            sections.append(f"{label}：\n{value}")
    return "\n\n".join(sections)


def _call_flow(tool_name: str, args: dict[str, Any]) -> str:
    token = os.environ.get("DASHSCOPE_API_KEY", "").strip()
    if token != "${DASHSCOPE_API_KEY}":
        raise RuntimeError("请在 Managed Agent Session 中绑定包含 DASHSCOPE_API_KEY 的 Vault")

    prompt = _flow_prompt(args)
    app_id = APP_ALLOWLIST[tool_name]["app_id"]
    request = urllib.request.Request(
        f"https://dashscope.aliyuncs.com/api/v1/apps/{app_id}/completion",
        data=json.dumps({"input": {"prompt": prompt}}, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # Do not include headers or request contents in error details.
        detail = exc.read(1000).decode("utf-8", errors="replace")
        raise RuntimeError(f"Flow App 调用失败（HTTP {exc.code}）：{detail}") from None
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"Flow App 网络调用失败：{type(exc).__name__}") from None

    output = payload.get("output") or {}
    result = output.get("text") if isinstance(output, dict) else None
    if not isinstance(result, str) or not result.strip():
        raise RuntimeError("Flow App 返回空正文；停止，不生成状态说明替代成稿")
    return result.strip()


def _tool_schema() -> list[dict[str, Any]]:
    properties = {
        "task": {"type": "string", "description": "当前写作任务，最多 6000 字符"},
        "audience": {"type": "string", "description": "受众，可省略"},
        "channel": {"type": "string", "description": "渠道或体裁，可省略"},
        "length": {"type": "string", "description": "篇幅要求，可省略"},
        "constraints": {"type": "string", "description": "关键约束，可省略，最多 3000 字符"},
        "theory_summary": {"type": "string", "description": "必要的短理论摘要及来源，可省略，最多 3000 字符"},
    }
    return [
        {
            "name": name,
            "description": f"调用已发布的{name} Flow Agent。仅提交当前任务简报及必要摘要，直接返回正文。",
            "inputSchema": {
                "type": "object",
                "properties": properties,
                "required": ["task"],
                "additionalProperties": False,
            },
        }
        for name in APP_ALLOWLIST
    ]


def _dispatch(message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")
    params = message.get("params") or {}

    if method == "notifications/initialized" or method == "notifications/cancelled":
        return None

    if method == "initialize":
        result = {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": SERVER_INFO,
        }
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": _tool_schema()}
    elif method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        if name not in APP_ALLOWLIST:
            result = {"content": [{"type": "text", "text": "工具未在允许列表中"}], "isError": True}
        else:
            try:
                text = _call_flow(name, args)
                result = {"content": [{"type": "text", "text": text}], "isError": False}
            except Exception as exc:  # Return a useful tool error without secrets.
                result = {"content": [{"type": "text", "text": str(exc)}], "isError": True}
    else:
        if request_id is None:
            return None
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "Method not found"}}

    if request_id is None:
        return None
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def main() -> None:
    for line in sys.stdin:
        try:
            message = json.loads(line)
            response = _dispatch(message)
        except Exception as exc:
            request_id = None
            try:
                request_id = json.loads(line).get("id")
            except Exception:
                pass
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32603, "message": str(exc)},
            }
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
