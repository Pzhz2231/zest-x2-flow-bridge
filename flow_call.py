"""Call one of the two approved X² Flow Apps from a Vault-bound MA session."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any


APP_ALLOWLIST = {
    "simple": "ba86217448de4d49bafa80c956eec8ae",
    "complex": "578f133457ba468b82eec09d21e6c0b9",
}
EXPECTED_VAULT_PLACEHOLDER = "BMA_SECRET_PLACEHOLDER_DASHSCOPE_API_KEY"
MAX_INPUT_BYTES = 24_000
MAX_TASK_CHARS = 6_000
MAX_CONTEXT_CHARS = 3_000


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


def _build_prompt(data: dict[str, Any]) -> str:
    task = _text(data.get("task"), "task", MAX_TASK_CHARS, required=True)
    audience = _text(data.get("audience"), "audience", 300)
    channel = _text(data.get("channel"), "channel", 200)
    length = _text(data.get("length"), "length", 200)
    constraints = _text(data.get("constraints"), "constraints", MAX_CONTEXT_CHARS)
    theory_summary = _text(data.get("theory_summary"), "theory_summary", MAX_CONTEXT_CHARS)

    sections = [
        "请直接完成以下任务，只返回可交付的完整正文；如材料不足，用一句话标出关键疑点。",
        f"任务：\n{task}",
    ]
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


def _read_input() -> dict[str, Any]:
    raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError(f"输入超过 {MAX_INPUT_BYTES} 字节限制")
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("标准输入必须是 UTF-8 JSON 对象") from None
    if not isinstance(data, dict):
        raise ValueError("标准输入必须是 JSON 对象")
    allowed = {"task", "audience", "channel", "length", "constraints", "theory_summary"}
    unknown = set(data) - allowed
    if unknown:
        raise ValueError("输入包含未支持字段")
    return data


def call_flow(tier: str, data: dict[str, Any]) -> str:
    if tier not in APP_ALLOWLIST:
        raise ValueError("档位必须是 simple 或 complex")

    # Vault values must remain placeholders in the session. The platform's egress
    # gateway performs the authorized-host swap in the Authorization header.
    token = os.environ.get("DASHSCOPE_API_KEY", "").strip()
    if token != EXPECTED_VAULT_PLACEHOLDER:
        raise RuntimeError("当前 Session 未检测到预期 Vault 占位符；请停止并检查 Vault 绑定，不要粘贴真实 API Key")

    request = urllib.request.Request(
        f"https://dashscope.aliyuncs.com/api/v1/apps/{APP_ALLOWLIST[tier]}/completion",
        data=json.dumps({"input": {"prompt": _build_prompt(data)}}, ensure_ascii=False).encode("utf-8"),
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
        raise RuntimeError(f"所选 Flow API 返回 HTTP {exc.code}；本脚本未重试") from None
    except urllib.error.URLError as exc:
        reason = exc.reason
        reason_name = type(reason).__name__ if reason is not None else "NetworkError"
        raise RuntimeError(f"Flow API 网络/TLS 调用失败（{reason_name}）；本脚本未重试") from None
    except TimeoutError:
        raise RuntimeError("Flow API 请求超时；本脚本未重试") from None
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise RuntimeError("Flow API 返回内容无法解析；本脚本未重试") from None

    output = payload.get("output") or {}
    text = output.get("text") if isinstance(output, dict) else None
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError("Flow API 返回空正文；停止，不用状态说明替代成稿")
    return text.strip()


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in APP_ALLOWLIST:
        sys.stderr.write("用法：python3 flow_call.py simple|complex < request.json\n")
        return 2
    try:
        result = call_flow(sys.argv[1], _read_input())
    except Exception as exc:
        sys.stderr.write(f"Flow 调用失败：{exc}\n")
        return 1
    sys.stdout.write(result + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

