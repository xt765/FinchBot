"""MCP 连接管理器.

使用 AsyncExitStack 管理 MCP 连接生命周期，支持：
- 资源自动清理
- 连接状态监控
- 断线重连
- 健康检查
"""

from __future__ import annotations

import asyncio
import time
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from langchain_core.tools import BaseTool
from loguru import logger

from finchbot.tools.mcp_wrapper import MCPToolWithTimeout

if TYPE_CHECKING:
    from finchbot.config.schema import Config, MCPServerConfig


@dataclass
class MCPServerState:
    """MCP 服务器状态."""

    name: str
    config: MCPServerConfig
    connected: bool = False
    last_heartbeat_ms: int = 0
    last_error: str | None = None
    reconnect_count: int = 0
    tools: list[BaseTool] = field(default_factory=list)


class MCPConnectionManager:
    """MCP 连接管理器.

    管理所有 MCP 服务器的连接生命周期。

    Attributes:
        config: FinchBot 配置
        _stack: AsyncExitStack 用于资源管理
        _servers: 服务器状态映射
        _health_task: 健康检查任务
        _running: 是否运行中
    """

    def __init__(self, config: Config) -> None:
        """初始化连接管理器.

        Args:
            config: FinchBot 配置
        """
        self.config = config
        self._stack: AsyncExitStack | None = None
        self._servers: dict[str, MCPServerState] = {}
        self._health_task: asyncio.Task | None = None
        self._running = False
        self._reconnect_interval_s = 30
        self._health_check_interval_s = 60

    async def __aenter__(self) -> MCPConnectionManager:
        """异步上下文管理器入口."""
        await self.start()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """异步上下文管理器退出."""
        await self.stop()

    async def start(self) -> None:
        """启动连接管理器."""
        if self._running:
            return

        self._stack = AsyncExitStack()
        await self._stack.__aenter__()
        self._running = True

        for name, server_config in self.config.mcp.servers.items():
            if not server_config.disabled:
                self._servers[name] = MCPServerState(name=name, config=server_config)

        self._health_task = asyncio.create_task(self._health_check_loop())
        logger.info(f"MCP Connection Manager started with {len(self._servers)} servers")

    async def stop(self) -> None:
        """停止连接管理器."""
        self._running = False

        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
            self._health_task = None

        if self._stack:
            await self._stack.__aexit__(None, None, None)
            self._stack = None

        self._servers.clear()
        logger.info("MCP Connection Manager stopped")

    async def connect_all(self) -> list[BaseTool]:
        """连接所有 MCP 服务器并获取工具.

        Returns:
            所有 MCP 工具列表
        """
        if not self._stack:
            await self.start()

        all_tools: list[BaseTool] = []
        connect_tasks = []

        for name, state in self._servers.items():
            connect_tasks.append(self._connect_server(name, state))

        results = await asyncio.gather(*connect_tasks, return_exceptions=True)

        for name, result in zip(self._servers.keys(), results):
            if isinstance(result, Exception):
                logger.error(f"Failed to connect MCP server '{name}': {result}")
            elif isinstance(result, list):
                all_tools.extend(result)

        connected_count = sum(1 for s in self._servers.values() if s.connected)
        logger.info(
            f"MCP: {connected_count}/{len(self._servers)} servers connected, {len(all_tools)} tools loaded"
        )

        return all_tools

    async def _connect_server(self, name: str, state: MCPServerState) -> list[BaseTool]:
        """连接单个 MCP 服务器.

        Args:
            name: 服务器名称
            state: 服务器状态

        Returns:
            该服务器的工具列表
        """
        try:
            from langchain_mcp_adapters.client import MultiServerMCPClient

            server_config = self._build_server_config(name, state.config)
            if not server_config:
                return []

            client = MultiServerMCPClient({name: server_config})
            self._stack.push_async_exit(client)
            raw_tools = await client.get_tools()

            tools = []
            for tool in raw_tools:
                wrapped = MCPToolWithTimeout(tool, name, state.config.tool_timeout)
                tools.append(wrapped)

            state.tools = tools
            state.connected = True
            state.last_heartbeat_ms = int(time.time() * 1000)
            state.last_error = None

            logger.info(f"MCP server '{name}' connected with {len(tools)} tools")
            return tools

        except Exception as e:
            state.connected = False
            state.last_error = str(e)
            logger.error(f"Failed to connect MCP server '{name}': {e}")
            return []

    def _build_server_config(self, name: str, config: MCPServerConfig) -> dict | None:
        """构建服务器配置.

        Args:
            name: 服务器名称
            config: 服务器配置

        Returns:
            配置字典
        """
        if config.disabled:
            return None

        if config.command:
            server_cfg = {
                "command": config.command,
                "args": config.args or [],
                "transport": "stdio",
            }
            if config.env:
                server_cfg["env"] = config.env
            return server_cfg

        if config.url:
            server_cfg = {
                "url": config.url,
                "transport": "http",
            }
            if config.headers:
                server_cfg["headers"] = config.headers
            return server_cfg

        return None

    async def _health_check_loop(self) -> None:
        """健康检查循环."""
        while self._running:
            try:
                await asyncio.sleep(self._health_check_interval_s)
                await self._check_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")

    async def _check_health(self) -> None:
        """检查所有服务器健康状态."""
        for name, state in self._servers.items():
            if not state.connected:
                if state.reconnect_count < 3:
                    logger.info(f"Attempting to reconnect MCP server '{name}'")
                    await self._reconnect_server(name, state)
                else:
                    logger.warning(f"MCP server '{name}' exceeded max reconnect attempts")

    async def _reconnect_server(self, name: str, state: MCPServerState) -> None:
        """重连服务器.

        Args:
            name: 服务器名称
            state: 服务器状态
        """
        state.reconnect_count += 1
        tools = await self._connect_server(name, state)
        if tools:
            state.reconnect_count = 0
            logger.info(f"MCP server '{name}' reconnected successfully")

    def get_status(self) -> dict[str, dict]:
        """获取所有服务器状态.

        Returns:
            服务器状态映射
        """
        return {
            name: {
                "connected": state.connected,
                "tools": len(state.tools),
                "last_error": state.last_error,
                "reconnect_count": state.reconnect_count,
            }
            for name, state in self._servers.items()
        }

    async def reconnect_all(self) -> list[BaseTool]:
        """重连所有断开的服务器.

        Returns:
            所有工具列表
        """
        all_tools: list[BaseTool] = []

        for name, state in self._servers.items():
            if state.connected:
                all_tools.extend(state.tools)
            else:
                tools = await self._connect_server(name, state)
                all_tools.extend(tools)

        return all_tools
