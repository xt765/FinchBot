"""FinchBot 工具模块.

集成 ToolRegistry 动态工具注册和管理系统。
"""

from finchbot.tools.base import FinchTool
from finchbot.tools.config_tools import (
    ConfigureMCPTool,
    GetCapabilitiesTool,
    GetMCPConfigPathTool,
    RefreshCapabilitiesTool,
)
from finchbot.tools.filesystem import EditFileTool, ListDirTool, ReadFileTool, WriteFileTool
from finchbot.tools.memory import ForgetTool, RecallTool, RememberTool
from finchbot.tools.registry import (
    ToolRegistry,
    execute_tool,
    get_global_registry,
    register_tool,
    unregister_tool,
)
from finchbot.tools.session_title import SessionTitleTool
from finchbot.tools.shell import ExecTool
from finchbot.tools.web import WebExtractTool, WebSearchTool

__all__ = [
    # 工具基类
    "FinchTool",
    # 文件系统工具
    "ReadFileTool",
    "WriteFileTool",
    "EditFileTool",
    "ListDirTool",
    # 系统命令工具
    "ExecTool",
    # 网络工具
    "WebSearchTool",
    "WebExtractTool",
    # 记忆管理工具
    "RememberTool",
    "RecallTool",
    "ForgetTool",
    # 会话管理工具
    "SessionTitleTool",
    # 配置工具
    "ConfigureMCPTool",
    "RefreshCapabilitiesTool",
    "GetCapabilitiesTool",
    "GetMCPConfigPathTool",
    # 工具注册表
    "ToolRegistry",
    "get_global_registry",
    "register_tool",
    "unregister_tool",
    "execute_tool",
]
