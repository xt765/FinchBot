"""FinchBot Agent 核心.

使用 LangChain 官方推荐的 create_agent 构建。
支持对话持久化存储和动态工具注册。
"""

import platform
import threading
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.state import CompiledStateGraph  # type: ignore[attr-defined]
from loguru import logger

from finchbot.agent.context import ContextBuilder
from finchbot.i18n import t

_default_tools_registered: bool = False
_tools_registration_lock = threading.Lock()


def _register_default_tools() -> None:
    """注册默认工具到全局工具注册表.

    自动发现并注册所有 FinchBot 内置工具。
    使用懒加载模式，只在首次调用时注册。

    使用线程锁确保并发安全。
    """
    global _default_tools_registered

    # 双重检查锁定模式 (Double-checked locking)
    if _default_tools_registered:
        return

    with _tools_registration_lock:
        if _default_tools_registered:
            return

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
            get_global_registry,
        )

        registry = get_global_registry()

        # 检查是否已经有工具注册，避免重复注册
        if len(registry) > 0:
            logger.debug(f"工具注册表已有 {len(registry)} 个工具，跳过默认工具注册")
            _default_tools_registered = True
            return

        tools = [
            ReadFileTool(),
            WriteFileTool(),
            EditFileTool(),
            ListDirTool(),
            ExecTool(),
            WebSearchTool(),
            WebExtractTool(),
            RememberTool(),
            RecallTool(),
            ForgetTool(),
            SessionTitleTool(),
        ]

        registered_count = 0
        for tool in tools:
            try:
                # 检查工具是否已存在，避免重复注册
                if registry.has(tool.name):
                    logger.debug(f"工具 '{tool.name}' 已存在，跳过注册")
                    continue
                registry.register(tool)
                registered_count += 1
                logger.debug(f"工具已注册: {tool.name}")
            except Exception as e:
                logger.error(f"注册工具失败 {tool.name}: {e}")

        _default_tools_registered = True
        logger.info(f"默认工具注册完成: {registered_count}/{len(tools)} 个工具")


def _create_workspace_templates(workspace: Path) -> None:
    """创建默认工作区模板文件.

    Args:
        workspace: 工作目录路径。
    """
    from finchbot.config import load_config
    from finchbot.i18n.loader import I18n

    config = load_config()
    i18n = I18n(config.language)

    templates = {
        "SYSTEM.md": i18n.get("bootstrap.templates.system_md"),
        "MEMORY_GUIDE.md": i18n.get("bootstrap.templates.memory_guide_md"),
        "SOUL.md": i18n.get("bootstrap.templates.soul_md"),
        "AGENT_CONFIG.md": i18n.get("bootstrap.templates.agents_md"),
    }

    for filename, content in templates.items():
        file_path = workspace / filename
        if not file_path.exists():
            file_path.write_text(content, encoding="utf-8")

    skills_dir = workspace / "skills"
    skills_dir.mkdir(exist_ok=True)


def build_system_prompt(
    workspace: Path,
    use_cache: bool = True,
) -> str:
    """构建系统提示.

    支持 Bootstrap 文件和技能系统，集成 ToolRegistry 动态工具发现。

    Args:
        workspace: 工作目录路径。
        use_cache: 是否使用缓存。

    Returns:
        系统提示字符串。
    """
    from finchbot.tools.tools_generator import ToolsGenerator

    now = datetime.now().strftime("%Y-%m-%d %H:%M (%A)")
    runtime = f"{platform.system()} {platform.machine()}, Python {platform.python_version()}"

    prompt_parts = []

    # 加载 SYSTEM.md
    system_md = workspace / "SYSTEM.md"
    if system_md.exists():
        try:
            content = system_md.read_text(encoding="utf-8")
            if content.strip():
                prompt_parts.append(content)
        except Exception as e:
            logger.warning(f"读取 SYSTEM.md 失败: {e}")

    # 加载 MEMORY_GUIDE.md
    memory_guide_md = workspace / "MEMORY_GUIDE.md"
    if memory_guide_md.exists():
        try:
            content = memory_guide_md.read_text(encoding="utf-8")
            if content.strip():
                prompt_parts.append(content)
        except Exception as e:
            logger.warning(f"读取 MEMORY_GUIDE.md 失败: {e}")

    # 加载 SOUL.md
    soul_md = workspace / "SOUL.md"
    if soul_md.exists():
        try:
            content = soul_md.read_text(encoding="utf-8")
            if content.strip():
                prompt_parts.append(content)
        except Exception as e:
            logger.warning(f"读取 SOUL.md 失败: {e}")

    # 加载 SOUL.md
    agent_config_md = workspace / "AGENT_CONFIG.md"
    if soul_md.exists():
        try:
            content = agent_config_md.read_text(encoding="utf-8")
            if content.strip():
                prompt_parts.append(content)
        except Exception as e:
            logger.warning(f"读取 AGENT_CONFIG.md 失败: {e}")

    # 添加运行时信息
    prompt_parts.append(f"## {t('agent.current_time')}\n{now}")
    prompt_parts.append(f"## {t('agent.runtime')}\n{runtime}")
    prompt_parts.append(f"## {t('agent.workspace')}\n{workspace}")

    # 构建上下文（Bootstrap 文件和技能）
    context_builder = ContextBuilder(workspace)
    bootstrap_and_skills = context_builder.build_system_prompt(use_cache=use_cache)
    if bootstrap_and_skills:
        prompt_parts.append(bootstrap_and_skills)

    # 确保默认工具已注册（懒加载，只在首次调用时注册）
    _register_default_tools()

    # 生成工具文档（从 ToolRegistry 动态发现）
    tools_generator = ToolsGenerator(workspace)
    tools_content = tools_generator.generate_tools_content()

    # 将工具文档写入工作区文件，供 Agent 查看
    tools_file = tools_generator.write_to_file("TOOLS.md")
    if tools_file:
        logger.debug(f"工具文档已生成: {tools_file}")

    prompt_parts.append(tools_content)

    return "\n\n".join(prompt_parts)


def get_default_workspace() -> Path:
    """获取默认工作目录."""
    workspace = Path.home() / ".finchbot" / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    _create_workspace_templates(workspace)
    return workspace


@contextmanager
def get_sqlite_checkpointer(workspace: Path) -> Iterator[SqliteSaver]:
    """获取 SQLite Checkpointer 上下文管理器.

    Args:
        workspace: 工作目录路径。

    Yields:
        SqliteSaver 实例。
    """
    db_path = workspace / "checkpoints.db"
    with SqliteSaver.from_conn_string(str(db_path)) as checkpointer:
        yield checkpointer


def get_memory_checkpointer() -> MemorySaver:
    """获取内存 Checkpointer.

    用于简单场景，会话不持久化。

    Returns:
        MemorySaver 实例。
    """
    return MemorySaver()


def create_finch_agent(
    model: BaseChatModel,
    workspace: Path,
    tools: Sequence[BaseTool] | None = None,
    use_persistent: bool = True,
) -> tuple[CompiledStateGraph, SqliteSaver | MemorySaver]:
    """创建 FinchBot Agent.

    Args:
        model: 语言模型实例。
        workspace: 工作目录路径。
        tools: 可选的工具列表。
        use_persistent: 是否使用持久化 checkpointer（默认 True）。

    Returns:
        (agent, checkpointer) 元组。
    """
    workspace = Path(workspace).expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    if use_persistent:
        db_path = workspace / "checkpoints.db"
        import sqlite3

        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        checkpointer = SqliteSaver(conn)
    else:
        checkpointer = get_memory_checkpointer()

    system_prompt = build_system_prompt(workspace)

    agent = create_agent(
        model=model,
        tools=list(tools) if tools else None,
        system_prompt=system_prompt,
        checkpointer=checkpointer,
    )

    return agent, checkpointer


def agent() -> CompiledStateGraph:
    """导出 Agent 供 LangGraph CLI 使用.

    Returns:
        编译好的 LangGraph 图。
    """
    import os

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
