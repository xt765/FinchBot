from loguru import logger
from finchbot.channels.base import BaseChannel
from finchbot.channels.schema import OutboundMessage

class EmailChannel(BaseChannel):
    name = "email"
    
    async def start(self) -> None:
        logger.info("EmailChannel started (placeholder)")
        # TODO: Implement IMAP polling

    async def stop(self) -> None:
        logger.info("EmailChannel stopped")

    async def send(self, msg: OutboundMessage) -> None:
        logger.info(f"EmailChannel sending to {msg.target_id}: {msg.content}")
