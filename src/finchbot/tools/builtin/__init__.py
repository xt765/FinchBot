"""内置工具模块.

提供文件、记忆、网络、Shell、配置、后台任务、定时任务等工具。
所有工具从旧类方式迁移为装饰器方式，保留完整功能。
"""

from finchbot.tools.builtin._utils import configure_tools, decode_output, validate_path
from finchbot.tools.builtin.background import (
    cancel_task,
    check_task_status,
    get_task_result,
    list_background_tasks,
    start_background_task,
)
from finchbot.tools.builtin.config import (
    configure_config_tools,
    configure_mcp,
    get_capabilities,
    get_mcp_config_path_tool,
    refresh_capabilities,
)
from finchbot.tools.builtin.file import edit_file, list_dir, read_file, write_file
from finchbot.tools.builtin.memory import (
    forget,
    recall,
    remember,
    set_memory_manager,
)
from finchbot.tools.builtin.schedule import (
    create_cron,
    delete_cron,
    list_crons,
    run_cron_now,
    toggle_cron,
)
from finchbot.tools.builtin.session import configure_session_tools, session_title
from finchbot.tools.builtin.settlement import (
    build_proof_of_work_payload,
    configure_settlement_tools,
    report_agent_work,
    sign_payload,
)
from finchbot.tools.builtin.shell import configure_shell_tools, exec_command
from finchbot.tools.builtin.web import configure_web_tools, web_extract, web_search

__all__ = [
    # 公共函数
    "configure_tools",
    "validate_path",
    "decode_output",
    # 文件工具
    "read_file",
    "write_file",
    "edit_file",
    "list_dir",
    # 记忆工具
    "remember",
    "recall",
    "forget",
    "set_memory_manager",
    # 网络工具
    "web_search",
    "web_extract",
    "configure_web_tools",
    # 结算上报工具 (issue #2)
    "report_agent_work",
    "configure_settlement_tools",
    "build_proof_of_work_payload",
    "sign_payload",
    # Shell 工具
    "exec_command",
    "configure_shell_tools",
    # 配置工具
    "configure_mcp",
    "refresh_capabilities",
    "get_capabilities",
    "get_mcp_config_path_tool",
    "configure_config_tools",
    # 后台任务工具
    "start_background_task",
    "check_task_status",
    "get_task_result",
    "cancel_task",
    "list_background_tasks",
    # 定时任务工具
    "create_cron",
    "list_crons",
    "delete_cron",
    "toggle_cron",
    "run_cron_now",
    # 会话工具
    "session_title",
    "configure_session_tools",
]
