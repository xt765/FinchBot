"""Shell 命令执行工具.

提供安全的命令行执行功能。
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Any

from loguru import logger
from pydantic import Field

from finchbot.i18n import t
from finchbot.tools.base import FinchTool

DEFAULT_DENY_PATTERNS = [
    r"\brm\s+-[rf]{1,2}\b",
    r"\bdel\s+/[fq]\b",
    r"\brmdir\s+/s\b",
    r"\b(format|mkfs|diskpart)\b",
    r"\bdd\s+if=",
    r">\s*/dev/sd",
    r"\b(shutdown|reboot|poweroff)\b",
    r":\(\)\s*\{.*\};\s*:",
]


class ExecTool(FinchTool):
    """Shell 命令执行工具.

    安全地执行 shell 命令并返回输出。

    Attributes:
        timeout: 命令超时时间（秒）。
        working_dir: 默认工作目录。
        deny_patterns: 禁止的命令模式列表。
        allow_patterns: 允许的命令模式列表。
        restrict_to_workspace: 是否限制在工作目录内。
    """

    name: str = Field(default="exec", description="工具名称")
    description: str = Field(default="", description="工具描述")

    def model_post_init(self, __context: Any) -> None:
        """初始化后设置描述."""
        desc = t("tools.exec.description")
        hint = t("tools.exec.hint")
        self.description = f"{desc} {hint}" if hint != "tools.exec.hint" else desc

    timeout: int = Field(default=60, description="命令超时时间（秒）")
    working_dir: str | None = Field(default=None, description="默认工作目录")
    deny_patterns: list[str] = Field(
        default_factory=lambda: DEFAULT_DENY_PATTERNS.copy(),
        description="禁止的命令模式",
    )
    allow_patterns: list[str] = Field(default_factory=list, description="允许的命令模式")
    restrict_to_workspace: bool = Field(default=False, description="限制在工作目录")

    @property
    def parameters(self) -> dict[str, Any]:
        """返回参数定义."""
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "要执行的 shell 命令",
                },
                "working_dir": {
                    "type": "string",
                    "description": "可选的工作目录",
                },
            },
            "required": ["command"],
        }

    def _run(self, command: str, working_dir: str | None = None) -> str:
        """执行 shell 命令.

        Args:
            command: 要执行的命令。
            working_dir: 可选的工作目录。

        Returns:
            命令输出或错误信息。
        """
        cwd = working_dir or self.working_dir or os.getcwd()
        logger.debug(f"Executing command: '{command}' in '{cwd}'")

        guard_error = self._guard_command(command, cwd)
        if guard_error:
            logger.warning(f"Command blocked by security guard: {guard_error}")
            return guard_error

        try:
            # 使用 shell=True 允许管道和重定向，但在 Windows 上可能有风险
            # 通过 _guard_command 进行简单的安全检查
            proc = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
                # text=False 以便手动处理编码
            )

            try:
                stdout_bytes, stderr_bytes = proc.communicate(timeout=self.timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                logger.error(f"Command timed out after {self.timeout}s: {command}")
                return f"错误: 命令在 {self.timeout} 秒后超时"

            def decode_output(data: bytes) -> str:
                """智能解码输出，自动尝试多种编码."""
                encodings = ["utf-8", "gbk", "cp936", "gb18030", "latin-1"]
                for enc in encodings:
                    try:
                        return data.decode(enc)
                    except UnicodeDecodeError:
                        continue
                return data.decode("utf-8", errors="replace")

            output_parts = []

            # 处理标准输出
            if stdout_bytes:
                out_text = decode_output(stdout_bytes)
                output_parts.append(out_text)

            # 处理标准错误
            stderr_text = ""
            if stderr_bytes:
                stderr_text = decode_output(stderr_bytes)
                if stderr_text.strip():
                    output_parts.append(f"STDERR:\n{stderr_text}")

            if proc.returncode != 0:
                output_parts.append(f"\n退出码: {proc.returncode}")
                logger.warning(
                    f"Command failed (code {proc.returncode}): {command}\nStderr: {stderr_text[:200]}"
                )
            else:
                logger.debug(f"Command finished successfully: {command}")

            result = "\n".join(output_parts) if output_parts else "(无输出)"

            max_len = 10000
            if len(result) > max_len:
                result = result[:max_len] + f"\n... (已截断，还有 {len(result) - max_len} 字符)"

            return result

        except Exception as e:
            logger.exception(f"Command execution error: {command}")
            return f"执行命令时出错: {str(e)}"

    def _guard_command(self, command: str, cwd: str) -> str | None:
        """安全检查命令.

        检查命令是否包含危险操作或违反限制。

        Args:
            command: 要检查的命令。
            cwd: 当前工作目录。

        Returns:
            如果命令被阻止，返回错误信息；否则返回 None。
        """
        cmd = command.strip()
        lower = cmd.lower()

        for pattern in self.deny_patterns:
            if re.search(pattern, lower):
                return "错误: 命令被安全检查阻止（检测到危险模式）"

        if self.allow_patterns and not any(re.search(p, lower) for p in self.allow_patterns):
            return "错误: 命令被安全检查阻止（不在允许列表中）"

        if self.restrict_to_workspace:
            # 检测路径遍历（跨平台）
            if ".." + os.sep in cmd or "../" in cmd or "..\\" in cmd:
                return "错误: 命令被安全检查阻止（检测到路径遍历）"

            cwd_path = Path(cwd).resolve()

            # Windows 绝对路径检测
            win_paths = re.findall(r"[A-Za-z]:\\[^\\\"']+", cmd)
            # POSIX 绝对路径检测
            posix_paths = re.findall(r"(?:^|[\s|>])(/[^\s\"'>]+)", cmd)

            for raw in win_paths + posix_paths:
                try:
                    p = Path(raw.strip()).resolve()
                except Exception:
                    continue
                if p.is_absolute() and cwd_path not in p.parents and p != cwd_path:
                    return "错误: 命令被安全检查阻止（路径在工作目录外）"

        return None
