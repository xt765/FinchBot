"""工具信息自动生成器.

扫描工具模块，自动生成 TOOLS.md 文件。
"""

from pathlib import Path

from loguru import logger


class ToolsGenerator:
    """工具信息自动生成器."""

    def __init__(self, workspace: Path) -> None:
        """初始化工具生成器.

        Args:
            workspace: 工作目录路径。
        """
        self.workspace = workspace

    def generate_tools_md(self) -> str:
        """生成 TOOLS.md 文件.

        Returns:
            TOOLS.md 内容。
        """
        from finchbot.tools import (
            EditFileTool,
            ExecTool,
            ForgetTool,
            ListDirTool,
            ReadFileTool,
            RecallTool,
            RememberTool,
            SessionTitleTool,
            WebExtractTool,
            WebSearchTool,
            WriteFileTool,
        )

        tools = [
            ReadFileTool,
            WriteFileTool,
            EditFileTool,
            ListDirTool,
            ExecTool,
            WebSearchTool,
            WebExtractTool,
            RememberTool,
            RecallTool,
            ForgetTool,
            SessionTitleTool,
        ]

        lines = ["# 可用工具\n"]

        for tool_cls in tools:
            tool = tool_cls()
            lines.append(f"## {tool.name}")
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
        self._write_file(self.workspace / "TOOLS.md", content)
        logger.info("TOOLS.md generated")
        return content

    def _write_file(self, file_path: Path, content: str) -> None:
        """写入文件.

        Args:
            file_path: 文件路径。
            content: 文件内容。
        """
        try:
            file_path.write_text(content, encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to write file {file_path}: {e}")
