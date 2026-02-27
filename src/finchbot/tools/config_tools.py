"""Agent 配置工具.

提供 Agent 自配置能力，包括 MCP 服务器配置和能力描述刷新。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import Field

from finchbot.config.loader import load_mcp_config, save_mcp_config
from finchbot.config.schema import MCPServerConfig
from finchbot.tools.base import FinchTool
from finchbot.workspace import get_mcp_config_path


class ConfigureMCPTool(FinchTool):
    """配置 MCP 服务器的工具.

    允许 Agent 动态添加、修改或删除 MCP 服务器配置。
    """

    name: str = "configure_mcp"
    description: str = """Configure MCP servers dynamically.

Actions:
- add: Add a new MCP server
- update: Update an existing MCP server
- remove: Remove an MCP server
- list: List all configured MCP servers

For 'add' and 'update' actions, provide:
- server_name: Unique name for the server
- command: The command to run (e.g., 'npx', 'uvx')
- args: List of arguments (optional)
- env: Environment variables dict (optional)
- url: URL for HTTP-based MCP servers (optional)

For 'remove' action, provide:
- server_name: Name of the server to remove

For 'list' action, no additional parameters needed.
"""
    workspace: str = Field(default="", exclude=True)

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "update", "remove", "list"],
                    "description": "Action to perform",
                },
                "server_name": {
                    "type": "string",
                    "description": "Name of the MCP server",
                },
                "command": {
                    "type": "string",
                    "description": "Command to run the MCP server",
                },
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Arguments for the command",
                },
                "env": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                    "description": "Environment variables",
                },
                "url": {
                    "type": "string",
                    "description": "URL for HTTP-based MCP servers",
                },
            },
            "required": ["action"],
        }

    def _run(
        self,
        action: str,
        server_name: str | None = None,
        command: str | None = None,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
        url: str | None = None,
    ) -> str:
        workspace = Path(self.workspace) if self.workspace else Path.cwd()

        if action == "list":
            return self._list_servers(workspace)

        if not server_name:
            return "Error: server_name is required for this action"

        if action == "add" or action == "update":
            return self._add_or_update_server(
                workspace, server_name, command, args, env, url
            )
        elif action == "remove":
            return self._remove_server(workspace, server_name)
        else:
            return f"Error: Unknown action '{action}'"

    def _list_servers(self, workspace: Path) -> str:
        servers = load_mcp_config(workspace)

        if not servers:
            return "No MCP servers configured."

        lines = ["Configured MCP servers:"]
        for name, config in servers.items():
            status = "disabled" if config.disabled else "enabled"
            cmd_info = f"command: {config.command}" if config.command else ""
            url_info = f"url: {config.url}" if config.url else ""
            lines.append(f"  - {name} ({status})")
            if cmd_info:
                lines.append(f"    {cmd_info}")
            if url_info:
                lines.append(f"    {url_info}")
            if config.args:
                lines.append(f"    args: {' '.join(config.args)}")

        return "\n".join(lines)

    def _add_or_update_server(
        self,
        workspace: Path,
        server_name: str,
        command: str | None,
        args: list[str] | None,
        env: dict[str, str] | None,
        url: str | None,
    ) -> str:
        servers = load_mcp_config(workspace)

        if server_name in servers:
            existing = servers[server_name]
            new_config = MCPServerConfig(
                command=command or existing.command,
                args=args if args is not None else existing.args,
                env={**(existing.env or {}), **(env or {})} if env or existing.env else None,
                url=url or existing.url,
                disabled=existing.disabled,
            )
            servers[server_name] = new_config
            action_text = "updated"
        else:
            if not command and not url:
                return "Error: Either 'command' or 'url' is required for adding a new server"

            config_kwargs = {}
            if command:
                config_kwargs["command"] = command
            if args:
                config_kwargs["args"] = args
            if env:
                config_kwargs["env"] = env
            if url:
                config_kwargs["url"] = url

            servers[server_name] = MCPServerConfig(**config_kwargs)
            action_text = "added"

        save_mcp_config(servers, workspace)

        return f"MCP server '{server_name}' has been {action_text} successfully."

    def _remove_server(self, workspace: Path, server_name: str) -> str:
        servers = load_mcp_config(workspace)

        if server_name not in servers:
            return f"Error: MCP server '{server_name}' not found"

        del servers[server_name]
        save_mcp_config(servers, workspace)

        return f"MCP server '{server_name}' has been removed successfully."


class RefreshCapabilitiesTool(FinchTool):
    """刷新能力描述文件的工具.

    重新生成 CAPABILITIES.md 文件，反映当前的 MCP 和工具配置。
    """

    name: str = "refresh_capabilities"
    description: str = """Refresh the CAPABILITIES.md file.

This tool regenerates the CAPABILITIES.md file to reflect the current
MCP server configuration and available tools.

Use this after modifying MCP server configuration to update the
capabilities description visible to users.
"""
    workspace: str = Field(default="", exclude=True)

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
        }

    def _run(self) -> str:
        from finchbot.agent.capabilities import write_capabilities_md
        from finchbot.config import load_config

        workspace = Path(self.workspace) if self.workspace else Path.cwd()
        config = load_config()

        mcp_servers = load_mcp_config(workspace)
        if mcp_servers:
            config.mcp.servers = mcp_servers

        try:
            file_path = write_capabilities_md(workspace, config)
            if file_path:
                return f"CAPABILITIES.md has been refreshed at: {file_path}"
            else:
                return "Failed to refresh CAPABILITIES.md"
        except Exception as e:
            return f"Error refreshing CAPABILITIES.md: {str(e)}"


class GetCapabilitiesTool(FinchTool):
    """获取当前能力描述的工具.

    返回当前配置的 MCP 服务器和可用工具的能力描述。
    """

    name: str = "get_capabilities"
    description: str = """Get the current capabilities description.

Returns a summary of currently configured MCP servers and available tools.
Use this to understand what capabilities are currently available.
"""
    workspace: str = Field(default="", exclude=True)

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
        }

    def _run(self) -> str:
        from finchbot.agent.capabilities import CapabilitiesBuilder
        from finchbot.config import load_config

        workspace = Path(self.workspace) if self.workspace else Path.cwd()
        config = load_config()

        mcp_servers = load_mcp_config(workspace)
        if mcp_servers:
            config.mcp.servers = mcp_servers

        try:
            builder = CapabilitiesBuilder(config)
            capabilities = builder.build_capabilities_prompt()
            return capabilities
        except Exception as e:
            return f"Error getting capabilities: {str(e)}"


class GetMCPConfigPathTool(FinchTool):
    """获取 MCP 配置文件路径的工具.

    返回工作区中 MCP 配置文件的路径。
    """

    name: str = "get_mcp_config_path"
    description: str = """Get the path to the MCP configuration file.

Returns the path where MCP server configuration is stored.
Users can manually edit this file to configure MCP servers.
"""
    workspace: str = Field(default="", exclude=True)

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
        }

    def _run(self) -> str:
        workspace = Path(self.workspace) if self.workspace else Path.cwd()
        mcp_path = get_mcp_config_path(workspace)

        result = f"MCP configuration file path: {mcp_path}\n\n"
        result += "You can manually edit this file to configure MCP servers.\n"
        result += "Format:\n"
        result += json.dumps(
            {
                "servers": {
                    "server-name": {
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-example"],
                        "env": {"API_KEY": "your-api-key"},
                    }
                }
            },
            indent=2,
        )

        return result
