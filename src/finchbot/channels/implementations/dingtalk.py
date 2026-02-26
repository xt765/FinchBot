import json
import time

from loguru import logger

from finchbot.channels.base import BaseChannel
from finchbot.channels.schema import OutboundMessage


class DingTalkChannel(BaseChannel):
    """DingTalk Channel - simplified like nanobot."""

    name = "dingtalk"

    def __init__(self, config, bus):
        super().__init__(config, bus)
        cfg = config.get("dingtalk", {})
        self.client_id = cfg.get("client_id")
        self.client_secret = cfg.get("client_secret")
        self.token = None
        self.expires_at = 0

    async def _get_token(self):
        if self.token and time.time() < self.expires_at:
            return self.token

        import aiohttp
        url = "https://api.dingtalk.com/v1.0/oauth2/accessToken"
        async with aiohttp.ClientSession() as session, session.post(
            url, json={"appKey": self.client_id, "appSecret": self.client_secret}
        ) as resp:
            data = await resp.json()
            if data.get("accessToken"):
                self.token = data["accessToken"]
                self.expires_at = time.time() + data.get("expireIn", 7200) - 300
                return self.token
        return None

    async def start(self):
        if not self.client_id or not self.client_secret:
            logger.warning("DingTalk credentials not configured")
            return
        logger.info("DingTalk channel ready (webhook mode)")

    async def stop(self):
        self.token = None
        logger.info("DingTalk stopped")

    async def handle_webhook(self, data: dict) -> dict:
        """Handle incoming webhook from DingTalk."""
        if data.get("msgtype") == "text":
            content = data.get("text", {}).get("content", "")
            sender = data.get("senderStaffId", "unknown")
            chat = data.get("conversationId", "unknown")

            await self._handle_message(
                sender_id=sender,
                chat_id=chat,
                content=content,
                metadata={"source": "dingtalk"}
            )

        return {"msgtype": "text", "text": {"content": "received"}}

    async def send(self, msg: OutboundMessage):
        token = await self._get_token()
        if not token:
            return

        import aiohttp
        url = "https://api.dingtalk.com/v1.0/robot/oToMessages/batchSend"
        headers = {"x-acs-dingtalk-access-token": token, "Content-Type": "application/json"}
        data = {
            "robotCode": self.client_id,
            "userIds": [msg.target_id],
            "msgKey": "sampleText",
            "msgParam": json.dumps({"content": msg.content})
        }

        try:
            async with aiohttp.ClientSession() as session, session.post(
                url, headers=headers, json=data
            ) as resp:
                result = await resp.json()
                if result.get("code") != "OK":
                    logger.error(f"DingTalk send error: {result}")
        except Exception as e:
            logger.error(f"DingTalk send error: {e}")

    @property
    def connection_count(self):
        return 1 if self.token else 0

    @property
    def status(self):
        return "running" if self.token else "stopped"
