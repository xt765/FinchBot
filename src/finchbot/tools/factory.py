from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from langchain_core.tools import BaseTool

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

    def create_default_tools(self) -> list[BaseTool]:
        """创建默认工具集.

        Returns:
            工具列表.
        """
        allowed_read_dirs = [
            self.workspace,
            BUILTIN_SKILLS_DIR.parent,
        ]

        memory_manager = MemoryManager(self.workspace, use_global_services=True)

        tools: list[BaseTool] = [
            ReadFileTool(allowed_dirs=allowed_read_dirs),
            WriteFileTool(allowed_dirs=[self.workspace]),
            EditFileTool(allowed_dirs=[self.workspace]),
            ListDirTool(allowed_dirs=allowed_read_dirs),
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
        tools.append(ExecTool(timeout=exec_timeout))

        tools.append(WebExtractTool())

        web_search_tool = self._create_web_search_tool()
        if web_search_tool:
            tools.append(web_search_tool)

        return tools

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
