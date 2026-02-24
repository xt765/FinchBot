from loguru import logger
from finchbot.channels.base import BaseChannel
from finchbot.channels.schema import OutboundMessage

class FeishuChannel(BaseChannel):
    name = "feishu"
    
    async def start(self) -> None:
        logger.info("FeishuChannel started (placeholder)")
        # TODO: Implement lark-oapi WSClient

    async def stop(self) -> None:
        logger.info("FeishuChannel stopped")

    async def send(self, msg: OutboundMessage) -> None:
        logger.info(f"FeishuChannel sending to {msg.target_id}: {msg.content}")
