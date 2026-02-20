"""聊天会话模块.

提供 REPL 模式下的聊天功能，包括会话管理、历史记录、消息回退等。
"""

from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path
from typing import Any

import typer
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from loguru import logger
from rich import box
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from finchbot.config import load_config
from finchbot.i18n import t
from finchbot.sessions import SessionMetadataStore

console = Console()

EXIT_COMMANDS = {"exit", "quit", "/exit", "/quit", ":q", "q"}
GOODBYE_MESSAGE = "\n[dim]Goodbye! 👋[/dim]"


def _format_message(
    msg: BaseMessage | Any,
    index: int,
    show_index: bool = True,
    max_content_len: int = 9999,
    render_markdown: bool = True,
) -> None:
    """格式化并显示单条消息。

    支持 HumanMessage, AIMessage, SystemMessage, ToolMessage 等多种类型。
    使用 Rich Panel 进行美化输出。

    Args:
        msg: 消息对象 (BaseMessage 实例)。
        index: 消息在历史记录中的索引。
        show_index: 是否显示索引（用于回滚操作参考）。
        max_content_len: 内容最大显示长度（超过截断），默认不截断。
        render_markdown: 是否将 AI 消息渲染为 Markdown，默认为 True。
    """
    msg_type = getattr(msg, "type", None)
    content = getattr(msg, "content", "") or ""
    tool_calls = getattr(msg, "tool_calls", None) or []
    name = getattr(msg, "name", None)

    prefix = f"[{index}] " if show_index else ""

    panel_width = None

    msg_role = getattr(msg, "role", None)
    if msg_type == "human" or msg_role == "user":
        role_label = t("cli.history.role_you")
        role_icon = "👤"
        role_color = "cyan"
        console.print(
            Panel(
                str(content),
                title=f"[{role_color}]{prefix}{role_icon} {role_label}[/{role_color}]",
                border_style=role_color,
                padding=(0, 1),
                width=panel_width,
            )
        )

    elif tool_calls:
        role_label = t("cli.history.role_tool")
        role_icon = "🔧"
        role_color = "yellow"
        tool_names = [tc.get("name", "unknown") for tc in tool_calls]
        tool_info = f" {', '.join(tool_names)}" if tool_names else ""
        console.print(
            Panel(
                tool_info.strip() or "tool call",
                title=f"[{role_color}]{prefix}{role_icon} {role_label}[/{role_color}]",
                border_style=role_color,
                padding=(0, 1),
                width=panel_width,
            )
        )

    elif name:
        role_label = t("cli.history.role_tool")
        role_icon = "🔧"
        role_color = "yellow"
        console.print(
            Panel(
                str(content),
                title=f"[{role_color}]{prefix}{role_icon} {name}[/{role_color}]",
                border_style=role_color,
                padding=(0, 1),
                width=panel_width,
            )
        )

    elif msg_type == "ai" or msg_role == "assistant":
        if not content:
            return
        role_label = t("cli.history.role_bot")
        role_icon = "🐦"
        role_color = "green"
        body = Markdown(str(content)) if render_markdown else Text(str(content))
        console.print(
            Panel(
                body,
                title=f"[{role_color}]{prefix}{role_icon} {role_label}[/{role_color}]",
                border_style=role_color,
                padding=(0, 1),
                width=panel_width,
            )
        )

    elif msg_type == "system" or msg_role == "system":
        role_label = t("cli.history.role_system")
        role_icon = "⚙️"
        role_color = "dim"
        console.print(
            Panel(
                str(content),
                title=f"[{role_color}]{prefix}{role_icon} {role_label}[/{role_color}]",
                border_style=role_color,
                padding=(0, 1),
                width=panel_width,
            )
        )

    else:
        role_label = "未知"
        role_icon = "❓"
        role_color = "red"
        console.print(
            Panel(
                str(content),
                title=f"[{role_color}]{prefix}{role_icon} {role_label}[/{role_color}]",
                border_style=role_color,
                padding=(0, 1),
                width=panel_width,
            )
        )


def _display_tool_call(tool_name: str, tool_args: dict, console: Console) -> None:
    """显示工具调用参数.

    Args:
        tool_name: 工具名称
        tool_args: 工具参数
        console: Rich Console
    """
    table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
    table.add_column(t("cli.tool_display.param_column"), style="cyan", no_wrap=True)
    table.add_column(t("cli.tool_display.value_column"), style="white")

    for key, value in tool_args.items():
        value_str = str(value)
        if len(value_str) > 60:
            value_str = value_str[:57] + "..."
        table.add_row(key, value_str)

    console.print(
        Panel(
            table,
            title=t("cli.tool_display.tool_call_title").format(tool_name),
            border_style="yellow",
            padding=(0, 1),
        )
    )


def _display_tool_result(tool_name: str, result: str, duration: float, console: Console) -> None:
    """显示工具执行结果.

    Args:
        tool_name: 工具名称
        result: 执行结果
        duration: 执行时间（秒）
        console: Rich Console
    """
    display_result = result
    if len(display_result) > 200:
        display_result = display_result[:197] + "..."

    border_color = "green" if "✅" in result or result.startswith("Success") else "yellow"

    console.print(
        Panel(
            f"{display_result}\n\n[dim]{t('cli.tool_display.execution_time').format(duration)}[/dim]",
            title=t("cli.tool_display.tool_result_title").format(tool_name),
            border_style=border_color,
            padding=(0, 1),
        )
    )


def _stream_ai_response(
    agent: CompiledStateGraph,
    user_input: str,
    config: RunnableConfig,
    console: Console,
    render_markdown: bool = True,
) -> list[BaseMessage]:
    """流式输出 AI 响应，并显示详细的工具调用信息.

    Args:
        agent: LangGraph Agent
        user_input: 用户输入
        config: 运行配置
        console: Rich Console
        render_markdown: 是否渲染 Markdown

    Returns:
        所有消息列表
    """
    input_data = {"messages": [{"role": "user", "content": user_input}]}
    full_content = ""
    all_messages: list[BaseMessage] = []
    tool_start_time: float | None = None
    current_tool_name: str | None = None

    with Live(
        Panel(Text(""), title="🐦 FinchBot", border_style="green"),
        console=console,
        refresh_per_second=10,
        transient=True,
    ) as live:
        for event in agent.stream(input_data, config=config, stream_mode=["messages", "updates"]):
            if isinstance(event, tuple):
                token, metadata = event
                if (
                    isinstance(metadata, dict)
                    and metadata.get("langgraph_node") == "model"
                    or isinstance(token, str)
                ):
                    full_content += token
                    live.update(
                        Panel(
                            Text(full_content),
                            title="🐦 FinchBot",
                            border_style="green",
                        )
                    )
            elif isinstance(event, dict):
                for _node_name, node_data in event.items():
                    if not isinstance(node_data, dict):
                        continue
                    messages = node_data.get("messages", [])
                    if not messages:
                        continue
                    for msg in messages:
                        if hasattr(msg, "tool_calls") and msg.tool_calls:
                            for tc in msg.tool_calls:
                                tool_name: str = tc.get("name") or "unknown"
                                _display_tool_call(tool_name, tc.get("args", {}), console)
                                tool_start_time = time.time()
                        elif hasattr(msg, "name") and msg.name:
                            duration = 0.0
                            if tool_start_time:
                                duration = time.time() - tool_start_time
                                tool_start_time = None
                            _display_tool_result(msg.name, str(msg.content), duration, console)
                        all_messages.append(msg)

    if render_markdown and full_content:
        console.print(
            Panel(
                Markdown(full_content),
                title="🐦 FinchBot",
                border_style="green",
                padding=(0, 1),
            )
        )

    return all_messages


def _display_messages_by_turn(
    messages: list[BaseMessage | Any], show_index: bool = True, render_markdown: bool = True
) -> None:
    """按轮次分组显示消息。

    将连续的消息（User -> AI -> Tools -> AI）视为一轮对话进行展示。

    Args:
        messages: 消息对象列表 (BaseMessage)。
        show_index: 是否显示索引。
        render_markdown: 是否将 AI 消息渲染为 Markdown。
    """
    if not messages:
        return

    console.print(Rule(style="dim"))
    turn_num = 0
    i = 0

    while i < len(messages):
        msg = messages[i]
        msg_type = getattr(msg, "type", None)
        msg_role = getattr(msg, "role", None)

        if msg_type == "human" or msg_role == "user":
            turn_num += 1
            console.print()
            console.print(f"[dim]─── 第 {turn_num} 轮对话 ───[/dim]")

            _format_message(msg, i, show_index=show_index, render_markdown=render_markdown)

            j = i + 1
            while j < len(messages):
                next_msg = messages[j]
                next_type = getattr(next_msg, "type", None)
                next_role = getattr(next_msg, "role", None)
                tool_calls = getattr(next_msg, "tool_calls", None) or []
                name = getattr(next_msg, "name", None)

                if next_type == "human" or next_role == "user":
                    break
                if next_type == "ai" or next_role == "assistant":
                    _format_message(
                        next_msg,
                        j,
                        show_index=show_index,
                        max_content_len=80,
                        render_markdown=render_markdown,
                    )
                    j += 1
                    break
                elif tool_calls or name:
                    _format_message(
                        next_msg,
                        j,
                        show_index=show_index,
                        max_content_len=50,
                        render_markdown=render_markdown,
                    )
                    j += 1
                else:
                    break

            i = j
        else:
            _format_message(msg, i, show_index=show_index, render_markdown=render_markdown)
            i += 1

    console.print()


def calculate_turn_count(messages: list[BaseMessage | Any]) -> int:
    """计算会话轮次。

    一问一答算一轮，即统计有多少个有效的"human消息+ai消息"对。
    如果最后一条消息是人类消息（没有AI回答），则不计入轮次。

    Args:
        messages: 消息列表

    Returns:
        会话轮次数量
    """
    if not messages:
        return 0

    turn_count = 0
    prev_was_human = False

    for msg in messages:
        msg_type = getattr(msg, "type", None)
        if msg_type == "human":
            prev_was_human = True
        elif msg_type == "ai" and prev_was_human:
            turn_count += 1
            prev_was_human = False

    return turn_count


def _update_session_turn_count(
    session_store: SessionMetadataStore,
    session_id: str,
    agent: Any,
    chat_model: Any = None,
) -> None:
    """更新会话的轮次计数和标题。

    Args:
        session_store: 会话元数据存储
        session_id: 会话ID
        agent: Agent 实例
        chat_model: 可选的聊天模型，用于生成标题
    """
    try:
        config = {"configurable": {"thread_id": session_id}}
        current_state = agent.get_state(config)
        messages = current_state.values.get("messages", [])
        turn_count = calculate_turn_count(messages)
        session_store.update_activity(session_id, turn_count=turn_count)

        if chat_model and turn_count >= 2:
            session = session_store.get_session(session_id)
            if session and (not session.title.strip() or session.title == session_id):
                from finchbot.sessions.title_generator import generate_session_title_with_ai

                title = generate_session_title_with_ai(chat_model, messages)
                if title:
                    session_store.update_activity(
                        session_id, title=title, message_count=session.message_count
                    )
                    console.print(f"[dim]💡 {t('cli.chat.session_title').format(title)}[/dim]")
    except Exception as e:
        logger.warning(f"Failed to update turn count for session {session_id}: {e}")


def _get_llm_config(model: str, config_obj: Any) -> tuple[str | None, str | None, str | None]:
    """获取 LLM 配置.

    优先级：显式传入 > 环境变量 > 配置文件 > 自动检测。

    Args:
        model: 模型名称
        config_obj: 配置对象

    Returns:
        (api_key, api_base, detected_model) 元组
    """

    model_lower = model.lower()

    provider_keywords = {
        "openai": ["gpt", "openai"],
        "anthropic": ["claude", "anthropic"],
        "google": ["gemini", "google"],
        "azure": ["azure"],
        "ollama": ["ollama", "localhost"],
        "deepseek": ["deepseek"],
    }

    provider = "openai"
    for name, keywords in provider_keywords.items():
        if any(kw in model_lower for kw in keywords):
            provider = name
            break

    api_key, api_base = _get_provider_config(provider, config_obj)

    detected_model = None
    if not api_key:
        api_key, api_base, detected_provider, detected_model = _auto_detect_provider()

    return api_key, api_base, detected_model


def _get_provider_config(provider: str, config_obj: Any) -> tuple[str | None, str | None]:
    """获取指定 provider 的 API key 和 base.

    Args:
        provider: provider 名称
        config_obj: 配置对象

    Returns:
        (api_key, api_base) 元组
    """
    env_prefix = provider.upper()
    api_key = os.environ.get(f"{env_prefix}_API_KEY")
    if api_key:
        api_base = os.environ.get(f"{env_prefix}_API_BASE")
        return api_key, api_base

    api_key = None
    api_base = None
    if hasattr(config_obj, "providers") and config_obj.providers:
        provider_config = config_obj.providers.get(provider)
        if provider_config:
            api_key = provider_config.api_key
            api_base = provider_config.api_base

    return api_key, api_base


def _auto_detect_provider() -> tuple[str | None, str | None, str | None, str | None]:
    """自动检测可用的 provider.

    Returns:
        (api_key, api_base, provider, model) 元组
    """
    providers = ["OPENAI", "ANTHROPIC", "GOOGLE", "DEEPSEEK", "AZURE_OPENAI"]

    for provider in providers:
        api_key = os.environ.get(f"{provider}_API_KEY")
        if api_key:
            api_base = os.environ.get(f"{provider}_API_BASE")
            model_map = {
                "OPENAI": "gpt-4o",
                "ANTHROPIC": "claude-sonnet-4-20250514",
                "GOOGLE": "gemini-2.0-flash",
                "DEEPSEEK": "deepseek-chat",
                "AZURE_OPENAI": "gpt-4o",
            }
            return api_key, api_base, provider.lower(), model_map.get(provider)

    return None, None, None, None


def _get_tavily_key(config_obj: Any) -> str | None:
    """获取 Tavily API key.

    优先级：环境变量 > 配置文件

    Args:
        config_obj: 配置对象

    Returns:
        API key 或 None
    """
    env_key = os.environ.get("TAVILY_API_KEY")
    if env_key:
        return env_key

    if hasattr(config_obj, "tools") and hasattr(config_obj.tools, "web"):
        return config_obj.tools.web.search.tavily_api_key
    return None


def _setup_chat_tools(config_obj: Any, ws_path: Path, session_id: str) -> tuple[list, bool]:
    """设置聊天工具列表.

    Args:
        config_obj: 配置对象
        ws_path: 工作目录路径
        session_id: 会话 ID

    Returns:
        (tools, web_enabled) 元组
    """
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

    allowed_read_dirs = [
        ws_path,
        BUILTIN_SKILLS_DIR.parent,
    ]

    memory_manager = MemoryManager(ws_path)

    tools = [
        ReadFileTool(allowed_dirs=allowed_read_dirs),
        WriteFileTool(allowed_dirs=[ws_path]),
        EditFileTool(allowed_dirs=[ws_path]),
        ListDirTool(allowed_dirs=allowed_read_dirs),
        RememberTool(workspace=str(ws_path), memory_manager=memory_manager),
        RecallTool(workspace=str(ws_path), memory_manager=memory_manager),
        ForgetTool(workspace=str(ws_path), memory_manager=memory_manager),
        SessionTitleTool(workspace=str(ws_path), session_id=session_id),
        ExecTool(timeout=config_obj.tools.exec.timeout),
        WebExtractTool(),
    ]

    tavily_key = _get_tavily_key(config_obj)
    brave_key = config_obj.tools.web.search.brave_api_key
    web_enabled = False
    if tavily_key or brave_key:
        tools.append(
            WebSearchTool(
                tavily_api_key=tavily_key,
                brave_api_key=brave_key,
                max_results=config_obj.tools.web.search.max_results,
            )
        )
        web_enabled = True

    return tools, web_enabled


def _run_chat_session(
    session_id: str,
    model: str | None,
    workspace: str | None,
    first_message: str | None = None,
    render_markdown: bool = True,
) -> None:
    """启动聊天会话（REPL 模式）.

    Args:
        session_id: 会话 ID
        model: 模型名称
        workspace: 工作目录
        first_message: 第一条消息（可选，如提供则先发送此消息再进入交互模式）
        render_markdown: 是否将 AI 消息渲染为 Markdown，默认为 True
    """
    from prompt_toolkit import PromptSession
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.patch_stdout import patch_stdout

    from finchbot.agent import create_finch_agent
    from finchbot.providers import create_chat_model

    config_obj = load_config()
    use_model = model or config_obj.default_model
    api_key, api_base, detected_model = _get_llm_config(use_model, config_obj)

    if detected_model:
        use_model = detected_model
        console.print(f"[dim]{t('cli.chat.auto_detected_model').format(use_model)}[/dim]")

    if not api_key:
        console.print(f"[red]{t('cli.error_no_api_key')}[/red]")
        console.print(t("cli.error_config_hint"))
        raise typer.Exit(1)

    if workspace:
        ws_path = Path(workspace).expanduser()
    else:
        from finchbot.agent import get_default_workspace

        ws_path = get_default_workspace()

    tools, web_enabled = _setup_chat_tools(config_obj, ws_path, session_id)

    chat_model = create_chat_model(
        model=use_model,
        api_key=api_key,
        api_base=api_base,
        temperature=config_obj.agents.defaults.temperature,
    )

    history_file = Path.home() / ".finchbot" / "history" / "chat_history"
    history_file.parent.mkdir(parents=True, exist_ok=True)

    console.print(f"\n[bold cyan]{t('cli.chat.title')}[/bold cyan]")
    session_store = SessionMetadataStore(ws_path)
    if not session_store.session_exists(session_id):
        session_store.create_session(session_id, title=session_id)

    current_session = session_store.get_session(session_id)
    session_title = current_session.title if current_session else None
    if session_title == session_id:
        session_title = None

    session_display = session_id
    if session_title:
        session_display = f"{session_id} ({session_title})"
    console.print(f"[dim]{t('cli.chat.session').format(session_display)}[/dim]")

    console.print(f"[dim]{t('cli.chat.model').format(use_model)}[/dim]")
    console.print(f"[dim]{t('cli.chat.workspace').format(ws_path)}[/dim]")
    web_status = (
        t("cli.chat.web_search_enabled") if web_enabled else t("cli.chat.web_search_disabled")
    )
    console.print(f"[dim]{web_status}[/dim]")
    console.print(f"[dim]{t('cli.chat.type_to_quit')}[/dim]\n")

    agent, checkpointer = create_finch_agent(
        model=chat_model,
        workspace=ws_path,
        tools=tools,
        use_persistent=True,
    )

    config = {"configurable": {"thread_id": session_id}}
    current_state = agent.get_state(config)
    messages = current_state.values.get("messages", []) if current_state else []
    if messages:
        console.print(f"\n[dim]{t('cli.history.title')}[/dim]")
        _display_messages_by_turn(messages, show_index=False, render_markdown=render_markdown)
        console.print(f"[dim]{t('cli.history.total_messages').format(len(messages))}[/dim]")
        console.print()

    if first_message:
        runnable_config: RunnableConfig = {"configurable": {"thread_id": session_id}}
        try:
            all_messages = _stream_ai_response(
                agent, first_message, runnable_config, console, render_markdown
            )
        except Exception as stream_error:
            logger.error(f"Stream error: {stream_error}")
            console.print(f"[red]Error: {stream_error}[/red]")
            all_messages = []

        if not all_messages:
            console.print("[yellow]No response from agent[/yellow]")

        msg_count = len(all_messages)
        session_store.update_activity(session_id, message_count=msg_count)
        _update_session_turn_count(session_store, session_id, agent, chat_model)

        console.print()

    prompt_session = PromptSession(
        history=FileHistory(str(history_file)),
        enable_open_in_editor=False,
        multiline=False,
    )

    while True:
        try:
            with patch_stdout():
                user_input = prompt_session.prompt(
                    HTML("<b fg='ansiblue'>You:</b> "),
                )

            command = user_input.strip()
            if not command:
                continue

            if command.lower() in EXIT_COMMANDS:
                _update_session_turn_count(session_store, session_id, agent, chat_model)
                console.print(GOODBYE_MESSAGE)
                break

            if command.lower() in {"history", "/history"}:
                try:
                    config = {"configurable": {"thread_id": session_id}}
                    current_state = agent.get_state(config)
                    messages = current_state.values.get("messages", [])

                    console.print(f"\n[dim]{t('cli.history.title')}[/dim]")
                    _display_messages_by_turn(
                        messages, show_index=True, render_markdown=render_markdown
                    )
                    console.print(
                        f"[dim]{t('cli.history.total_messages').format(len(messages))}[/dim]"
                    )
                    console.print(f"[dim]{t('cli.history.rollback_hint')}[/dim]\n")
                except Exception as e:
                    console.print(f"[red]{t('cli.rollback.error_showing').format(e)}[/red]")
                continue

            if command.startswith("/rollback "):
                parts = command.split(maxsplit=2)
                if len(parts) < 2:
                    console.print(f"[red]{t('cli.rollback.usage_rollback')}[/red]")
                    continue

                try:
                    msg_index = int(parts[1])
                    new_sess = parts[2].strip() if len(parts) > 2 else None

                    config = {"configurable": {"thread_id": session_id}}
                    current_state = agent.get_state(config)
                    messages = current_state.values.get("messages", [])

                    if msg_index < 0 or msg_index > len(messages):
                        console.print(
                            f"[red]{t('cli.rollback.invalid_index').format(len(messages) - 1)}[/red]"
                        )
                        continue

                    rolled_back = messages[:msg_index]

                    if new_sess:
                        # 创建新会话并初始化状态
                        new_config: RunnableConfig = {"configurable": {"thread_id": new_sess}}

                        # 确保新会话 ID 在 metadata 存储中存在
                        if not session_store.session_exists(new_sess):
                            session_store.create_session(new_sess, title=f"Fork from {session_id}")

                        # 更新 Agent 状态到新会话
                        agent.update_state(new_config, {"messages": rolled_back})

                        # 切换当前会话 ID
                        session_id = new_sess
                        msg_count = len(rolled_back)

                        # 更新新会话的显示信息
                        session_display = f"{session_id} (Forked)"
                        console.print(f"[dim]{t('cli.chat.session').format(session_display)}[/dim]")

                        console.print(
                            f"[green]{t('cli.rollback.create_success').format(new_sess, msg_count)}[/green]"
                        )
                    else:
                        agent.update_state(config, {"messages": rolled_back})
                        console.print(
                            f"[green]{t('cli.rollback.rollback_success').format(len(rolled_back))}[/green]"
                        )

                    console.print(
                        f"[dim]{t('cli.rollback.removed_messages').format(len(messages) - msg_index)}[/dim]\n"
                    )

                except ValueError:
                    console.print(f"[red]{t('cli.rollback.message_index_number')}[/red]")
                except Exception as e:
                    console.print(f"[red]{t('cli.rollback.error_showing').format(e)}[/red]")

                continue

            if command.startswith("/back "):
                parts = command.split(maxsplit=1)
                if len(parts) < 2:
                    console.print(f"[red]{t('cli.rollback.usage_back')}[/red]")
                    continue

                try:
                    n = int(parts[1])

                    config = {"configurable": {"thread_id": session_id}}
                    current_state = agent.get_state(config)
                    messages = current_state.values.get("messages", [])

                    if n <= 0 or n > len(messages):
                        console.print(
                            f"[red]{t('cli.rollback.invalid_number').format(len(messages))}[/red]"
                        )
                        continue

                    new_count = len(messages) - n
                    rolled_back = messages[:new_count]
                    agent.update_state(config, {"messages": rolled_back})

                    console.print(f"[green]{t('cli.rollback.remove_success').format(n)}[/green]")
                    console.print(
                        f"[dim]{t('cli.rollback.current_messages').format(new_count)}[/dim]\n"
                    )

                except ValueError:
                    console.print(f"[red]{t('cli.rollback.number_integer')}[/red]")
                except Exception as e:
                    console.print(f"[red]{t('cli.rollback.error_showing').format(e)}[/red]")

                continue

            config: RunnableConfig = {"configurable": {"thread_id": session_id}}
            try:
                all_messages = _stream_ai_response(agent, command, config, console, render_markdown)
            except Exception as stream_error:
                logger.error(f"Stream error: {stream_error}")
                console.print(f"[red]Error: {stream_error}[/red]")
                all_messages = []

            if not all_messages:
                console.print("[yellow]No response from agent[/yellow]")

            msg_count = len(all_messages)
            session_store.update_activity(session_id, message_count=msg_count)
            _update_session_turn_count(session_store, session_id, agent, chat_model)

            console.print()

        except KeyboardInterrupt:
            _update_session_turn_count(session_store, session_id, agent, chat_model)
            console.print(GOODBYE_MESSAGE)
            break
        except EOFError:
            _update_session_turn_count(session_store, session_id, agent, chat_model)
            console.print(GOODBYE_MESSAGE)
            break
        except Exception as e:
            logger.exception("Error in chat loop")
            console.print(f"[red]{t('cli.rollback.error_showing').format(e)}[/red]")
            console.print(f"[dim]{t('cli.chat.check_logs')}[/dim]")


def _get_last_active_session(workspace: Path) -> str:
    """获取最近活跃的会话 ID.

    Args:
        workspace: 工作目录路径

    Returns:
        最近活跃的会话 ID，如果没有会话则生成新的会话 ID
    """
    db_path = workspace / "sessions_metadata.db"
    if not db_path.exists():
        from finchbot.sessions import SessionMetadataStore

        store = SessionMetadataStore(workspace)
        return store.get_next_session_id()

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.execute("SELECT session_id FROM sessions ORDER BY last_active DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            return row[0]

    from finchbot.sessions import SessionMetadataStore

    store = SessionMetadataStore(workspace)
    return store.get_next_session_id()
