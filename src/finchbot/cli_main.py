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
from finchbot.i18n import t

app = typer.Typer(
    name="finchbot",
    help=t("cli.help"),
)


@app.callback()
def main(
    verbose: int = typer.Option(0, "--verbose", "-v", count=True, help=t("cli.verbose_help")),
) -> None:
    """FinchBot - 智能 Agent 框架."""
    from finchbot.utils.logger import setup_logger

    if verbose >= 2:
        console_level = "DEBUG"
    elif verbose == 1:
        console_level = "INFO"
    else:
        console_level = "WARNING"

    setup_logger(console_level=console_level, console_enabled=True)


@app.command()
def version() -> None:
    """显示版本信息."""
    console.print(
        f"[bold cyan]FinchBot[/bold cyan] {t('cli.version')}: [green]{__version__}[/green]"
    )


@app.command(name="chat")
def repl(
    session: str = typer.Option(None, "--session", "-s", help=t("cli.chat.session_option")),
    model: str = typer.Option(None, "--model", "-m", help=t("cli.chat.model_option")),
    workspace: str = typer.Option(None, "--workspace", "-w", help=t("cli.chat.workspace_option")),
    markdown: bool = typer.Option(
        True,
        "--markdown/--no-markdown",
        help=t("cli.chat.markdown_option"),
    ),
) -> None:
    """与 FinchBot 对话 (交互式聊天模式).

    无 -s 参数时自动进入最近活跃的会话。
    """
    ws_path = Path(workspace).expanduser() if workspace else get_default_workspace()

    if not session:
        session = _get_last_active_session(ws_path)
        console.print(f"[dim]{t('sessions.using_last_active')}: {session}[/dim]\n")

    _run_chat_session(session, model, workspace, render_markdown=markdown)


sessions_app = typer.Typer(help=t("cli.commands.sessions_help"))
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


config_app = typer.Typer(help=t("cli.commands.config_help"))
app.add_typer(config_app, name="config")


@config_app.callback(invoke_without_command=True)
def config_callback(
    ctx: typer.Context,
    workspace: str = typer.Option(
        None,
        "--workspace",
        "-w",
        help=t("cli.chat.workspace_option"),
    ),
) -> None:
    """配置管理（完全交互式界面）."""
    if ctx.invoked_subcommand is None:
        ws_path = Path(workspace).expanduser() if workspace else get_default_workspace()
        _run_interactive_config(ws_path)


models_app = typer.Typer(help=t("cli.commands.models_help"))
app.add_typer(models_app, name="models")


@models_app.command("download")
def models_download() -> None:
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

    success = ensure_models(verbose=True)

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


cron_app = typer.Typer(help=t("cli.commands.cron_help"))
app.add_typer(cron_app, name="cron")


@cron_app.callback(invoke_without_command=True)
def cron_callback(ctx: typer.Context) -> None:
    """定时任务管理（交互式界面）."""
    if ctx.invoked_subcommand is None:
        from finchbot.cron.service import CronService
        from finchbot.cron.ui import CronTaskUI

        ws_path = get_default_workspace()
        cron_service = CronService(ws_path / "data")
        ui = CronTaskUI(cron_service, ws_path)
        ui.interactive_manage()


channel_app = typer.Typer(help=t("cli.commands.channel_help"))
app.add_typer(channel_app, name="channel")


@channel_app.callback(invoke_without_command=True)
def channel_callback(ctx: typer.Context) -> None:
    """渠道管理（交互式界面）."""
    if ctx.invoked_subcommand is None:
        from finchbot.channels.selector import ChannelSelector

        selector = ChannelSelector()
        selector.interactive_manage()


@channel_app.command("serve")
def channel_serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help=t("cli.channel.host_help")),
    port: int = typer.Option(8000, "--port", "-p", help=t("cli.channel.port_help")),
) -> None:
    """启动 Webhook 服务器.

    启动 HTTP 服务接收 LangBot 的消息事件。
    """
    _serve_webhook(host, port)


@app.command("webhook")
def webhook_serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help=t("cli.channel.host_help")),
    port: int = typer.Option(8000, "--port", "-p", help=t("cli.channel.port_help")),
) -> None:
    """启动 Webhook 服务器.

    文档中公开的快捷命令，等价于 `finchbot channel serve`。
    """
    _serve_webhook(host, port)


def _serve_webhook(host: str, port: int) -> None:
    """启动 LangBot Webhook 服务."""
    from finchbot.channels.webhook_server import run_webhook_server
    from finchbot.config import load_config

    config = load_config()

    if not config.channels.langbot_enabled:
        console.print(f"[yellow]{t('cli.channel.not_enabled')}[/yellow]")
        console.print(f"[dim]{t('cli.channel.run_config')}[/dim]")
        raise typer.Exit(1)

    console.print(f"[bold cyan]{t('cli.channel.starting')}[/bold cyan]")
    console.print(f"[dim]{t('cli.channel.listening', host=host, port=port)}[/dim]")
    console.print(
        f"[dim]{t('cli.channel.endpoint', path=config.channels.langbot_webhook_path)}[/dim]"
    )
    console.print()

    try:
        run_webhook_server(config, host=host, port=port)
    except KeyboardInterrupt:
        console.print(f"\n[dim]{t('cli.channel.stopped')}[/dim]")


if __name__ == "__main__":
    app()
