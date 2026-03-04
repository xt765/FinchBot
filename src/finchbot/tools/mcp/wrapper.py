"""MCP 工具包装器.

为 MCP 工具添加超时控制，防止工具调用无限阻塞。
"""

from __future__ import annotations

import asyncio
from typing import Any

from langchain_core.tools import BaseTool
from loguru import logger


class MCPToolWithTimeout(BaseTool):
    """带超时控制的 MCP 工具包装器.

    包装 MCP 工具，添加超时控制。

    Attributes:
        _wrapped_tool: 被包装的原始工具
        _timeout: 超时时间（秒）
        _server_name: MCP 服务器名称
    """

    _wrapped_tool: BaseTool
    _timeout: int
    _server_name: str
    _mcp_server_name: str
    _args_schema: Any
    _parameters: dict | None

    def __init__(self, tool: BaseTool, server_name: str, timeout: int = 30) -> None:
        """初始化包装器.

        Args:
            tool: 原始 MCP 工具
            server_name: MCP 服务器名称
            timeout: 超时时间（秒）
        """
        super().__init__(
            name=tool.name,
            description=tool.description,
        )
        self._wrapped_tool = tool
        self._timeout = timeout
        self._server_name = server_name
        self._mcp_server_name = server_name

        if hasattr(tool, "args_schema") and tool.args_schema:
            self._args_schema = tool.args_schema
        if hasattr(tool, "parameters"):
            self._parameters = tool.parameters

    @property
    def args_schema(self) -> Any:
        """参数 schema."""
        if hasattr(self, "_args_schema"):
            return self._args_schema
        return getattr(self._wrapped_tool, "args_schema", None)

    @property
    def parameters(self) -> dict | None:
        """参数定义."""
        if hasattr(self, "_parameters"):
            return self._parameters
        return getattr(self._wrapped_tool, "parameters", None)

    def _run(self, *args: Any, **kwargs: Any) -> str:
        """同步执行（不支持，返回提示）."""
        return "MCP 工具仅支持异步执行，请使用 ainvoke。"

    async def _arun(self, *args: Any, **kwargs: Any) -> str:
        """异步执行，带超时控制.

        Returns:
            执行结果
        """
        try:
            result = await asyncio.wait_for(
                self._wrapped_tool.ainvoke(kwargs),
                timeout=self._timeout,
            )
            return str(result)
        except TimeoutError:
            logger.warning(f"MCP 工具 '{self.name}' 超时（{self._timeout}s）")
            return f"(MCP 工具调用超时，已等待 {self._timeout}s)"
        except Exception as e:
            logger.error(f"MCP 工具 '{self.name}' 错误: {e}")
            return f"MCP 工具错误: {e}"

    def get_server_name(self) -> str:
        """获取 MCP 服务器名称.

        Returns:
            服务器名称
        """
        return self._server_name


def wrap_mcp_tools_with_timeout(
    tools: list[BaseTool],
    server_name: str,
    timeout: int = 30,
) -> list[BaseTool]:
    """为 MCP 工具列表添加超时控制.

    Args:
        tools: 原始工具列表
        server_name: MCP 服务器名称
        timeout: 超时时间（秒）

    Returns:
        包装后的工具列表
    """
    return [MCPToolWithTimeout(tool, server_name, timeout) for tool in tools]
