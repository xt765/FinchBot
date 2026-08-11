"""Agent 结算上报 (Proof of Work / Settlement) 单元测试.

对应 issue #2: FinchBot agents 原生支持向外部结算层 (如 Wheat Community Nexus)
上报 JSON Proof of Work。
"""

from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import sys
import types

# --- 隔离依赖: 用 stub 替换 finchbot.tools.decorator，避免导入重依赖 ---
_decorator_stub = types.ModuleType("finchbot.tools.decorator")


class _ToolCategory:
    PLUGIN = "plugin"
    FILE = "file"
    WEB = "web"


def _fake_tool(name, description, category=None, **kwargs):
    def decorator(func):
        func.__name__ = name
        func.__doc__ = description
        return func

    return decorator


_decorator_stub.ToolCategory = _ToolCategory
_decorator_stub.tool = _fake_tool
sys.modules["finchbot.tools.decorator"] = _decorator_stub

_SETTLEMENT_PATH = (
    pathlib.Path(__file__).resolve().parent.parent
    / "src"
    / "finchbot"
    / "tools"
    / "builtin"
    / "settlement.py"
)
_spec = importlib.util.spec_from_file_location("_settlement_mod", _SETTLEMENT_PATH)
settlement = importlib.util.module_from_spec(_spec)
sys.modules["_settlement_mod"] = settlement
_spec.loader.exec_module(settlement)


# --- httpx fake ---
class _FakeResponse:
    status_code = 200

    def raise_for_status(self):
        pass


class _FakeAsyncClient:
    captured: list[tuple[str, dict, dict]] = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, json=None, headers=None):
        _FakeAsyncClient.captured.append((url, json, headers))
        return _FakeResponse()


def _reset_config():
    settlement.configure_settlement_tools(
        webhook_url="",
        api_key="",
        enabled=True,
        timeout_seconds=10,
        max_summary_chars=2000,
        max_evidence_chars=5000,
    )
    _FakeAsyncClient.captured = []


# ---------------------------------------------------------------- payload 构建
def test_payload_structure() -> None:
    payload = settlement.build_proof_of_work_payload(
        summary="完成了 X 任务", evidence="产出文件 report.md", work_type="task_completion"
    )
    assert payload["version"] == "1.0"
    assert payload["schema"] == "finchbot/proof-of-work/v1"
    assert payload["work_type"] == "task_completion"
    assert payload["summary"] == "完成了 X 任务"
    assert payload["evidence"] == "产出文件 report.md"
    assert payload["agent_id"]
    assert payload["timestamp"]
    # task_id 未指定时自动生成
    assert payload["task_id"]


def test_payload_idempotency_key_becomes_task_id() -> None:
    payload = settlement.build_proof_of_work_payload(summary="s", idempotency_key="job-42")
    assert payload["task_id"] == "job-42"


def test_payload_evidence_optional() -> None:
    payload = settlement.build_proof_of_work_payload(summary="s")
    assert payload["evidence"] == ""


# ---------------------------------------------------------------- HMAC 签名
def test_signature_is_deterministic() -> None:
    payload = {"a": 1, "b": "x"}
    s1 = settlement.sign_payload(payload, "key-1")
    s2 = settlement.sign_payload(payload, "key-1")
    assert s1 == s2
    assert len(s1) == 64  # sha256 hex


def test_signature_changes_with_key_and_content() -> None:
    payload = {"a": 1, "b": "x"}
    s_key2 = settlement.sign_payload(payload, "key-2")
    s_content = settlement.sign_payload({"a": 1, "b": "y"}, "key-1")
    assert s_key2 != settlement.sign_payload(payload, "key-1")
    assert s_content != settlement.sign_payload(payload, "key-1")


def test_signature_canonical_json_key_order_independent() -> None:
    """排序 key 的规范 JSON 保证跨运行时签名一致."""
    s1 = settlement.sign_payload({"a": 1, "b": 2}, "k")
    s2 = settlement.sign_payload({"b": 2, "a": 1}, "k")
    assert s1 == s2


# ---------------------------------------------------------------- 未配置处理
def test_unconfigured_returns_hint_without_error() -> None:
    _reset_config()

    import asyncio

    coro = settlement.report_agent_work(summary="任务")
    result = asyncio.get_event_loop().run_until_complete(coro)
    assert "未配置" in result
    assert "FINCHBOT_SETTLEMENT_WEBHOOK_URL" in result


def test_disabled_returns_hint() -> None:
    settlement.configure_settlement_tools(webhook_url="https://example.com/hook", enabled=False)
    import asyncio

    result = asyncio.get_event_loop().run_until_complete(settlement.report_agent_work(summary="x"))
    assert "未配置" in result


# ---------------------------------------------------------------- env 懒加载
def test_env_lazy_load(monkeypatch) -> None:
    _reset_config()
    monkeypatch.setattr("httpx.AsyncClient", _FakeAsyncClient)
    monkeypatch.setenv("FINCHBOT_SETTLEMENT_WEBHOOK_URL", "https://nexus.test/api/v1/pow")

    import asyncio

    result = asyncio.get_event_loop().run_until_complete(settlement.report_agent_work(summary="x"))
    assert "结算上报成功" in result
    assert len(_FakeAsyncClient.captured) == 1
    url, payload, headers = _FakeAsyncClient.captured[0]
    assert url == "https://nexus.test/api/v1/pow"
    assert payload["schema"] == "finchbot/proof-of-work/v1"


# ---------------------------------------------------------------- 发送与签名头
def test_webhook_send_with_signature_header(monkeypatch) -> None:
    _reset_config()
    monkeypatch.setattr("httpx.AsyncClient", _FakeAsyncClient)
    settlement.configure_settlement_tools(
        webhook_url="https://nexus.test/api/v1/pow", api_key="secret-key"
    )

    import asyncio

    result = asyncio.get_event_loop().run_until_complete(
        settlement.report_agent_work(summary="完成报告", idempotency_key="task-1")
    )
    assert "结算上报成功" in result
    url, payload, headers = _FakeAsyncClient.captured[0]
    assert payload["task_id"] == "task-1"
    sig = headers["X-Settlement-Signature"]
    assert sig.startswith("sha256=")
    # 验证签名内容正确
    expected = settlement.sign_payload(payload, "secret-key")
    assert sig == f"sha256={expected}"


def test_webhook_send_no_signature_without_api_key(monkeypatch) -> None:
    _reset_config()
    monkeypatch.setattr("httpx.AsyncClient", _FakeAsyncClient)
    settlement.configure_settlement_tools(webhook_url="https://nexus.test/api/v1/pow")

    import asyncio

    asyncio.get_event_loop().run_until_complete(settlement.report_agent_work(summary="x"))
    url, payload, headers = _FakeAsyncClient.captured[0]
    assert "X-Settlement-Signature" not in headers


# ---------------------------------------------------------------- 截断
def test_summary_truncated(monkeypatch) -> None:
    _reset_config()
    monkeypatch.setattr("httpx.AsyncClient", _FakeAsyncClient)
    settlement.configure_settlement_tools(
        webhook_url="https://nexus.test/api/v1/pow", max_summary_chars=10
    )

    import asyncio

    result = asyncio.get_event_loop().run_until_complete(
        settlement.report_agent_work(summary="这是一个很长的任务摘要内容")
    )
    assert "截断" in result
    url, payload, headers = _FakeAsyncClient.captured[0]
    assert len(payload["summary"]) == 10


def test_evidence_truncated(monkeypatch) -> None:
    _reset_config()
    monkeypatch.setattr("httpx.AsyncClient", _FakeAsyncClient)
    settlement.configure_settlement_tools(
        webhook_url="https://nexus.test/api/v1/pow", max_evidence_chars=5
    )

    import asyncio

    asyncio.get_event_loop().run_until_complete(
        settlement.report_agent_work(summary="s", evidence="非常长的证据内容")
    )
    url, payload, headers = _FakeAsyncClient.captured[0]
    assert len(payload["evidence"]) == 5


# ---------------------------------------------------------------- HTTP 错误
def test_http_error_returns_message(monkeypatch) -> None:
    _reset_config()
    import httpx

    class _ErrResponse:
        status_code = 500

        def raise_for_status(self):
            raise httpx.HTTPStatusError("500", request=None, response=None)

    class _ErrClient(_FakeAsyncClient):
        async def post(self, url, json=None, headers=None):
            return _ErrResponse()

    monkeypatch.setattr("httpx.AsyncClient", _ErrClient)
    settlement.configure_settlement_tools(webhook_url="https://nexus.test/api/v1/pow")

    import asyncio

    result = asyncio.get_event_loop().run_until_complete(settlement.report_agent_work(summary="x"))
    assert "结算上报失败" in result
