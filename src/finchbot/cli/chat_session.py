"""聊天会话模块.

提供 REPL 模式下的聊天功能，包括会话管理、历史记录、消息回退等。
"""

from __future__ import annotations

import asyncio
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

import typer
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from loguru import logger
from rich import box
from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from finchbot.config import ProviderConfig, load_config
from finchbot.constants import EXIT_COMMANDS
from finchbot.i18n import t
from finchbot.sessions import SessionMetadataStore
from finchbot.workspace import SESSIONS_DIR

console = Console()

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

    elif msg_type == "tool" or (name and not tool_calls) or msg_role == "tool":
        _render_tool_message(
            name or "unknown",
            str(content),
            console,
            show_index=show_index,
            index=index,
        )

    else:
        role_label = t("cli.history.role_unknown")
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


def _render_tool_message(
    tool_name: str,
    result: str,
    console: Console,
    tool_args: dict | None = None,
    duration: float | None = None,
    show_index: bool = False,
    index: int = 0,
) -> None:
    """统一的工具消息渲染函数.

    Args:
        tool_name: 工具名称
        result: 执行结果
        console: Rich Console
        tool_args: 工具参数（可选）
        duration: 执行时间（可选）
        show_index: 是否显示索引
        index: 消息索引
    """
    content_parts: list[Any] = []

    if tool_args:
        args_table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
        args_table.add_column(t("cli.tool_display.param_column"), style="cyan", no_wrap=True)
        args_table.add_column(t("cli.tool_display.value_column"), style="white")

        for key, value in tool_args.items():
            value_str = str(value)
            if len(value_str) > 60:
                value_str = value_str[:57] + "..."
            args_table.add_row(key, value_str)

        content_parts.extend(
            [
                Text("📥 " + t("cli.tool_display.call_label") + ":", style="bold"),
                args_table,
                Text(""),
            ]
        )

    display_result = result
    if len(display_result) > 200:
        display_result = display_result[:197] + "..."

    content_parts.extend(
        [
            Text("📤 " + t("cli.tool_display.result_label") + ":", style="bold"),
            Text(display_result),
        ]
    )

    if duration is not None:
        content_parts.extend(
            [
                Text(""),
                Text(t("cli.tool_display.execution_time").format(duration), style="dim"),
            ]
        )

    # 修复：确保 content_parts 不为空，如果为空则添加占位符
    if not content_parts:
        content_parts.append(Text(str(result)))

    group_content = Group(*content_parts)

    prefix = f"[{index}] " if show_index else ""
    console.print(
        Panel(
            group_content,
            title=f"{prefix}🔧 {tool_name}",
            border_style="yellow",
            padding=(0, 1),
        )
    )


def _display_tool_call_with_result(
    tool_name: str,
    tool_args: dict,
    result: str,
    duration: float,
    console: Console,
) -> None:
    """显示工具调用和结果在同一个 Panel（流式输出专用）.

    Args:
        tool_name: 工具名称
        tool_args: 工具参数
        result: 执行结果
        duration: 执行时间（秒）
        console: Rich Console
    """
    _render_tool_message(tool_name, result, console, tool_args=tool_args, duration=duration)


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
            console.print(f"[dim]─── {t('cli.history.turn_label').format(turn_num)} ───[/dim]")

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
                    ai_content = getattr(next_msg, "content", "") or ""
                    if ai_content:
                        _format_message(
                            next_msg,
                            j,
                            show_index=show_index,
                            max_content_len=80,
                            render_markdown=render_markdown,
                        )
                    if tool_calls:
                        for tc in tool_calls:
                            tool_name = tc.get("name", "unknown")
                            tool_args = tc.get("args", {})
                            tool_id = tc.get("id")
                            result = ""
                            for k in range(j + 1, len(messages)):
                                result_msg = messages[k]
                                result_tool_id = getattr(result_msg, "tool_call_id", None)
                                if result_tool_id and result_tool_id == tool_id:
                                    result = str(getattr(result_msg, "content", ""))
                                    break
                            _render_tool_message(
                                tool_name,
                                result or t("cli.history.no_result"),
                                console,
                                tool_args=tool_args if tool_args else None,
                                show_index=show_index,
                                index=j,
                            )
                        j += 1
                    else:
                        j += 1
                        break
                elif name:
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


async def _update_session_turn_count_async(
    session_store: SessionMetadataStore,
    session_id: str,
    agent: Any,
    chat_model: Any = None,
) -> None:
    """更新会话的轮次计数和标题（异步版）.

    Args:
        session_store: 会话元数据存储
        session_id: 会话ID
        agent: Agent 实例
        chat_model: 可选的聊天模型，用于生成标题
    """
    try:
        config = {"configurable": {"thread_id": session_id}}

        # 异步获取状态
        try:
            current_state = await agent.aget_state(config)
        except AttributeError:
            current_state = agent.get_state(config)

        messages = current_state.values.get("messages", []) if current_state else []
        turn_count = calculate_turn_count(messages)

        # session_store 是同步的 SQLite 操作，可以在这里直接调用
        # 如果将来 session_store 也变异步了，这里也需要 await
        session_store.update_activity(session_id, turn_count=turn_count)

        # 自动生成标题逻辑
        if chat_model and turn_count >= 2:
            from finchbot.sessions.title_generator import generate_session_title_with_ai

            session = session_store.get_session(session_id)
            if session:
                current_title = session.title
                needs_title = not current_title.strip() or current_title == session_id

                if needs_title:
                    generated_title = generate_session_title_with_ai(chat_model, messages)
                    if generated_title:
                        session_store.update_activity(session_id, title=generated_title)
                        logger.info(f"自动生成会话标题: {generated_title}")

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
        provider_name_map = {
            "google": "gemini",
            "azure": "openai",
        }
        config_provider = provider_name_map.get(provider, provider)
        provider_config: ProviderConfig | None = getattr(
            config_obj.providers, config_provider, None
        )
        if provider_config and provider_config.api_key:
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


async def _stream_ai_response(
    agent: CompiledStateGraph,
    message: str,
    runnable_config: RunnableConfig,
    console: Console,
    render_markdown: bool,
    show_progress: bool = True,
) -> list[BaseMessage]:
    """流式输出 AI 响应，并显示详细的工具调用信息.

    Args:
        agent: 编译好的 Agent 图.
        message: 用户消息.
        runnable_config: 运行配置.
        console: Rich 控制台.
        render_markdown: 是否渲染 Markdown.
        show_progress: 是否显示进度提示.

    Returns:
        完整的消息列表.
    """

    input_data = {"messages": [HumanMessage(content=message)]}
    full_content = ""
    all_messages: list[BaseMessage] = []
    pending_tool_calls: list[dict] = []
    last_render_time: float = 0.0
    render_interval = 0.1
    tool_call_count = 0

    def _render_ai_content(content: str) -> None:
        if content.strip():
            body = Markdown(content) if render_markdown else Text(content)
            console.print(
                Panel(
                    body,
                    title="🐦 FinchBot",
                    border_style="green",
                    padding=(0, 1),
                )
            )

    def _create_content_panel(content: str) -> Panel:
        body = Markdown(content) if render_markdown else Text(content)
        return Panel(
            body,
            title="🐦 FinchBot",
            border_style="green",
            padding=(0, 1),
        )

    def _show_progress_hint(text: str) -> None:
        """显示进度提示."""
        if show_progress:
            console.print(f"  [dim]↳ {text}[/dim]")

    with Live(
        Panel(Text(""), title="🐦 FinchBot", border_style="green"),
        console=console,
        refresh_per_second=10,
        transient=True,
    ) as live:
        try:
            async for event in agent.astream(
                input_data, config=runnable_config, stream_mode=["messages", "updates"]
            ):
                if isinstance(event, tuple) and len(event) == 2:
                    mode, data = event
                    if mode == "messages":
                        if isinstance(data, tuple) and len(data) == 2:
                            msg_chunk, metadata = data
                            node_name = (
                                metadata.get("langgraph_node", "")
                                if isinstance(metadata, dict)
                                else ""
                            )
                            if node_name == "model" or node_name == "agent":
                                token = getattr(msg_chunk, "content", "") or ""
                                if token:
                                    full_content += token
                                    current_time = time.time()
                                    if current_time - last_render_time > render_interval:
                                        live.update(_create_content_panel(full_content))
                                        last_render_time = current_time
                    elif mode == "updates" and isinstance(data, dict):
                        for _node_name, node_data in data.items():
                            if not isinstance(node_data, dict):
                                continue
                            messages = node_data.get("messages", [])
                            if not messages:
                                continue
                            for msg in messages:
                                if hasattr(msg, "tool_calls") and msg.tool_calls:
                                    if full_content.strip():
                                        _render_ai_content(full_content)
                                        full_content = ""
                                        live.update(
                                            Panel(
                                                Text(""),
                                                title="🐦 FinchBot",
                                                border_style="green",
                                            )
                                        )
                                    for tc in msg.tool_calls:
                                        tool_name = tc.get("name") or "unknown"
                                        tool_args = tc.get("args", {})
                                        pending_tool_calls.append(
                                            {
                                                "name": tool_name,
                                                "args": tool_args,
                                                "start_time": time.time(),
                                            }
                                        )
                                        # 显示工具调用进度提示
                                        if show_progress:
                                            tool_call_count += 1
                                            args_hint = ""
                                            if tool_args:
                                                first_arg = next(iter(tool_args.values()), "")
                                                if (
                                                    isinstance(first_arg, str)
                                                    and len(first_arg) < 30
                                                ):
                                                    args_hint = f'("{first_arg}")'
                                            _show_progress_hint(f"{tool_name}{args_hint}")
                                elif hasattr(msg, "name") and msg.name:
                                    tool_name = msg.name
                                    for i, call_info in enumerate(pending_tool_calls):
                                        if call_info["name"] == tool_name:
                                            duration = time.time() - call_info["start_time"]
                                            _display_tool_call_with_result(
                                                call_info["name"],
                                                call_info["args"],
                                                str(msg.content),
                                                duration,
                                                console,
                                            )
                                            pending_tool_calls.pop(i)
                                            live.update(
                                                Panel(
                                                    Text(""),
                                                    title="🐦 FinchBot",
                                                    border_style="green",
                                                )
                                            )
                                            break
                                all_messages.append(msg)
        except (KeyboardInterrupt, asyncio.CancelledError):
            logger.info("Stream interrupted by user")
            raise

    if not full_content:
        console.print("[yellow]No content generated[/yellow]")
    else:
        console.print(_create_content_panel(full_content))

    # 显示工具调用统计
    if show_progress and tool_call_count > 0:
        console.print(f"  [dim]🔧 {tool_call_count} 个工具调用[/dim]")

    return all_messages


def _run_chat_session(
    session_id: str,
    model: str | None,
    workspace: str | None,
    first_message: str | None = None,
    render_markdown: bool = True,
) -> None:
    """启动聊天会话（REPL 模式）."""
    import signal

    def signal_handler(signum, frame):
        """处理 Ctrl+C 信号."""
        raise KeyboardInterrupt

    # 设置信号处理器
    original_handler = signal.signal(signal.SIGINT, signal_handler)

    loop = None
    try:
        # 创建新的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        loop.run_until_complete(
            _run_chat_session_async(session_id, model, workspace, first_message, render_markdown)
        )
    except KeyboardInterrupt:
        console.print(GOODBYE_MESSAGE)
    except asyncio.CancelledError:
        console.print(GOODBYE_MESSAGE)
    finally:
        # 清理事件循环
        if loop is not None:
            try:
                # 取消所有待处理任务
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()

                # 等待所有任务完成或取消
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception:
                pass
            finally:
                loop.close()

        # 恢复原始信号处理器
        signal.signal(signal.SIGINT, original_handler)


async def _run_chat_session_async(
    session_id: str,
    model: str | None,
    workspace: str | None,
    first_message: str | None = None,
    render_markdown: bool = True,
) -> None:
    """启动聊天会话（REPL 模式 - 异步实现）.

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

    from finchbot.providers import create_chat_model

    loop = asyncio.get_running_loop()

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

        # get_default_workspace can be slow (file I/O), move to thread pool
        ws_path = await loop.run_in_executor(None, get_default_workspace)

    from functools import partial

    from finchbot.agent.factory import AgentFactory

    # create_chat_model can be very slow (tiktoken loading etc.), move to thread pool
    chat_model = await loop.run_in_executor(
        None,
        partial(
            create_chat_model,
            model=use_model,
            api_key=api_key,
            api_base=api_base,
            temperature=config_obj.agents.defaults.temperature,
        ),
    )

    history_file = Path.home() / ".finchbot" / "history" / "chat_history"
    history_file.parent.mkdir(parents=True, exist_ok=True)

    console.print(f"\n[bold cyan]{t('cli.chat.title')}[/bold cyan]")

    # Session store init involves SQLite connection, move to thread pool
    session_store = await loop.run_in_executor(None, SessionMetadataStore, ws_path)

    if not await loop.run_in_executor(None, session_store.session_exists, session_id):
        await loop.run_in_executor(
            None, partial(session_store.create_session, session_id, title=session_id)
        )

    current_session = await loop.run_in_executor(None, session_store.get_session, session_id)
    session_title = current_session.title if current_session else None
    if session_title == session_id:
        session_title = None

    session_display = session_id
    if session_title:
        session_display = f"{session_id} ({session_title})"
    console.print(f"[dim]{t('cli.chat.session').format(session_display)}[/dim]")

    console.print(f"[dim]{t('cli.chat.model').format(use_model)}[/dim]")
    console.print(f"[dim]{t('cli.chat.workspace').format(ws_path)}[/dim]")

    (
        agent,
        checkpointer,
        tools,
        subagent_manager,
        service_manager,
    ) = await AgentFactory.create_for_cli(
        session_id=session_id,
        workspace=ws_path,
        model=chat_model,
        config=config_obj,
    )

    config = {"configurable": {"thread_id": session_id}}

    async def deliver_message(channel: str, to: str, message: str) -> None:
        """消息投递回调.

        将定时任务或子代理的结果注入到当前会话。

        Args:
            channel: 渠道标识
            to: 目标 ID
            message: 消息内容
        """
        try:
            current_state = await agent.aget_state(config)
            messages = list(current_state.values.get("messages", []))
            messages.append(SystemMessage(content=f"[定时任务通知]\n{message}"))
            await agent.aupdate_state(config, {"messages": messages})
            console.print(
                Panel(
                    message,
                    title="🔔 定时任务通知",
                    border_style="yellow",
                    padding=(0, 1),
                )
            )
        except Exception as e:
            logger.error(f"Failed to deliver message: {e}")

    async def notify_result(session_key: str, label: str, result: str) -> None:
        """子代理结果通知回调.

        Args:
            session_key: 会话标识
            label: 任务标签
            result: 执行结果
        """
        try:
            current_state = await agent.aget_state(config)
            messages = list(current_state.values.get("messages", []))
            messages.append(SystemMessage(content=f"[后台任务完成: {label}]\n{result}"))
            await agent.aupdate_state(config, {"messages": messages})
            console.print(
                Panel(
                    result[:500] + ("..." if len(result) > 500 else ""),
                    title=f"🔔 后台任务完成: {label}",
                    border_style="green",
                    padding=(0, 1),
                )
            )
        except Exception as e:
            logger.error(f"Failed to notify result: {e}")

    if service_manager:
        service_manager._on_cron_deliver = deliver_message

    if subagent_manager:
        subagent_manager.on_notify = notify_result

    web_enabled = any(t.name == "web_search" for t in tools)
    web_status = (
        t("cli.chat.web_search_enabled") if web_enabled else t("cli.chat.web_search_disabled")
    )
    console.print(f"[dim]{web_status}[/dim]")
    console.print(f"[dim]{t('cli.chat.type_to_quit')}[/dim]\n")

    # Try async get_state if available, else sync
    try:
        current_state = await agent.aget_state(config)
    except AttributeError:
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
            all_messages = await _stream_ai_response(
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
        await _update_session_turn_count_async(session_store, session_id, agent, chat_model)

        console.print()

    prompt_session = PromptSession(
        history=FileHistory(str(history_file)),
        enable_open_in_editor=False,
        multiline=False,
    )

    while True:
        try:
            with patch_stdout():
                user_input = await prompt_session.prompt_async(
                    HTML("<b fg='ansiblue'>You:</b> "),
                )

            command = user_input.strip()
            if not command:
                continue

            if command.lower() in EXIT_COMMANDS:
                await _update_session_turn_count_async(session_store, session_id, agent, chat_model)
                console.print(GOODBYE_MESSAGE)
                break

            if command.lower() in {"history", "/history"}:
                try:
                    config = {"configurable": {"thread_id": session_id}}
                    try:
                        current_state = await agent.aget_state(config)
                    except AttributeError:
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
                        await agent.aupdate_state(new_config, {"messages": rolled_back})

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
                        await agent.aupdate_state(config, {"messages": rolled_back})
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
                    await agent.aupdate_state(config, {"messages": rolled_back})

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
                all_messages = await _stream_ai_response(
                    agent, command, config, console, render_markdown
                )
            except (KeyboardInterrupt, asyncio.CancelledError):
                raise  # 让外层处理
            except Exception as stream_error:
                logger.error(f"Stream error: {stream_error}")
                console.print(f"[red]Error: {stream_error}[/red]")
                all_messages = []

            if not all_messages:
                console.print("[yellow]No response from agent[/yellow]")

            msg_count = len(all_messages)
            session_store.update_activity(session_id, message_count=msg_count)
            await _update_session_turn_count_async(session_store, session_id, agent, chat_model)

            console.print()

        except KeyboardInterrupt:
            logger.info("User interrupted with Ctrl+C")
            console.print(GOODBYE_MESSAGE)
            break
        except EOFError:
            logger.info("User interrupted with EOF")
            console.print(GOODBYE_MESSAGE)
            break
        except Exception as e:
            logger.exception("Error in chat loop")
            console.print(f"[red]{t('cli.rollback.error_showing').format(e)}[/red]")
            console.print(f"[dim]{t('cli.chat.check_logs')}[/dim]")

    # 清理资源 - 确保在所有退出路径都执行
    logger.info("Cleaning up resources...")

    # 停止所有后台服务
    try:
        await service_manager.stop_all()
        logger.debug("ServiceManager stopped all services")
    except Exception as e:
        logger.debug(f"Error stopping services: {e}")

    # 关闭 checkpointer 连接
    if hasattr(checkpointer, "conn") and checkpointer.conn:
        try:
            await asyncio.sleep(0.1)
            await checkpointer.conn.close()
            logger.debug("Checkpointer connection closed")
        except Exception as e:
            logger.debug(f"Error closing checkpointer: {e}")


def _get_last_active_session(workspace: Path) -> str:
    """获取最近活跃的会话 ID.

    Args:
        workspace: 工作目录路径

    Returns:
        最近活跃的会话 ID，如果没有会话则生成新的会话 ID
    """
    db_path = workspace / SESSIONS_DIR / "metadata.db"
    if not db_path.exists():
        from finchbot.sessions import SessionMetadataStore

        store = SessionMetadataStore(workspace)
        return store.get_next_session_id()

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    try:
        cursor = conn.execute("SELECT session_id FROM sessions ORDER BY last_active DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            return row[0]
    finally:
        conn.close()

    from finchbot.sessions import SessionMetadataStore

    store = SessionMetadataStore(workspace)
    return store.get_next_session_id()
