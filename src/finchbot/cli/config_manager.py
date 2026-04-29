"""配置管理模块。

提供交互式配置管理功能，包括配置项的查看、编辑和重置。
"""

from __future__ import annotations

import os
from pathlib import Path

import questionary
import readchar
from loguru import logger
from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from finchbot.cli.providers import PRESET_PROVIDERS, _get_provider_name
from finchbot.cli.ui import _keyboard_select
from finchbot.config import get_config_path, load_config, save_config
from finchbot.config.loader import load_mcp_config, save_mcp_config
from finchbot.config.schema import (
    Config,
    MCPServerConfig,
    ProviderConfig,
    WebSearchConfig,
)
from finchbot.i18n import set_language, t
from finchbot.workspace import get_mcp_config_path, init_workspace

console = Console()

MCP_SERVER_TEMPLATES = {
    "filesystem": {
        "name": "Filesystem (Local files)",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem"],
        "requires_path": True,
    },
    "fetch": {
        "name": "Fetch (Web content)",
        "command": "uvx",
        "args": ["mcp-server-fetch"],
    },
    "sqlite": {
        "name": "SQLite (Database)",
        "command": "uvx",
        "args": ["mcp-server-sqlite"],
        "requires_db_path": True,
    },
    "github": {
        "name": "GitHub API",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "requires_env": ["GITHUB_PERSONAL_ACCESS_TOKEN"],
    },
    "brave-search": {
        "name": "Brave Search",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-brave-search"],
        "requires_env": ["BRAVE_API_KEY"],
    },
    "puppeteer": {
        "name": "Puppeteer (Browser automation)",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-puppeteer"],
    },
}


class ConfigManager:
    """交互式配置管理器。

    提供键盘导航的配置管理界面，支持：
    - 查看所有配置项
    - 选中配置项后按 Enter 修改
    - 格式化重置配置（带确认）
    """

    def __init__(self, workspace: Path | None = None) -> None:
        self.config = load_config()
        self.config_path = get_config_path()
        self.workspace = workspace or Path.cwd()
        self._init_workspace()
        self._load_workspace_mcp()

    def _init_workspace(self) -> None:
        if not self.workspace.exists():
            self.workspace.mkdir(parents=True, exist_ok=True)
        init_workspace(self.workspace, create_gitignore=True)

    def _load_workspace_mcp(self) -> None:
        mcp_servers = load_mcp_config(self.workspace)
        if mcp_servers:
            self.config.mcp.servers = mcp_servers

    def interactive_manage(self) -> None:
        """启动交互式配置管理."""
        try:
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
                console.print(f"[dim]{t('cli.config.config_file')} {self.config_path}[/dim]")
                console.print(f"[dim]{t('cli.config.workspace')}: {self.workspace}[/dim]")
                console.print(
                    f"[dim]{t('cli.config.mcp_config_file')}: {get_mcp_config_path(self.workspace)}[/dim]\n"
                )

                self._render_config_list(config_items, selected_idx)

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
                    self._edit_config_item(config_items[selected_idx])
                    self.config = load_config()
                    self._load_workspace_mcp()
                    config_items = self._get_config_items()
                elif key.lower() == "r":
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
                "value": (
                    ", ".join(self.config.get_configured_providers())
                    or t("cli.status.not_configured")
                ),
                "editable": False,
            },
            {
                "key": "search_engines",
                "name": t("cli.config.search_engines"),
                "value": self._get_search_engines_status(),
                "editable": True,
            },
            {
                "key": "mcp",
                "name": t("cli.config.mcp_servers"),
                "value": self._get_mcp_status(),
                "editable": True,
            },
        ]

        for provider_name in self.config.get_configured_providers():
            if provider_name.startswith("custom:"):
                name = provider_name.replace("custom:", "")
                items.append(
                    {
                        "key": f"custom.{name}",
                        "name": f"  └─ {t('cli.config.custom')}: {name}",
                        "value": "***",
                        "editable": True,
                    }
                )

        for server_name, server_config in self.config.mcp.servers.items():
            items.append(
                {
                    "key": f"mcp.{server_name}",
                    "name": f"  └─ MCP: {server_name}",
                    "value": t("cli.config.channel_enabled") if not server_config.disabled else t("cli.config.channel_disabled"),
                    "editable": True,
                }
            )

        return items

    def _get_search_engines_status(self) -> str:
        """获取搜索引擎配置状态."""

        web_config = self.config.tools.web.search

        has_tavily = bool(
            web_config.api_key
            or os.getenv("FINCHBOT_TOOLS__WEB__SEARCH__API_KEY")
            or os.getenv("TAVILY_API_KEY")
        )
        has_brave = bool(
            web_config.brave_api_key
            or os.getenv("FINCHBOT_TOOLS__WEB__SEARCH__BRAVE_API_KEY")
            or os.getenv("BRAVE_API_KEY")
        )

        engines = []
        if has_tavily:
            engines.append(f"Tavily ({t('search.status.available')})")
        if has_brave:
            engines.append(f"Brave ({t('search.status.available')})")
        if engines:
            return " | ".join(engines)
        return t("search.status.no_api_key")

    def _get_mcp_status(self) -> str:
        """获取 MCP 配置状态."""
        server_count = len(self.config.mcp.servers)
        if server_count == 0:
            return t("cli.status.not_configured")
        return t("cli.config.mcp_servers_count").format(count=server_count)

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
            self._configure_providers_submenu()
        elif key == "search_engines":
            self._configure_search_engines()
        elif key == "mcp":
            self._configure_mcp()
        elif key.startswith("custom."):
            provider_name = key.replace("custom.", "")
            self._edit_custom_provider(provider_name)
        elif key.startswith("mcp."):
            server_name = key.replace("mcp.", "")
            self._edit_mcp_server(server_name)

        if key.startswith("mcp.") or key == "mcp":
            self._save_mcp_config()
        else:
            save_config(self.config)
        console.print(f"[green]✓ {t('cli.config.config_updated')}[/green]")
        console.print(f"[dim]{t('config.manager.press_any_key_to_continue')}[/dim]")
        readchar.readkey()

    def _save_mcp_config(self) -> None:
        """保存 MCP 配置到工作区."""
        save_mcp_config(self.config.mcp.servers, self.workspace)

    def _configure_providers_submenu(self) -> None:
        """配置提供商子菜单（键盘导航）."""
        providers = [
            {"name": _get_provider_name(name), "value": name}
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

    def _configure_search_engines(self) -> None:
        """配置搜索引擎 API Key（键盘导航菜单）."""

        web_config = self.config.tools.web.search

        # 从环境变量读取
        env_tavily = os.getenv("FINCHBOT_TOOLS__WEB__SEARCH__API_KEY") or os.getenv(
            "TAVILY_API_KEY"
        )
        env_brave = os.getenv("FINCHBOT_TOOLS__WEB__SEARCH__BRAVE_API_KEY") or os.getenv(
            "BRAVE_API_KEY"
        )

        while True:
            # 获取当前状态
            config_tavily = web_config.api_key
            if config_tavily:
                tavily_status = f"*** ({t('cli.config.from_config')})"
            elif env_tavily:
                tavily_status = f"*** ({t('cli.config.from_env')})"
            else:
                tavily_status = t("cli.config.not_set")

            config_brave = web_config.brave_api_key
            if config_brave:
                brave_status = f"*** ({t('cli.config.from_config')})"
            elif env_brave:
                brave_status = f"*** ({t('cli.config.from_env')})"
            else:
                brave_status = t("cli.config.not_set")

            # 构建菜单项
            items = [
                {
                    "name": f"Tavily Search       [{tavily_status}]",
                    "value": "tavily",
                },
                {
                    "name": f"Brave Search        [{brave_status}]",
                    "value": "brave",
                },
            ]

            title = f"\n[bold cyan]{t('cli.config.search_engines_title')}[/bold cyan]\n"
            help_text = (
                f"\n[dim cyan]↑↓[/dim cyan] [dim]{t('config.manager.navigate')}[/dim]  "
                f"[dim cyan]Enter[/dim cyan] [dim]{t('config.manager.select')}[/dim]  "
                f"[dim cyan]Q[/dim cyan] [dim]{t('config.manager.quit')}[/dim]"
            )

            result = _keyboard_select(items, title, help_text)

            if result is None:
                break
            elif result == "tavily":
                self._configure_tavily_api_key(web_config, config_tavily, env_tavily)
            elif result == "brave":
                self._configure_brave_api_key(web_config, config_brave, env_brave)

    def _configure_tavily_api_key(
        self,
        web_config: WebSearchConfig,
        config_value: str,
        env_value: str | None,
    ) -> None:
        """配置 Tavily API Key."""
        console.print("\n[bold cyan]Tavily Search[/bold cyan]")

        if config_value:
            status = f"*** ({t('cli.config.from_config')})"
        elif env_value:
            status = f"*** ({t('cli.config.from_env')})"
        else:
            status = t("cli.config.not_set")

        console.print(f"[dim]{t('cli.config.current_tavily')}: {status}[/dim]")

        if env_value and not config_value:
            console.print(f"[dim cyan]{t('cli.config.tavily_env_hint')}[/dim cyan]")

        # 未配置时直接进入输入框；已配置时显示菜单选择设置或清除
        if not config_value:
            # 直接输入新密钥
            new_key = questionary.text(
                t("cli.config.tavily_key_prompt"),
                default="",
                is_password=True,
            ).unsafe_ask()
            if new_key:
                web_config.api_key = new_key
                console.print(f"[green]✓ Tavily API Key {t('cli.config.updated')}[/green]")
                console.print(f"[dim]{t('config.manager.press_any_key_to_continue')}[/dim]")
                readchar.readkey()
        else:
            # 已配置，显示菜单选择设置或清除
            items = [
                {"name": t("cli.config.set_api_key"), "value": "set"},
                {"name": t("cli.config.clear_api_key"), "value": "clear"},
            ]

            title = f"\n[dim]{t('cli.config.select_action')}:[/dim]\n"
            help_text = (
                f"\n[dim cyan]↑↓[/dim cyan] [dim]{t('config.manager.navigate')}[/dim]  "
                f"[dim cyan]Enter[/dim cyan] [dim]{t('config.manager.select')}[/dim]  "
                f"[dim cyan]Q[/dim cyan] [dim]{t('config.manager.back')}[/dim]"
            )

            action = _keyboard_select(items, title, help_text)

            if action == "set":
                new_key = questionary.text(
                    t("cli.config.tavily_key_prompt"),
                    default="",
                    is_password=True,
                ).unsafe_ask()
                if new_key:
                    web_config.api_key = new_key
                    console.print(f"[green]✓ Tavily API Key {t('cli.config.updated')}[/green]")
                    console.print(f"[dim]{t('config.manager.press_any_key_to_continue')}[/dim]")
                    readchar.readkey()
            elif action == "clear":
                web_config.api_key = ""
                console.print(f"[yellow]✓ Tavily API Key {t('cli.config.cleared')}[/yellow]")
                console.print(f"[dim]{t('config.manager.press_any_key_to_continue')}[/dim]")
                readchar.readkey()

    def _configure_brave_api_key(
        self,
        web_config: WebSearchConfig,
        config_value: str,
        env_value: str | None,
    ) -> None:
        """配置 Brave API Key."""
        console.print("\n[bold cyan]Brave Search[/bold cyan]")

        if config_value:
            status = f"*** ({t('cli.config.from_config')})"
        elif env_value:
            status = f"*** ({t('cli.config.from_env')})"
        else:
            status = t("cli.config.not_set")

        console.print(f"[dim]{t('cli.config.current_brave')}: {status}[/dim]")

        if env_value and not config_value:
            console.print(f"[dim cyan]{t('cli.config.brave_env_hint')}[/dim cyan]")

        # 未配置时直接进入输入框；已配置时显示菜单选择设置或清除
        if not config_value:
            # 直接输入新密钥
            new_key = questionary.text(
                t("cli.config.brave_key_prompt"),
                default="",
                is_password=True,
            ).unsafe_ask()
            if new_key:
                web_config.brave_api_key = new_key
                console.print(f"[green]✓ Brave API Key {t('cli.config.updated')}[/green]")
                console.print(f"[dim]{t('config.manager.press_any_key_to_continue')}[/dim]")
                readchar.readkey()
        else:
            # 已配置，显示菜单选择设置或清除
            items = [
                {"name": t("cli.config.set_api_key"), "value": "set"},
                {"name": t("cli.config.clear_api_key"), "value": "clear"},
            ]

            title = f"\n[dim]{t('cli.config.select_action')}:[/dim]\n"
            help_text = (
                f"\n[dim cyan]↑↓[/dim cyan] [dim]{t('config.manager.navigate')}[/dim]  "
                f"[dim cyan]Enter[/dim cyan] [dim]{t('config.manager.select')}[/dim]  "
                f"[dim cyan]Q[/dim cyan] [dim]{t('config.manager.back')}[/dim]"
            )

            action = _keyboard_select(items, title, help_text)

            if action == "set":
                new_key = questionary.text(
                    t("cli.config.brave_key_prompt"),
                    default="",
                    is_password=True,
                ).unsafe_ask()
                if new_key:
                    web_config.brave_api_key = new_key
                    console.print(f"[green]✓ Brave API Key {t('cli.config.updated')}[/green]")
                    console.print(f"[dim]{t('config.manager.press_any_key_to_continue')}[/dim]")
                    readchar.readkey()
            elif action == "clear":
                web_config.brave_api_key = ""
                console.print(f"[yellow]✓ Brave API Key {t('cli.config.cleared')}[/yellow]")
                console.print(f"[dim]{t('config.manager.press_any_key_to_continue')}[/dim]")
                readchar.readkey()

    def _confirm_reset(self) -> bool:
        """确认重置配置."""
        console.print(f"\n[red]{t('cli.config.reset_warning')}[/red]")
        console.print(f"[dim]{t('config.manager.press_any_key_to_continue')}[/dim]")
        console.print(f"[dim]{t('cli.config.reset_confirm')} (Y/n)[/dim]")
        key = readchar.readkey()
        return key.lower() == "y"

    def _reset_config(self) -> None:
        """重置配置为默认值."""
        default_config = Config()
        save_config(default_config)
        console.print(f"[green]✓ {t('cli.config.reset_success')}[/green]")
        console.print(f"[dim]{t('cli.config.reset_run_again')}[/dim]")

    def _configure_mcp(self) -> None:
        """配置 MCP Servers（键盘导航菜单）."""
        while True:
            items = [
                {"name": t("cli.config.mcp_add"), "value": "add"},
            ]

            for server_name, server_config in self.config.mcp.servers.items():
                status = (
                    t("cli.config.mcp_enabled")
                    if not server_config.disabled
                    else t("cli.config.mcp_disabled")
                )
                items.append(
                    {
                        "name": f"{server_name}  [{status}]",
                        "value": f"edit.{server_name}",
                    }
                )

            title = f"\n[bold cyan]{t('cli.config.mcp_title')}[/bold cyan]\n"
            help_text = (
                f"\n[dim cyan]↑↓[/dim cyan] [dim]{t('config.manager.navigate')}[/dim]  "
                f"[dim cyan]Enter[/dim cyan] [dim]{t('config.manager.select')}[/dim]  "
                f"[dim cyan]Q[/dim cyan] [dim]{t('config.manager.quit')}[/dim]"
            )

            result = _keyboard_select(items, title, help_text)

            if result is None:
                break
            elif result == "add":
                self._add_mcp_server()
                self._save_mcp_config()
            elif result.startswith("edit."):
                server_name = result.replace("edit.", "")
                self._edit_mcp_server(server_name)
                self._save_mcp_config()

    def _add_mcp_server(self) -> None:
        """添加 MCP Server."""
        items = [
            {"name": info["name"], "value": name} for name, info in MCP_SERVER_TEMPLATES.items()
        ]
        items.append({"name": t("cli.config.mcp_custom"), "value": "custom"})

        title = f"\n[bold cyan]{t('cli.config.mcp_select_template')}[/bold cyan]\n"
        help_text = (
            f"\n[dim cyan]↑↓[/dim cyan] [dim]{t('config.manager.navigate')}[/dim]  "
            f"[dim cyan]Enter[/dim cyan] [dim]{t('config.manager.select')}[/dim]  "
            f"[dim cyan]Q[/dim cyan] [dim]{t('config.manager.back')}[/dim]"
        )

        result = _keyboard_select(items, title, help_text)
        if result is None:
            return

        try:

            if result == "custom":
                server_name = questionary.text(
                    t("cli.config.mcp_server_name"),
                ).unsafe_ask()
                if not server_name:
                    return

                command = questionary.text(
                    t("cli.config.mcp_command"),
                ).unsafe_ask()
                args_str = questionary.text(
                    t("cli.config.mcp_args"),
                ).unsafe_ask()
                args = [a.strip() for a in args_str.split(",")] if args_str else []
                # Ask for HTTP headers if URL is provided
                url = None
                headers = None
                use_url = questionary.confirm(
                    t("cli.config.mcp_use_http"),
                    default=False,
                ).unsafe_ask()

                if use_url:
                    url = questionary.text(
                        t("cli.config.mcp_url"),
                    ).unsafe_ask()

                    use_headers = questionary.confirm(
                        t("cli.config.mcp_add_headers"),
                        default=False,
                    ).unsafe_ask()

                    if use_headers:
                        headers = {}
                        console.print(f"[dim]{t('cli.config.mcp_headers_hint')}[/dim]")
                        while True:
                            header_key = questionary.text(
                                "Header name (or empty to finish):",
                            ).unsafe_ask()
                            if not header_key:
                                break
                            header_value = questionary.text(
                                f"Value for {header_key}:",
                            ).unsafe_ask()
                            headers[header_key] = header_value

                config_kwargs = {
                    "command": command,
                    "args": args,
                }
                if url:
                    config_kwargs["url"] = url
                if headers:
                    config_kwargs["headers"] = headers

                self.config.mcp.servers[server_name] = MCPServerConfig(**config_kwargs)
                console.print(f"[green]✓ MCP server '{server_name}' {t('cli.config.updated')}[/green]")
            else:
                template = MCP_SERVER_TEMPLATES[result]
                args = template["args"].copy()

                if template.get("requires_path"):
                    path = questionary.text(
                        t("cli.config.mcp_path_required"),
                    ).unsafe_ask()
                    if path:
                        args.append(path)

                if template.get("requires_db_path"):
                    db_path = questionary.text(
                        t("cli.config.mcp_db_path_required"),
                    ).unsafe_ask()
                    if db_path:
                        args.append("--db-path")
                        args.append(db_path)

                env = None
                if template.get("requires_env"):
                    env = {}
                    for env_var in template["requires_env"]:
                        value = questionary.text(
                            t("cli.config.mcp_env_required").format(env_var=env_var),
                        ).unsafe_ask()
                        env[env_var] = value

                self.config.mcp.servers[result] = MCPServerConfig(
                    command=template["command"],
                    args=args,
                    env=env,
                )

                console.print(f"[green]✓ MCP server '{result}' {t('cli.config.updated')}[/green]")
        except KeyboardInterrupt:
            console.print(f"\n[dim]{t('sessions.actions.cancelled')}[/dim]")

    def _edit_mcp_server(self, server_name: str) -> None:
        """编辑 MCP Server."""
        if server_name not in self.config.mcp.servers:
            return

        server_config = self.config.mcp.servers[server_name]
        console.print(f"\n[bold cyan]MCP: {server_name}[/bold cyan]")
        console.print(f"[dim]Command: {server_config.command}[/dim]")
        console.print(f"[dim]Args: {' '.join(server_config.args)}[/dim]")

        if server_config.disabled:
            toggle_name = t("cli.config.mcp_enable")
            toggle_value = "enable"
        else:
            toggle_name = t("cli.config.mcp_disable")
            toggle_value = "disable"

        items = [
            {"name": toggle_name, "value": toggle_value},
            {"name": t("cli.config.mcp_delete"), "value": "delete"},
            {"name": t("config.manager.back"), "value": "back"},
        ]

        title = f"\n[dim]{t('cli.config.select_action')}:[/dim]\n"
        help_text = (
            f"\n[dim cyan]↑↓[/dim cyan] [dim]{t('config.manager.navigate')}[/dim]  "
            f"[dim cyan]Enter[/dim cyan] [dim]{t('config.manager.select')}[/dim]  "
            f"[dim cyan]Q[/dim cyan] [dim]{t('config.manager.back')}[/dim]"
        )

        result = _keyboard_select(items, title, help_text)

        if result == "enable":
            server_config.disabled = False
            console.print(
                f"[green]✓ {t('cli.config.mcp_enable_success').format(server_name=server_name)}[/green]"
            )
        elif result == "disable":
            server_config.disabled = True
            console.print(
                f"[yellow]✓ {t('cli.config.mcp_disable_success').format(server_name=server_name)}[/yellow]"
            )
        elif result == "delete":
            del self.config.mcp.servers[server_name]
            console.print(
                f"[yellow]✓ MCP server '{server_name}' {t('cli.config.cleared')}[/yellow]"
            )


def _run_interactive_config(workspace: Path | None = None) -> None:
    """运行交互式配置（入口函数）."""
    manager = ConfigManager(workspace)
    manager.interactive_manage()


def _configure_language(config_obj: Config) -> None:
    """配置语言（键盘导航）."""
    languages = [
        {"name": "English (en-US)", "value": "en-US"},
        {"name": "简体中文 (zh-CN)", "value": "zh-CN"},
    ]

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

    default_base = info["default_base"]
    use_custom_base = questionary.confirm(
        f"{t('cli.config.use_custom_api_base')} "
        f"({t('cli.config.default_hint').format(default_base)})",
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
