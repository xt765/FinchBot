"""FinchBot Agent 核心.

使用 LangChain 官方推荐的 create_agent 构建。
支持对话持久化存储。
"""

import platform
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.state import CompiledStateGraph

from finchbot.i18n import t
from finchbot.memory.enhanced import EnhancedMemoryStore


def build_system_prompt(workspace: Path, memory: EnhancedMemoryStore | None = None) -> str:
    """构建系统提示.

    Args:
        workspace: 工作目录路径。
        memory: 可选的记忆存储。

    Returns:
        系统提示字符串。
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M (%A)")
    runtime = f"{platform.system()} {platform.machine()}, Python {platform.python_version()}"

    prompt = f"""# {t("agent.title")}

{t("agent.system_prompt")}

## {t("agent.current_time")}
{now}

## {t("agent.runtime")}
{runtime}

## {t("agent.workspace")}
{workspace}
"""
    if memory:
        memory_context = memory.get_memory_context()
        if memory_context:
            prompt += f"\n## {t('agent.memory')}\n{memory_context}"

    return prompt


def get_default_workspace() -> Path:
    """获取默认工作目录."""
    workspace = Path.home() / ".finchbot" / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
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
    memory: EnhancedMemoryStore | None = None,
    use_persistent: bool = True,
) -> tuple[CompiledStateGraph, SqliteSaver | MemorySaver]:
    """创建 FinchBot Agent.

    Args:
        model: 语言模型实例。
        workspace: 工作目录路径。
        tools: 可选的工具列表。
        memory: 可选的记忆存储。
        use_persistent: 是否使用持久化 checkpointer（默认 True）。

    Returns:
        (agent, checkpointer) 元组。
    """
    workspace = Path(workspace).expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    if use_persistent:
        db_path = workspace / "checkpoints.db"
        # 直接创建 SqliteSaver 实例
        import sqlite3

        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        checkpointer = SqliteSaver(conn)
    else:
        checkpointer = get_memory_checkpointer()

    system_prompt = build_system_prompt(workspace, memory)

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

    api_key = os.getenv("OPENAI_API_KEY")
    api_base = os.getenv("OPENAI_API_BASE")
    model_name = os.getenv("MODEL_NAME", "gpt-5")

    model = ChatOpenAI(
        model=model_name,
        api_key=api_key,
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
