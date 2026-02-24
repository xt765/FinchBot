from abc import ABC, abstractmethod
from typing import Any, List, Optional
from loguru import logger
from .bus import MessageBus
from .schema import InboundMessage, OutboundMessage

class BaseChannel(ABC):
    """
    Abstract base class for chat channel implementations.
    
    Each channel (Telegram, Discord, etc.) should implement this interface
    to integrate with the FinchBot message bus.
    """
    
    name: str = "base"
    
    def __init__(self, config: Any, bus: MessageBus):
        self.config = config
        self.bus = bus
        self._running = False
    
    @abstractmethod
    async def start(self) -> None:
        """
        Start the channel and begin listening for messages.
        
        This should be a long-running async task that:
        1. Connects to the chat platform
        2. Listens for incoming messages
        3. Forwards messages to the bus via _handle_message()
        """
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop the channel and clean up resources."""
        pass
    
    @abstractmethod
    async def send(self, msg: OutboundMessage) -> None:
        """Send a message through this channel."""
        pass
    
    async def _handle_message(
        self,
        sender_id: str,
        chat_id: str,
        content: str,
        media: Optional[List[str]] = None,
        metadata: Optional[dict[str, Any]] = None
    ) -> None:
        """Handle an incoming message from the chat platform."""
        msg = InboundMessage(
            channel=self.name,
            sender_id=str(sender_id),
            chat_id=str(chat_id),
            content=content,
            media=media or [],
            metadata=metadata or {}
        )
        
        await self.bus.publish_inbound(msg)
