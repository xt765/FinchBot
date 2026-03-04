"""FinchBot 智能体能力构建器.

统一管理智能体的能力信息注入，包括 MCP、工具等。
让智能体"知道"自己有哪些能力，以及如何扩展这些能力。
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
    - MCP 工具列表
    - 扩展指南
    """

    def __init__(self, config: "Config", tools: Sequence[BaseTool] | None = None) -> None:
        """初始化能力构建器.

        Args:
            config: FinchBot 配置对象.
            tools: 可选的工具列表（用于显示 MCP 工具）.
        """
        self.config = config
        self.tools = list(tools) if tools else []

    def build_capabilities_prompt(self) -> str:
        """构建完整的能力说明提示词.

        Returns:
            能力说明字符串.
        """
        parts = []

        mcp_section = self._build_mcp_section()
        if mcp_section:
            parts.append(mcp_section)

        extension_guide = self._build_extension_guide()
        if extension_guide:
            parts.append(extension_guide)

        return "\n\n---\n\n".join(parts)

    def _build_mcp_section(self) -> str:
        """构建 MCP 服务器和工具信息.

        Returns:
            MCP 相关信息字符串.
        """
        lines = ["## MCP 配置\n"]

        if self.config.mcp.servers:
            enabled_names = [n for n, s in self.config.mcp.servers.items() if not s.disabled]
            disabled_names = [n for n, s in self.config.mcp.servers.items() if s.disabled]

            lines.append(f"已配置 {len(enabled_names)} 个启用的 MCP 服务器：\n")

            for name in enabled_names:
                server = self.config.mcp.servers[name]
                transport = "HTTP" if server.url else "stdio"
                cmd_info = ""
                if server.command:
                    cmd_info = f" `{server.command}`"
                elif server.url:
                    cmd_info = f" `{server.url}`"
                lines.append(f"- **{name}** ({transport}{cmd_info})")

            if disabled_names:
                lines.append(f"\n已禁用: {', '.join(disabled_names)}")

            lines.append("")
        else:
            lines.append("暂未配置 MCP 服务器。\n")

        mcp_tools = [t for t in self.tools if self._is_mcp_tool(t)]
        if mcp_tools:
            lines.append(f"**已加载 {len(mcp_tools)} 个 MCP 工具**\n")
            lines.append("使用 `get_mcp_tools` 工具查看详细的工具列表和参数说明。\n")

        return "\n".join(lines)

    def _build_extension_guide(self) -> str:
        """构建扩展指南.

        Returns:
            扩展指南字符串.
        """
        lines = ["## 扩展能力\n"]

        lines.append("### MCP 服务器管理\n")
        lines.append("使用 `configure_mcp` 工具管理 MCP 服务器：\n")
        lines.append("```")
        lines.append("# 添加服务器")
        lines.append(
            'configure_mcp action=add server_name=github command=npx args=\'["-y", "@modelcontextprotocol/server-github"]\''
        )
        lines.append("")
        lines.append("# 列出所有服务器")
        lines.append("configure_mcp action=list")
        lines.append("")
        lines.append("# 禁用/启用服务器")
        lines.append("configure_mcp action=disable server_name=github")
        lines.append("configure_mcp action=enable server_name=github")
        lines.append("")
        lines.append("# 删除服务器")
        lines.append("configure_mcp action=remove server_name=github")
        lines.append("```\n")

        lines.append("### 环境变量配置\n")
        lines.append("MCP 服务器的 API Key 等敏感信息通过环境变量配置：\n")
        lines.append("```bash")
        lines.append("export FINCHBOT_MCP_GITHUB_TOKEN=ghp_...")
        lines.append("export FINCHBOT_MCP_BRAVE_API_KEY=...")
        lines.append("```\n")

        lines.append("### 诊断工具\n")
        lines.append("- `get_mcp_status`: 查看 MCP 连接状态和诊断信息")
        lines.append("- `get_mcp_tools`: 获取所有 MCP 工具的详细参数说明")
        lines.append("- `refresh_capabilities`: 刷新能力描述文件\n")

        lines.append("### 自定义技能\n")
        lines.append("在 `~/.finchbot/skills/` 目录下创建 Python 文件，定义自定义工具。")
        lines.append("工具会自动被发现并注册。\n")

        return "\n".join(lines)

    def _is_mcp_tool(self, tool: BaseTool) -> bool:
        """判断工具是否是 MCP 工具.

        Args:
            tool: 工具实例

        Returns:
            是否是 MCP 工具
        """
        if hasattr(tool, "_mcp_server_name"):
            return True

        tool_name = tool.name.lower()
        if tool_name.startswith("mcp_"):
            return True

        tool_module = type(tool).__module__.lower()
        return "mcp" in tool_module or "langchain_mcp" in tool_module

    def get_mcp_server_count(self) -> int:
        """获取已启用的 MCP 服务器数量.

        Returns:
            服务器数量.
        """
        return len([s for s in self.config.mcp.servers.values() if not s.disabled])

    def get_mcp_tool_count(self) -> int:
        """获取已加载的 MCP 工具数量.

        Returns:
            工具数量.
        """
        return len([t for t in self.tools if self._is_mcp_tool(t)])


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
