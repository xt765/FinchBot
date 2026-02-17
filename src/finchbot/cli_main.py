"""FinchBot CLI 入口.

提供命令行交互界面，支持多语言和交互式配置。
使用 LangGraph 官方推荐的 create_agent 构建。
"""

from __future__ import annotations

from pathlib import Path

import typer

from finchbot import __version__
from finchbot.agent import get_default_workspace
from finchbot.cli import (
    _get_last_active_session,
    _run_chat_session,
    _run_interactive_config,
    console,
)
from finchbot.config import load_config
from finchbot.i18n import init_language_from_config, set_language, t

app = typer.Typer(
    name="finchbot",
    help="FinchBot (雀翎) - Lightweight AI Agent Framework",
)


@app.callback()
def main(
    lang: str = typer.Option(None, "--lang", "-l", help="Set language / 设置语言"),
) -> None:
    """全局回调."""
    if lang:
        set_language(lang)
    else:
        config_obj = load_config()
        init_language_from_config(config_obj.language)


@app.command()
def version() -> None:
    """显示版本信息."""
    console.print(
        f"[bold cyan]FinchBot[/bold cyan] {t('cli.version')}: [green]{__version__}[/green]"
    )


@app.command(name="chat")
def repl(
    session: str = typer.Option(None, "--session", "-s", help="Session ID / 会话 ID"),
    model: str = typer.Option(None, "--model", "-m", help="Model to use / 使用的模型"),
    workspace: str = typer.Option(None, "--workspace", "-w", help="Workspace directory / 工作目录"),
) -> None:
    """与 FinchBot 对话 (交互式聊天模式).

    无 -s 参数时自动进入最近活跃的会话。
    """
    ws_path = Path(workspace).expanduser() if workspace else get_default_workspace()

    if not session:
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
        ws_path = get_default_workspace()

        from finchbot.sessions import SessionSelector

        selector = SessionSelector(ws_path)
        selector.interactive_manage()


@sessions_app.command("show")
def sessions_show(
    session_id: str = typer.Argument("default", help="Session ID to show"),
    limit: int = typer.Option(10, "--limit", "-l", help="Max messages to show"),
    show_index: bool = typer.Option(False, "--index", "-i", help="Show message index for rollback"),
) -> None:
    """显示会话历史."""
    from finchbot.cli.sessions import show_session

    show_session(session_id, limit, show_index)


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
    from finchbot.cli.sessions import rollback_session

    rollback_session(session_id, message_index, new_session, force)


config_app = typer.Typer(help="Manage configuration / 管理配置")
app.add_typer(config_app, name="config")


@config_app.callback(invoke_without_command=True)
def config_callback(ctx: typer.Context) -> None:
    """配置管理（完全交互式界面）."""
    if ctx.invoked_subcommand is None:
        _run_interactive_config()


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

    mirror_url, mirror_name = _detect_best_mirror()

    console.print(f"\n[bold cyan]{t('cli.models.download_title')}[/bold cyan]\n")
    console.print(t("cli.models.model_name"))
    console.print(t("cli.models.source").format(mirror_name, mirror_url))
    console.print()

    success = ensure_models(verbose=not quiet)

    if success:
        console.print(f"\n[green]{t('cli.models.download_success')}[/green]")
        raise typer.Exit(0)
    else:
        console.print(f"\n[red]{t('cli.models.download_failed')}[/red]")
        if mirror_name == "官方源":
            console.print(f"[dim]{t('cli.models.check_network_proxy')}[/dim]")
        else:
            console.print(f"[dim]{t('cli.models.check_network_retry')}[/dim]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
