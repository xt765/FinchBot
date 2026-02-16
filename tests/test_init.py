"""FinchBot 基础测试."""

from finchbot import __version__


def test_version() -> None:
    """测试版本号."""
    assert __version__ == "0.1.0"
