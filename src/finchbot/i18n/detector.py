"""FinchBot 系统语言检测.

自动检测操作系统的语言设置。
"""

import locale
import os
import platform

_detected_language: str | None = None


def detect_system_language() -> str:
    """检测系统语言.

    支持 Windows、macOS 和 Linux。
    使用缓存避免重复检测。

    Returns:
        检测到的语言代码，如 "zh-CN"、"en-US"。
    """
    global _detected_language

    if _detected_language is not None:
        return _detected_language

    system = platform.system()

    if system == "Windows":
        _detected_language = _detect_windows_language()
    elif system == "Darwin":
        _detected_language = _detect_macos_language()
    else:
        _detected_language = _detect_linux_language()

    return _detected_language


def reset_language_cache() -> None:
    """重置语言检测缓存."""
    global _detected_language
    _detected_language = None


def _detect_windows_language() -> str:
    """检测 Windows 系统语言.

    Returns:
        语言代码。
    """
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

    return "en-US"


def _detect_macos_language() -> str:
    """检测 macOS 系统语言.

    Returns:
        语言代码。
    """
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

    return "en-US"


def _detect_linux_language() -> str:
    """检测 Linux 系统语言.

    Returns:
        语言代码。
    """
    lang = os.getenv("LANG") or os.getenv("LC_ALL") or os.getenv("LC_MESSAGES")
    if lang:
        return _normalize_locale(lang)

    try:
        lang = locale.getdefaultlocale()[0]
        if lang:
            return _normalize_locale(lang)
    except Exception:
        pass

    return "en-US"


def _normalize_locale(lang: str) -> str:
    """标准化语言代码.

    将各种格式的语言代码标准化为 "zh-CN"、"en-US" 等格式。

    Args:
        lang: 原始语言代码。

    Returns:
        标准化后的语言代码。
    """
    if not lang:
        return "en-US"

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

    return "en-US"


def _langid_to_locale(lang_id: int) -> str:
    """将 Windows 语言 ID 转换为语言代码.

    Args:
        lang_id: Windows 语言 ID。

    Returns:
        语言代码。
    """
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

    return lang_map.get(lang_id, "en-US")
