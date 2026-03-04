"""FinchBot Agent 核心.

使用 LangChain 官方推荐的 create_agent 构建。
支持对话持久化存储和动态工具注册。
集成 MCP 和 Channel 能力信息注入。
"""

import asyncio
import os
import platform
import threading
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import aiosqlite
from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph.state import CompiledStateGraph  # type: ignore[attr-defined]
from loguru import logger

from finchbot.agent.context import ContextBuilder
from finchbot.i18n import t
from finchbot.workspace import SESSIONS_DIR

if TYPE_CHECKING:
    from finchbot.config.schema import Config

_tools_registered: bool = False
_tools_lock = threading.Lock()


def _ensure_tools_registered(
    workspace: Path | None = None, tools: Sequence[BaseTool] | None = None
) -> None:
    """确保工具已注册到全局注册表（线程安全）.

    Args:
        workspace: 工作目录路径（用于创建默认工具）
        tools: 直接传入的工具列表（优先级高于workspace）
    """
    global _tools_registered

    with _tools_lock:
        if _tools_registered:
            return

        from finchbot.tools import register_tool

        # 获取工具列表
        if tools:
            tool_list = list(tools)
        elif workspace:
            tool_list = _create_default_tools(workspace)
        else:
            tool_list = []

        # 批量注册
        registered = 0
        for tool in tool_list:
            register_tool(tool)
            registered += 1

        _tools_registered = True
        logger.info(f"工具注册完成: {registered}/{len(tool_list)}")


def _create_default_tools(workspace: Path) -> list[BaseTool]:
    """创建默认工具列表."""
    import asyncio

    from finchbot.agent.skills import BUILTIN_SKILLS_DIR
    from finchbot.config import load_config
    from finchbot.tools.builtin._utils import configure_tools
    from finchbot.tools.builtin.config import configure_config_tools
    from finchbot.tools.builtin.shell import configure_shell_tools
    from finchbot.tools.core import ToolRegistry

    config = load_config()
    allowed_dirs = [workspace]
    if BUILTIN_SKILLS_DIR.exists():
        allowed_dirs.append(BUILTIN_SKILLS_DIR)
    configure_tools(workspace, allowed_dirs)
    configure_config_tools(workspace)
    configure_shell_tools(working_dir=str(workspace))

    registry = ToolRegistry(workspace, config)
    return asyncio.get_event_loop().run_until_complete(registry.initialize())


def _create_workspace_templates(workspace: Path) -> None:
    """创建默认工作区模板文件.

    使用新的目录结构：
    - bootstrap/ 目录存放 Bootstrap 文件
    - config/ 目录存放配置文件
    - generated/ 目录存放自动生成的文件

    Args:
        workspace: 工作目录路径。
    """
    from finchbot.config import load_config
    from finchbot.i18n.loader import I18n
    from finchbot.workspace import (
        BOOTSTRAP_DIR,
        CONFIG_DIR,
        DEFAULT_GITIGNORE,
        GENERATED_DIR,
        GITIGNORE_FILE,
        MEMORY_DIR,
        SESSIONS_DIR,
        SKILLS_DIR,
    )

    config = load_config()
    i18n = I18n(config.language)

    # 创建目录结构
    (workspace / CONFIG_DIR).mkdir(parents=True, exist_ok=True)
    (workspace / BOOTSTRAP_DIR).mkdir(parents=True, exist_ok=True)
    (workspace / GENERATED_DIR).mkdir(parents=True, exist_ok=True)
    (workspace / SKILLS_DIR).mkdir(parents=True, exist_ok=True)
    (workspace / MEMORY_DIR).mkdir(parents=True, exist_ok=True)
    (workspace / SESSIONS_DIR).mkdir(parents=True, exist_ok=True)

    # Bootstrap 文件模板
    templates = {
        "SYSTEM.md": i18n.get("bootstrap.templates.system_md"),
        "MEMORY_GUIDE.md": i18n.get("bootstrap.templates.memory_guide_md"),
        "SOUL.md": i18n.get("bootstrap.templates.soul_md"),
        "AGENT_CONFIG.md": i18n.get("bootstrap.templates.agents_md"),
    }

    # 写入 Bootstrap 文件到 bootstrap/ 目录
    bootstrap_dir = workspace / BOOTSTRAP_DIR
    for filename, content in templates.items():
        file_path = bootstrap_dir / filename
        if not file_path.exists():
            file_path.write_text(content, encoding="utf-8")

    # 创建默认 MCP 配置
    mcp_path = workspace / CONFIG_DIR / "mcp.json"
    if not mcp_path.exists():
        mcp_path.write_text('{"servers": {}}', encoding="utf-8")

    # 创建 .gitignore
    gitignore_path = workspace / GITIGNORE_FILE
    if not gitignore_path.exists():
        gitignore_path.write_text(DEFAULT_GITIGNORE, encoding="utf-8")


def build_system_prompt(
    workspace: Path,
    use_cache: bool = True,
    tools: Sequence[BaseTool] | None = None,
    config: "Config | None" = None,
) -> str:
    """构建系统提示.

    支持 Bootstrap 文件和技能系统，集成 ToolRegistry 动态工具发现。
    注入 MCP 和 Channel 能力信息，让智能体"知道"自己的能力。
    从工作区加载 MCP 配置，并生成 CAPABILITIES.md 文件。

    Args:
        workspace: 工作目录路径。
        use_cache: 是否使用缓存。
        tools: 可选的工具列表，如果提供则直接注册，避免重新创建。
        config: 可选的配置对象，用于构建能力信息。

    Returns:
        系统提示字符串。
    """
    from finchbot.agent.capabilities import build_capabilities_prompt, write_capabilities_md
    from finchbot.config.loader import load_mcp_config
    from finchbot.tools.tools_generator import ToolsGenerator

    now = datetime.now().strftime("%Y-%m-%d %H:%M (%A)")

    system_name = platform.system()
    if system_name == "Windows":
        platform_hint = "Windows (请使用 Windows/PowerShell 命令语法)"
    elif system_name == "Darwin":
        platform_hint = "macOS (请使用 Unix/BSD 命令语法)"
    else:
        platform_hint = f"{system_name} (请使用 Unix/Linux 命令语法)"

    runtime = f"{platform_hint}, Python {platform.python_version()}"

    prompt_parts = []

    # 构建上下文（Bootstrap 文件和技能）
    context_builder = ContextBuilder(workspace)
    bootstrap_and_skills = context_builder.build_system_prompt(use_cache=use_cache)
    if bootstrap_and_skills:
        prompt_parts.append(bootstrap_and_skills)

    # 添加运行时信息
    prompt_parts.append(f"## {t('agent.current_time')}\n{now}")
    prompt_parts.append(f"## {t('agent.runtime')}\n{runtime}")
    prompt_parts.append(f"## {t('agent.workspace')}\n{workspace}")

    # 确保默认工具已注册（懒加载，只在首次调用时注册）
    _ensure_tools_registered(workspace=workspace, tools=tools)

    # 生成工具文档（从 ToolRegistry 动态发现 + 外部工具）
    tools_generator = ToolsGenerator(workspace, tools=tools)
    tools_content = tools_generator.generate_tools_content()

    # 将工具文档写入工作区文件，供 Agent 查看
    tools_file = tools_generator.write_to_file("TOOLS.md")
    if tools_file:
        logger.debug(f"工具文档已生成: {tools_file}")

    prompt_parts.append(tools_content)

    # 加载配置
    if config is None:
        from finchbot.config import load_config

        config = load_config()

    # 从工作区加载 MCP 配置（覆盖全局配置）
    mcp_servers = load_mcp_config(workspace)
    if mcp_servers:
        config.mcp.servers = mcp_servers
        logger.debug(f"从工作区加载 MCP 配置: {len(mcp_servers)} 个服务器")

    # 构建能力信息
    capabilities_prompt = build_capabilities_prompt(config, tools)
    if capabilities_prompt:
        prompt_parts.append(capabilities_prompt)
        logger.debug("已注入 MCP 和 Channel 能力信息到系统提示词")

        # 生成 CAPABILITIES.md 文件
        capabilities_file = write_capabilities_md(workspace, config, tools)
        if capabilities_file:
            logger.debug(f"能力信息已生成: {capabilities_file}")

    return "\n\n".join(prompt_parts)


def get_default_workspace() -> Path:
    """获取默认工作目录.

    优先级：
    1. 环境变量 FINCHBOT_WORKSPACE（Docker 环境使用）
    2. 配置文件中的 agents.defaults.workspace（用户自定义路径）
    3. 默认路径 ~/.finchbot/workspace
    """
    import os

    workspace: Path | None = None

    env_workspace = os.environ.get("FINCHBOT_WORKSPACE")
    if env_workspace:
        workspace = Path(env_workspace).expanduser().resolve()
        logger.debug(f"使用环境变量 FINCHBOT_WORKSPACE: {workspace}")
    else:
        try:
            from finchbot.config import load_config

            config = load_config()
            config_workspace = config.agents.defaults.workspace
            if config_workspace:
                workspace = Path(config_workspace).expanduser().resolve()
                logger.debug(f"使用配置文件中的 workspace: {workspace}")
        except Exception as e:
            logger.debug(f"读取配置文件失败，使用默认路径: {e}")

    if not workspace:
        workspace = Path.home() / ".finchbot" / "workspace"
        logger.debug(f"使用默认路径: {workspace}")

    workspace.mkdir(parents=True, exist_ok=True)
    _create_workspace_templates(workspace)
    return workspace


@asynccontextmanager
async def get_sqlite_checkpointer(workspace: Path) -> AsyncIterator[AsyncSqliteSaver]:
    """获取 SQLite Checkpointer 上下文管理器.

    Args:
        workspace: 工作目录路径。

    Yields:
        AsyncSqliteSaver 实例。
    """
    db_path = workspace / SESSIONS_DIR / "checkpoints.db"
    conn = await aiosqlite.connect(str(db_path), check_same_thread=False)
    try:
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA busy_timeout=30000")
        checkpointer = AsyncSqliteSaver(conn)
        yield checkpointer
    finally:
        await conn.close()


def get_memory_checkpointer() -> MemorySaver:
    """获取内存 Checkpointer.

    用于简单场景，会话不持久化。

    Returns:
        MemorySaver 实例。
    """
    return MemorySaver()


async def create_finch_agent(
    model: BaseChatModel,
    workspace: Path,
    tools: Sequence[BaseTool] | None = None,
    use_persistent: bool = True,
    config: "Config | None" = None,
    enable_mcp_hot_update: bool = True,
) -> tuple[CompiledStateGraph, AsyncSqliteSaver | MemorySaver]:
    """创建 FinchBot Agent.

    Args:
        model: 语言模型实例。
        workspace: 工作目录路径。
        tools: 可选的工具列表。
        use_persistent: 是否使用持久化 checkpointer（默认 True）。
        config: 可选的配置对象。
        enable_mcp_hot_update: 是否启用 MCP 热更新 middleware。

    Returns:
        (agent, checkpointer) 元组。
    """
    workspace = Path(workspace).expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    if use_persistent:
        db_path = workspace / SESSIONS_DIR / "checkpoints.db"
        conn = await aiosqlite.connect(str(db_path), check_same_thread=False)
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA busy_timeout=30000")
        checkpointer = AsyncSqliteSaver(conn)
    else:
        checkpointer = get_memory_checkpointer()

    if config is None:
        from finchbot.config import load_config

        config = load_config()

    middleware_list = []

    from finchbot.tools.core import ToolRegistry

    registry = ToolRegistry.get_instance()
    if not registry:
        registry = ToolRegistry(workspace, config)
        ToolRegistry.set_instance(registry)

    if enable_mcp_hot_update:
        try:
            from finchbot.tools.mcp.hot_update import MCPHotUpdateManager
            from finchbot.tools.middleware import (
                create_full_dynamic_middleware_stack,
                is_dynamic_prompt_available,
            )

            mcp_manager = MCPHotUpdateManager.get_instance()

            if is_dynamic_prompt_available():
                middleware_list = create_full_dynamic_middleware_stack(
                    mcp_manager=mcp_manager,
                    registry=registry,
                    initial_tools=tools,
                )
                system_prompt = ""
                logger.info("动态系统提示词 middleware 已启用")
            else:
                def _build_prompt():
                    return build_system_prompt(workspace, True, tools, config)

                loop = asyncio.get_running_loop()
                system_prompt = await loop.run_in_executor(None, _build_prompt)

                from finchbot.tools.middleware import create_mcp_hot_update_middleware
                mcp_middleware = create_mcp_hot_update_middleware(
                    mcp_manager,
                    registry,
                    initial_tools=tools,
                )
                if mcp_middleware:
                    middleware_list.append(mcp_middleware)
                logger.info("MCP 热更新 middleware 已启用（静态系统提示词模式）")

        except Exception as e:
            logger.warning(f"启用 MCP 热更新 middleware 失败: {e}")
            def _build_prompt():
                return build_system_prompt(workspace, True, tools, config)

            loop = asyncio.get_running_loop()
            system_prompt = await loop.run_in_executor(None, _build_prompt)
    else:
        def _build_prompt():
            return build_system_prompt(workspace, True, tools, config)

        loop = asyncio.get_running_loop()
        system_prompt = await loop.run_in_executor(None, _build_prompt)

    agent = create_agent(
        model=model,
        tools=list(tools) if tools else None,
        system_prompt=system_prompt,
        checkpointer=checkpointer,
        middleware=middleware_list,
    )

    return agent, checkpointer


def agent() -> CompiledStateGraph:
    """导出 Agent 供 LangGraph CLI 使用.

    Returns:
        编译好的 LangGraph 图。
    """

    from langchain_openai import ChatOpenAI
    from pydantic import SecretStr

    api_key = os.getenv("OPENAI_API_KEY")
    api_base = os.getenv("OPENAI_API_BASE")
    model_name = os.getenv("MODEL_NAME", "gpt-5")

    model = ChatOpenAI(
        model=model_name,
        api_key=SecretStr(api_key) if api_key else None,
        base_url=api_base,
    )

    workspace = get_default_workspace()
    checkpointer = get_memory_checkpointer()

    system_prompt = build_system_prompt(workspace)

    return create_agent(
        model=model,
        tools=None,
        system_prompt=system_prompt,
        checkpointer=checkpointer,
    )
