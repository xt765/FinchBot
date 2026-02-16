"""FinchBot 国际化模块.

提供多语言支持，包括：
- 语言文件加载
- 系统语言检测
- 语言回退机制
"""

from finchbot.i18n.loader import I18n, get_i18n, init_language_from_config, set_language, t

__all__ = [
    "I18n",
    "get_i18n",
    "set_language",
    "t",
    "init_language_from_config",
]
