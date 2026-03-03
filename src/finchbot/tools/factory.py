"""工具工厂类.

负责根据配置创建和组装工具列表。
支持加载内置工具和 MCP 工具（通过 langchain-mcp-adapters）。
MCP 工具支持超时控制和连接管理。
"""

from __future__ import annotations

import os
from contextlib import AsyncExitStack
from pathlib import Path
from typing import TYPE_CHECKING

from langchain_core.tools import BaseTool
from loguru import logger

from finchbot.agent.skills import BUILTIN_SKILLS_DIR
from finchbot.agent.tools.background import BACKGROUND_TOOLS
from finchbot.agent.tools.cron import CRON_TOOLS, set_cron_service
from finchbot.cron import CronService
from finchbot.memory import MemoryManager
from finchbot.tools import (
    ConfigureMCPTool,
    EditFileTool,
    ExecTool,
    ForgetTool,
    GetCapabilitiesTool,
    GetMCPConfigPathTool,
    ListDirTool,
    ReadFileTool,
    RecallTool,
    RefreshCapabilitiesTool,
    RememberTool,
    SessionTitleTool,
    WebExtractTool,
    WebSearchTool,
    WriteFileTool,
)
from finchbot.tools.mcp_manager import MCPConnectionManager

if TYPE_CHECKING:
    from finchbot.config.schema import Config


class ToolFactory:
    """工具工厂类.

    负责根据配置创建和组装工具列表。
    支持加载内置工具和 MCP 工具（通过 langchain-mcp-adapters）。
    MCP 工具支持超时控制和连接管理。

    Attributes:
        config: FinchBot 配置
        workspace: 工作目录
        session_id: 会话 ID
        _mcp_manager: MCP 连接管理器
        _stack: AsyncExitStack 用于资源管理
    """

    def __init__(self, config: Config, workspace: Path, session_id: str = "default") -> None:
        """初始化工具工厂.

        Args:
            config: FinchBot 配置对象.
            workspace: 工作目录路径.
            session_id: 会话 ID.
        """
        self.config = config
        self.workspace = workspace
        self.session_id = session_id
        self._mcp_manager: MCPConnectionManager | None = None
        self._stack: AsyncExitStack | None = None

    def create_default_tools(self) -> list[BaseTool]:
        """创建默认工具集.

        Returns:
            工具列表.
        """
        allowed_read_dirs = [
            self.workspace,
            BUILTIN_SKILLS_DIR.parent,
        ]

        memory_manager = MemoryManager(self.workspace)

        tools: list[BaseTool] = [
            ReadFileTool(allowed_dirs=allowed_read_dirs, workspace=str(self.workspace)),
            WriteFileTool(allowed_dirs=[self.workspace], workspace=str(self.workspace)),
            EditFileTool(allowed_dirs=[self.workspace], workspace=str(self.workspace)),
            ListDirTool(allowed_dirs=allowed_read_dirs, workspace=str(self.workspace)),
        ]

        tools.extend(
            [
                RememberTool(workspace=str(self.workspace), memory_manager=memory_manager),
                RecallTool(workspace=str(self.workspace), memory_manager=memory_manager),
                ForgetTool(workspace=str(self.workspace), memory_manager=memory_manager),
            ]
        )

        tools.append(SessionTitleTool(workspace=str(self.workspace), session_id=self.session_id))

        exec_timeout = 60
        if hasattr(self.config, "tools") and hasattr(self.config.tools, "exec"):
            exec_timeout = self.config.tools.exec.timeout
        tools.append(ExecTool(timeout=exec_timeout, working_dir=str(self.workspace)))

        tools.append(WebExtractTool())

        web_search_tool = self._create_web_search_tool()
        if web_search_tool:
            tools.append(web_search_tool)

        tools.extend(
            [
                ConfigureMCPTool(workspace=str(self.workspace)),
                RefreshCapabilitiesTool(workspace=str(self.workspace)),
                GetCapabilitiesTool(workspace=str(self.workspace)),
                GetMCPConfigPathTool(workspace=str(self.workspace)),
            ]
        )

        tools.extend(BACKGROUND_TOOLS)

        cron_service = CronService(self.workspace / "data")
        set_cron_service(cron_service)
        tools.extend(CRON_TOOLS)

        return tools

    async def create_all_tools(self) -> list[BaseTool]:
        """创建所有工具（包括 MCP 工具）.

        Returns:
            工具列表.
        """
        tools = self.create_default_tools()

        mcp_tools = await self._load_mcp_tools()
        tools.extend(mcp_tools)

        return tools

    async def _load_mcp_tools(self) -> list[BaseTool]:
        """加载 MCP 工具.

        使用 MCPConnectionManager 管理 MCP 连接生命周期。

        Returns:
            MCP 工具列表.
        """
        if not self._has_mcp_config():
            return []

        try:
            self._stack = AsyncExitStack()
            await self._stack.__aenter__()

            self._mcp_manager = MCPConnectionManager(self.config)
            await self._stack.enter_async_context(self._mcp_manager)

            tools = await self._mcp_manager.connect_all()
            return tools

        except ImportError:
            logger.warning(
                "langchain-mcp-adapters not installed. Run: pip install langchain-mcp-adapters"
            )
            return []
        except Exception as e:
            logger.error(f"Failed to load MCP tools: {e}")
            return []

    def _has_mcp_config(self) -> bool:
        """检查是否有 MCP 配置."""
        return bool(self.config.mcp.servers)

    async def close(self) -> None:
        """清理 MCP 资源."""
        if self._stack:
            await self._stack.__aexit__(None, None, None)
            self._stack = None
            self._mcp_manager = None

    def get_mcp_status(self) -> dict[str, dict]:
        """获取 MCP 服务器状态.

        Returns:
            服务器状态映射
        """
        if self._mcp_manager:
            return self._mcp_manager.get_status()
        return {}

    async def reconnect_mcp(self) -> list[BaseTool]:
        """重连所有 MCP 服务器.

        Returns:
            所有工具列表
        """
        if self._mcp_manager:
            return await self._mcp_manager.reconnect_all()
        return []

    def _create_web_search_tool(self) -> WebSearchTool | None:
        """创建网页搜索工具.

        Returns:
            WebSearchTool 实例.
        """
        if not (hasattr(self.config, "tools") and hasattr(self.config.tools, "web")):
            return None

        tavily_key = self._get_tavily_key()
        brave_key = self.config.tools.web.search.brave_api_key

        return WebSearchTool(
            tavily_api_key=tavily_key,
            brave_api_key=brave_key,
            max_results=self.config.tools.web.search.max_results,
        )

    def _get_tavily_key(self) -> str | None:
        """获取 Tavily API Key.

        优先级: 环境变量 > 配置文件.
        """
        env_key = os.environ.get("TAVILY_API_KEY")
        if env_key:
            return env_key

        if hasattr(self.config, "tools") and hasattr(self.config.tools, "web"):
            return self.config.tools.web.search.api_key
        return None
