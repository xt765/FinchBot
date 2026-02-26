"""FinchBot 配置加载工具."""

import json
from pathlib import Path
from typing import Any

from finchbot.config.schema import Config, ProviderConfig


def get_config_path() -> Path:
    """获取默认配置文件路径.

    Returns:
        默认配置文件路径。
    """
    return Path.home() / ".finchbot" / "config.json"


def _auto_detect_default_model() -> str | None:
    """根据环境变量自动检测默认模型.

    Returns:
        检测到的模型名称，如果没有可用的 provider 则返回 None。
    """
    from finchbot.config.utils import get_api_key

    provider_models = [
        ("openai", "gpt-5"),
        ("anthropic", "claude-sonnet-4.5"),
        ("deepseek", "deepseek-chat"),
        ("groq", "llama-4-scout"),
        ("moonshot", "kimi-k2.5"),
        ("dashscope", "qwen-turbo"),
        ("gemini", "gemini-2.5-flash"),
    ]

    for provider, model in provider_models:
        if get_api_key(provider):
            return model
    return None


def _load_providers_from_env() -> dict[str, ProviderConfig]:
    """从环境变量加载提供商配置.

    Returns:
        提供商名称到配置的映射。
    """
    from finchbot.config.utils import get_api_base, get_api_key

    providers: dict[str, ProviderConfig] = {}

    provider_configs = [
        ("openai", ["OPENAI_API_KEY"], ["OPENAI_API_BASE", "OPENAI_BASE_URL"]),
        ("anthropic", ["ANTHROPIC_API_KEY"], ["ANTHROPIC_API_BASE", "ANTHROPIC_BASE_URL"]),
        ("gemini", ["GOOGLE_API_KEY", "GEMINI_API_KEY"], ["GOOGLE_API_BASE", "GEMINI_API_BASE"]),
        ("deepseek", ["DEEPSEEK_API_KEY", "DS_API_KEY"], ["DEEPSEEK_API_BASE", "DS_BASE_URL"]),
        ("groq", ["GROQ_API_KEY"], ["GROQ_API_BASE", "GROQ_BASE_URL"]),
        ("moonshot", ["MOONSHOT_API_KEY"], ["MOONSHOT_API_BASE", "MOONSHOT_BASE_URL"]),
        ("openrouter", ["OPENROUTER_API_KEY"], ["OPENROUTER_API_BASE", "OPENROUTER_BASE_URL"]),
        (
            "dashscope",
            ["DASHSCOPE_API_KEY", "ALIBABA_API_KEY"],
            ["DASHSCOPE_API_BASE", "DASHSCOPE_BASE_URL"],
        ),
    ]

    for provider, key_vars, base_vars in provider_configs:
        api_key = get_api_key(provider, env_vars=key_vars)
        if api_key:
            api_base = get_api_base(provider, env_vars=base_vars)
            providers[provider] = ProviderConfig(api_key=api_key, api_base=api_base)

    return providers


def load_config(config_path: Path | None = None) -> Config:
    """从文件加载配置或创建默认配置.

    Args:
        config_path: 可选的配置文件路径，未提供则使用默认路径。

    Returns:
        加载的配置对象。
    """
    from finchbot.i18n.loader import detect_system_language

    path = config_path or get_config_path()

    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            data = _migrate_config(data)
            config = Config.model_validate(convert_keys(data))
        except (json.JSONDecodeError, ValueError) as e:
            print(f"警告: 无法从 {path} 加载配置: {e}")
            print("使用默认配置。")
            config = Config()
            # 配置文件损坏，检测系统语言
            config.language = detect_system_language()
            config.language_set_by_user = False
    else:
        config = Config()
        # 新配置，检测系统语言和默认模型
        config.language = detect_system_language()
        config.language_set_by_user = False
        detected_model = _auto_detect_default_model()
        if detected_model:
            config.default_model = detected_model
        config.default_model_set_by_user = False

    # 如果语言未被用户设置过，尝试检测系统语言
    if not config.language_set_by_user:
        detected_lang = detect_system_language()
        if detected_lang != config.language:
            config.language = detected_lang

    # 从环境变量加载提供商配置并合并
    env_providers = _load_providers_from_env()
    for provider_name, provider_config in env_providers.items():
        # 环境变量优先级高于配置文件
        if provider_name not in config.providers.model_fields:
            # 自定义 provider
            config.providers.custom[provider_name] = provider_config
        else:
            # 预设 provider
            setattr(config.providers, provider_name, provider_config)

    # 如果默认模型未被用户设置过，尝试自动检测
    if not config.default_model_set_by_user:
        detected_model = _auto_detect_default_model()
        if detected_model and detected_model != config.default_model:
            config.default_model = detected_model

    return config


def save_config(config: Config, config_path: Path | None = None) -> None:
    """保存配置到文件.

    Args:
        config: 要保存的配置对象。
        config_path: 可选的保存路径，未提供则使用默认路径。
    """
    path = config_path or get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    data = config.model_dump()
    data = convert_to_camel(data)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _migrate_config(data: dict) -> dict:
    """迁移旧配置格式.

    Args:
        data: 原始配置数据。

    Returns:
        迁移后的配置数据。
    """
    return data


def convert_keys(data: Any) -> Any:
    """将 camelCase 键转换为 snake_case.

    Args:
        data: 要转换的数据。

    Returns:
        转换后的数据。
    """
    if isinstance(data, dict):
        return {camel_to_snake(k): convert_keys(v) for k, v in data.items()}
    if isinstance(data, list):
        return [convert_keys(item) for item in data]
    return data


def convert_to_camel(data: Any) -> Any:
    """将 snake_case 键转换为 camelCase.

    Args:
        data: 要转换的数据。

    Returns:
        转换后的数据。
    """
    if isinstance(data, dict):
        return {snake_to_camel(k): convert_to_camel(v) for k, v in data.items()}
    if isinstance(data, list):
        return [convert_to_camel(item) for item in data]
    return data


def camel_to_snake(name: str) -> str:
    """将 camelCase 转换为 snake_case.

    Args:
        name: camelCase 字符串。

    Returns:
        snake_case 字符串。
    """
    result = []
    for i, char in enumerate(name):
        if char.isupper() and i > 0:
            result.append("_")
        result.append(char.lower())
    return "".join(result)


def snake_to_camel(name: str) -> str:
    """将 snake_case 转换为 camelCase.

    Args:
        name: snake_case 字符串。

    Returns:
        camelCase 字符串。
    """
    components = name.split("_")
    return components[0] + "".join(x.title() for x in components[1:])
