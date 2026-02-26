"""工具信息自动生成器.

扫描工具模块，自动生成 TOOLS.md 文件。
支持从 ToolRegistry 动态发现工具。
支持外部工具列表（如 MCP 工具）。
"""

from collections.abc import Sequence
from pathlib import Path

from langchain_core.tools import BaseTool

from finchbot.i18n import t
from finchbot.tools.registry import get_global_registry


class ToolsGenerator:
    """工具信息自动生成器.

    支持从 ToolRegistry 或外部工具列表生成工具文档。
    自动识别 MCP 工具并单独分类。
    """

    def __init__(
        self,
        workspace: Path | None = None,
        tools: Sequence[BaseTool] | None = None,
    ) -> None:
        """初始化工具生成器.

        Args:
            workspace: 工作目录路径（可选，仅用于写入文件时）。
            tools: 可选的外部工具列表（如 MCP 工具），优先于注册表。
        """
        self.workspace = workspace
        self.registry = get_global_registry()
        self._external_tools = list(tools) if tools else None

    def generate_tools_content(self) -> str:
        """生成工具文档内容（不写入文件）.

        优先使用外部工具列表，否则从 ToolRegistry 获取。

        Returns:
            TOOLS.md 内容字符串。
        """
        lines = [f"# {t('agent.available_tools')}\n"]

        # 获取工具列表
        if self._external_tools is not None:
            tools = self._external_tools
        else:
            tools = [self.registry.get(name) for name in self.registry.tool_names]
            tools = [t for t in tools if t is not None]

        if not tools:
            lines.append(t("agent.no_tools_available"))
            return "\n".join(lines)

        # 按类别分组工具
        tools_by_category = self._categorize_tools(tools)

        # 生成每个类别的工具文档
        for category, category_tools in tools_by_category.items():
            lines.append(f"## {category}")
            lines.append("")

            for tool in category_tools:
                lines.append(f"### {tool.name}")
                lines.append("")

                # 获取描述
                description = self._get_tool_description(tool)
                lines.append(description)
                lines.append("")

                # 参数说明
                params = self._get_tool_parameters(tool)
                if params:
                    lines.append("**参数:**")
                    lines.append("")
                    for param_name, param_info in params.items():
                        required_mark = " (必填)" if param_info.get("required") else ""
                        param_desc = param_info.get("description", "")
                        lines.append(f"- `{param_name}`{required_mark}: {param_desc}")
                    lines.append("")

                lines.append("---")
                lines.append("")

        content = "\n".join(lines)
        return content

    def write_to_file(self, filename: str = "TOOLS.md") -> Path | None:
        """将工具文档写入文件.

        Args:
            filename: 文件名，默认为 TOOLS.md。

        Returns:
            写入的文件路径，如果 workspace 未设置则返回 None。
        """
        if not self.workspace:
            return None

        content = self.generate_tools_content()
        file_path = self.workspace / filename

        try:
            file_path.write_text(content, encoding="utf-8")
            return file_path
        except Exception:
            return None

    def _categorize_tools(self, tools: list[BaseTool]) -> dict[str, list[BaseTool]]:
        """将工具按类别分组.

        Args:
            tools: 工具列表。

        Returns:
            按类别分组的工具字典。
        """
        tools_by_category = {
            t("tools.categories.file_ops"): [],
            t("tools.categories.sys_cmd"): [],
            t("tools.categories.net_tools"): [],
            t("tools.categories.mem_mgmt"): [],
            t("tools.categories.session_mgmt"): [],
            t("tools.categories.mcp"): [],  # 新增 MCP 工具分类
            t("tools.categories.others"): [],
        }

        for tool in tools:
            # 先检查是否是 MCP 工具
            if self._is_mcp_tool(tool):
                tools_by_category[t("tools.categories.mcp")].append(tool)
            else:
                # 根据工具名称或描述确定类别
                category = self._determine_category(tool)
                tools_by_category[category].append(tool)

        # 移除空类别
        return {k: v for k, v in tools_by_category.items() if v}

    def _is_mcp_tool(self, tool: BaseTool) -> bool:
        """判断工具是否是 MCP 工具.

        Args:
            tool: 工具实例。

        Returns:
            是否是 MCP 工具。
        """
        tool_name = tool.name.lower()
        tool_module = type(tool).__module__.lower()

        # 方法1: 检查工具名称是否包含 mcp 前缀
        if tool_name.startswith("mcp_"):
            return True

        # 方法2: 检查工具是否有 MCP 相关属性
        if hasattr(tool, "_mcp_server_name"):
            return True

        # 方法3: 检查工具模块是否来自 mcp 相关包
        if "mcp" in tool_module or "langchain_mcp" in tool_module:
            return True

        return False

    def _determine_category(self, tool: BaseTool) -> str:
        """确定工具类别.

        Args:
            tool: 工具实例。

        Returns:
            工具类别名称。
        """
        tool_name = tool.name.lower()
        tool_desc = (self._get_tool_description(tool)).lower()

        # 文件操作工具
        file_keywords = ["file", "read", "write", "edit", "list", "dir", "directory"]
        if any(keyword in tool_name for keyword in file_keywords) or any(
            keyword in tool_desc for keyword in file_keywords
        ):
            return t("tools.categories.file_ops")

        # 系统命令工具
        sys_keywords = ["exec", "shell", "command", "run", "execute"]
        if any(keyword in tool_name for keyword in sys_keywords) or any(
            keyword in tool_desc for keyword in sys_keywords
        ):
            return t("tools.categories.sys_cmd")

        # 网络工具
        web_keywords = ["web", "search", "fetch", "extract", "http", "url"]
        if any(keyword in tool_name for keyword in web_keywords) or any(
            keyword in tool_desc for keyword in web_keywords
        ):
            return t("tools.categories.net_tools")

        # 记忆管理工具
        memory_keywords = ["memory", "remember", "recall", "forget", "store"]
        if any(keyword in tool_name for keyword in memory_keywords) or any(
            keyword in tool_desc for keyword in memory_keywords
        ):
            return t("tools.categories.mem_mgmt")

        # 会话管理工具
        session_keywords = ["session", "title", "chat", "conversation"]
        if any(keyword in tool_name for keyword in session_keywords) or any(
            keyword in tool_desc for keyword in session_keywords
        ):
            return t("tools.categories.session_mgmt")

        return t("tools.categories.others")

    def _get_tool_description(self, tool: BaseTool) -> str:
        """获取工具描述.

        Args:
            tool: 工具实例。

        Returns:
            工具描述。
        """
        # 尝试多种方式获取描述
        desc = getattr(tool, "description", "")
        if not desc:
            desc = getattr(tool, "_description", "")
        if not desc:
            desc = t("tools.categories.no_description")

        # 如果是 MCP 工具，添加来源标识
        if self._is_mcp_tool(tool):
            server_name = self._get_mcp_server_name(tool)
            if server_name:
                desc = f"[MCP: {server_name}] {desc}"

        return desc

    def _get_tool_parameters(self, tool: BaseTool) -> dict:
        """获取工具参数.

        Args:
            tool: 工具实例。

        Returns:
            参数字典。
        """
        params = {}

        # 方法1: 从 parameters 属性获取
        if hasattr(tool, "parameters") and tool.parameters:
            props = tool.parameters.get("properties", {})
            required = tool.parameters.get("required", [])
            for name, info in props.items():
                params[name] = {
                    "description": info.get("description", ""),
                    "required": name in required,
                }

        # 方法2: 从 args_schema 获取 (LangChain 工具)
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

    def _get_mcp_server_name(self, tool: BaseTool) -> str | None:
        """获取 MCP 工具的服务器名称.

        Args:
            tool: 工具实例。

        Returns:
            服务器名称，如果不是 MCP 工具则返回 None。
        """
        if not self._is_mcp_tool(tool):
            return None

        # 方法1: 从属性获取
        if hasattr(tool, "_mcp_server_name"):
            return tool._mcp_server_name

        # 方法2: 从名称解析 (格式: mcp_servername_toolname)
        if tool.name.startswith("mcp_"):
            parts = tool.name.split("_")
            if len(parts) >= 2:
                return parts[1]

        return "unknown"
