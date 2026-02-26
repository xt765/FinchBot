"""FinchBot 渠道模块.

注意：渠道功能已迁移到 LangBot 平台。
LangBot 支持 QQ、微信、飞书、钉钉、Discord、Telegram、Slack 等 12+ 平台。

安装 LangBot:
    uvx langbot

官方文档: https://docs.langbot.app

此模块保留用于兼容性，后续版本将移除。
"""

from .base import BaseChannel
from .bus import MessageBus
from .langbot_integration import LangBotIntegration
from .manager import ChannelManager
from .schema import InboundMessage, OutboundMessage

__all__ = [
    "InboundMessage",
    "OutboundMessage",
    "MessageBus",
    "BaseChannel",
    "ChannelManager",
    "LangBotIntegration",
]
