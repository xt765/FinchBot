"""Dynamic middleware regression tests."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from finchbot.tools.middleware import MCPHotUpdateMiddleware


class DummyTool:
    """Small stand-in for a LangChain tool."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.description = f"{name} description"


class DummyRegistry:
    """Registry stub used by MCPHotUpdateMiddleware."""

    def __init__(self, tools: list[DummyTool]) -> None:
        self._tools = tools

    def get_tools(self) -> list[DummyTool]:
        return self._tools


class DummyMCPManager:
    """MCP manager stub returning a configured tool update."""

    def __init__(self, tools: list[DummyTool] | None) -> None:
        self.tools = tools

    async def check_and_update(self) -> list[DummyTool] | None:
        await asyncio.sleep(0)
        return self.tools


@pytest.mark.asyncio
async def test_sync_mcp_hot_update_schedules_task_without_mutating_request_to_task() -> None:
    """Sync middleware should not treat an asyncio.Task as a tool list."""
    old_tool = DummyTool("old")
    new_tool = DummyTool("new")
    request = SimpleNamespace(tools=[old_tool])
    middleware = MCPHotUpdateMiddleware(
        mcp_manager=DummyMCPManager([new_tool]),
        registry=DummyRegistry([old_tool, new_tool]),
        initial_tools=[old_tool],
    )

    def handler(received_request: Any) -> str:
        assert received_request.tools == [old_tool]
        return "ok"

    result = middleware.wrap_model_call(request, handler)
    await asyncio.sleep(0.01)

    assert result == "ok"
    assert middleware.tools == [new_tool]
    assert all(not isinstance(tool, asyncio.Task) for tool in middleware.tools)


@pytest.mark.asyncio
async def test_async_mcp_hot_update_updates_current_request_tools() -> None:
    """Async middleware should apply freshly loaded MCP tools immediately."""
    old_tool = DummyTool("old")
    new_tool = DummyTool("new")
    request = SimpleNamespace(tools=[old_tool])
    middleware = MCPHotUpdateMiddleware(
        mcp_manager=DummyMCPManager([new_tool]),
        registry=DummyRegistry([old_tool, new_tool]),
        initial_tools=[old_tool],
    )

    async def handler(received_request: Any) -> str:
        assert [tool.name for tool in received_request.tools] == ["old", "new"]
        return "ok"

    result = await middleware.awrap_model_call(request, handler)

    assert result == "ok"
    assert middleware.tools == [new_tool]
