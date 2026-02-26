from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from langchain_core.tools import BaseTool
from loguru import logger

from finchbot.agent.skills import BUILTIN_SKILLS_DIR
from finchbot.memory import MemoryManager
from finchbot.tools import (
    EditFileTool,
    ExecTool,
    ForgetTool,
    ListDirTool,
    ReadFileTool,
    RecallTool,
    RememberTool,
    SessionTitleTool,
    WebExtractTool,
    WebSearchTool,
    WriteFileTool,
)

if TYPE_CHECKING:
    from finchbot.config.schema import Config


class ToolFactory:
    """工具工厂类.

    负责根据配置创建和组装工具列表。
    支持加载内置工具和 MCP 工具（通过 langchain-mcp-adapters）。
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
        self._mcp_client = None

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

        # 基础文件系统工具
        tools: list[BaseTool] = [
            ReadFileTool(allowed_dirs=allowed_read_dirs),
            WriteFileTool(allowed_dirs=[self.workspace]),
            EditFileTool(allowed_dirs=[self.workspace]),
            ListDirTool(allowed_dirs=allowed_read_dirs),
        ]

        # 记忆工具
        tools.extend([
            RememberTool(workspace=str(self.workspace), memory_manager=memory_manager),
            RecallTool(workspace=str(self.workspace), memory_manager=memory_manager),
            ForgetTool(workspace=str(self.workspace), memory_manager=memory_manager),
        ])

        # 会话工具
        tools.append(SessionTitleTool(workspace=str(self.workspace), session_id=self.session_id))

        # 执行工具
        exec_timeout = 60
        if hasattr(self.config, "tools") and hasattr(self.config.tools, "exec"):
            exec_timeout = self.config.tools.exec.timeout
        tools.append(ExecTool(timeout=exec_timeout))

        # 网页提取工具
        tools.append(WebExtractTool())

        # 网页搜索工具
        web_search_tool = self._create_web_search_tool()
        if web_search_tool:
            tools.append(web_search_tool)

        return tools

    async def create_all_tools(self) -> list[BaseTool]:
        """创建所有工具（包括 MCP 工具）.

        Returns:
            工具列表.
        """
        tools = self.create_default_tools()

        # 加载 MCP 工具
        mcp_tools = await self._load_mcp_tools()
        tools.extend(mcp_tools)

        return tools

    async def _load_mcp_tools(self) -> list[BaseTool]:
        """加载 MCP 工具.

        使用 langchain-mcp-adapters 官方库加载 MCP 服务器提供的工具。

        Returns:
            MCP 工具列表.
        """
        if not self._has_mcp_config():
            return []

        try:
            from langchain_mcp_adapters.client import MultiServerMCPClient

            server_config = self._build_mcp_server_config()
            if not server_config:
                return []

            self._mcp_client = MultiServerMCPClient(server_config)
            tools = await self._mcp_client.get_tools()

            logger.info(f"Loaded {len(tools)} MCP tools from {len(server_config)} servers")
            return tools

        except ImportError:
            logger.warning(
                "langchain-mcp-adapters not installed. "
                "Run: pip install langchain-mcp-adapters"
            )
            return []
        except Exception as e:
            logger.error(f"Failed to load MCP tools: {e}")
            return []

    def _has_mcp_config(self) -> bool:
        """检查是否有 MCP 配置."""
        return bool(self.config.mcp.servers)

    def _build_mcp_server_config(self) -> dict:
        """构建 MCP 服务器配置.

        将 FinchBot 的 MCPServerConfig 转换为 langchain-mcp-adapters 需要的格式。

        Returns:
            MCP 服务器配置字典.
        """
        config = {}

        for name, server in self.config.mcp.servers.items():
            if server.disabled:
                continue

            server_cfg = {}

            # stdio 传输
            if server.command:
                server_cfg = {
                    "command": server.command,
                    "args": server.args or [],
                    "transport": "stdio",
                }
                if server.env:
                    server_cfg["env"] = server.env

            # HTTP 传输
            elif server.url:
                server_cfg = {
                    "url": server.url,
                    "transport": "http",
                }
                if server.headers:
                    server_cfg["headers"] = server.headers

            if server_cfg:
                config[name] = server_cfg

        return config

    async def close(self) -> None:
        """清理 MCP 资源."""
        self._mcp_client = None

    def _create_web_search_tool(self) -> WebSearchTool | None:
        """创建网页搜索工具.

        Returns:
            WebSearchTool 实例.
        """
        if not (hasattr(self.config, "tools") and hasattr(self.config.tools, "web")):
            return None

        tavily_key = self._get_tavily_key()
        brave_key = self.config.tools.web.search.brave_api_key

        # 即使没有 API Key，也可以使用 DuckDuckGo，所以总是返回工具
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
