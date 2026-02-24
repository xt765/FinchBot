import asyncio
from typing import Dict, Any, Optional
from loguru import logger
from .bus import MessageBus
from .base import BaseChannel

class ChannelManager:
    """Manages chat channels and coordinates message routing."""
    
    def __init__(self, config: Any, bus: MessageBus):
        self.config = config
        self.bus = bus
        self.channels: Dict[str, BaseChannel] = {}
        self._dispatch_task: Optional[asyncio.Task] = None
        # Channels should be registered manually or via a loader method

    def register_channel(self, name: str, channel: BaseChannel) -> None:
        """Register a channel instance."""
        self.channels[name] = channel
        logger.info(f"Registered channel: {name}")

    async def start_all(self) -> None:
        """Start all channels and the outbound dispatcher."""
        # Start outbound dispatcher regardless of channels, though it needs channels to work
        self._dispatch_task = asyncio.create_task(self._dispatch_outbound())
        logger.info("Outbound dispatcher started")
        
        if not self.channels:
            logger.warning("No channels registered to start")
            return
        
        # Start channels
        # We don't await them as they are long-running loops
        for name, channel in self.channels.items():
            logger.info(f"Starting {name} channel...")
            asyncio.create_task(self._start_channel_safe(name, channel))

    async def _start_channel_safe(self, name: str, channel: BaseChannel) -> None:
        """Safely start a channel and log errors if it crashes."""
        try:
            await channel.start()
        except asyncio.CancelledError:
            logger.info(f"Channel {name} cancelled")
        except Exception as e:
            logger.exception(f"Channel {name} crashed: {e}")

    async def stop_all(self) -> None:
        """Stop all channels and the dispatcher."""
        logger.info("Stopping all channels...")
        
        if self._dispatch_task:
            self._dispatch_task.cancel()
            try:
                await self._dispatch_task
            except asyncio.CancelledError:
                pass
        
        stop_tasks = []
        for name, channel in self.channels.items():
            stop_tasks.append(self._stop_channel_safe(name, channel))
            
        if stop_tasks:
            await asyncio.gather(*stop_tasks)

    async def _stop_channel_safe(self, name: str, channel: BaseChannel) -> None:
        try:
            await channel.stop()
            logger.info(f"Stopped {name} channel")
        except Exception as e:
            logger.error(f"Error stopping {name}: {e}")

    async def _dispatch_outbound(self) -> None:
        """Dispatch outbound messages to the appropriate channel."""
        while True:
            try:
                # Blocks until message available
                msg = await self.bus.consume_outbound()
                
                channel = self.channels.get(msg.target_channel)
                if channel:
                    try:
                        # We await here to ensure ordered delivery per message if needed,
                        # but could be parallelized if strictly necessary.
                        await channel.send(msg)
                    except Exception as e:
                        logger.error(f"Error sending to {msg.target_channel}: {e}")
                else:
                    logger.warning(f"Unknown target channel: {msg.target_channel}")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in dispatcher: {e}")
                await asyncio.sleep(1) # Prevent tight loop on repeated errors
