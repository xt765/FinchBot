"""Agent 结算上报工具 (Proof of Work / Settlement).

对应 issue #2 (Feature Request: Native Integration with Wheat Community Nexus):
agent 完成任务后，可将结构化 JSON 格式的 Proof of Work 上报到外部结算层
(如 Wheat Community Nexus) 的 webhook endpoint。

设计原则:
- 通用: 不绑定单一第三方。通过可配置的 webhook URL 对接任意结算层。
- 安全: 默认禁用 (webhook_url 为空即不生效); 配置 api_key 后以
  HMAC-SHA256 签名防篡改与伪造。
- 结构化: 输出标准 JSON (version / schema / agent_id / task_id /
  timestamp / summary / evidence / signature)。
- 幂等: 调用方可传 idempotency_key 控制重复上报。
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import platform
import socket
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from pydantic import Field

from finchbot.tools.decorator import ToolCategory, tool

# 默认配置 (由 configure_settlement_tools 覆盖)
_webhook_url: str = ""
_api_key: str = ""
_enabled: bool = True
_timeout_seconds: int = 10
_max_summary_chars: int = 2000
_max_evidence_chars: int = 5000

# 环境变量 fallback (与 web.py 的 env 读取模式一致)
_ENV_WEBHOOK_URL = "FINCHBOT_SETTLEMENT_WEBHOOK_URL"
_ENV_API_KEY = "FINCHBOT_SETTLEMENT_API_KEY"
_ENV_ENABLED = "FINCHBOT_SETTLEMENT_ENABLED"

_AGENT_ID: str = f"{socket.gethostname()}-{platform.python_version()}"


def configure_settlement_tools(
    webhook_url: str | None = None,
    api_key: str | None = None,
    enabled: bool | None = None,
    timeout_seconds: int | None = None,
    max_summary_chars: int | None = None,
    max_evidence_chars: int | None = None,
) -> None:
    """配置结算上报工具参数.

    Args:
        webhook_url: 结算层 webhook URL。为空时工具不生效 (返回未配置说明)。
        api_key: 可选 API Key，用于 HMAC-SHA256 签名。
        enabled: 是否启用。默认 True (但 webhook_url 为空时自动不生效)。
        timeout_seconds: HTTP 请求超时秒数。
        max_summary_chars: summary 最大长度。
        max_evidence_chars: evidence 最大长度。
    """
    global _webhook_url, _api_key, _enabled, _timeout_seconds
    global _max_summary_chars, _max_evidence_chars

    _webhook_url = webhook_url if webhook_url is not None else os.getenv(_ENV_WEBHOOK_URL, "")
    _api_key = api_key if api_key is not None else os.getenv(_ENV_API_KEY, "")
    _enabled = (
        enabled
        if enabled is not None
        else os.getenv(_ENV_ENABLED, "true").lower() not in ("0", "false", "no", "off")
    )
    if timeout_seconds is not None:
        _timeout_seconds = timeout_seconds
    if max_summary_chars is not None:
        _max_summary_chars = max_summary_chars
    if max_evidence_chars is not None:
        _max_evidence_chars = max_evidence_chars


def _is_configured() -> bool:
    """结算上报是否可用."""
    return _enabled and bool(_webhook_url)


def sign_payload(payload: dict[str, Any], api_key: str) -> str:
    """对 payload 计算 HMAC-SHA256 签名.

    使用排序 key 的规范 JSON (无空白) 作为签名输入，
    保证跨语言/跨运行时签名一致。

    Args:
        payload: 要签名的 payload。
        api_key: 签名密钥。

    Returns:
        hex 格式的签名。
    """
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hmac.new(api_key.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()


def build_proof_of_work_payload(
    summary: str,
    evidence: str | None = None,
    work_type: str = "task_completion",
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """构建标准 Proof of Work payload.

    Args:
        summary: 任务摘要。
        evidence: 证据 / 产物描述 (可选)。
        work_type: 工作类型，默认 task_completion。
        idempotency_key: 幂等键 (可选)。相同 key 表示同一工作，便于结算层去重。

    Returns:
        结构化 JSON payload。
    """
    return {
        "version": "1.0",
        "schema": "finchbot/proof-of-work/v1",
        "agent_id": _AGENT_ID,
        "task_id": idempotency_key or str(uuid.uuid4()),
        "work_type": work_type,
        "summary": summary,
        "evidence": evidence or "",
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def _truncate(text: str, limit: int) -> tuple[str, bool]:
    """截断文本到限制长度，返回 (文本, 是否截断)."""
    if len(text) <= limit:
        return text, False
    return text[:limit], True


@tool(
    name="report_agent_work",
    description=(
        "上报 Agent 完成的工作 (Proof of Work) 到外部结算层 (如 Wheat Community Nexus / Genesis Protocol)。"
        "当用户要求结算工作、赚取积分/代币、或任务完成需要向结算系统提交工作证明时使用。"
        "生成结构化 JSON 并通过配置的 webhook 提交，返回提交结果。"
        "未配置结算 webhook 时返回未配置说明，不影响主流程。"
    ),
    category=ToolCategory.PLUGIN,
    tags=["settlement", "proof-of-work", "wheat", "report"],
)
async def report_agent_work(
    summary: Annotated[str, Field(description="任务摘要，描述完成的工作内容")],
    evidence: Annotated[
        str | None, Field(description="证据 / 产物描述，如生成的文件路径、关键输出 (可选)")
    ] = None,
    work_type: Annotated[
        str, Field(description="工作类型，默认 task_completion")
    ] = "task_completion",
    idempotency_key: Annotated[
        str | None, Field(description="幂等键，相同 key 表示同一工作，避免重复结算 (可选)")
    ] = None,
) -> str:
    """上报 Agent 完成的工作到外部结算层.

    Args:
        summary: 任务摘要。
        evidence: 证据 / 产物描述 (可选)。
        work_type: 工作类型。
        idempotency_key: 幂等键 (可选)。

    Returns:
        提交结果字符串。
    """
    if not _webhook_url and os.getenv(_ENV_WEBHOOK_URL):
        # 任何创建路径下都支持 env 配置 (懒加载)
        configure_settlement_tools()

    if not _is_configured():
        return (
            "结算上报未启用: 未配置 webhook URL。"
            "请设置 FINCHBOT_SETTLEMENT_WEBHOOK_URL 或在配置文件中配置 tools.settlement.webhook_url。"
        )

    summary, summary_truncated = _truncate(summary, _max_summary_chars)
    evidence, evidence_truncated = _truncate(evidence or "", _max_evidence_chars)

    payload = build_proof_of_work_payload(
        summary=summary,
        evidence=evidence,
        work_type=work_type,
        idempotency_key=idempotency_key,
    )

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if _api_key:
        headers["X-Settlement-Signature"] = f"sha256={sign_payload(payload, _api_key)}"

    try:
        import httpx

        async with httpx.AsyncClient(timeout=_timeout_seconds) as client:
            response = await client.post(_webhook_url, json=payload, headers=headers)
        response.raise_for_status()
    except ImportError:
        return "错误: httpx 未安装。请运行: uv add httpx"
    except httpx.HTTPStatusError as e:
        status = getattr(e.response, "status_code", "?")
        detail = getattr(e.response, "text", "") or ""
        return f"结算上报失败: HTTP {status} {detail[:300]}"
    except httpx.TimeoutException:
        return "结算上报失败: 请求超时"
    except Exception as e:
        return f"结算上报失败: {str(e)[:300]}"

    notes = []
    if summary_truncated:
        notes.append("summary 超长已截断")
    if evidence_truncated:
        notes.append("evidence 超长已截断")
    note = f" ({'; '.join(notes)})" if notes else ""

    return (
        f"结算上报成功: task_id={payload['task_id']} timestamp={payload['timestamp']}"
        f" status={response.status_code}{note}"
    )
