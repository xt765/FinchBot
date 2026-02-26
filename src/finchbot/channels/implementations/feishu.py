import json
import time

from loguru import logger

from finchbot.channels.base import BaseChannel
from finchbot.channels.schema import OutboundMessage


class FeishuChannel(BaseChannel):
    """Feishu/Lark Channel - simplified like nanobot."""

    name = "feishu"

    def __init__(self, config, bus):
        super().__init__(config, bus)
        feishu_cfg = config.get("feishu", {})
        self.app_id = feishu_cfg.get("app_id")
        self.app_secret = feishu_cfg.get("app_secret")
        self.token = None
        self.expires_at = 0

    async def _get_token(self):
        if self.token and time.time() < self.expires_at:
            return self.token

        import aiohttp
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        async with aiohttp.ClientSession() as session, session.post(
            url, json={"app_id": self.app_id, "app_secret": self.app_secret}
        ) as resp:
            data = await resp.json()
            if data.get("code") == 0:
                self.token = data["tenant_access_token"]
                self.expires_at = time.time() + data["expire"] - 300
                return self.token
        return None

    async def start(self):
        if not self.app_id or not self.app_secret:
            logger.warning("Feishu credentials not configured")
            return
        logger.info("Feishu channel ready (webhook mode)")

    async def stop(self):
        self.token = None
        logger.info("Feishu stopped")

    async def handle_webhook(self, event: dict) -> dict:
        """Handle incoming webhook from Feishu."""
        if event.get("type") == "url_verification":
            return {"challenge": event.get("challenge")}

        if event.get("type") == "event_callback":
            msg_event = event.get("event", {})
            if msg_event.get("type") == "im.message.receive_v1":
                message = msg_event.get("message", {})
                sender = msg_event.get("sender", {})

                content = message.get("content", "{}")
                try:
                    content_json = json.loads(content)
                    text = content_json.get("text", content)
                except json.JSONDecodeError:
                    text = content

                await self._handle_message(
                    sender_id=sender.get("sender_id", {}).get("user_id", "unknown"),
                    chat_id=message.get("chat_id", "unknown"),
                    content=text,
                    metadata={"msg_type": message.get("msg_type")}
                )

        return {"code": 0}

    async def send(self, msg: OutboundMessage):
        token = await self._get_token()
        if not token:
            return

        import aiohttp
        url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        data = {
            "receive_id": msg.target_id,
            "msg_type": "text",
            "content": json.dumps({"text": msg.content})
        }

        try:
            async with aiohttp.ClientSession() as session, session.post(
                url, headers=headers, json=data
            ) as resp:
                result = await resp.json()
                if result.get("code") != 0:
                    logger.error(f"Feishu send error: {result}")
        except Exception as e:
            logger.error(f"Feishu send error: {e}")

    @property
    def connection_count(self):
        return 1 if self.token else 0

    @property
    def status(self):
        return "running" if self.token else "stopped"
