"""FinchBot 配置加载工具."""

import json
from pathlib import Path
from typing import Any

from finchbot.config.schema import Config


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


def load_config(config_path: Path | None = None) -> Config:
    """从文件加载配置或创建默认配置.

    Args:
        config_path: 可选的配置文件路径，未提供则使用默认路径。

    Returns:
        加载的配置对象。
    """
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
    else:
        config = Config()

    # 方案 B：如果 default_model 是默认值且没有配置 provider，尝试自动检测
    if config.default_model == "gpt-5" and not config.get_configured_providers():
        detected_model = _auto_detect_default_model()
        if detected_model:
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
