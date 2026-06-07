"""Shell 命令执行工具.

提供安全的命令行执行功能。
从 tools/shell.py 迁移，保留完整功能。
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Annotated

from loguru import logger
from pydantic import Field

from finchbot.tools.builtin._utils import decode_output
from finchbot.tools.decorator import ToolCategory, tool

# 默认禁止的命令模式
DEFAULT_DENY_PATTERNS = [
    r"\brm\s+-[rf]{1,2}\b",
    r"\brm\s+--(?:recursive|force)\b",
    r"\bdel\s+/[fq]\b",
    r"\brmdir\s+/s\b",
    r"\bformat\s+[a-zA-Z]:",
    r"\bformat\s+/dev/",
    r"\bmkfs\b",
    r"\bdiskpart\b",
    r"\bdd\s+if=",
    r">\s*/dev/[a-z0-9]+",
    r"\b(shutdown|reboot|poweroff)\b",
    r":\(\)\s*\{.*\};\s*:",
    r"\b(?:curl|wget)\b.+\|\s*(?:sh|bash)\b",
]

# 全局配置
_timeout: int = 60
_working_dir: str | None = None
_deny_patterns: list[str] = DEFAULT_DENY_PATTERNS.copy()
_allow_patterns: list[str] = []
_restrict_to_workspace: bool = False


def configure_shell_tools(
    timeout: int = 60,
    working_dir: str | None = None,
    deny_patterns: list[str] | None = None,
    allow_patterns: list[str] | None = None,
    restrict_to_workspace: bool = False,
) -> None:
    """配置 Shell 工具参数.

    Args:
        timeout: 命令超时时间（秒）
        working_dir: 默认工作目录
        deny_patterns: 禁止的命令模式列表
        allow_patterns: 允许的命令模式列表
        restrict_to_workspace: 是否限制在工作目录内
    """
    global _timeout, _working_dir, _deny_patterns, _allow_patterns, _restrict_to_workspace
    _timeout = timeout
    _working_dir = working_dir
    _deny_patterns = deny_patterns if deny_patterns is not None else DEFAULT_DENY_PATTERNS.copy()
    _allow_patterns = allow_patterns or []
    _restrict_to_workspace = restrict_to_workspace


def guard_command(command: str, cwd: str) -> str | None:
    """安全检查命令.

    检查命令是否包含危险操作或违反限制。

    Args:
        command: 要检查的命令
        cwd: 当前工作目录

    Returns:
        如果命令被阻止，返回错误信息；否则返回 None
    """
    cmd = command.strip()
    lower = cmd.lower()

    if _allow_patterns and any(re.search(p, lower) for p in _allow_patterns):
        return None

    for pattern in _deny_patterns:
        if re.search(pattern, lower):
            return "错误: 命令被安全检查阻止（检测到危险模式）"

    if _restrict_to_workspace:
        if ".." + os.sep in cmd or "../" in cmd or "..\\" in cmd:
            return "错误: 命令被安全检查阻止（检测到路径遍历）"

        cwd_path = Path(cwd).resolve()

        win_paths = re.findall(r"[A-Za-z]:\\[^\\\"']+", cmd)
        posix_paths = re.findall(r"(?:^|[\s|>])(/[^\s\"'>]+)", cmd)

        for raw in win_paths + posix_paths:
            try:
                p = Path(raw.strip()).resolve()
            except Exception:
                continue
            if p.is_absolute() and cwd_path not in p.parents and p != cwd_path:
                return "错误: 命令被安全检查阻止（路径在工作目录外）"

    return None


# 别名，保持向后兼容
_guard_command = guard_command


@tool(
    name="exec",
    description="执行 shell 命令并返回输出。默认超时 60 秒，输出超过 10000 字符会被截断。包含安全检查，禁止危险命令。优先使用文件系统工具（read_file/write_file/edit_file）处理文件，仅在需要批量操作、复杂文本处理或系统命令时使用 exec。",
    category=ToolCategory.SHELL,
    tags=["shell", "command"],
    dangerous=True,
)
async def exec_command(
    command: Annotated[str, Field(description="要执行的 shell 命令")],
    working_dir: Annotated[str | None, Field(description="可选的工作目录，默认为当前目录")] = None,
) -> str:
    """执行 shell 命令.

    安全地执行 shell 命令并返回输出。

    Args:
        command: 要执行的命令
        working_dir: 可选的工作目录

    Returns:
        命令输出或错误信息
    """
    cwd = working_dir or _working_dir or os.getcwd()
    logger.debug(f"Executing command: '{command}' in '{cwd}'")

    guard_error = _guard_command(command, cwd)
    if guard_error:
        logger.warning(f"Command blocked by security guard: {guard_error}")
        return guard_error

    try:
        proc = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
        )

        try:
            stdout_bytes, stderr_bytes = proc.communicate(timeout=_timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            logger.error(f"Command timed out after {_timeout}s: {command}")
            return f"错误: 命令在 {_timeout} 秒后超时"

        output_parts = []

        if stdout_bytes:
            out_text = decode_output(stdout_bytes)
            output_parts.append(out_text)

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
