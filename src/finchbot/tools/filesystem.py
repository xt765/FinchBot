"""文件系统工具.

提供文件读写、编辑、目录列表等功能。
"""

from pathlib import Path
from typing import Any

from pydantic import Field

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


def _resolve_path(path: str, allowed_dir: Path | None = None) -> Path:
    """解析路径并可选地限制目录访问.

    Args:
        path: 要解析的路径字符串。
        allowed_dir: 允许访问的目录，如果指定则限制路径必须在此目录下。

    Returns:
        解析后的绝对路径。

    Raises:
        PermissionError: 如果路径不在允许的目录内。
    """
    resolved = Path(path).expanduser().resolve()
    if allowed_dir and not str(resolved).startswith(str(allowed_dir.resolve())):
        raise PermissionError(f"Path {path} not in allowed directory {allowed_dir}")
    return resolved


class ReadFileTool(FinchTool):
    """读取文件工具.

    读取指定路径的文件内容。

    Attributes:
        allowed_dir: 允许访问的目录限制。
    """

    name: str = Field(default="read_file", description="Tool name")
    description: str = Field(default="", description="Tool description")
    allowed_dir: Path | None = Field(default=None, exclude=True)

    def model_post_init(self, __context: Any) -> None:
        """初始化后设置描述."""
        self.description = t("tools.read_file.description")

    @property
    def parameters(self) -> dict[str, Any]:
        """返回参数定义."""
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path to read",
                }
            },
            "required": ["path"],
        }

    def _run(self, path: str) -> str:
        """执行文件读取.

        Args:
            path: 文件路径。

        Returns:
            文件内容或错误信息。
        """
        try:
            file_path = _resolve_path(path, self.allowed_dir)
            if not file_path.exists():
                return f"{t('tools.read_file.error_not_found')}: {path}"
            if not file_path.is_file():
                return f"{t('tools.read_file.error_not_file')}: {path}"

            content_bytes = file_path.read_bytes()
            content = decode_output(content_bytes)
            return content
        except PermissionError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error reading file: {str(e)}"


class WriteFileTool(FinchTool):
    """写入文件工具.

    将内容写入指定路径的文件，自动创建父目录。

    Attributes:
        allowed_dir: 允许访问的目录限制。
    """

    name: str = Field(default="write_file", description="Tool name")
    description: str = Field(default="", description="Tool description")
    allowed_dir: Path | None = Field(default=None, exclude=True)

    def model_post_init(self, __context: Any) -> None:
        """初始化后设置描述."""
        self.description = t("tools.write_file.description")

    @property
    def parameters(self) -> dict[str, Any]:
        """返回参数定义."""
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path to write",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write",
                },
            },
            "required": ["path", "content"],
        }

    def _run(self, path: str, content: str) -> str:
        """执行文件写入.

        Args:
            path: 文件路径。
            content: 要写入的内容。

        Returns:
            操作结果信息。
        """
        try:
            file_path = _resolve_path(path, self.allowed_dir)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            return f"Successfully wrote {len(content)} bytes to {path}"
        except PermissionError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error writing file: {str(e)}"


class EditFileTool(FinchTool):
    """编辑文件工具.

    通过替换文本编辑文件内容。

    Attributes:
        allowed_dir: 允许访问的目录限制。
    """

    name: str = Field(default="edit_file", description="Tool name")
    description: str = Field(default="", description="Tool description")
    allowed_dir: Path | None = Field(default=None, exclude=True)

    def model_post_init(self, __context: Any) -> None:
        """初始化后设置描述."""
        self.description = t("tools.edit_file.description")

    @property
    def parameters(self) -> dict[str, Any]:
        """返回参数定义."""
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path to edit",
                },
                "old_text": {
                    "type": "string",
                    "description": "Text to find and replace",
                },
                "new_text": {
                    "type": "string",
                    "description": "Replacement text",
                },
            },
            "required": ["path", "old_text", "new_text"],
        }

    def _run(self, path: str, old_text: str, new_text: str) -> str:
        """执行文件编辑.

        Args:
            path: 文件路径。
            old_text: 要替换的文本。
            new_text: 替换后的文本。

        Returns:
            操作结果信息。
        """
        try:
            file_path = _resolve_path(path, self.allowed_dir)
            if not file_path.exists():
                return f"{t('tools.read_file.error_not_found')}: {path}"

            content_bytes = file_path.read_bytes()
            content = decode_output(content_bytes)

            if old_text not in content:
                return "Error: old_text not found, please ensure exact match."

            count = content.count(old_text)
            if count > 1:
                return f"Warning: old_text appears {count} times, please provide more context."

            new_content = content.replace(old_text, new_text, 1)
            file_path.write_text(new_content, encoding="utf-8")

            return f"Successfully edited {path}"
        except PermissionError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error editing file: {str(e)}"


class ListDirTool(FinchTool):
    """列出目录工具.

    列出指定目录的内容。

    Attributes:
        allowed_dir: 允许访问的目录限制。
    """

    name: str = Field(default="list_dir", description="Tool name")
    description: str = Field(default="", description="Tool description")
    allowed_dir: Path | None = Field(default=None, exclude=True)

    def model_post_init(self, __context: Any) -> None:
        """初始化后设置描述."""
        self.description = t("tools.list_dir.description")

    @property
    def parameters(self) -> dict[str, Any]:
        """返回参数定义."""
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path to list",
                }
            },
            "required": ["path"],
        }

    def _run(self, path: str) -> str:
        """执行目录列表.

        Args:
            path: 目录路径。

        Returns:
            目录内容列表或错误信息。
        """
        try:
            dir_path = _resolve_path(path, self.allowed_dir)
            if not dir_path.exists():
                return f"Error: Directory not found: {path}"
            if not dir_path.is_dir():
                return f"Error: Not a directory: {path}"

            items = []
            for item in sorted(dir_path.iterdir()):
                prefix = "📁 " if item.is_dir() else "📄 "
                items.append(f"{prefix}{item.name}")

            if not items:
                return f"Directory {path} is empty"

            return "\n".join(items)
        except PermissionError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error listing directory: {str(e)}"
