from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from langchain_core.language_models import BaseChatModel
from langgraph.graph.state import CompiledStateGraph
from loguru import logger

from finchbot.agent.core import create_finch_agent
from finchbot.agent.subagent import SubagentManager
from finchbot.agent.tools.background import get_job_manager
from finchbot.tools.factory import ToolFactory

if TYPE_CHECKING:
    from finchbot.config.schema import Config


class AgentFactory:
    """Agent 工厂类.

    负责组装 Agent，包括模型、工具和 checkpointer。
    支持加载 MCP 工具（通过 langchain-mcp-adapters）。
    支持 SubagentManager 后台任务执行。
    """

    @staticmethod
    async def create_for_cli(
        session_id: str,
        workspace: Path,
        model: BaseChatModel,
        config: Config,
    ) -> tuple[CompiledStateGraph, Any, list[Any], SubagentManager | None]:
        """为 CLI 创建 Agent.

        Args:
            session_id: 会话 ID.
            workspace: 工作目录.
            model: 聊天模型实例.
            config: 配置对象.

        Returns:
            (agent, checkpointer, tools, subagent_manager) 元组.
        """
        tool_factory = ToolFactory(config, workspace, session_id)

        tools = await tool_factory.create_all_tools()
        logger.info(f"Created {len(tools)} tools for session {session_id}")

        subagent_manager = SubagentManager(
            model=model,
            workspace=workspace,
            tools=tools,
            config=config,
            on_notify=None,
        )

        job_manager = get_job_manager()
        job_manager.set_subagent_manager(subagent_manager)
        logger.debug("SubagentManager injected into JobManager")

        agent, checkpointer = await create_finch_agent(
            model=model,
            workspace=workspace,
            tools=tools,
            use_persistent=True,
            config=config,
        )

        return agent, checkpointer, tools, subagent_manager
