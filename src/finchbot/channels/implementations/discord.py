from loguru import logger
from finchbot.channels.base import BaseChannel
from finchbot.channels.schema import OutboundMessage

class DiscordChannel(BaseChannel):
    name = "discord"
    
    async def start(self) -> None:
        logger.info("DiscordChannel started (placeholder)")
        # TODO: Implement discord.Client

    async def stop(self) -> None:
        logger.info("DiscordChannel stopped")

    async def send(self, msg: OutboundMessage) -> None:
        logger.info(f"DiscordChannel sending to {msg.target_id}: {msg.content}")
