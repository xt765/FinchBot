import time

from loguru import logger

from finchbot.channels.base import BaseChannel
from finchbot.channels.schema import OutboundMessage


class WeChatWorkChannel(BaseChannel):
    """WeChat Work Channel - simplified like nanobot."""

    name = "wechat"

    def __init__(self, config, bus):
        super().__init__(config, bus)
        cfg = config.get("wechat", {})
        self.corp_id = cfg.get("corp_id")
        self.agent_id = cfg.get("agent_id")
        self.secret = cfg.get("secret")
        self.token = None
        self.expires_at = 0

    async def _get_token(self):
        if self.token and time.time() < self.expires_at:
            return self.token

        import aiohttp
        url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={self.corp_id}&corpsecret={self.secret}"
        async with aiohttp.ClientSession() as session, session.get(url) as resp:
            data = await resp.json()
            if data.get("access_token"):
                self.token = data["access_token"]
                self.expires_at = time.time() + data.get("expires_in", 7200) - 300
                return self.token
        return None

    async def start(self):
        if not self.corp_id or not self.secret:
            logger.warning("WeChat Work credentials not configured")
            return
        logger.info("WeChat Work channel ready (webhook mode)")

    async def stop(self):
        self.token = None
        logger.info("WeChat Work stopped")

    async def handle_callback(self, body: str, signature: str = None) -> str:
        """Handle callback from WeChat Work."""
        # Simplified: just return success
        # Full implementation would parse XML and verify signature
        return "success"

    async def send(self, msg: OutboundMessage):
        token = await self._get_token()
        if not token:
            return

        import aiohttp
        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
        data = {
            "touser": msg.target_id,
            "msgtype": "text",
            "agentid": self.agent_id,
            "text": {"content": msg.content}
        }

        try:
            async with aiohttp.ClientSession() as session, session.post(url, json=data) as resp:
                result = await resp.json()
                if result.get("errcode") != 0:
                    logger.error(f"WeChat send error: {result}")
        except Exception as e:
            logger.error(f"WeChat send error: {e}")

    @property
    def connection_count(self):
        return 1 if self.token else 0

    @property
    def status(self):
        return "running" if self.token else "stopped"
