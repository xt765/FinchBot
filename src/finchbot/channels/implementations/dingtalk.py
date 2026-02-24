from loguru import logger
from finchbot.channels.base import BaseChannel
from finchbot.channels.schema import OutboundMessage

class DingTalkChannel(BaseChannel):
    name = "dingtalk"
    
    async def start(self) -> None:
        logger.info("DingTalkChannel started (placeholder)")
        # TODO: Implement dingtalk-stream

    async def stop(self) -> None:
        logger.info("DingTalkChannel stopped")

    async def send(self, msg: OutboundMessage) -> None:
        logger.info(f"DingTalkChannel sending to {msg.target_id}: {msg.content}")
