"""FinchBot 与 LangBot 集成指南.

LangBot 是一个生产级的多平台智能机器人开发平台，支持：
- QQ（个人 & 官方 API）
- 微信（个人 & 公众号）
- 企业微信（智能机器人、外部客服）
- 飞书（支持流式输出）
- 钉钉（支持流式输出）
- Discord
- Telegram
- Slack
- LINE
- KOOK
- Satori

安装 LangBot:
    uvx langbot
    或
    pip install langbot

启动 LangBot:
    uvx langbot
    访问 http://localhost:5300 进行配置

LangBot 官方文档: https://docs.langbot.app
LangBot GitHub: https://github.com/langbot-app/LangBot

集成方式:
1. 部署 LangBot 作为消息平台层
2. FinchBot 作为 Agent 核心提供 AI 能力
3. 通过 API 或消息队列连接两者

示例架构:
    用户消息 → LangBot（平台适配）→ FinchBot（Agent 处理）→ LangBot → 用户
"""

from __future__ import annotations

from typing import Any


class LangBotIntegration:
    """LangBot 集成接口.

    提供 FinchBot 与 LangBot 的集成能力。
    """

    @staticmethod
    def get_langbot_info() -> dict[str, Any]:
        """获取 LangBot 信息."""
        return {
            "name": "LangBot",
            "version": "4.8.5+",
            "platforms": [
                "QQ",
                "WeChat",
                "WeCom",
                "Feishu",
                "DingTalk",
                "Discord",
                "Telegram",
                "Slack",
                "LINE",
                "KOOK",
                "Satori",
            ],
            "features": [
                "WebUI 管理面板",
                "插件系统",
                "MCP 协议支持",
                "知识库",
                "流式输出",
            ],
            "install": "uvx langbot",
            "docs": "https://docs.langbot.app",
            "github": "https://github.com/langbot-app/LangBot",
        }

    @staticmethod
    async def forward_to_finchbot(message: str, session_id: str) -> str:
        """将消息转发给 FinchBot 处理.

        这是一个示例接口，实际实现需要根据具体架构调整。

        Args:
            message: 用户消息.
            session_id: 会话 ID.

        Returns:
            FinchBot 的响应.
        """
        # 实际实现需要调用 FinchBot 的 Agent API
        raise NotImplementedError(
            "Please implement this method based on your deployment architecture. "
            "You can use HTTP API, message queue, or direct function call."
        )
