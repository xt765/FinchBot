"""Agent 工厂类.

负责组装 Agent，包括模型、工具和 checkpointer。
支持加载 MCP 工具（通过 langchain-mcp-adapters）。
支持 SubagentManager 后台任务执行。
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from langchain_core.language_models import BaseChatModel
from langgraph.graph.state import CompiledStateGraph
from loguru import logger

from finchbot.agent.core import create_finch_agent
from finchbot.agent.skills import BUILTIN_SKILLS_DIR
from finchbot.agent.subagent import SubagentManager
from finchbot.agent.tools.background import get_job_manager
from finchbot.tools.builtin._utils import configure_tools
from finchbot.tools.builtin.config import configure_config_tools
from finchbot.tools.builtin.memory import set_memory_manager
from finchbot.tools.builtin.session import configure_session_tools
from finchbot.tools.builtin.shell import configure_shell_tools
from finchbot.tools.core import ToolRegistry

if TYPE_CHECKING:
    from finchbot.config.schema import Config
    from finchbot.services.manager import ServiceManager


def _update_generated_docs(workspace: Path, config: Config, tools: list[Any]) -> None:
    """更新生成的文档（TOOLS.md 和 CAPABILITIES.md）.

    Args:
        workspace: 工作目录.
        config: 配置对象.
        tools: 工具列表.
    """
    from finchbot.agent.capabilities import write_capabilities_md
    from finchbot.tools.tools_generator import ToolsGenerator

    tools_gen = ToolsGenerator(workspace, tools)
    tools_file = tools_gen.write_to_file("TOOLS.md")
    if tools_file:
        logger.debug(f"TOOLS.md updated at: {tools_file}")

    cap_file = write_capabilities_md(workspace, config, tools)
    if cap_file:
        logger.debug(f"CAPABILITIES.md updated at: {cap_file}")


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
    ) -> tuple[CompiledStateGraph, Any, list[Any], SubagentManager | None, ServiceManager | None]:
        """为 CLI 创建 Agent.

        统一初始化所有服务，确保正确的启动顺序和依赖关系。

        Args:
            session_id: 会话 ID.
            workspace: 工作目录.
            model: 聊天模型实例.
            config: 配置对象.

        Returns:
            (agent, checkpointer, tools, subagent_manager, service_manager) 元组.
        """
        allowed_dirs = [workspace]
        if BUILTIN_SKILLS_DIR.exists():
            allowed_dirs.append(BUILTIN_SKILLS_DIR)
        configure_tools(workspace, allowed_dirs)
        configure_config_tools(workspace)
        configure_session_tools(workspace, session_id)
        configure_shell_tools(working_dir=str(workspace))

        from finchbot.memory import MemoryManager

        memory_manager = MemoryManager(workspace)
        set_memory_manager(memory_manager)

        registry = ToolRegistry(workspace, config)
        ToolRegistry.set_instance(registry)
        builtin_tools = await registry.initialize()

        from finchbot.tools.mcp.hot_update import MCPHotUpdateManager

        mcp_manager = MCPHotUpdateManager(workspace, config, registry)
        MCPHotUpdateManager.set_instance(mcp_manager)
        mcp_tools = await mcp_manager.initialize()

        all_tools = list(builtin_tools) + list(mcp_tools)

        logger.info(f"Created {len(builtin_tools)} builtin + {len(mcp_tools)} MCP tools for session {session_id}")

        _update_generated_docs(workspace, config, all_tools)

        subagent_manager = SubagentManager(
            model=model,
            workspace=workspace,
            tools=all_tools,
            config=config,
        )

        job_manager = get_job_manager()
        job_manager.set_subagent_manager(subagent_manager)
        logger.debug("SubagentManager injected into JobManager")

        agent, checkpointer = await create_finch_agent(
            model=model,
            workspace=workspace,
            tools=all_tools,
            use_persistent=True,
            config=config,
        )

        service_manager = await AgentFactory._initialize_services(
            workspace=workspace,
            config=config,
            registry=registry,
            model=model,
            subagent_manager=subagent_manager,
        )

        return agent, checkpointer, all_tools, subagent_manager, service_manager

    @staticmethod
    async def _initialize_services(
        workspace: Path,
        config: Config,
        registry: ToolRegistry,
        model: BaseChatModel,
        subagent_manager: SubagentManager,
    ) -> ServiceManager:
        """初始化所有后台服务.

        确保服务在事件循环内正确启动。

        Args:
            workspace: 工作目录.
            config: 配置对象.
            registry: 工具注册表.
            model: 聊天模型实例.
            subagent_manager: 子代理管理器.

        Returns:
            ServiceManager 实例.
        """
        from finchbot.services.config import ServiceConfig
        from finchbot.services.manager import ServiceManager

        service_config = ServiceConfig(
            cron_enabled=True,
            heartbeat_enabled=False,
        )

        service_manager = ServiceManager(
            workspace=workspace,
            config=config,
            registry=registry,
            model=model,
            service_config=service_config,
        )
        ServiceManager.set_instance(service_manager)

        service_manager._services["subagent_manager"] = subagent_manager
        logger.debug("SubagentManager integrated with ServiceManager")

        await service_manager.start_all()
        logger.info(f"ServiceManager started for workspace: {workspace}")

        return service_manager

    @staticmethod
    async def create_for_langbot(
        workspace: Path,
        model: BaseChatModel,
        config: Config,
    ) -> tuple[CompiledStateGraph, Any, list[Any]]:
        """为 LangBot 渠道创建 Agent.

        Args:
            workspace: 工作目录.
            model: 聊天模型实例.
            config: 配置对象.

        Returns:
            (agent, checkpointer, tools) 元组.
        """
        allowed_dirs = [workspace]
        if BUILTIN_SKILLS_DIR.exists():
            allowed_dirs.append(BUILTIN_SKILLS_DIR)
        configure_tools(workspace, allowed_dirs)
        configure_config_tools(workspace)
        configure_shell_tools(working_dir=str(workspace))

        registry = ToolRegistry(workspace, config)
        ToolRegistry.set_instance(registry)
        builtin_tools = await registry.initialize()

        from finchbot.tools.mcp.hot_update import MCPHotUpdateManager

        mcp_manager = MCPHotUpdateManager(workspace, config, registry)
        MCPHotUpdateManager.set_instance(mcp_manager)
        mcp_tools = await mcp_manager.initialize()

        all_tools = list(builtin_tools) + list(mcp_tools)

        logger.info(f"Created {len(builtin_tools)} builtin + {len(mcp_tools)} MCP tools for LangBot")

        _update_generated_docs(workspace, config, all_tools)

        agent, checkpointer = await create_finch_agent(
            model=model,
            workspace=workspace,
            tools=all_tools,
            use_persistent=True,
            config=config,
        )

        return agent, checkpointer, all_tools
