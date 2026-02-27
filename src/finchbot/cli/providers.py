"""Provider 配置模块.

提供 Provider 预设、关键词映射、优先级配置及相关辅助函数。
用于 LLM Provider 的自动检测和配置管理。
"""

from __future__ import annotations

import os
from typing import Any

from finchbot.config.schema import Config, ProviderConfig
from finchbot.config.utils import get_api_base, get_api_key
from finchbot.i18n import t


def _get_provider_name(provider_id: str) -> str:
    """获取提供商的本地化名称."""
    key = f"providers.{provider_id}"
    result = t(key, default=None)
    if result:
        return result
    return PRESET_PROVIDERS.get(provider_id, {}).get("name", provider_id)


PRESET_PROVIDERS: dict[str, dict[str, Any]] = {
    "openai": {
        "name": "OpenAI",
        "default_base": "https://api.openai.com/v1",
        "models": ["gpt-5", "gpt-5.2", "o3-mini"],
    },
    "anthropic": {
        "name": "Anthropic",
        "default_base": "https://api.anthropic.com/v1",
        "models": ["claude-sonnet-4.5", "claude-opus-4.6"],
    },
    "gemini": {
        "name": "Google Gemini",
        "default_base": "https://generativelanguage.googleapis.com/v1beta",
        "models": ["gemini-2.5-flash", "gemini-2.5-flash-lite"],
    },
    "deepseek": {
        "name": "DeepSeek",
        "default_base": "https://api.deepseek.com/v1",
        "models": ["deepseek-chat", "deepseek-reasoner"],
    },
    "dashscope": {
        "name": "DashScope / 阿里云通义千问",
        "default_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": ["qwen-turbo", "qwq-32b", "qwen-plus"],
    },
    "groq": {
        "name": "Groq",
        "default_base": "https://api.groq.com/openai/v1",
        "models": ["llama-4-scout", "llama-4-maverick", "llama-3.3-70b"],
    },
    "moonshot": {
        "name": "Moonshot / Kimi",
        "default_base": "https://api.moonshot.cn/v1",
        "models": ["kimi-k2.5", "kimi-k1.5"],
    },
    "openrouter": {
        "name": "OpenRouter",
        "default_base": "https://openrouter.ai/api/v1",
        "models": [],
    },
}

PROVIDER_KEYWORDS: dict[str, list[str]] = {
    "openai": ["gpt", "o1", "o3", "o4"],
    "anthropic": ["claude"],
    "openrouter": ["openrouter"],
    "deepseek": ["deepseek"],
    "groq": ["groq", "llama", "mixtral"],
    "gemini": ["gemini"],
    "moonshot": ["moonshot", "kimi"],
    "dashscope": ["qwen", "tongyi", "dashscope", "qwq"],
}

PROVIDER_PRIORITY: list[tuple[str, str, list[str]]] = [
    ("openai", "gpt-5", ["OPENAI_API_KEY"]),
    ("anthropic", "claude-sonnet-4.5", ["ANTHROPIC_API_KEY"]),
    ("deepseek", "deepseek-chat", ["DEEPSEEK_API_KEY", "DS_API_KEY"]),
    ("groq", "llama-4-scout", ["GROQ_API_KEY"]),
    ("moonshot", "kimi-k2.5", ["MOONSHOT_API_KEY"]),
    ("dashscope", "qwen-turbo", ["DASHSCOPE_API_KEY", "ALIBABA_API_KEY"]),
    ("gemini", "gemini-2.5-flash", ["GOOGLE_API_KEY", "GEMINI_API_KEY"]),
]


def _get_tavily_key(config_obj: Config) -> str | None:
    """获取 Tavily API 密钥."""
    return os.getenv("TAVILY_API_KEY") or config_obj.tools.web.search.api_key


def _get_provider_config(provider: str, config_obj: Config) -> tuple[str | None, str | None]:
    """获取 provider 的 API key 和 base.

    优先级：环境变量 > 配置文件预设 > 配置文件自定义

    Args:
        provider: Provider 名称
        config_obj: 配置对象

    Returns:
        (api_key, api_base) 元组
    """
    api_key = get_api_key(provider)
    api_base = get_api_base(provider)

    if not api_key:
        if hasattr(config_obj.providers, provider):
            prov_config = getattr(config_obj.providers, provider)
            if prov_config and isinstance(prov_config, ProviderConfig):
                api_key = prov_config.api_key or None
                api_base = prov_config.api_base or api_base

        if not api_key and provider in config_obj.providers.custom:
            custom = config_obj.providers.custom[provider]
            if custom and isinstance(custom, ProviderConfig):
                api_key = custom.api_key or None
                api_base = custom.api_base or api_base

    return api_key, api_base


def _get_llm_config(model: str, config_obj: Config) -> tuple[str | None, str | None, str | None]:
    """获取 LLM 配置.

    优先级：显式传入 > 环境变量 > 配置文件 > 自动检测。

    Returns:
        (api_key, api_base, detected_model) 元组，detected_model 为自动检测到的模型名称（如果有）。
    """
    model_lower = model.lower()

    provider = "openai"
    for name, keywords in PROVIDER_KEYWORDS.items():
        if any(kw in model_lower for kw in keywords):
            provider = name
            break

    api_key, api_base = _get_provider_config(provider, config_obj)

    detected_model = None
    if not api_key:
        api_key, api_base, detected_provider, detected_model = _auto_detect_provider()

    return api_key, api_base, detected_model


def _auto_detect_provider() -> tuple[str | None, str | None, str | None, str | None]:
    """根据环境变量自动检测可用的 provider.

    Returns:
        (api_key, api_base, provider, detected_model) 元组，
        如果没有可用的 provider 则返回 (None, None, None, None)。
    """
    for provider, default_model, env_vars in PROVIDER_PRIORITY:
        for env_var in env_vars:
            api_key = os.getenv(env_var)
            if api_key:
                api_base = get_api_base(provider)
                return api_key, api_base, provider, default_model

    return None, None, None, None
