"""FinchBot LLM 提供商工厂.

简化 LLM 模型创建，支持多种 API Key 配置方式。
"""

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import SecretStr

from finchbot.config.utils import get_api_base, get_api_key


def create_chat_model(
    model: str,
    api_key: str | None = None,
    api_base: str | None = None,
    temperature: float = 0.7,
    **kwargs: Any,
) -> BaseChatModel:
    """创建聊天模型实例。

    根据模型名称自动选择合适的 LangChain 集成。
    API Key 优先级：显式传入 > 环境变量。

    Args:
        model: 模型名称，如 "gpt-4o", "claude-3-opus", "qwen-turbo"。
        api_key: API 密钥（可选，优先使用环境变量）。
        api_base: API 基础 URL（可选，优先使用环境变量）。
        temperature: 生成温度。
        **kwargs: 其他模型参数。

    Returns:
        配置好的聊天模型实例。
    """
    model_lower = model.lower()
    provider = _detect_provider(model_lower)

    final_key = get_api_key(provider, api_key)
    final_base = get_api_base(provider, api_base)
    secret_key = SecretStr(final_key) if final_key else None

    return _create_model(provider, model, secret_key, final_base, temperature, **kwargs)


def _detect_provider(model_lower: str) -> str:
    """根据模型名称检测提供商。

    Args:
        model_lower: 小写的模型名称。

    Returns:
        提供商名称。
    """
    provider_keywords: dict[str, list[str]] = {
        "openai": ["gpt", "o1", "o3", "o4"],
        "anthropic": ["claude"],
        "openrouter": ["openrouter"],
        "deepseek": ["deepseek"],
        "groq": ["groq", "llama", "mixtral"],
        "gemini": ["gemini"],
        "moonshot": ["moonshot", "kimi"],
        "dashscope": ["qwen", "tongyi", "dashscope", "qwq"],
    }

    for provider_name, keywords in provider_keywords.items():
        if any(kw in model_lower for kw in keywords):
            return provider_name

    return "openai"


def _create_model(
    provider: str,
    model: str,
    secret_key: SecretStr | None,
    base_url: str | None,
    temperature: float,
    **kwargs: Any,
) -> BaseChatModel:
    """创建具体的模型实例。

    Args:
        provider: 提供商名称。
        model: 模型名称。
        secret_key: API 密钥。
        base_url: API 基础 URL。
        temperature: 生成温度。
        **kwargs: 其他参数。

    Returns:
        聊天模型实例。
    """
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model,
            api_key=secret_key,
            base_url=base_url,
            temperature=temperature,
            **kwargs,
        )

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        if secret_key is None:
            return ChatAnthropic(
                model_name=model,
                temperature=temperature,
                **kwargs,
            )
        return ChatAnthropic(
            model_name=model,
            api_key=secret_key,
            temperature=temperature,
            **kwargs,
        )

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        key = secret_key.get_secret_value() if secret_key else None
        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=key,
            temperature=temperature,
            **kwargs,
        )

    if provider in ("deepseek", "groq", "moonshot", "openrouter", "dashscope"):
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model,
            api_key=secret_key,
            base_url=base_url,
            temperature=temperature,
            **kwargs,
        )

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=model,
        api_key=secret_key,
        base_url=base_url,
        temperature=temperature,
        **kwargs,
    )
