from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Any

from langchain_core.language_models import BaseChatModel
from langgraph.graph.state import CompiledStateGraph

from finchbot.agent.core import create_finch_agent
from finchbot.tools.factory import ToolFactory

if TYPE_CHECKING:
    from finchbot.config.schema import Config


class AgentFactory:
    """Agent 工厂类.

    负责组装 Agent，包括模型、工具和 checkpointer。
    """

    @staticmethod
    async def create_for_cli(
        session_id: str,
        workspace: Path,
        model: BaseChatModel,
        config: Config,
    ) -> tuple[CompiledStateGraph, Any, list[Any]]:
        """为 CLI 创建 Agent.

        Args:
            session_id: 会话 ID.
            workspace: 工作目录.
            model: 聊天模型实例.
            config: 配置对象.

        Returns:
            (agent, checkpointer, tools) 元组.
        """
        # 1. 准备工具
        tool_factory = ToolFactory(config, workspace, session_id)

        loop = asyncio.get_running_loop()
        tools = await loop.run_in_executor(None, tool_factory.create_default_tools)

        # 2. 创建 Agent
        agent, checkpointer = await create_finch_agent(
            model=model,
            workspace=workspace,
            tools=tools,
            use_persistent=True,
        )

        return agent, checkpointer, tools
