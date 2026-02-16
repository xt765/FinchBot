"""FinchBot CLI 入口.

提供命令行交互界面，支持多语言和交互式配置。
使用 LangGraph 官方推荐的 create_agent 构建。
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Any

import questionary
import readchar
import typer
from langchain_core.runnables import RunnableConfig
from loguru import logger
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from finchbot.config import get_config_path, load_config, save_config
from finchbot.config.schema import Config, ProviderConfig
from finchbot.i18n import init_language_from_config, set_language, t
from finchbot.sessions import SessionMetadataStore, SessionSelector

# 配置 loguru
logger.add(
    lambda msg: print(msg, end=""),
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG",
)

app = typer.Typer(
    name="finchbot",
    help="FinchBot (雀翎) - Lightweight AI Agent Framework",
)
console = Console()


def _generate_session_title_with_ai(
    chat_model,
    messages: list,
) -> str | None:
    """使用 AI 分析对话内容生成会话标题.

    Args:
        chat_model: 聊天模型实例
        messages: 对话消息列表

    Returns:
        生成的标题，如果失败则返回 None
    """
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        # 构建对话摘要
        conversation = []
        for msg in messages[-4:]:  # 只取最近 4 条消息
            if hasattr(msg, "type") and hasattr(msg, "content"):
                role = "用户" if msg.type == "human" else "AI"
                content = msg.content[:100]  # 限制长度
                conversation.append(f"{role}: {content}")

        conversation_text = "\n".join(conversation)

        # 构建提示词
        system_prompt = """你是一个会话标题生成助手。请根据以下对话内容，生成一个简洁的标题（不超过15个字符）。

要求：
1. 标题要准确概括对话主题
2. 使用中文
3. 不要包含标点符号
4. 长度控制在 5-15 个字符

请直接输出标题，不要添加任何解释。"""

        user_prompt = f"请为以下对话生成标题：\n\n{conversation_text}"

        # 调用 AI
        response = chat_model.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
        )

        title = response.content.strip()

        # 清理标题
        title = re.sub(r'["\'""' r"，。？！,.?!\s]+", "", title)

        # 限制长度
        if len(title) > 15:
            title = title[:15]

        return title if title else None

    except Exception as e:
        logger.warning(f"Failed to generate session title with AI: {e}")
        return None


def _generate_session_title_simple(first_message: str, max_length: int = 20) -> str:
    """根据第一条消息生成会话标题（简单版本，作为备选）.

    Args:
        first_message: 用户的第一条消息
        max_length: 标题最大长度

    Returns:
        生成的标题
    """
    # 去除常见前缀
    prefixes = ["请", "帮我", "我想", "我要", "能不能", "可以", "请问"]
    content = first_message.strip()
    for prefix in prefixes:
        if content.startswith(prefix):
            content = content[len(prefix) :].strip()
            break

    # 提取核心内容（去除标点）

    content = re.sub(r"[，。？！,.?!\"'\s]+", " ", content).strip()

    # 限制长度
    if len(content) <= max_length:
        return content if content else "新会话"

    # 智能截断（尽量在空格处截断）
    truncated = content[:max_length]
    last_space = truncated.rfind(" ")
    if last_space > max_length // 2:
        truncated = truncated[:last_space]

    return truncated.strip() + "..."


PRESET_PROVIDERS = {
    "openai": {
        "name": "OpenAI",
        "default_base": "https://api.openai.com/v1",
        "models": ["gpt-5", "gpt-5.2", "o3-mini"],
    },
    "anthropic": {
        "name": "Anthropic",
        "default_base": "https://api.anthropic.com/v1",
        "models": ["claude-sonnet-4.5", "claude-opus-4.6"],
    },
    "gemini": {
        "name": "Google Gemini",
        "default_base": "https://generativelanguage.googleapis.com/v1beta",
        "models": ["gemini-2.5-flash", "gemini-2.5-flash-lite"],
    },
    "deepseek": {
        "name": "DeepSeek",
        "default_base": "https://api.deepseek.com/v1",
        "models": ["deepseek-chat", "deepseek-reasoner"],
    },
    "dashscope": {
        "name": "DashScope / 阿里云通义千问",
        "default_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": ["qwen-turbo", "qwq-32b", "qwen-plus"],
    },
    "groq": {
        "name": "Groq",
        "default_base": "https://api.groq.com/openai/v1",
        "models": ["llama-4-scout", "llama-4-maverick", "llama-3.3-70b"],
    },
    "moonshot": {
        "name": "Moonshot / Kimi",
        "default_base": "https://api.moonshot.cn/v1",
        "models": ["kimi-k2.5", "kimi-k1.5"],
    },
    "openrouter": {
        "name": "OpenRouter",
        "default_base": "https://openrouter.ai/api/v1",
        "models": [],
    },
}

# Provider 关键词映射（用于从模型名称检测 provider）
PROVIDER_KEYWORDS: dict[str, list[str]] = {
    "openai": ["gpt", "o1", "o3", "o4"],
    "anthropic": ["claude"],
    "openrouter": ["openrouter"],
    "deepseek": ["deepseek"],
    "groq": ["groq", "llama", "mixtral"],
    "gemini": ["gemini"],
    "moonshot": ["moonshot", "kimi"],
    "dashscope": ["qwen", "tongyi", "dashscope", "qwq"],
}

# Provider 优先级列表（用于自动检测）
PROVIDER_PRIORITY: list[tuple[str, str, list[str]]] = [
    ("openai", "gpt-5", ["OPENAI_API_KEY"]),
    ("anthropic", "claude-sonnet-4.5", ["ANTHROPIC_API_KEY"]),
    ("deepseek", "deepseek-chat", ["DEEPSEEK_API_KEY", "DS_API_KEY"]),
    ("groq", "llama-4-scout", ["GROQ_API_KEY"]),
    ("moonshot", "kimi-k2.5", ["MOONSHOT_API_KEY"]),
    ("dashscope", "qwen-turbo", ["DASHSCOPE_API_KEY", "ALIBABA_API_KEY"]),
    ("gemini", "gemini-2.5-flash", ["GOOGLE_API_KEY", "GEMINI_API_KEY"]),
]


def _get_tavily_key(config_obj: Config) -> str | None:
    """获取 Tavily API 密钥."""
    return os.getenv("TAVILY_API_KEY") or config_obj.tools.web.search.api_key


def _keyboard_select(
    items: list[dict],
    title: str,
    help_text: str,
    allow_quit: bool = True,
    initial_idx: int = 0,
) -> Any | None:
    """通用键盘导航选择器.

    Args:
        items: 选项列表，每项包含 'name' 和 'value'
        title: 界面标题（已包含样式）
        help_text: 底部帮助文本（已包含样式）
        allow_quit: 是否允许按 Q 退出
        initial_idx: 初始选中项索引

    Returns:
        选中项的 value，或 None（如果用户退出）
    """
    selected_idx = initial_idx

    try:
        while True:
            console.clear()
            console.print(title)

            # 渲染列表
            for idx, item in enumerate(items):
                is_selected = idx == selected_idx
                cursor = "▶" if is_selected else "  "
                if is_selected:
                    console.print(f"{cursor} [cyan bold]{item['name']}[/cyan bold]")
                else:
                    console.print(f"{cursor} {item['name']}")

            console.print(help_text)

            key = readchar.readkey()

            if key == readchar.key.UP:
                selected_idx = max(0, selected_idx - 1)
            elif key == readchar.key.DOWN:
                selected_idx = min(len(items) - 1, selected_idx + 1)
            elif key == readchar.key.ENTER:
                return items[selected_idx]["value"]
            elif allow_quit and key.lower() == "q":
                return None
            elif key == readchar.key.CTRL_C:
                raise KeyboardInterrupt

    except KeyboardInterrupt:
        raise


@app.callback()
def main(
    lang: str = typer.Option(None, "--lang", "-l", help="Set language / 设置语言"),
) -> None:
    """全局回调."""
    if lang:
        set_language(lang)
    else:
        # 从配置加载语言
        config_obj = load_config()
        init_language_from_config(config_obj.language)


@app.command()
def version() -> None:
    """显示版本信息."""
    from finchbot import __version__

    console.print(f"[bold cyan]FinchBot[/bold cyan] version [green]{__version__}[/green]")


def _setup_chat_tools(config_obj: Config, ws_path: Path) -> tuple[list, bool]:
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
    from finchbot.agent import create_finch_agent
    from finchbot.memory import EnhancedMemoryStore
    from finchbot.providers import create_chat_model

    config_obj = load_config()
    use_model = model or config_obj.default_model
    api_key, api_base, detected_model = _get_llm_config(use_model, config_obj)

    # 如果自动检测到模型，使用检测到的模型
    if detected_model:
        use_model = detected_model
        console.print(f"[dim]Auto-detected model: {use_model}[/dim]")

    if not api_key:
        console.print(f"[red]{t('cli.error_no_api_key')}[/red]")
        console.print(t("cli.error_config_hint"))
        raise typer.Exit(1)

    ws_path = Path(workspace or config_obj.agents.defaults.workspace).expanduser()
    ws_path.mkdir(parents=True, exist_ok=True)

    # 设置工具
    tools, web_enabled = _setup_chat_tools(config_obj, ws_path)

    chat_model = create_chat_model(
        model=use_model,
        api_key=api_key,
        api_base=api_base,
        temperature=config_obj.agents.defaults.temperature,
    )

    history_file = Path.home() / ".finchbot" / "history" / "chat_history"
    history_file.parent.mkdir(parents=True, exist_ok=True)

    console.print("\n[bold cyan]🐦 FinchBot Chat[/bold cyan]")
    console.print(f"[dim]Session: {session_id}[/dim]")
    console.print(f"[dim]Model: {use_model}[/dim]")
    console.print(f"[dim]Workspace: {ws_path}[/dim]")
    console.print(f"[dim]Web Search: {'Enabled' if web_enabled else 'Disabled'}[/dim]")
    console.print("[dim]Type 'exit' or press Ctrl+C to quit[/dim]\n")

    # 创建 Agent
    agent, checkpointer = create_finch_agent(
        model=chat_model,
        workspace=ws_path,
        tools=tools,
        memory=EnhancedMemoryStore(ws_path),
        use_persistent=True,
    )

    # 初始化会话元数据
    session_store = SessionMetadataStore(ws_path)
    if not session_store.session_exists(session_id):
        session_store.create_session(session_id, title=session_id)

    # 如果有第一条消息，先处理
    if first_message:
        with console.status("[dim]Thinking...[/dim]", spinner="dots"):
            runnable_config: RunnableConfig = {"configurable": {"thread_id": session_id}}
            result = agent.invoke(
                {"messages": [{"role": "user", "content": first_message}]},
                config=runnable_config,
            )
            response = result["messages"][-1].content

            # 更新会话元数据
            msg_count = len(result.get("messages", []))

            # 获取当前会话信息
            current_session = session_store.get_session(session_id)
            needs_title = (
                current_session is None
                or not current_session.title.strip()
                or current_session.title == session_id
            )

            # 触发条件：消息数 >= 2 且标题为空
            if msg_count >= 2 and needs_title:
                # 使用 AI 生成标题
                title = _generate_session_title_with_ai(
                    chat_model, result.get("messages", [])
                )
                if title:
                    session_store.update_activity(session_id, title=title, message_count=msg_count)
                    console.print(f"[dim]会话标题: {title}[/dim]")
                else:
                    # AI 生成失败，使用简单版本
                    title = _generate_session_title_simple(first_message)
                    session_store.update_activity(session_id, title=title, message_count=msg_count)
            else:
                session_store.update_activity(session_id, message_count=msg_count)

        console.print("\n[cyan]🐦 FinchBot:[/cyan]")
        console.print(Panel(response))
        console.print()

    # 启动 REPL 循环
    from prompt_toolkit import PromptSession
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.patch_stdout import patch_stdout

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
                console.print("\n[dim]Goodbye! 👋[/dim]")
                break

            # /history 命令 - 显示带索引的历史消息
            if command.lower() in {"history", "/history"}:
                try:
                    config = {"configurable": {"thread_id": session_id}}
                    current_state = agent.get_state(config)
                    messages = current_state.values.get("messages", [])

                    console.print("\n[dim]Conversation History:[/dim]")
                    for i, msg in enumerate(messages):
                        role = "You" if msg.type == "human" else "FinchBot"
                        content = msg.content
                        # 截断长消息
                        if len(content) > 60:
                            content = content[:60] + "..."
                        console.print(f"[{i}] {role}: {content}")
                    console.print(f"\n[dim]Total: {len(messages)} messages[/dim]")
                    console.print("[dim]Use '/rollback <index> [new_session]' to rollback[/dim]\n")
                except Exception as e:
                    console.print(f"[red]Error showing history: {e}[/red]")
                continue

            # /rollback 命令 - 回退到指定消息
            if command.startswith("/rollback "):
                parts = command.split(maxsplit=2)
                if len(parts) < 2:
                    console.print("[red]Usage: /rollback <message_index> [new_session_name][/red]")
                    continue

                try:
                    msg_index = int(parts[1])
                    new_sess = parts[2].strip() if len(parts) > 2 else None

                    config = {"configurable": {"thread_id": session_id}}
                    current_state = agent.get_state(config)
                    messages = current_state.values.get("messages", [])

                    if msg_index < 0 or msg_index > len(messages):
                        console.print(f"[red]Invalid index. Range: 0-{len(messages)}[/red]")
                        continue

                    # 截取消息
                    rolled_back = messages[:msg_index]

                    if new_sess:
                        # 创建新会话
                        new_config: RunnableConfig = {"configurable": {"thread_id": new_sess}}
                        agent.update_state(new_config, {"messages": rolled_back})
                        session_id = new_sess  # 切换到新会话
                        console.print(
                            f"[green]✓ Created '{new_sess}' with {len(rolled_back)} messages[/green]"
                        )
                    else:
                        # 原地回退
                        agent.update_state(config, {"messages": rolled_back})
                        console.print(
                            f"[green]✓ Rolled back to {len(rolled_back)} messages[/green]"
                        )

                    console.print(f"[dim]Removed {len(messages) - msg_index} messages[/dim]\n")

                except ValueError:
                    console.print("[red]Message index must be a number[/red]")
                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]")

                continue

            # /back 命令 - 快速删除最后 N 条消息
            if command.startswith("/back "):
                parts = command.split(maxsplit=1)
                if len(parts) < 2:
                    console.print("[red]Usage: /back <number_of_messages>[/red]")
                    continue

                try:
                    n = int(parts[1])

                    config = {"configurable": {"thread_id": session_id}}
                    current_state = agent.get_state(config)
                    messages = current_state.values.get("messages", [])

                    if n <= 0 or n > len(messages):
                        console.print(f"[red]Invalid number. Range: 1-{len(messages)}[/red]")
                        continue

                    # 回退 N 条消息
                    new_count = len(messages) - n
                    rolled_back = messages[:new_count]
                    agent.update_state(config, {"messages": rolled_back})

                    console.print(f"[green]✓ Removed last {n} messages[/green]")
                    console.print(f"[dim]Current: {new_count} messages[/dim]\n")

                except ValueError:
                    console.print("[red]Number must be an integer[/red]")
                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]")

                continue

            with console.status("[dim]Thinking...[/dim]", spinner="dots"):
                config: RunnableConfig = {"configurable": {"thread_id": session_id}}
                result = agent.invoke(
                    {"messages": [{"role": "user", "content": command}]},
                    config=config,
                )
                response = result["messages"][-1].content

                # 更新会话元数据
                msg_count = len(result.get("messages", []))

                # 获取当前会话信息
                current_session = session_store.get_session(session_id)
                needs_title = (
                    current_session is None
                    or not current_session.title.strip()
                    or current_session.title == session_id
                )

                # 触发条件：消息数 >= 2 且标题为空
                if msg_count >= 2 and needs_title:
                    # 使用 AI 生成标题
                    title = _generate_session_title_with_ai(
                        chat_model, result.get("messages", [])
                    )
                    if title:
                        session_store.update_activity(
                            session_id, title=title, message_count=msg_count
                        )
                        console.print(f"[dim]会话标题: {title}[/dim]")
                    else:
                        # AI 生成失败，使用简单版本
                        title = _generate_session_title_simple(command)
                        session_store.update_activity(
                            session_id, title=title, message_count=msg_count
                        )
                else:
                    session_store.update_activity(session_id, message_count=msg_count)

            console.print("\n[cyan]🐦 FinchBot:[/cyan]")
            console.print(Panel(response))
            console.print()

        except KeyboardInterrupt:
            console.print("\n[dim]Goodbye! 👋[/dim]")
            break
        except EOFError:
            console.print("\n[dim]Goodbye! 👋[/dim]")
            break
        except Exception as e:
            logger.exception("Error in chat loop")
            console.print(f"[red]Error: {e}[/red]")
            console.print("[dim]Check logs for more details.[/dim]")


def _get_provider_config(provider: str, config_obj: Config) -> tuple[str | None, str | None]:
    """获取 provider 的 API key 和 base.

    优先级：环境变量 > 配置文件预设 > 配置文件自定义

    Args:
        provider: Provider 名称
        config_obj: 配置对象

    Returns:
        (api_key, api_base) 元组
    """
    from finchbot.config.utils import get_api_base, get_api_key

    api_key = get_api_key(provider)
    api_base = get_api_base(provider)

    if not api_key:
        # 检查预设 provider
        if hasattr(config_obj.providers, provider):
            prov_config = getattr(config_obj.providers, provider)
            if prov_config and isinstance(prov_config, ProviderConfig):
                api_key = prov_config.api_key or None
                api_base = prov_config.api_base or api_base

        # 检查自定义 provider
        if not api_key and provider in config_obj.providers.custom:
            custom = config_obj.providers.custom[provider]
            if custom and isinstance(custom, ProviderConfig):
                api_key = custom.api_key or None
                api_base = custom.api_base or api_base

    return api_key, api_base


def _get_llm_config(model: str, config_obj: Config) -> tuple[str | None, str | None, str | None]:
    """获取 LLM 配置.

    优先级：显式传入 > 环境变量 > 配置文件 > 自动检测。

    Returns:
        (api_key, api_base, detected_model) 元组，detected_model 为自动检测到的模型名称（如果有）。
    """
    model_lower = model.lower()

    provider = "openai"
    for name, keywords in PROVIDER_KEYWORDS.items():
        if any(kw in model_lower for kw in keywords):
            provider = name
            break

    # 获取 provider 配置（环境变量 > 配置文件）
    api_key, api_base = _get_provider_config(provider, config_obj)

    # 如果仍然没有 api_key，尝试自动检测
    detected_model = None
    if not api_key:
        api_key, api_base, detected_provider, detected_model = _auto_detect_provider()

    return api_key, api_base, detected_model


def _auto_detect_provider() -> tuple[str | None, str | None, str | None, str | None]:
    """根据环境变量自动检测可用的 provider.

    Returns:
        (api_key, api_base, provider, detected_model) 元组，如果没有可用的 provider 则返回 (None, None, None, None)。
    """
    from finchbot.config.utils import get_api_base

    for provider, default_model, env_vars in PROVIDER_PRIORITY:
        for env_var in env_vars:
            api_key = os.getenv(env_var)
            if api_key:
                api_base = get_api_base(provider)
                return api_key, api_base, provider, default_model

    return None, None, None, None


EXIT_COMMANDS = {"exit", "quit", "/exit", "/quit", ":q", "q"}


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


@app.command(name="chat")
def repl(
    session: str = typer.Option(None, "--session", "-s", help="Session ID / 会话 ID"),
    model: str = typer.Option(None, "--model", "-m", help="Model to use / 使用的模型"),
    workspace: str = typer.Option(None, "--workspace", "-w", help="Workspace directory / 工作目录"),
) -> None:
    """与 FinchBot 对话 (交互式聊天模式).

    无 -s 参数时自动进入最近活跃的会话。
    """
    config_obj = load_config()
    ws_path = Path(workspace or config_obj.agents.defaults.workspace).expanduser()

    # 如果没有指定会话，使用最近活跃的会话
    if session is None:
        session = _get_last_active_session(ws_path)
        console.print(f"[dim]{t('sessions.using_last_active')}: {session}[/dim]\n")

    _run_chat_session(session, model, workspace)


sessions_app = typer.Typer(help="Manage sessions / 管理会话")
app.add_typer(sessions_app, name="sessions")


@sessions_app.callback(invoke_without_command=True)
def sessions_callback(ctx: typer.Context) -> None:
    """会话管理命令组.

    无子命令时默认进入交互式管理界面。
    """
    if ctx.invoked_subcommand is None:
        # 默认进入交互式会话管理
        config_obj = load_config()
        ws_path = Path(config_obj.agents.defaults.workspace).expanduser()

        selector = SessionSelector(ws_path)
        selector.interactive_manage()


@sessions_app.command("show")
def sessions_show(
    session_id: str = typer.Argument("default", help="Session ID to show"),
    limit: int = typer.Option(10, "--limit", "-l", help="Max messages to show"),
    show_index: bool = typer.Option(False, "--index", "-i", help="Show message index for rollback"),
) -> None:
    """显示会话历史."""

    config_obj = load_config()
    ws_path = Path(config_obj.agents.defaults.workspace).expanduser()
    db_path = ws_path / "checkpoints.db"

    if not db_path.exists():
        console.print("[yellow]No sessions database found.[/yellow]")
        return

    try:
        with closing(sqlite3.connect(str(db_path))) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT checkpoint FROM checkpoints
                WHERE thread_id = ?
                ORDER BY checkpoint_id DESC
                LIMIT ?
            """,
                (session_id, limit),
            )
            checkpoints = cursor.fetchall()

        if not checkpoints:
            console.print(f"[yellow]No history found for session '{session_id}'.[/yellow]")
            return

        console.print(f"[bold cyan]📜 Session: {session_id}[/bold cyan]\n")

        messages = []
        for (checkpoint_json,) in checkpoints:
            try:
                data = json.loads(checkpoint_json)
                if "channel_values" in data and "messages" in data["channel_values"]:
                    messages.extend(data["channel_values"]["messages"])
            except (json.JSONDecodeError, KeyError, TypeError):
                pass

        # 去重并显示最近的对话
        seen = set()
        unique_messages = []
        for msg in reversed(messages[-limit * 2 :]):
            content = msg.get("content", "")
            if content and content not in seen:
                seen.add(content)
                unique_messages.append(msg)

        # 显示消息（带索引或不带索引）
        for idx, msg in enumerate(unique_messages):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            prefix = f"[{idx}] " if show_index else ""

            if role == "user":
                console.print(f"{prefix}[blue]You:[/blue] {content}")
            elif role == "assistant":
                console.print(
                    f"{prefix}[cyan]FinchBot:[/cyan] {content[:200]}{'...' if len(content) > 200 else ''}"
                )
            console.print()

        if show_index:
            console.print(
                f"[dim]Tip: Use 'sessions rollback {session_id} <index> --new-session <name>'[/dim]"
            )

    except Exception as e:
        console.print(f"[red]Error reading session: {e}[/red]")


@sessions_app.command("rollback")
def sessions_rollback(
    session_id: str = typer.Argument(..., help="Session ID to rollback"),
    message_index: int = typer.Argument(
        ..., help="Rollback to before this message index (0-based)"
    ),
    new_session: str = typer.Option(
        None, "--new-session", "-n", help="Create new session with rolled back messages"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Force rollback without confirmation"),
) -> None:
    """回退到指定消息之前，可选创建新会话."""
    config_obj = load_config()
    ws_path = Path(config_obj.agents.defaults.workspace).expanduser()
    db_path = ws_path / "checkpoints.db"

    if not db_path.exists():
        console.print("[yellow]No sessions database found.[/yellow]")
        return

    try:
        with closing(sqlite3.connect(str(db_path))) as conn:
            cursor = conn.cursor()

            # 获取源会话的最新检查点
            cursor.execute(
                """
                SELECT checkpoint_id, checkpoint FROM checkpoints
                WHERE thread_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (session_id,),
            )
            result = cursor.fetchone()

            if not result:
                console.print(f"[yellow]Session '{session_id}' not found.[/yellow]")
                return

            checkpoint_id, checkpoint_json = result
            checkpoint_data = json.loads(checkpoint_json)
            messages = checkpoint_data.get("channel_values", {}).get("messages", [])

            if message_index < 0 or message_index > len(messages):
                console.print(f"[red]Invalid message index. Range: 0-{len(messages)}[/red]")
                return

            # 确认回退
            if not force:
                confirm_msg = (
                    f"{t('sessions.rollback.confirm_rollback').format(message_index)} "
                    f"{t('sessions.rollback.keep_messages').format(message_index - 1, message_index)}, "
                    f"{t('sessions.rollback.remove_messages').format(message_index, len(messages) - 1, len(messages) - message_index)}."
                )
                confirm = questionary.confirm(confirm_msg, default=False).ask()
                if not confirm:
                    console.print(f"[dim]{t('sessions.rollback.cancelled')}[/dim]")
                    return

            # 截取消息（保留 0 到 message_index-1）
            rolled_back_messages = messages[:message_index]

            if new_session:
                # 创建新会话
                new_checkpoint = {
                    "channel_values": {"messages": rolled_back_messages},
                    "metadata": {
                        "source_session": session_id,
                        "source_checkpoint": checkpoint_id,
                        "rollback_to": message_index,
                        "created_at": datetime.now().isoformat(),
                    },
                }

                cursor.execute(
                    """
                    INSERT INTO checkpoints (thread_id, checkpoint_id, checkpoint, metadata, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        new_session,
                        f"rollback-{datetime.now().timestamp()}",
                        json.dumps(new_checkpoint),
                        json.dumps({"source": session_id, "rollback": True}),
                        datetime.now().isoformat(),
                    ),
                )
                conn.commit()

                console.print(
                    f"[green]✓ Created new session '{new_session}' "
                    f"with {len(rolled_back_messages)} messages[/green]"
                )
                console.print(
                    f"[dim]Rolled back from message {message_index} of '{session_id}'[/dim]"
                )
                console.print(f"[dim]Start chatting: finchbot repl -s {new_session}[/dim]")
            else:
                # 修改现有会话（原地回退）
                new_checkpoint = {
                    "channel_values": {"messages": rolled_back_messages},
                    "metadata": checkpoint_data.get("metadata", {}),
                }
                new_checkpoint["metadata"]["rolled_back"] = {
                    "from_index": message_index,
                    "original_count": len(messages),
                    "rolled_at": datetime.now().isoformat(),
                }

                cursor.execute(
                    """
                    UPDATE checkpoints
                    SET checkpoint = ?, metadata = ?
                    WHERE thread_id = ? AND checkpoint_id = ?
                    """,
                    (
                        json.dumps(new_checkpoint),
                        json.dumps(new_checkpoint["metadata"]),
                        session_id,
                        checkpoint_id,
                    ),
                )
                conn.commit()

                console.print(
                    f"[green]✓ Rolled back session '{session_id}' "
                    f"to message {message_index}[/green]"
                )
                console.print(
                    f"[dim]Kept {len(rolled_back_messages)} messages, removed {len(messages) - message_index}[/dim]"
                )

    except Exception as e:
        console.print(f"[red]Error rolling back session: {e}[/red]")


class ConfigManager:
    """交互式配置管理器.

    提供键盘导航的配置管理界面，支持：
    - 查看所有配置项
    - 选中配置项后按 Enter 修改
    - 格式化重置配置（带确认）
    """

    def __init__(self) -> None:
        self.config = load_config()
        self.config_path = get_config_path()

    def interactive_manage(self) -> None:
        """启动交互式配置管理."""
        try:
            # 直接进入配置管理界面（配置已自动初始化）
            self._run_config_manager()
        except KeyboardInterrupt:
            console.print("\n[dim]配置已取消。[/dim]")
            raise

    def _run_config_manager(self) -> None:
        """运行配置管理界面（键盘导航）."""
        config_items = self._get_config_items()
        selected_idx = 0

        try:
            while True:
                console.clear()
                console.print(f"[bold blue]🔧 {t('cli.config.init_title')}[/bold blue]")
                console.print(f"[dim]{t('cli.config.config_file')} {self.config_path}[/dim]\n")

                # 渲染配置项列表
                self._render_config_list(config_items, selected_idx)

                # 显示帮助信息
                console.print()
                console.print(
                    f"[dim cyan]↑↓[/dim cyan] [dim]{t('config.manager.navigate')}[/dim]  "
                    f"[dim cyan]Enter[/dim cyan] [dim]{t('config.manager.edit')}[/dim]  "
                    f"[dim cyan]R[/dim cyan] [dim]{t('config.manager.reset_all')}[/dim]  "
                    f"[dim cyan]Q[/dim cyan] [dim]{t('config.manager.quit')}[/dim]"
                )

                key = readchar.readkey()

                if key == readchar.key.UP:
                    selected_idx = max(0, selected_idx - 1)
                elif key == readchar.key.DOWN:
                    selected_idx = min(len(config_items) - 1, selected_idx + 1)
                elif key == readchar.key.ENTER:
                    # 编辑选中的配置项
                    self._edit_config_item(config_items[selected_idx])
                    # 重新加载配置
                    self.config = load_config()
                    config_items = self._get_config_items()
                elif key.lower() == "r":
                    # 重置所有配置（带确认）
                    if self._confirm_reset():
                        self._reset_config()
                        return
                elif key.lower() == "q" or key == readchar.key.CTRL_C:
                    return

        except KeyboardInterrupt:
            logger.debug("Config management cancelled by user")

    def _get_config_items(self) -> list[dict]:
        """获取配置项列表（用于展示）."""
        items = [
            {
                "key": "language",
                "name": t("cli.config.language_set").rstrip("："),
                "value": self.config.language,
                "editable": True,
            },
            {
                "key": "default_model",
                "name": t("cli.config.default_model").rstrip("："),
                "value": self.config.default_model,
                "editable": True,
            },
            {
                "key": "workspace",
                "name": t("cli.config.workspace"),
                "value": self.config.agents.defaults.workspace,
                "editable": True,
            },
            {
                "key": "providers",
                "name": t("cli.config.configured_providers").rstrip("："),
                "value": ", ".join(self.config.get_configured_providers()) or t("cli.status.not_configured"),
                "editable": False,  # 通过子菜单编辑
            },
        ]

        # 添加已配置的 provider
        for provider_name in self.config.get_configured_providers():
            if provider_name.startswith("custom:"):
                name = provider_name.replace("custom:", "")
                items.append({
                    "key": f"custom.{name}",
                    "name": f"  └─ {t('cli.config.custom')}: {name}",
                    "value": "***",
                    "editable": True,
                })

        return items

    def _render_config_list(self, items: list[dict], selected_idx: int) -> None:
        """渲染配置项列表."""
        table = Table(
            box=box.ROUNDED,
            show_header=True,
            header_style="blue bold",
            border_style="dim",
        )
        table.add_column("", width=2, justify="center")
        table.add_column(t("config.manager.setting"), min_width=20)
        table.add_column(t("config.manager.value"), min_width=30)

        for idx, item in enumerate(items):
            is_selected = idx == selected_idx
            cursor = "▶" if is_selected else " "

            if is_selected:
                cursor_text = Text(cursor, style="cyan bold")
                name_text = Text(item["name"], style="cyan bold")
                value_text = Text(str(item["value"]), style="cyan")
            else:
                cursor_text = Text(cursor, style="")
                name_text = Text(item["name"], style="white")
                value_text = Text(str(item["value"]), style="green")

            table.add_row(cursor_text, name_text, value_text)

        console.print(table)

    def _edit_config_item(self, item: dict) -> None:
        """编辑单个配置项."""
        key = item["key"]

        if key == "language":
            _configure_language(self.config)
        elif key == "default_model":
            _configure_default_model(self.config)
        elif key == "workspace":
            new_path = questionary.text(
                t("cli.config.workspace_path"),
                default=self.config.agents.defaults.workspace,
            ).unsafe_ask()
            if new_path:
                self.config.agents.defaults.workspace = new_path
        elif key == "providers":
            # 进入 provider 配置子菜单
            self._configure_providers_submenu()
        elif key.startswith("custom."):
            # 编辑自定义 provider
            provider_name = key.replace("custom.", "")
            self._edit_custom_provider(provider_name)

        save_config(self.config)
        console.print(f"[green]✓ {t('cli.config.config_updated')}[/green]")
        console.print(f"[dim]{t('config.manager.press_any_key_to_continue')}[/dim]")
        readchar.readkey()

    def _configure_providers_submenu(self) -> None:
        """配置提供商子菜单（键盘导航）."""
        # 构建提供商列表
        providers = [
            {"name": info["name"], "value": name}
            for name, info in PRESET_PROVIDERS.items()
        ]
        providers.append({"name": t("cli.config.add_custom_provider"), "value": "custom"})

        title = f"\n[bold cyan]{t('cli.config.select_provider_to_configure')}[/bold cyan]\n"
        help_text = (
            f"\n[dim cyan]↑↓[/dim cyan] [dim]{t('config.manager.navigate')}[/dim]  "
            f"[dim cyan]Enter[/dim cyan] [dim]{t('config.manager.select')}[/dim]  "
            f"[dim cyan]Q[/dim cyan] [dim]{t('config.manager.quit')}[/dim]"
        )

        result = _keyboard_select(providers, title, help_text)

        if result == "custom":
            _configure_custom_provider(self.config)
        elif result:
            _configure_preset_provider(self.config, result)

    def _edit_custom_provider(self, provider_name: str) -> None:
        """编辑自定义 provider."""
        if provider_name in self.config.providers.custom:
            prov = self.config.providers.custom[provider_name]
            new_key = questionary.text(
                t("cli.config.api_key"),
                default=prov.api_key,
                is_password=True,
            ).unsafe_ask()
            if new_key:
                prov.api_key = new_key

    def _confirm_reset(self) -> bool:
        """确认重置配置."""
        console.print(f"\n[red]{t('cli.config.reset_warning')}[/red]")
        console.print(f"[dim]{t('config.manager.press_any_key_to_continue')}[/dim]")
        console.print(f"[dim]{t('cli.config.reset_confirm')} (Y/n)[/dim]")
        key = readchar.readkey()
        return key.lower() == "y"

    def _reset_config(self) -> None:
        """重置配置为默认值."""
        # 创建默认配置
        default_config = Config()
        save_config(default_config)
        console.print(f"[green]✓ {t('cli.config.reset_success')}[/green]")
        console.print(f"[dim]{t('cli.config.reset_run_again')}[/dim]")


def _run_interactive_config() -> None:
    """运行交互式配置（入口函数）."""
    manager = ConfigManager()
    manager.interactive_manage()


config_app = typer.Typer(help="Manage configuration / 管理配置")
app.add_typer(config_app, name="config")


@config_app.callback(invoke_without_command=True)
def config_callback(ctx: typer.Context) -> None:
    """配置管理（完全交互式界面）."""
    if ctx.invoked_subcommand is None:
        _run_interactive_config()


def _configure_language(config_obj: Config) -> None:
    """配置语言（键盘导航）."""
    languages = [
        {"name": "English (en-US)", "value": "en-US"},
        {"name": "简体中文 (zh-CN)", "value": "zh-CN"},
        {"name": "繁體中文 (zh-HK)", "value": "zh-HK"},
    ]

    # 找到当前语言的索引
    initial_idx = 0
    for idx, lang in enumerate(languages):
        if lang["value"] == config_obj.language:
            initial_idx = idx
            break

    title = f"\n[bold cyan]{t('cli.config.choose_language')}[/bold cyan]\n"
    help_text = (
        f"\n[dim cyan]↑↓[/dim cyan] [dim]{t('config.manager.navigate')}[/dim]  "
        f"[dim cyan]Enter[/dim cyan] [dim]{t('config.manager.select')}[/dim]  "
        f"[dim cyan]Q[/dim cyan] [dim]{t('config.manager.skip')}[/dim]"
    )

    result = _keyboard_select(languages, title, help_text, initial_idx=initial_idx)

    if result:
        config_obj.language = result
        config_obj.language_set_by_user = True
        set_language(result)
        selected_name = languages[initial_idx]["name"]
        for lang in languages:
            if lang["value"] == result:
                selected_name = lang["name"]
                break
        console.print(f"[green]✓ {t('cli.config.language_set_to')} {selected_name}[/green]\n")


def _configure_preset_provider(config_obj: Config, provider: str) -> None:
    """配置预设提供商."""
    info = PRESET_PROVIDERS[provider]

    api_key = questionary.text(
        t("cli.config.api_key_for").format(info["name"]),
        is_password=True,
    ).ask()

    if not api_key:
        return

    use_custom_base = questionary.confirm(
        f"{t('cli.config.use_custom_api_base')} ({t('cli.config.default_hint').format(info['default_base'])})",
        default=False,
    ).ask()

    api_base = None
    if use_custom_base:
        api_base = questionary.text(
            t("cli.config.api_base_url"),
            default=info["default_base"],
        ).ask()

    prov_config = ProviderConfig(
        api_key=api_key,
        api_base=api_base,
    )
    setattr(config_obj.providers, provider, prov_config)
    console.print(f"[green]✓ Configured {info['name']}[/green]")


def _configure_custom_provider(config_obj: Config) -> None:
    """配置自定义提供商."""
    console.print(f"\n[bold cyan]{t('cli.config.add_custom_provider')}[/bold cyan]")
    console.print(f"[dim]Ctrl+C {t('sessions.actions.cancel')}[/dim]")

    try:
        name = questionary.text(
            t("cli.config.provider_name"),
        ).unsafe_ask()

        if not name:
            return

        api_key = questionary.password(
            t("cli.config.api_key"),
        ).unsafe_ask()

        api_base = questionary.text(
            t("cli.config.api_base_url"),
        ).unsafe_ask()
    except KeyboardInterrupt:
        console.print(f"\n[dim]{t('sessions.actions.cancelled')}[/dim]")
        return

    config_obj.providers.custom[name] = ProviderConfig(
        api_key=api_key,
        api_base=api_base,
    )
    console.print(f"[green]✓ {t('cli.config.configured_custom_provider')}: {name}[/green]")


def _configure_default_model(config_obj: Config) -> None:
    """配置默认模型."""
    model = questionary.text(
        t("cli.config.enter_model_name"),
        default=config_obj.default_model,
    ).ask()

    if model:
        config_obj.default_model = model
        config_obj.default_model_set_by_user = True


models_app = typer.Typer(help="Manage models / 管理模型")
app.add_typer(models_app, name="models")


@models_app.command("download")
def models_download(
    quiet: bool = typer.Option(False, "--quiet", "-q", help="静默模式"),
) -> None:
    """下载嵌入模型到本地.

    自动检测网络环境，选择最佳镜像源下载模型。
    国内用户使用 hf-mirror.com 镜像，国外用户使用官方源。
    """
    from finchbot.utils.model_downloader import (
        _detect_best_mirror,
        ensure_models,
    )

    # 检测最佳镜像
    mirror_url, mirror_name = _detect_best_mirror()

    console.print("[bold cyan]📥 下载 FinchBot 嵌入模型[/bold cyan]\n")
    console.print("模型: BAAI/bge-small-zh-v1.5")
    console.print(f"源: {mirror_name} ({mirror_url})")
    console.print()

    success = ensure_models(verbose=not quiet)

    if success:
        console.print("\n[green]✓ 模型下载完成[/green]")
        raise typer.Exit(0)
    else:
        console.print("\n[red]✗ 模型下载失败[/red]")
        if mirror_name == "官方源":
            console.print("[dim]提示: 检查网络连接或尝试设置代理[/dim]")
        else:
            console.print("[dim]提示: 检查网络连接或稍后重试[/dim]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
