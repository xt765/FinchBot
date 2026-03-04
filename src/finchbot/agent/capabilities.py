"""FinchBot 智能体能力构建器.

统一管理智能体的能力信息注入，包括 MCP、Channel、技能等。
让智能体"知道"自己有哪些能力，以及如何扩展这些能力。
支持新的目录结构（generated/ 目录）。
"""

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from langchain_core.tools import BaseTool

from finchbot.workspace import get_capabilities_path

if TYPE_CHECKING:
    from finchbot.config.schema import Config


class CapabilitiesBuilder:
    """智能体能力构建器.

    负责构建智能体能力相关的系统提示词，包括：
    - MCP 服务器配置状态
    - Channel 配置状态
    - 扩展指南
    """

    def __init__(self, config: "Config", tools: Sequence[BaseTool] | None = None) -> None:
        """初始化能力构建器.

        Args:
            config: FinchBot 配置对象.
            tools: 可选的工具列表（用于判断 MCP 工具数量）.
        """
        self.config = config
        self.tools = list(tools) if tools else []

    def build_capabilities_prompt(self) -> str:
        """构建完整的能力说明提示词.

        Returns:
            能力说明字符串.
        """
        parts = []

        mcp_section = self._build_mcp_server_status()
        if mcp_section:
            parts.append(mcp_section)

        mcp_tools_section = self._build_mcp_tools_section()
        if mcp_tools_section:
            parts.append(mcp_tools_section)

        channel_section = self._build_channel_section()
        if channel_section:
            parts.append(channel_section)

        extension_guide = self._build_extension_guide()
        if extension_guide:
            parts.append(extension_guide)

        return "\n\n---\n\n".join(parts)

    def _build_mcp_tools_section(self) -> str:
        """构建 MCP 工具列表.

        Returns:
            MCP 工具列表字符串.
        """
        mcp_tools = [t for t in self.tools if self._is_mcp_tool(t)]

        if not mcp_tools:
            return ""

        lines = ["## MCP 工具\n"]
        lines.append(f"已加载 {len(mcp_tools)} 个 MCP 工具：\n")

        by_server: dict[str, list[BaseTool]] = {}
        for tool in mcp_tools:
            server_name = getattr(tool, "_mcp_server_name", "unknown")
            if server_name not in by_server:
                by_server[server_name] = []
            by_server[server_name].append(tool)

        for server_name, server_tools in by_server.items():
            lines.append(f"### {server_name}\n")
            for tool in server_tools:
                desc = tool.description[:100] + "..." if len(tool.description) > 100 else tool.description
                lines.append(f"- **{tool.name}**: {desc}")

                params = self._get_tool_params(tool)
                if params:
                    param_strs = []
                    for name, info in params.items():
                        required = " (必填)" if info.get("required") else ""
                        param_strs.append(f"`{name}`{required}")
                    lines.append(f"  参数: {', '.join(param_strs)}")
            lines.append("")

        return "\n".join(lines)

    def _is_mcp_tool(self, tool: BaseTool) -> bool:
        """判断工具是否是 MCP 工具.

        Args:
            tool: 工具实例

        Returns:
            是否是 MCP 工具
        """
        tool_name = tool.name.lower()
        tool_module = type(tool).__module__.lower()

        if tool_name.startswith("mcp_"):
            return True

        if hasattr(tool, "_mcp_server_name"):
            return True

        return "mcp" in tool_module or "langchain_mcp" in tool_module

    def _get_tool_params(self, tool: BaseTool) -> dict:
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

    def _build_mcp_server_status(self) -> str:
        """构建 MCP 服务器状态（不含工具列表）.

        Returns:
            MCP 服务器状态字符串.
        """
        lines = ["## MCP 服务器\n"]

        if self.config.mcp.servers:
            enabled_count = sum(1 for s in self.config.mcp.servers.values() if not s.disabled)
            total_count = len(self.config.mcp.servers)
            lines.append(f"已配置 {enabled_count}/{total_count} 个服务器：\n")

            for name, server in self.config.mcp.servers.items():
                status = "已禁用" if server.disabled else "已启用"
                transport = "HTTP" if server.url else "stdio"
                lines.append(f"- **{name}** ({transport}, {status})")
            lines.append("")
        else:
            lines.append("暂未配置 MCP 服务器。\n")

        return "\n".join(lines)

    def _build_channel_section(self) -> str:
        """构建 Channel 配置和能力说明.

        Returns:
            Channel 相关提示词.
        """
        lines = ["## Channel 配置\n"]

        if self.config.channels.langbot_enabled:
            lines.append("LangBot 集成已启用。")
            lines.append("")
            lines.append(f"**LangBot URL:** {self.config.channels.langbot_url}")
            lines.append("")
        else:
            lines.append("LangBot 集成未启用。")
            lines.append("")
            lines.append(
                "如需启用 LangBot 集成，请在配置文件中设置 `channels.langbot_enabled = true`。"
            )
            lines.append("")

        return "\n".join(lines)

    def _build_extension_guide(self) -> str:
        """构建扩展指南.

        Returns:
            扩展指南字符串.
        """
        lines = ["## 扩展指南\n"]

        # 添加 MCP
        lines.append("### 添加 MCP 服务器\n")
        lines.append("使用 `configure_mcp` 工具添加 MCP 服务器：\n")
        lines.append("```")
        lines.append(
            'configure_mcp action=add server_name=github command=npx args=\'["-y", "@modelcontextprotocol/server-github"]\''
        )
        lines.append("```\n")

        # 环境变量
        lines.append("**环境变量配置（推荐）**\n")
        lines.append("MCP 服务器需要的 API Key 等敏感信息，建议通过环境变量配置：\n")
        lines.append("```bash")
        lines.append("# GitHub MCP")
        lines.append("export FINCHBOT_MCP_GITHUB_TOKEN=ghp_...")
        lines.append("")
        lines.append("# Brave Search MCP")
        lines.append("export FINCHBOT_MCP_BRAVE_API_KEY=...")
        lines.append("```\n")

        # 添加技能
        lines.append("### 添加技能\n")
        lines.append("在 `~/.finchbot/skills/` 目录下创建 Python 文件，定义自定义工具。")
        lines.append("工具会自动被发现并注册。\n")

        # 刷新能力
        lines.append("### 刷新能力\n")
        lines.append("使用 `refresh_capabilities` 工具刷新能力描述，更新 MCP 工具列表。\n")

        return "\n".join(lines)

    def get_mcp_server_count(self) -> int:
        """获取已配置的 MCP 服务器数量.

        Returns:
            服务器数量.
        """
        return len([s for s in self.config.mcp.servers.values() if not s.disabled])


def build_capabilities_prompt(
    config: "Config",
    tools: Sequence[BaseTool] | None = None,
) -> str:
    """构建能力说明提示词的便捷函数.

    Args:
        config: FinchBot 配置对象.
        tools: 可选的工具列表.

    Returns:
        能力说明字符串.
    """
    builder = CapabilitiesBuilder(config, tools)
    return builder.build_capabilities_prompt()


def write_capabilities_md(
    workspace: Path,
    config: "Config",
    tools: Sequence[BaseTool] | None = None,
) -> Path | None:
    """生成 CAPABILITIES.md 文件.

    写入到 generated/ 目录。

    Args:
        workspace: 工作区路径.
        config: FinchBot 配置对象.
        tools: 可选的工具列表.

    Returns:
        写入的文件路径.
    """
    builder = CapabilitiesBuilder(config, tools)
    content = builder.build_capabilities_prompt()

    if not content:
        return None

    file_path = get_capabilities_path(workspace)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        file_path.write_text(content, encoding="utf-8")
        return file_path
    except Exception:
        return None
