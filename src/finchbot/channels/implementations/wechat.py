from loguru import logger
from finchbot.channels.base import BaseChannel
from finchbot.channels.schema import OutboundMessage

class WeChatWorkChannel(BaseChannel):
    name = "wechat"
    
    async def start(self) -> None:
        logger.info("WeChatWorkChannel started (placeholder)")
        # TODO: Implement webhook callback registration

    async def stop(self) -> None:
        logger.info("WeChatWorkChannel stopped")

    async def send(self, msg: OutboundMessage) -> None:
        logger.info(f"WeChatWorkChannel sending to {msg.target_id}: {msg.content}")
