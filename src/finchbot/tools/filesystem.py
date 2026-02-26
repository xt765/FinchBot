"""文件系统工具.

提供文件读写、编辑、目录列表等功能。
"""

from __future__ import annotations

from typing import Any

from finchbot.i18n import t
from finchbot.tools.base import FinchTool


def decode_output(data: bytes) -> str:
    """智能解码输出，自动尝试多种编码.

    Args:
        data: 要解码的字节数据。

    Returns:
        解码后的字符串。
    """
    encodings = ["utf-8", "gbk", "cp936", "gb18030", "latin-1"]
    for encoding in encodings:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1", errors="replace")


class ReadFileTool(FinchTool):
    """读取文件工具.

    允许 Agent 读取指定目录下的文件内容。
    具有路径安全检查机制，防止越权访问。
    """

    name: str = "read_file"
    description: str = t("tools.read_file.description")

    @property
    def parameters(self) -> dict[str, Any]:
        """返回参数定义."""
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": t("tools.read_file.param_file_path"),
                }
            },
            "required": ["file_path"],
        }

    def _run(self, file_path: str) -> str:
        """执行读取文件操作.

        Args:
            file_path: 目标文件路径（绝对路径或相对路径）。

        Returns:
            str: 文件内容字符串。如果读取失败（如文件不存在、权限不足、路径越权），则返回以 "Error:" 开头的错误信息。
        """
        safe_path = self.validate_path(file_path)
        if not safe_path:
            return f"Error: {t('tools.common.access_denied')}: {file_path}"

        if not safe_path.exists():
            return f"Error: {t('tools.read_file.file_not_found')}: {file_path}"

        try:
            content = safe_path.read_text(encoding="utf-8")
            return content
        except Exception as e:
            return f"Error: {t('tools.read_file.read_error')}: {str(e)}"


class WriteFileTool(FinchTool):
    """写入文件工具.

    允许 Agent 创建或覆盖指定目录下的文件。
    具有路径安全检查机制。
    """

    name: str = "write_file"
    description: str = t("tools.write_file.description")

    @property
    def parameters(self) -> dict[str, Any]:
        """返回参数定义."""
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": t("tools.write_file.param_file_path"),
                },
                "content": {
                    "type": "string",
                    "description": t("tools.write_file.param_content"),
                },
            },
            "required": ["file_path", "content"],
        }

    def _run(self, file_path: str, content: str) -> str:
        """执行写入文件操作.

        如果文件已存在，将被覆盖。如果父目录不存在，将自动创建。

        Args:
            file_path: 目标文件路径。
            content: 要写入的文本内容。

        Returns:
            str: 成功消息或以 "Error:" 开头的错误信息。
        """
        safe_path = self.validate_path(file_path)
        if not safe_path:
            return f"Error: {t('tools.common.access_denied')}: {file_path}"

        try:
            safe_path.parent.mkdir(parents=True, exist_ok=True)
            safe_path.write_text(content, encoding="utf-8")
            return f"Success: {t('tools.write_file.success')}: {file_path}"
        except Exception as e:
            return f"Error: {t('tools.write_file.write_error')}: {str(e)}"


class ListDirTool(FinchTool):
    """列出目录工具.

    列出指定目录下的文件和子目录。
    """

    name: str = "list_dir"
    description: str = t("tools.list_dir.description")

    @property
    def parameters(self) -> dict[str, Any]:
        """返回参数定义."""
        return {
            "type": "object",
            "properties": {
                "dir_path": {
                    "type": "string",
                    "description": t("tools.list_dir.param_dir_path"),
                }
            },
            "required": ["dir_path"],
        }

    def _run(self, dir_path: str = ".") -> str:
        """执行列出目录操作.

        Args:
            dir_path: 目标目录路径，默认为当前目录。

        Returns:
            str: 包含文件和目录列表的格式化字符串，或错误信息。
        """
        safe_path = self.validate_path(dir_path)
        if not safe_path:
            return f"Error: {t('tools.common.access_denied')}: {dir_path}"

        if not safe_path.is_dir():
            return f"Error: {t('tools.list_dir.not_a_directory')}: {dir_path}"

        try:
            entries = sorted(safe_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            result = []
            for entry in entries:
                type_mark = "<DIR>" if entry.is_dir() else "<FILE>"
                result.append(f"{type_mark} {entry.name}")

            return "\n".join(result) if result else "(Empty directory)"
        except Exception as e:
            return f"Error: {t('tools.list_dir.list_error')}: {str(e)}"


class EditFileTool(FinchTool):
    """编辑文件工具.

    允许 Agent 通过替换文本的方式编辑文件内容。
    适用于小规模的文本修改。
    """

    name: str = "edit_file"
    description: str = t("tools.edit_file.description")

    @property
    def parameters(self) -> dict[str, Any]:
        """返回参数定义."""
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": t("tools.read_file.param_file_path"),
                },
                "old_str": {
                    "type": "string",
                    "description": "The exact string to be replaced.",
                },
                "new_str": {
                    "type": "string",
                    "description": "The new string to replace with.",
                },
            },
            "required": ["file_path", "old_str", "new_str"],
        }

    def _run(self, file_path: str, old_str: str, new_str: str) -> str:
        """执行编辑文件操作.

        Args:
            file_path: 目标文件路径。
            old_str: 要查找并替换的旧字符串（必须精确匹配）。
            new_str: 替换成的新字符串。

        Returns:
            str: 成功消息或错误信息。
        """
        safe_path = self.validate_path(file_path)
        if not safe_path:
            return f"Error: {t('tools.common.access_denied')}: {file_path}"

        if not safe_path.exists():
            return f"Error: {t('tools.read_file.file_not_found')}: {file_path}"

        try:
            content = safe_path.read_text(encoding="utf-8")

            if old_str not in content:
                return "Error: old_str not found in file. Please ensure exact match including whitespace."

            count = content.count(old_str)
            if count > 1:
                return (
                    f"Warning: old_str found {count} times. Only the first occurrence was replaced."
                )

            new_content = content.replace(old_str, new_str, 1)
            safe_path.write_text(new_content, encoding="utf-8")

            return f"Success: File edited successfully: {file_path}"
        except Exception as e:
            return f"Error: Failed to edit file: {str(e)}"
