"""Agent 配置工具.

提供 Agent 自配置能力，包括 MCP 服务器配置和能力描述刷新。
从 tools/config_tools.py 迁移，保留完整功能。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

from loguru import logger
from pydantic import Field

from finchbot.config.loader import load_mcp_config, save_mcp_config
from finchbot.config.schema import MCPServerConfig
from finchbot.tools.decorator import ToolCategory, tool
from finchbot.workspace import get_mcp_config_path

_workspace: Path | None = None


def configure_config_tools(workspace: Path) -> None:
    """配置配置工具参数.

    Args:
        workspace: 工作目录
    """
    global _workspace
    _workspace = workspace


def _get_workspace() -> Path:
    """获取工作目录."""
    return _workspace or Path.cwd()


async def _trigger_mcp_hot_reload(workspace: Path) -> bool:
    """触发 MCP 热更新.

    尝试调用 MCPHotUpdateManager 执行实际的热更新。
    同时更新 middleware 的动态工具列表。

    Args:
        workspace: 工作目录

    Returns:
        是否成功触发热更新
    """
    try:
        from finchbot.tools.mcp.hot_update import MCPHotUpdateManager

        mcp_manager = MCPHotUpdateManager.get_instance()
        if mcp_manager:
            logger.info("触发 MCP 热更新...")
            new_tools = await mcp_manager.hot_reload()
            logger.info(f"MCP 热更新完成: {len(new_tools)} 个工具")

            from finchbot.tools.middleware import get_mcp_middleware

            middleware = get_mcp_middleware()
            if middleware and new_tools:
                middleware._dynamic_tools = new_tools
                logger.info(f"已更新 middleware 动态工具列表: {len(new_tools)} 个工具")

            return True
        else:
            logger.debug("MCPHotUpdateManager 实例不存在，跳过热更新")
            return False
    except Exception as e:
        logger.warning(f"MCP 热更新失败: {e}")
        return False


def _trigger_docs_update(workspace: Path) -> None:
    """触发文档更新.

    在 MCP 配置变化后更新 TOOLS.md 和 CAPABILITIES.md。

    Args:
        workspace: 工作目录
    """
    from finchbot.agent.capabilities import write_capabilities_md
    from finchbot.config import load_config
    from finchbot.tools.core import ToolRegistry
    from finchbot.tools.tools_generator import ToolsGenerator

    config = load_config()
    mcp_servers = load_mcp_config(workspace)
    if mcp_servers:
        config.mcp.servers = mcp_servers

    registry = ToolRegistry.get_instance()
    tools = registry.get_tools() if registry else []

    tools_gen = ToolsGenerator(workspace, tools)
    tools_file = tools_gen.write_to_file("TOOLS.md")
    if tools_file:
        logger.debug(f"TOOLS.md updated at: {tools_file}")

    cap_file = write_capabilities_md(workspace, config, tools)
    if cap_file:
        logger.debug(f"CAPABILITIES.md updated at: {cap_file}")


@tool(
    name="configure_mcp",
    description="""Configure MCP servers dynamically.

Actions:
- add: Add a new MCP server
- update: Update an existing MCP server
- remove: Remove an MCP server
- enable: Enable a disabled MCP server
- disable: Disable an MCP server
- list: List all configured MCP servers

For 'add' and 'update' actions, provide:
- server_name: Unique name for the server
- command: The command to run (e.g., 'npx', 'uvx')
- args: List of arguments (optional)
- env: Environment variables dict (optional)
- url: URL for HTTP-based MCP servers (optional)
- headers: HTTP headers dict for authentication etc. (optional)


For 'remove', 'enable', 'disable' actions, provide:
- server_name: Name of the server

For 'list' action, no additional parameters needed.
""",
    category=ToolCategory.CONFIG,
    tags=["config", "mcp"],
)
async def configure_mcp(
    action: Annotated[
        str, Field(description="操作类型: add, update, remove, enable, disable, list")
    ],
    server_name: Annotated[str | None, Field(description="MCP 服务器名称")] = None,
    command: Annotated[str | None, Field(description="运行 MCP 服务器的命令")] = None,
    command_args: Annotated[list[str] | None, Field(description="命令参数")] = None,
    env: Annotated[dict[str, str] | None, Field(description="环境变量")] = None,
    url: Annotated[str | None, Field(description="HTTP MCP 服务器的 URL")] = None,
    headers: Annotated[dict[str, str] | str | None, Field(description="HTTP 请求头（用于认证等），可以是字典或JSON字符串")] = None,

) -> str:
    """配置 MCP 服务器.

    允许 Agent 动态添加、修改或删除 MCP 服务器配置。

    Args:
        action: 操作类型
        server_name: 服务器名称
        command: 命令
        command_args: 参数列表
        env: 环境变量
        url: URL
        headers: HTTP 请求头

    Returns:
        操作结果
    """
    workspace = _get_workspace()

    if action == "list":
        return _list_servers(workspace)

    if not server_name:
        return "Error: server_name is required for this action"

    # 处理 headers 参数类型转换
    converted_headers = None
    if headers is not None:
        if isinstance(headers, str):
            try:
                import json
                converted_headers = json.loads(headers)
                if not isinstance(converted_headers, dict):
                    return f"Error: headers must be a dictionary or JSON object string, got {type(converted_headers).__name__}"
            except json.JSONDecodeError as e:
                return f"Error: Invalid JSON format for headers: {e}"
        elif isinstance(headers, dict):
            converted_headers = headers
        else:
            return f"Error: headers must be a dictionary or JSON string, got {type(headers).__name__}"

    result: str
    needs_reload = False

    if action in ("add", "update"):
        result, needs_reload = _add_or_update_server(
            workspace, server_name, command, command_args, env, url, converted_headers
        )
    elif action == "remove":
        result, needs_reload = _remove_server(workspace, server_name)
    elif action == "enable":
        result, needs_reload = _toggle_server(workspace, server_name, disabled=False)
    elif action == "disable":
        result, needs_reload = _toggle_server(workspace, server_name, disabled=True)
    else:
        return f"Error: Unknown action '{action}'"

    if needs_reload:
        reload_success = await _trigger_mcp_hot_reload(workspace)
        if reload_success:
            result += "\n\nMCP tools have been reloaded."
        else:
            result += "\n\nNote: MCP tools will be reloaded on next model call."

    return result


def _list_servers(workspace: Path) -> str:
    """列出所有 MCP 服务器."""
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
        if config.headers:
            header_keys = ", ".join(config.headers.keys())
            lines.append(f"    headers: {header_keys}")

    return "\n".join(lines)


def _add_or_update_server(
    workspace: Path,
    server_name: str,
    command: str | None,
    command_args: list[str] | None,
    env: dict[str, str] | None,
    url: str | None,
    headers: dict[str, str] | None,
) -> tuple[str, bool]:
    """添加或更新 MCP 服务器.

    Args:
        workspace: 工作目录
        server_name: 服务器名称
        command: 命令
        command_args: 参数列表
        env: 环境变量
        url: URL
        headers: HTTP 请求头

    Returns:
        (结果消息, 是否需要热更新) 元组
    """
    servers = load_mcp_config(workspace)

    if server_name in servers:
        existing = servers[server_name]
        new_config = MCPServerConfig(
            command=command or existing.command,
            args=command_args if command_args is not None else existing.args,
            env={**(existing.env or {}), **(env or {})} if env or existing.env else None,
            url=url or existing.url,
            headers=headers if headers is not None else existing.headers,
            disabled=existing.disabled,
        )
        servers[server_name] = new_config
        action_text = "updated"
    else:
        if not command and not url:
            return "Error: Either 'command' or 'url' is required for adding a new server", False

        config_kwargs = {}
        if command:
            config_kwargs["command"] = command
        if command_args:
            config_kwargs["args"] = command_args
        if env:
            config_kwargs["env"] = env
        if url:
            config_kwargs["url"] = url
        if headers:
            config_kwargs["headers"] = headers

        servers[server_name] = MCPServerConfig(**config_kwargs)
        action_text = "added"

    save_mcp_config(servers, workspace)
    _trigger_docs_update(workspace)

    return f"MCP server '{server_name}' has been {action_text} successfully.", True


def _remove_server(workspace: Path, server_name: str) -> tuple[str, bool]:
    """删除 MCP 服务器.

    Args:
        workspace: 工作目录
        server_name: 服务器名称

    Returns:
        (结果消息, 是否需要热更新) 元组
    """
    servers = load_mcp_config(workspace)

    if server_name not in servers:
        return f"Error: MCP server '{server_name}' not found", False

    del servers[server_name]
    save_mcp_config(servers, workspace)
    _trigger_docs_update(workspace)

    return f"MCP server '{server_name}' has been removed successfully.", True


def _toggle_server(workspace: Path, server_name: str, disabled: bool) -> tuple[str, bool]:
    """启用/禁用 MCP 服务器.

    Args:
        workspace: 工作目录
        server_name: 服务器名称
        disabled: 是否禁用

    Returns:
        (结果消息, 是否需要热更新) 元组
    """
    servers = load_mcp_config(workspace)

    if server_name not in servers:
        return f"Error: MCP server '{server_name}' not found", False

    existing = servers[server_name]
    servers[server_name] = MCPServerConfig(
        command=existing.command,
        args=existing.args,
        env=existing.env,
        url=existing.url,
        headers=existing.headers,
        disabled=disabled,
    )
    save_mcp_config(servers, workspace)
    _trigger_docs_update(workspace)

    status = "disabled" if disabled else "enabled"
    return f"MCP server '{server_name}' has been {status} successfully.", True


@tool(
    name="refresh_capabilities",
    description="""Refresh the CAPABILITIES.md file.

This tool regenerates the CAPABILITIES.md file to reflect the current
MCP server configuration and available tools.

Use this after modifying MCP server configuration to update the
capabilities description visible to users.
""",
    category=ToolCategory.CONFIG,
    tags=["config", "capabilities"],
)
async def refresh_capabilities() -> str:
    """刷新能力描述文件.

    重新生成 CAPABILITIES.md 文件，反映当前的 MCP 和工具配置。

    Returns:
        操作结果
    """
    from finchbot.agent.capabilities import write_capabilities_md
    from finchbot.config import load_config

    workspace = _get_workspace()
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


@tool(
    name="get_capabilities",
    description="""Get the current capabilities description.

Returns a summary of currently configured MCP servers and available tools.
Use this to understand what capabilities are currently available.
""",
    category=ToolCategory.CONFIG,
    tags=["config", "capabilities"],
)
async def get_capabilities() -> str:
    """获取当前能力描述.

    返回当前配置的 MCP 服务器和可用工具的能力描述。

    Returns:
        能力描述字符串
    """
    from finchbot.agent.capabilities import CapabilitiesBuilder
    from finchbot.config import load_config

    workspace = _get_workspace()
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


@tool(
    name="get_mcp_status",
    description="""Get the current MCP connection status.

Returns information about MCP servers connection state and loaded tools.
Use this to diagnose MCP connection issues.
""",
    category=ToolCategory.CONFIG,
    tags=["config", "mcp", "diagnostics"],
)
async def get_mcp_status() -> str:
    """获取 MCP 连接状态.

    返回 MCP 服务器的连接状态和已加载的工具信息。

    Returns:
        MCP 状态信息
    """
    workspace = _get_workspace()

    lines = ["## MCP Status\n"]

    servers = load_mcp_config(workspace)
    if not servers:
        lines.append("No MCP servers configured.")
        return "\n".join(lines)

    enabled_count = sum(1 for s in servers.values() if not s.disabled)
    lines.append(f"Configured servers: {len(servers)} ({enabled_count} enabled)\n")

    for name, config in servers.items():
        status = "❌ disabled" if config.disabled else "✅ enabled"
        lines.append(f"### {name} ({status})")
        if config.command:
            cmd_str = f"{config.command} {' '.join(config.args or [])}"
            lines.append(f"- Command: `{cmd_str}`")
        if config.url:
            lines.append(f"- URL: {config.url}")
        if config.headers:
            header_keys = ", ".join(config.headers.keys())
            lines.append(f"- Headers: {header_keys}")
        lines.append("")

    from finchbot.tools.mcp.hot_update import MCPHotUpdateManager

    mcp_manager = MCPHotUpdateManager.get_instance()
    if mcp_manager:
        status = mcp_manager.get_mcp_status()
        lines.append("### Connection Status")
        lines.append(f"- Connected: {status.get('connected', False)}")
        lines.append(f"- Tools loaded: {status.get('tools_count', 0)}")
        lines.append(f"- Pending update: {status.get('pending_update', False)}")
    else:
        lines.append("### Connection Status")
        lines.append("- MCPHotUpdateManager not initialized")

    return "\n".join(lines)


@tool(
    name="get_mcp_config_path",
    description="""Get the path to the MCP configuration file.

Returns the path where MCP server configuration is stored.
Users can manually edit this file to configure MCP servers.
""",
    category=ToolCategory.CONFIG,
    tags=["config", "mcp"],
)
async def get_mcp_config_path_tool() -> str:
    """获取 MCP 配置文件路径.

    返回工作区中 MCP 配置文件的路径。

    Returns:
        配置文件路径信息
    """
    workspace = _get_workspace()
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
                },
                "server-name2": {
                    "url": "https://server-example/mcp",
                    "env": {"API_KEY": "your-api-key"},
                    "headers": {"Authorization": "Bearer your-token"},
                }
            }
        },
        indent=2,
    )

    return result


@tool(
    name="get_mcp_tools",
    description="""Get all loaded MCP tools with detailed descriptions.

Returns a list of all MCP tools currently loaded, including:
- Tool names and descriptions
- Required and optional parameters
- Which MCP server each tool belongs to

Use this to understand what MCP tools are available and how to use them.
""",
    category=ToolCategory.CONFIG,
    tags=["config", "mcp", "tools"],
)
async def get_mcp_tools() -> str:
    """获取所有已加载的 MCP 工具列表.

    返回所有已加载的 MCP 工具及其详细描述和参数说明。

    Returns:
        MCP 工具列表信息
    """
    from finchbot.tools.core import ToolRegistry

    workspace = _get_workspace()
    registry = ToolRegistry.get_instance()

    if not registry:
        return "Tool registry not initialized."

    mcp_tools = registry.get_tools_by_source("mcp")

    if not mcp_tools:
        return "No MCP tools are currently loaded.\n\nUse configure_mcp to add MCP servers."

    lines = ["## Loaded MCP Tools\n"]
    lines.append(f"Total: {len(mcp_tools)} tools\n")

    by_server: dict[str, list] = {}
    for tool in mcp_tools:
        server = getattr(tool, "_mcp_server_name", "unknown")
        if server not in by_server:
            by_server[server] = []
        by_server[server].append(tool)

    for server_name, server_tools in sorted(by_server.items()):
        lines.append(f"### {server_name} ({len(server_tools)} tools)\n")

        for tool in server_tools:
            desc = tool.description[:150] + "..." if len(tool.description) > 150 else tool.description
            lines.append(f"#### {tool.name}\n")
            lines.append(f"{desc}\n")

            params = _get_tool_params(tool)
            if params:
                lines.append("**Parameters:**\n")
                for name, info in params.items():
                    required = " (required)" if info.get("required") else " (optional)"
                    desc_text = info.get("description", "")
                    lines.append(f"- `{name}`{required}: {desc_text}\n")
            else:
                lines.append("No parameters required.\n")

            lines.append("")

    return "\n".join(lines)


def _get_tool_params(tool) -> dict:
    """获取工具参数.

    Args:
        tool: 工具实例

    Returns:
        参数字典
    """
    params = {}

    if hasattr(tool, "parameters") and tool.parameters:
        props = tool.parameters.get("properties", {})
        required = tool.parameters.get("required", [])
        for name, info in props.items():
            params[name] = {
                "description": info.get("description", ""),
                "required": name in required,
            }

    if not params and hasattr(tool, "args_schema"):
        try:
            schema = tool.args_schema.schema()
            props = schema.get("properties", {})
            required = schema.get("required", [])
            for name, info in props.items():
                params[name] = {
                    "description": info.get("description", ""),
                    "required": name in required,
                }
        except Exception:
            pass

    return params
