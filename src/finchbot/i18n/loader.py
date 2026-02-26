"""FinchBot 语言加载器.

负责加载 TOML 语言文件、缓存、键值查找和回退逻辑。
"""

import locale
import os
import platform
import tomllib
from pathlib import Path
from typing import Any

LOCALES_DIR = Path(__file__).parent / "locales"

SUPPORTED_LANGUAGES = ["en-US", "zh-CN", "zh-HK"]

DEFAULT_LANGUAGE = "en-US"


class I18n:
    """国际化管理器.

    负责加载语言文件、缓存、键值查找和回退。

    Attributes:
        language: 当前语言代码。
        _cache: 语言数据缓存。
        _fallback_chain: 回退链。
    """

    def __init__(self, language: str | None = None) -> None:
        """初始化国际化管理器.

        Args:
            language: 语言代码，如果为 None 则自动检测。
        """
        self._language: str = language or DEFAULT_LANGUAGE
        self._cache: dict[str, dict[str, Any]] = {}
        self._fallback_chain: list[str] = self._build_fallback_chain(self._language)

    @property
    def language(self) -> str:
        """获取当前语言代码."""
        return self._language

    @language.setter
    def language(self, value: str) -> None:
        """设置当前语言代码."""
        self._language = self._normalize_language(value)
        self._fallback_chain = self._build_fallback_chain(self._language)

    def _normalize_language(self, lang: str) -> str:
        """标准化语言代码.

        将各种格式的语言代码标准化为 "zh-CN"、"en-US" 等格式。
        支持从字符串中提取有效的语言代码。

        Args:
            lang: 原始语言代码。

        Returns:
            标准化后的语言代码。
        """
        if not lang:
            return DEFAULT_LANGUAGE

        lang = lang.replace("_", "-").strip()

        for supported in SUPPORTED_LANGUAGES:
            if supported.lower() in lang.lower():
                return supported

        if lang.lower() in ["zh", "zh-cn", "zh-hans", "zh-hans-cn"]:
            return "zh-CN"
        if lang.lower() in ["zh-hk", "zh-hant", "zh-hant-hk"]:
            return "zh-HK"
        if lang.lower() in ["zh-tw", "zh-hant-tw"]:
            return "zh-HK"
        if lang.lower().startswith("en"):
            return "en-US"
        if lang.lower() in SUPPORTED_LANGUAGES:
            return lang
        return DEFAULT_LANGUAGE

    def _build_fallback_chain(self, lang: str) -> list[str]:
        """构建语言回退链.

        Args:
            lang: 语言代码。

        Returns:
            回退链列表。
        """
        chain = [lang]
        if "-" in lang:
            base = lang.split("-")[0]
            if base != lang:
                chain.append(base)
        if DEFAULT_LANGUAGE not in chain:
            chain.append(DEFAULT_LANGUAGE)
        return chain

    def _load_language(self, lang: str) -> dict[str, Any]:
        """加载语言文件.

        Args:
            lang: 语言代码。

        Returns:
            语言数据字典。
        """
        if lang in self._cache:
            return self._cache[lang]

        lang_file = LOCALES_DIR / f"{lang}.toml"
        if not lang_file.exists():
            return {}

        with open(lang_file, "rb") as f:
            data = tomllib.load(f)

        self._cache[lang] = data
        return data

    def get(self, key: str, default: str | None = None, **kwargs: Any) -> str:
        """获取翻译文本.

        支持点号分隔的键路径，如 "cli.config.init_title"。

        Args:
            key: 翻译键。
            default: 默认值，如果未找到则返回。
            **kwargs: 格式化参数。

        Returns:
            翻译后的文本。
        """
        for lang in self._fallback_chain:
            data = self._load_language(lang)
            value = self._get_nested(data, key)
            if value is not None and isinstance(value, str):
                if kwargs:
                    try:
                        return value.format(**kwargs)
                    except KeyError:
                        return value
                return value

        return default if default is not None else key

    def get_raw(self, key: str, default: Any = None) -> Any:
        """获取原始值（任意类型）.

        支持点号分隔的键路径，如 "memory.categories.personal.keywords"。

        Args:
            key: 翻译键。
            default: 默认值，如果未找到则返回。

        Returns:
            原始值（可以是字符串、列表、字典等）。
        """
        for lang in self._fallback_chain:
            data = self._load_language(lang)
            value = self._get_nested(data, key)
            if value is not None:
                return value
        return default

    def _get_nested(self, data: dict[str, Any], key: str) -> Any:
        """获取嵌套字典中的值.

        Args:
            data: 数据字典。
            key: 点号分隔的键路径。

        Returns:
            找到的值，如果未找到则返回 None。
        """
        keys = key.split(".")
        current = data
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None
        return current

    def detect_and_set_language(self) -> str:
        """检测系统语言并设置.

        Returns:
            检测到的语言代码。
        """
        detected = detect_system_language()
        self.language = detected
        return self._language


def detect_system_language() -> str:
    """检测系统语言.

    支持 Windows、macOS 和 Linux。

    Returns:
        检测到的语言代码，如 "zh-CN"、"en-US"。
    """
    system = platform.system()

    if system == "Windows":
        return _detect_windows_language()
    if system == "Darwin":
        return _detect_macos_language()
    return _detect_linux_language()


def _detect_windows_language() -> str:
    """检测 Windows 系统语言."""
    try:
        lang = locale.getdefaultlocale()[0]
        if lang:
            return _normalize_locale(lang)
    except Exception:
        pass

    try:
        import ctypes

        windll = ctypes.windll.kernel32
        lang_id = windll.GetUserDefaultUILanguage()
        lang = _langid_to_locale(lang_id)
        if lang:
            return lang
    except Exception:
        pass

    return DEFAULT_LANGUAGE


def _detect_macos_language() -> str:
    """检测 macOS 系统语言."""
    lang = os.getenv("LANG")
    if lang:
        return _normalize_locale(lang)

    try:
        import subprocess

        result = subprocess.run(
            ["defaults", "read", "-g", "AppleLocale"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return _normalize_locale(result.stdout.strip())
    except Exception:
        pass

    return DEFAULT_LANGUAGE


def _detect_linux_language() -> str:
    """检测 Linux 系统语言."""
    lang = os.getenv("LANG") or os.getenv("LC_ALL") or os.getenv("LC_MESSAGES")
    if lang:
        return _normalize_locale(lang)

    try:
        lang = locale.getdefaultlocale()[0]
        if lang:
            return _normalize_locale(lang)
    except Exception:
        pass

    return DEFAULT_LANGUAGE


def _normalize_locale(lang: str) -> str:
    """标准化语言代码."""
    if not lang:
        return DEFAULT_LANGUAGE

    lang = lang.strip().split(".")[0].split("@")[0]
    lang = lang.replace("_", "-")

    parts = lang.split("-")
    if len(parts) == 2:
        lang_code = parts[0].lower()
        region = parts[1].upper()
        return f"{lang_code}-{region}"

    if len(parts) == 1:
        lang_code = parts[0].lower()
        if lang_code == "zh":
            return "zh-CN"
        if lang_code == "en":
            return "en-US"
        return f"{lang_code}-{lang_code.upper()}"

    return DEFAULT_LANGUAGE


def _langid_to_locale(lang_id: int) -> str:
    """将 Windows 语言 ID 转换为语言代码."""
    lang_map = {
        0x0404: "zh-HK",
        0x0804: "zh-CN",
        0x0C04: "zh-HK",
        0x1004: "zh-CN",
        0x1404: "zh-CN",
        0x0409: "en-US",
        0x0809: "en-GB",
        0x0C09: "en-AU",
        0x1009: "en-CA",
        0x1409: "en-NZ",
        0x0411: "ja-JP",
        0x0412: "ko-KR",
        0x0419: "ru-RU",
        0x0407: "de-DE",
        0x040C: "fr-FR",
        0x0C0A: "es-ES",
        0x0410: "it-IT",
        0x0416: "pt-BR",
        0x0816: "pt-PT",
    }

    return lang_map.get(lang_id, DEFAULT_LANGUAGE)


_i18n_instance: I18n | None = None


def _auto_init_language() -> None:
    """自动从配置文件初始化语言.

    在模块导入时调用，确保 i18n 在任何使用前都已初始化。
    """
    global _i18n_instance

    if _i18n_instance is not None:
        return

    _i18n_instance = I18n()

    env_lang = os.getenv("FINCHBOT_LANG") or os.getenv("LANG")
    if env_lang:
        _i18n_instance.language = env_lang
        return

    try:
        import json

        config_path = Path.home() / ".finchbot" / "config.json"
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                config = json.load(f)
            config_lang = config.get("language")
            if config_lang and config_lang in SUPPORTED_LANGUAGES:
                _i18n_instance.language = config_lang
                return
    except Exception:
        pass

    _i18n_instance.detect_and_set_language()


_auto_init_language()


def get_i18n() -> I18n:
    """获取全局 I18n 实例.

    Returns:
        I18n 实例。
    """
    global _i18n_instance
    if _i18n_instance is None:
        _i18n_instance = I18n()
    return _i18n_instance


def set_language(language: str) -> None:
    """设置全局语言.

    Args:
        language: 语言代码。
    """
    i18n = get_i18n()
    i18n.language = language


def t(key: str, default: str | None = None, **kwargs: Any) -> str:
    """便捷翻译函数.

    Args:
        key: 翻译键。
        default: 默认值。
        **kwargs: 格式化参数。

    Returns:
        翻译后的文本。
    """
    return get_i18n().get(key, default, **kwargs)


def init_language_from_config(config_language: str | None = None) -> str:
    """从配置初始化语言.

    优先级：环境变量 > 配置文件 > 系统检测 > 默认。

    Args:
        config_language: 配置文件中的语言设置。

    Returns:
        最终确定的语言代码。
    """
    i18n = get_i18n()

    env_lang = os.getenv("FINCHBOT_LANG") or os.getenv("LANG")
    if env_lang:
        i18n.language = env_lang
        return i18n.language

    if config_language and config_language in SUPPORTED_LANGUAGES:
        i18n.language = config_language
        return i18n.language

    i18n.detect_and_set_language()
    return i18n.language
