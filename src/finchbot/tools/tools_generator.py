"""工具信息自动生成器.

扫描工具模块，自动生成 TOOLS.md 文件。
支持从 ToolRegistry 动态发现工具。
"""

from pathlib import Path

from finchbot.tools.registry import get_global_registry


class ToolsGenerator:
    """工具信息自动生成器."""

    def __init__(self, workspace: Path | None = None) -> None:
        """初始化工具生成器.

        Args:
            workspace: 工作目录路径（可选，仅用于写入文件时）。
        """
        self.workspace = workspace
        self.registry = get_global_registry()

    def generate_tools_content(self) -> str:
        """生成工具文档内容（不写入文件）.

        从 ToolRegistry 动态发现所有已注册工具。

        Returns:
            TOOLS.md 内容字符串。
        """
        lines = ["# 可用工具\n"]

        # 获取所有已注册工具
        tool_names = self.registry.tool_names
        if not tool_names:
            lines.append("当前没有可用的工具。")
            return "\n".join(lines)

        # 按类别分组工具
        tools_by_category = self._categorize_tools()

        # 生成每个类别的工具文档
        for category, tools in tools_by_category.items():
            lines.append(f"## {category}")
            lines.append("")

            for tool in tools:
                lines.append(f"### {tool.name}")
                lines.append("")
                lines.append(tool.description)
                lines.append("")

                if hasattr(tool, "parameters") and tool.parameters:
                    params = tool.parameters.get("properties", {})
                    required = tool.parameters.get("required", [])

                    if params:
                        lines.append("**参数:**")
                        lines.append("")
                        for param_name, param_info in params.items():
                            required_mark = " (必填)" if param_name in required else ""
                            param_desc = param_info.get("description", "")
                            lines.append(f"- `{param_name}`{required_mark}: {param_desc}")
                        lines.append("")

                lines.append("---")
                lines.append("")

        content = "\n".join(lines)
        return content

    def _categorize_tools(self) -> dict[str, list]:
        """将工具按类别分组.

        Returns:
            按类别分组的工具字典。
        """
        tools_by_category = {
            "文件操作": [],
            "系统命令": [],
            "网络工具": [],
            "记忆管理": [],
            "会话管理": [],
            "其他工具": [],
        }

        # 获取所有工具实例
        for tool_name in self.registry.tool_names:
            tool = self.registry.get(tool_name)
            if not tool:
                continue

            # 根据工具名称或描述确定类别
            category = self._determine_category(tool)
            tools_by_category[category].append(tool)

        # 移除空类别
        return {k: v for k, v in tools_by_category.items() if v}

    def _determine_category(self, tool) -> str:
        """确定工具类别.

        Args:
            tool: 工具实例。

        Returns:
            工具类别名称。
        """
        tool_name = tool.name.lower()
        tool_desc = (tool.description or "").lower()

        # 文件操作工具
        file_keywords = ["file", "read", "write", "edit", "list", "dir", "directory"]
        if any(keyword in tool_name for keyword in file_keywords) or any(
            keyword in tool_desc for keyword in file_keywords
        ):
            return "文件操作"

        # 系统命令工具
        sys_keywords = ["exec", "shell", "command", "run", "execute"]
        if any(keyword in tool_name for keyword in sys_keywords) or any(
            keyword in tool_desc for keyword in sys_keywords
        ):
            return "系统命令"

        # 网络工具
        web_keywords = ["web", "search", "fetch", "extract", "http", "url"]
        if any(keyword in tool_name for keyword in web_keywords) or any(
            keyword in tool_desc for keyword in web_keywords
        ):
            return "网络工具"

        # 记忆管理工具
        memory_keywords = ["memory", "remember", "recall", "forget", "store"]
        if any(keyword in tool_name for keyword in memory_keywords) or any(
            keyword in tool_desc for keyword in memory_keywords
        ):
            return "记忆管理"

        # 会话管理工具
        session_keywords = ["session", "title", "chat", "conversation"]
        if any(keyword in tool_name for keyword in session_keywords) or any(
            keyword in tool_desc for keyword in session_keywords
        ):
            return "会话管理"

        return "其他工具"
