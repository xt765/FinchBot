"""FinchBot 常量定义模块.

集中管理所有默认常量和配置值.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

# 退出命令
EXIT_COMMANDS: Final[frozenset[str]] = frozenset({"exit", "quit", "/exit", "/quit", ":q", "q"})


@dataclass(frozen=True)
class MemoryDefaults:
    """记忆系统默认值."""

    MAX_RETRIES: int = 3
    TOP_K: int = 5
    SIMILARITY_THRESHOLD: float = 0.5
    FORGET_LIMIT: int = 1000
    SEARCH_LIMIT: int = 100
    RECENT_DAYS: int = 7
    RECENT_LIMIT: int = 20
    IMPORTANT_MIN_IMPORTANCE: float = 0.8
    IMPORTANT_LIMIT: int = 20


@dataclass(frozen=True)
class AgentDefaults:
    """Agent 默认值."""

    MAX_TOKENS: int = 8192
    TEMPERATURE: float = 0.7
    MAX_TOOL_ITERATIONS: int = 20


@dataclass(frozen=True)
class ToolDefaults:
    """工具默认值."""

    EXEC_TIMEOUT: int = 60
    WEB_SEARCH_MAX_RESULTS: int = 5


# 导出实例供使用
MEMORY_DEFAULTS = MemoryDefaults()
AGENT_DEFAULTS = AgentDefaults()
TOOL_DEFAULTS = ToolDefaults()
