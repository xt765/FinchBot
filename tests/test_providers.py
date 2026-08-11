"""LLM provider detection regression tests.

Covers https://github.com/xt765/FinchBot/issues/4:
- Tencent HunYuan should be recognized as a first-class provider.
- Custom providers configured via `providers.custom` should be matched by
  model name instead of being ignored due to hardcoded keyword lists.
"""

from __future__ import annotations

from finchbot.cli.providers import (
    PRESET_PROVIDERS,
    PROVIDER_KEYWORDS,
    PROVIDER_PRIORITY,
    _get_llm_config,
    _is_valid_custom_provider_name,
)
from finchbot.config.schema import Config, ProviderConfig
from finchbot.config.utils import get_api_base
from finchbot.providers.factory import _detect_provider

HUNYUAN_DEFAULT_BASE = "https://api.hunyuan.cloud.tencent.com/v1"


def _clear_api_key_env(monkeypatch) -> None:
    """Clear provider env vars so auto-detection does not interfere."""
    for key in list(__import__("os").environ):
        if key.endswith("_API_KEY") or key in (
            "GOOGLE_API_KEY",
            "GEMINI_API_KEY",
            "ALIBABA_API_KEY",
            "DS_API_KEY",
        ):
            monkeypatch.delenv(key, raising=False)


def test_hunyuan_model_detected_as_hunyuan_provider() -> None:
    """HunYuan model names should map to the `hunyuan` provider."""
    assert _detect_provider("hunyuan-turbos-latest") == "hunyuan"
    assert _detect_provider("hunyuan-turbo-latest") == "hunyuan"
    assert _detect_provider("hunyuan-lite") == "hunyuan"
    assert _detect_provider("tencent-hunyuan-turbo") == "hunyuan"


def test_unknown_model_falls_back_to_openai() -> None:
    """Unrecognized models keep the safe OpenAI-compatible fallback."""
    assert _detect_provider("some-unknown-model") == "openai"


def test_hunyuan_keyword_registered_in_all_keyword_sets() -> None:
    assert "hunyuan" in PROVIDER_KEYWORDS
    assert any(kw in ("hunyuan", "tencent") for kw in PROVIDER_KEYWORDS["hunyuan"])


def test_hunyuan_preset_provider_metadata() -> None:
    """HunYuan should be a built-in preset with a default base URL."""
    assert "hunyuan" in PRESET_PROVIDERS
    assert PRESET_PROVIDERS["hunyuan"]["default_base"] == HUNYUAN_DEFAULT_BASE
    assert any(entry[0] == "hunyuan" for entry in PROVIDER_PRIORITY)


def test_get_api_base_hunyuan_default() -> None:
    """`get_api_base` should fall back to the HunYuan default base."""
    assert get_api_base("hunyuan") == HUNYUAN_DEFAULT_BASE


def test_load_providers_from_env_includes_hunyuan(monkeypatch) -> None:
    """HUNYUAN_API_KEY env should be loaded as a configured provider."""
    _clear_api_key_env(monkeypatch)
    monkeypatch.setenv("HUNYUAN_API_KEY", "sk-hy-env")

    from finchbot.config.loader import _load_providers_from_env

    providers = _load_providers_from_env()

    assert providers["hunyuan"].api_key == "sk-hy-env"
    assert providers["hunyuan"].api_base == HUNYUAN_DEFAULT_BASE


def test_providers_config_has_hunyuan_field() -> None:
    """`providers.hunyuan` should exist in the config schema."""
    config = Config()
    assert config.providers.hunyuan.api_key == ""
    config.providers.hunyuan = ProviderConfig(api_key="sk-hy")
    assert "hunyuan" in config.get_configured_providers()


def test_custom_provider_matched_by_model_name(monkeypatch) -> None:
    """A custom provider whose name appears in the model must be used.

    This is the exact scenario from issue #4: the user configured a custom
    provider (API key + base URL) and expects `hunyuan-*` models to use it.
    """
    _clear_api_key_env(monkeypatch)
    config = Config()
    config.providers.custom["hunyuan"] = ProviderConfig(
        api_key="sk-hunyuan-test",
        api_base=HUNYUAN_DEFAULT_BASE,
    )

    api_key, api_base, _ = _get_llm_config("hunyuan-turbos-latest", config)

    assert api_key == "sk-hunyuan-test"
    assert api_base == HUNYUAN_DEFAULT_BASE


def test_custom_provider_with_aliased_name(monkeypatch) -> None:
    """Custom provider named differently (e.g. `tencent`) also matches."""
    _clear_api_key_env(monkeypatch)
    config = Config()
    config.providers.custom["tencent"] = ProviderConfig(
        api_key="sk-tencent",
        api_base=HUNYUAN_DEFAULT_BASE,
    )

    api_key, api_base, _ = _get_llm_config("tencent-hunyuan-turbo", config)

    assert api_key == "sk-tencent"
    assert api_base == HUNYUAN_DEFAULT_BASE


def test_preset_hunyuan_provider_config_used(monkeypatch) -> None:
    """Keys stored under the built-in `hunyuan` slot are honored."""
    _clear_api_key_env(monkeypatch)
    config = Config()
    config.providers.hunyuan = ProviderConfig(api_key="sk-preset-hy")

    api_key, _, _ = _get_llm_config("hunyuan-turbos-latest", config)

    assert api_key == "sk-preset-hy"


def test_unrelated_model_does_not_match_custom_provider(monkeypatch) -> None:
    """gpt-* models must not pick up a `hunyuan` custom provider."""
    _clear_api_key_env(monkeypatch)
    config = Config()
    config.providers.custom["hunyuan"] = ProviderConfig(api_key="sk-hy")

    api_key, _, _ = _get_llm_config("gpt-5", config)

    assert api_key is None


def test_custom_provider_name_validation() -> None:
    """Overly generic names should not be used as model-name keywords."""
    assert not _is_valid_custom_provider_name("ai")
    assert not _is_valid_custom_provider_name("v1")
    assert not _is_valid_custom_provider_name("")
    assert _is_valid_custom_provider_name("hunyuan")
    assert _is_valid_custom_provider_name("my-provider")
    assert _is_valid_custom_provider_name("deepseek-custom")
