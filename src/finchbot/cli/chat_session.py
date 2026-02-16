"""聊天会话模块.

提供 REPL 模式下的聊天功能，包括会话管理、历史记录、消息回退等。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import typer
from langchain_core.runnables import RunnableConfig
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from finchbot.config import load_config
from finchbot.i18n import t
from finchbot.sessions import SessionMetadataStore

console = Console()

EXIT_COMMANDS = {"exit", "quit", "/exit", "/quit", ":q", "q"}
GOODBYE_MESSAGE = "\n[dim]Goodbye! 👋[/dim]"


def _format_message(msg: Any, index: int, show_index: bool = True, max_content_len: int = 9999) -> None:
    """格式化并显示单条消息。

    Args:
        msg: 消息对象
        index: 消息索引
        show_index: 是否显示索引
        max_content_len: 内容最大显示长度（默认很大，基本不截断）
    """
    msg_type = getattr(msg, "type", None)
    content = getattr(msg, "content", "") or ""
    tool_calls = getattr(msg, "tool_calls", None) or []
    name = getattr(msg, "name", None)

    prefix = f"[{index}] " if show_index else ""

    panel_width = None

    if msg_type == "human" or (hasattr(msg, "role") and msg.role == "user"):
        role_label = t("cli.history.role_you")
        role_icon = "👤"
        role_color = "cyan"
        console.print(Panel(
            content,
            title=f"[{role_color}]{prefix}{role_icon} {role_label}[/{role_color}]",
            border_style=role_color,
            padding=(0, 1),
            width=panel_width,
        ))

    elif msg_type == "ai" or (hasattr(msg, "role") and msg.role == "assistant"):
        role_label = t("cli.history.role_bot")
        role_icon = "🤖"
        role_color = "green"
        console.print(Panel(
            content,
            title=f"[{role_color}]{prefix}{role_icon} {role_label}[/{role_color}]",
            border_style=role_color,
            padding=(0, 1),
            width=panel_width,
        ))

    elif tool_calls:
        role_label = t("cli.history.role_tool")
        role_icon = "🔧"
        role_color = "yellow"
        tool_names = [tc.get("name", "unknown") for tc in tool_calls]
        tool_info = f" {', '.join(tool_names)}" if tool_names else ""
        console.print(Panel(
            tool_info.strip() or "tool",
            title=f"[{role_color}]{prefix}{role_icon} {role_label}[/{role_color}]",
            border_style=role_color,
            padding=(0, 1),
            width=panel_width,
        ))

    elif name:
        role_label = t("cli.history.role_tool")
        role_icon = "🔧"
        role_color = "yellow"
        console.print(Panel(
            content,
            title=f"[{role_color}]{prefix}{role_icon} {name}[/{role_color}]",
            border_style=role_color,
            padding=(0, 1),
            width=panel_width,
        ))

    elif msg_type == "system" or (hasattr(msg, "role") and msg.role == "system"):
        role_label = t("cli.history.role_system")
        role_icon = "⚙️"
        role_color = "dim"
        console.print(Panel(
            content,
            title=f"[{role_color}]{prefix}{role_icon} {role_label}[/{role_color}]",
            border_style=role_color,
            padding=(0, 1),
            width=panel_width,
        ))

    else:
        role_label = "未知"
        role_icon = "❓"
        role_color = "red"
        console.print(Panel(
            content,
            title=f"[{role_color}]{prefix}{role_icon} {role_label}[/{role_color}]",
            border_style=role_color,
            padding=(0, 1),
            width=panel_width,
        ))


def _display_messages_by_turn(messages: list[Any], show_index: bool = True) -> None:
    """按轮次分组显示消息。

    Args:
        messages: 消息列表
        show_index: 是否显示索引
    """
    if not messages:
        return

    console.print(Rule(style="dim"))
    turn_num = 0
    i = 0

    while i < len(messages):
        msg = messages[i]
        msg_type = getattr(msg, "type", None)

        if msg_type == "human" or (hasattr(msg, "role") and msg.role == "user"):
            turn_num += 1
            console.print()
            console.print(f"[dim]─── 第 {turn_num} 轮对话 ───[/dim]")

            _format_message(msg, i, show_index=show_index)

            j = i + 1
            while j < len(messages):
                next_msg = messages[j]
                next_type = getattr(next_msg, "type", None)
                tool_calls = getattr(next_msg, "tool_calls", None) or []
                name = getattr(next_msg, "name", None)

                if (next_type == "human" or (hasattr(next_msg, "role") and next_msg.role == "user")):
                    break
                if next_type == "ai" or (hasattr(next_msg, "role") and next_msg.role == "assistant"):
                    _format_message(next_msg, j, show_index=show_index, max_content_len=80)
                    j += 1
                    break
                elif tool_calls or name:
                    _format_message(next_msg, j, show_index=show_index, max_content_len=50)
                    j += 1
                else:
                    break

            i = j
        else:
            _format_message(msg, i, show_index=show_index)
            i += 1

    console.print()


def calculate_turn_count(messages: list[Any]) -> int:
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
) -> None:
    """更新会话的轮次计数。

    Args:
        session_store: 会话元数据存储
        session_id: 会话ID
        agent: Agent 实例
    """
    try:
        config = {"configurable": {"thread_id": session_id}}
        current_state = agent.get_state(config)
        messages = current_state.values.get("messages", [])
        turn_count = calculate_turn_count(messages)
        session_store.update_activity(session_id, turn_count=turn_count)
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

    Returns:
        (tools, web_enabled) 元组
    """
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

    tools = [
        ReadFileTool(allowed_dir=ws_path),
        WriteFileTool(allowed_dir=ws_path),
        EditFileTool(allowed_dir=ws_path),
        ListDirTool(allowed_dir=ws_path),
        RememberTool(workspace=str(ws_path)),
        RecallTool(workspace=str(ws_path)),
        ForgetTool(workspace=str(ws_path)),
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
) -> None:
    """启动聊天会话（REPL 模式）.

    Args:
        session_id: 会话 ID
        model: 模型名称
        workspace: 工作目录
        first_message: 第一条消息（可选，如提供则先发送此消息再进入交互模式）
    """
    from prompt_toolkit import PromptSession
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.patch_stdout import patch_stdout

    from finchbot.agent import create_finch_agent
    from finchbot.memory import EnhancedMemoryStore
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

    ws_path = Path(workspace or config_obj.agents.defaults.workspace).expanduser()
    ws_path.mkdir(parents=True, exist_ok=True)

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
        memory=EnhancedMemoryStore(ws_path),
        use_persistent=True,
        session_title=session_title,
    )

    config = {"configurable": {"thread_id": session_id}}
    current_state = agent.get_state(config)
    messages = current_state.values.get("messages", []) if current_state else []
    if messages:
        console.print(f"\n[dim]{t('cli.history.title')}[/dim]")
        _display_messages_by_turn(messages, show_index=False)
        console.print(f"[dim]{t('cli.history.total_messages').format(len(messages))}[/dim]")
        console.print()

    if first_message:
        with console.status("[dim]Thinking...[/dim]", spinner="dots"):
            runnable_config: RunnableConfig = {"configurable": {"thread_id": session_id}}
            result = agent.invoke(
                {"messages": [{"role": "user", "content": first_message}]},
                config=runnable_config,
            )
            all_messages = result.get("messages", [])

            msg_count = len(all_messages)
            session_store.update_activity(session_id, message_count=msg_count)
            _update_session_turn_count(session_store, session_id, agent)

        for i, msg in enumerate(all_messages):
            _format_message(msg, i, show_index=False)
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
                _update_session_turn_count(session_store, session_id, agent)
                console.print(GOODBYE_MESSAGE)
                break

            if command.lower() in {"history", "/history"}:
                try:
                    config = {"configurable": {"thread_id": session_id}}
                    current_state = agent.get_state(config)
                    messages = current_state.values.get("messages", [])

                    console.print(f"\n[dim]{t('cli.history.title')}[/dim]")
                    _display_messages_by_turn(messages, show_index=True)
                    console.print(f"[dim]{t('cli.history.total_messages').format(len(messages))}[/dim]")
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
                        new_config: RunnableConfig = {"configurable": {"thread_id": new_sess}}
                        agent.update_state(new_config, {"messages": rolled_back})
                        session_id = new_sess
                        msg_count = len(rolled_back)
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

            with console.status("[dim]Thinking...[/dim]", spinner="dots"):
                config: RunnableConfig = {"configurable": {"thread_id": session_id}}
                result = agent.invoke(
                    {"messages": [{"role": "user", "content": command}]},
                    config=config,
                )
                all_messages = result.get("messages", [])

                msg_count = len(all_messages)
                session_store.update_activity(session_id, message_count=msg_count)

            for i, msg in enumerate(all_messages):
                _format_message(msg, i, show_index=False)
            console.print()

        except KeyboardInterrupt:
            _update_session_turn_count(session_store, session_id, agent)
            console.print(GOODBYE_MESSAGE)
            break
        except EOFError:
            _update_session_turn_count(session_store, session_id, agent)
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
        最近活跃的会话 ID，如果没有会话则返回 "default"
    """
    store = SessionMetadataStore(workspace)
    sessions = store.get_all_sessions()

    if sessions:
        return sessions[0].session_id
    return "default"
