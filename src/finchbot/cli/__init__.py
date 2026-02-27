"""FinchBot CLI 模块

提供命令行界面的核心功能，包括：
- 提供商配置与管理
- UI 交互组件
- 配置管理
- 聊天会话处理
"""

from finchbot.cli.chat_session import (
    EXIT_COMMANDS,
    GOODBYE_MESSAGE,
    _get_last_active_session,
    _run_chat_session,
)
from finchbot.cli.config_manager import (
    ConfigManager,
    _configure_custom_provider,
    _configure_default_model,
    _configure_language,
    _configure_preset_provider,
    _run_interactive_config,
)
from finchbot.cli.providers import (
    PRESET_PROVIDERS,
    PROVIDER_KEYWORDS,
    PROVIDER_PRIORITY,
    _auto_detect_provider,
    _get_llm_config,
    _get_provider_config,
    _get_provider_name,
    _get_tavily_key,
)
from finchbot.cli.ui import (
    _keyboard_select,
    console,
)

__all__ = [
    "PRESET_PROVIDERS",
    "PROVIDER_KEYWORDS",
    "PROVIDER_PRIORITY",
    "_get_tavily_key",
    "_get_provider_config",
    "_get_llm_config",
    "_get_provider_name",
    "_auto_detect_provider",
    "console",
    "_keyboard_select",
    "ConfigManager",
    "_run_interactive_config",
    "_configure_language",
    "_configure_preset_provider",
    "_configure_custom_provider",
    "_configure_default_model",
    "EXIT_COMMANDS",
    "GOODBYE_MESSAGE",
    "_run_chat_session",
    "_get_last_active_session",
]
