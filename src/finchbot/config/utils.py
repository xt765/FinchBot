"""FinchBot 配置工具函数.

提供统一的 API Key 和配置获取逻辑。
"""

import os
from pathlib import Path

from dotenv import load_dotenv

_env_file = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(_env_file)


def get_api_key(
    provider: str,
    explicit_key: str | None = None,
    env_vars: list[str] | None = None,
) -> str | None:
    """获取 API 密钥.

    优先级：显式传入 > 环境变量 > None。

    Args:
        provider: 提供商名称，用于自动推断环境变量。
        explicit_key: 显式传入的 API 密钥。
        env_vars: 自定义环境变量名列表（按优先级排序）。

    Returns:
        API 密钥，如果未配置则返回 None。
    """
    if explicit_key:
        return explicit_key

    provider_env_vars: dict[str, list[str]] = {
        "openai": ["OPENAI_API_KEY"],
        "anthropic": ["ANTHROPIC_API_KEY"],
        "gemini": ["GOOGLE_API_KEY", "GEMINI_API_KEY"],
        "deepseek": ["DEEPSEEK_API_KEY", "DS_API_KEY"],
        "groq": ["GROQ_API_KEY"],
        "moonshot": ["MOONSHOT_API_KEY"],
        "openrouter": ["OPENROUTER_API_KEY"],
        "tavily": ["TAVILY_API_KEY"],
        "dashscope": ["DASHSCOPE_API_KEY", "ALIBABA_API_KEY"],
    }

    var_names = env_vars or provider_env_vars.get(provider.lower(), [])
    for var_name in var_names:
        value = os.getenv(var_name)
        if value:
            return value

    return None


def get_api_base(
    provider: str,
    explicit_base: str | None = None,
    env_vars: list[str] | None = None,
) -> str | None:
    """获取 API Base URL.

    优先级：显式传入 > 环境变量 > 默认值。

    Args:
        provider: 提供商名称，用于自动推断环境变量和默认值。
        explicit_base: 显式传入的 Base URL。
        env_vars: 自定义环境变量名列表（按优先级排序）。

    Returns:
        Base URL，如果未配置则返回 None。
    """
    if explicit_base:
        return explicit_base

    provider_env_vars: dict[str, list[str]] = {
        "openai": ["OPENAI_API_BASE", "OPENAI_BASE_URL"],
        "anthropic": ["ANTHROPIC_API_BASE", "ANTHROPIC_BASE_URL"],
        "deepseek": ["DEEPSEEK_API_BASE", "DS_BASE_URL"],
        "groq": ["GROQ_API_BASE", "GROQ_BASE_URL"],
        "moonshot": ["MOONSHOT_API_BASE", "MOONSHOT_BASE_URL"],
        "openrouter": ["OPENROUTER_API_BASE", "OPENROUTER_BASE_URL"],
        "dashscope": ["DASHSCOPE_API_BASE", "DASHSCOPE_BASE_URL"],
    }

    var_names = env_vars or provider_env_vars.get(provider.lower(), [])
    for var_name in var_names:
        value = os.getenv(var_name)
        if value:
            return value

    provider_defaults: dict[str, str] = {
        "deepseek": "https://api.deepseek.com/v1",
        "moonshot": "https://api.moonshot.cn/v1",
        "openrouter": "https://openrouter.ai/api/v1",
        "groq": "https://api.groq.com/openai/v1",
        "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    }

    return provider_defaults.get(provider.lower())
