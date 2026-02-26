from loguru import logger

from finchbot.channels.base import BaseChannel
from finchbot.channels.schema import OutboundMessage


class DiscordChannel(BaseChannel):
    """Discord Channel - simplified like nanobot."""

    name = "discord"

    def __init__(self, config, bus):
        super().__init__(config, bus)
        self.token = config.get("discord", {}).get("token")
        self.client = None

    async def start(self):
        if not self.token:
            logger.warning("Discord token not configured")
            return

        try:
            import discord
            intents = discord.Intents.default()
            intents.message_content = True
            self.client = discord.Client(intents=intents)

            @self.client.event
            async def on_ready():
                logger.info(f"Discord bot logged in as {self.client.user}")

            @self.client.event
            async def on_message(message):
                if message.author.bot:
                    return
                await self._handle_message(
                    sender_id=str(message.author.id),
                    chat_id=str(message.channel.id),
                    content=message.content,
                    metadata={"username": message.author.name}
                )

            await self.client.start(self.token)
        except ImportError:
            logger.error("discord-py not installed. Run: pip install discord-py")
        except Exception as e:
            logger.error(f"Discord error: {e}")

    async def stop(self):
        if self.client:
            await self.client.close()
            logger.info("Discord stopped")

    async def send(self, msg: OutboundMessage):
        if not self.client:
            return
        try:
            channel = self.client.get_channel(int(msg.target_id))
            if channel:
                await channel.send(msg.content)
        except Exception as e:
            logger.error(f"Discord send error: {e}")

    @property
    def connection_count(self):
        return len(self.client.guilds) if self.client else 0

    @property
    def status(self):
        if self.client and self.client.is_ready():
            return "running"
        return "stopped"
