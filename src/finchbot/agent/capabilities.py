"""FinchBot 智能体能力构建器.

统一管理智能体的能力信息注入，包括 MCP、Channel、技能等。
让智能体"知道"自己有哪些能力，以及如何扩展这些能力。
支持新的目录结构（generated/ 目录）。
"""

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from langchain_core.tools import BaseTool

from finchbot.i18n import t
from finchbot.workspace import get_capabilities_path

if TYPE_CHECKING:
    from finchbot.config.schema import Config


class CapabilitiesBuilder:
    """智能体能力构建器.

    负责构建智能体能力相关的系统提示词，包括：
    - MCP 服务器配置信息
    - MCP 工具列表
    - Channel 配置状态
    - 扩展指南
    """

    def __init__(self, config: "Config", tools: Sequence[BaseTool] | None = None) -> None:
        """初始化能力构建器.

        Args:
            config: FinchBot 配置对象.
            tools: 可选的工具列表（包含 MCP 工具）.
        """
        self.config = config
        self.tools = list(tools) if tools else []

    def build_capabilities_prompt(self) -> str:
        """构建完整的能力说明提示词.

        Returns:
            能力说明字符串.
        """
        parts = []

        # 1. MCP 配置和能力
        mcp_section = self._build_mcp_section()
        if mcp_section:
            parts.append(mcp_section)

        # 2. Channel 配置和能力
        channel_section = self._build_channel_section()
        if channel_section:
            parts.append(channel_section)

        # 3. 扩展指南
        extension_guide = self._build_extension_guide()
        if extension_guide:
            parts.append(extension_guide)

        return "\n\n---\n\n".join(parts)

    def _build_mcp_section(self) -> str:
        """构建 MCP 配置和能力说明.

        Returns:
            MCP 相关提示词.
        """
        lines = []

        # MCP 服务器配置信息
        if self.config.mcp.servers:
            lines.append(f"## {t('capabilities.mcp.title')}\n")
            lines.append(f"{t('capabilities.mcp.configured_servers')}\n")

            for name, server in self.config.mcp.servers.items():
                status = t("capabilities.status.disabled") if server.disabled else t("capabilities.status.enabled")
                if server.url:
                    transport = "HTTP"
                else:
                    transport = "stdio"
                lines.append(f"- **{name}** ({transport}, {status})")

            lines.append("")

        # MCP 工具列表
        mcp_tools = self._get_mcp_tools()
        if mcp_tools:
            lines.append(f"### {t('capabilities.mcp.available_tools')}\n")
            lines.append(f"{t('capabilities.mcp.tools_intro')}\n")

            # 按服务器分组
            tools_by_server: dict[str, list[BaseTool]] = {}
            for tool in mcp_tools:
                server_name = self._get_tool_server_name(tool)
                if server_name not in tools_by_server:
                    tools_by_server[server_name] = []
                tools_by_server[server_name].append(tool)

            for server_name, tools in tools_by_server.items():
                lines.append(f"**{server_name}:**")
                for tool in tools:
                    desc = self._get_tool_description(tool)
                    lines.append(f"  - `{tool.name}`: {desc}")
                lines.append("")

        # 如何新增 MCP
        lines.append(f"### {t('capabilities.mcp.how_to_add')}\n")
        lines.append(t("capabilities.mcp.add_steps"))

        return "\n".join(lines) if lines else ""

    def _build_channel_section(self) -> str:
        """构建 Channel 配置和能力说明.

        Returns:
            Channel 相关提示词.
        """
        lines = [f"## {t('capabilities.channel.title')}\n"]

        if self.config.channels.langbot_enabled:
            lines.append(t("capabilities.channel.langbot_enabled"))
            lines.append("")
            lines.append(f"**LangBot URL:** {self.config.channels.langbot_url}")
            lines.append("")
        else:
            lines.append(t("capabilities.channel.langbot_migration"))
            lines.append("")
            lines.append(t("capabilities.channel.langbot_steps"))
            lines.append("")

        return "\n".join(lines)

    def _build_extension_guide(self) -> str:
        """构建扩展指南.

        Returns:
            扩展指南字符串.
        """
        lines = [f"## {t('capabilities.extension.title')}\n"]

        lines.append(f"### {t('capabilities.extension.add_mcp')}\n")
        lines.append(t("capabilities.extension.mcp_steps"))
        lines.append("")
        lines.append(f"**{t('capabilities.extension.mcp_config_location')}**\n")

        lines.append(f"**{t('config.env.title')}（推荐）**\n")
        lines.append(t("config.env.mcp_env_hint"))
        lines.append("\n```bash")
        lines.append("# GitHub MCP")
        lines.append("export FINCHBOT_MCP_GITHUB_TOKEN=ghp_...")
        lines.append("")
        lines.append("# Brave Search MCP")
        lines.append("export FINCHBOT_MCP_BRAVE_API_KEY=...")
        lines.append("```\n")

        lines.append(f"### {t('capabilities.extension.add_skill')}\n")
        lines.append(t("capabilities.extension.skill_steps"))
        lines.append("")

        lines.append(f"### {t('capabilities.extension.refresh_capabilities')}\n")
        lines.append(t("capabilities.extension.refresh_hint"))
        lines.append("")

        lines.append(f"## {t('workspace.title')}\n")
        lines.append(t("workspace.description"))

        return "\n".join(lines)

    def _get_mcp_tools(self) -> list[BaseTool]:
        """获取 MCP 工具列表.

        Returns:
            MCP 工具列表.
        """
        mcp_tools = []
        for tool in self.tools:
            # 检查是否是 MCP 工具
            # langchain-mcp-adapters 加载的工具可能有特定属性
            tool_name = tool.name
            # MCP 工具通常来自配置的服务器
            if self._is_mcp_tool(tool):
                mcp_tools.append(tool)
        return mcp_tools

    def _is_mcp_tool(self, tool: BaseTool) -> bool:
        """判断工具是否是 MCP 工具.

        Args:
            tool: 工具实例.

        Returns:
            是否是 MCP 工具.
        """
        # 方法1: 检查工具名称是否匹配 MCP 服务器前缀
        for server_name in self.config.mcp.servers.keys():
            if tool.name.startswith(f"mcp_{server_name}_"):
                return True

        # 方法2: 检查工具是否有 MCP 相关属性
        if hasattr(tool, "_mcp_server_name"):
            return True

        # 方法3: 检查工具是否来自 langchain_mcp_adapters
        tool_module = type(tool).__module__
        if "mcp" in tool_module.lower():
            return True

        return False

    def _get_tool_server_name(self, tool: BaseTool) -> str:
        """获取工具所属的 MCP 服务器名称.

        Args:
            tool: 工具实例.

        Returns:
            服务器名称.
        """
        # 方法1: 从属性获取
        if hasattr(tool, "_mcp_server_name"):
            return tool._mcp_server_name

        # 方法2: 从名称解析
        for server_name in self.config.mcp.servers.keys():
            prefix = f"mcp_{server_name}_"
            if tool.name.startswith(prefix):
                return server_name

        return "unknown"

    def _get_tool_description(self, tool: BaseTool) -> str:
        """获取工具描述.

        Args:
            tool: 工具实例.

        Returns:
            工具描述.
        """
        desc = getattr(tool, "description", "")
        if not desc:
            desc = t("capabilities.mcp.no_description")
        # 截断过长的描述
        if len(desc) > 100:
            desc = desc[:97] + "..."
        return desc

    def get_mcp_server_count(self) -> int:
        """获取已配置的 MCP 服务器数量.

        Returns:
            服务器数量.
        """
        return len([s for s in self.config.mcp.servers.values() if not s.disabled])

    def get_mcp_tool_count(self) -> int:
        """获取 MCP 工具数量.

        Returns:
            工具数量.
        """
        return len(self._get_mcp_tools())


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
