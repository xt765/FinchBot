import asyncio
from typing import Dict
from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger
from finchbot.channels.base import BaseChannel
from finchbot.channels.schema import OutboundMessage

class WebChannel(BaseChannel):
    """
    Web Channel using FastAPI WebSockets.
    
    This channel manages WebSocket connections and forwards messages between
    web clients and the agent core.
    """
    name = "web"
    
    def __init__(self, config, bus):
        super().__init__(config, bus)
        self.active_connections: Dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """
        WebChannel is passive, waiting for WebSocket connections via FastAPI routes.
        It doesn't start a server itself, but relies on the main app.
        """
        logger.info("WebChannel ready to accept connections")

    async def stop(self) -> None:
        """Close all active WebSocket connections."""
        logger.info("WebChannel stopping, closing all connections")
        async with self._lock:
            # Create a copy of items to iterate while modifying
            connections = list(self.active_connections.items())
            for client_id, ws in connections:
                try:
                    await ws.close()
                except Exception:
                    pass
            self.active_connections.clear()

    async def connect(self, websocket: WebSocket, client_id: str):
        """Handle new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections[client_id] = websocket
        logger.info(f"Web client connected: {client_id}")

    async def disconnect(self, client_id: str):
        """Handle WebSocket disconnection."""
        async with self._lock:
            if client_id in self.active_connections:
                del self.active_connections[client_id]
        logger.info(f"Web client disconnected: {client_id}")

    async def handle_incoming(self, client_id: str, content: str):
        """Process incoming message from WebSocket."""
        # Forward to bus
        await self._handle_message(
            sender_id=client_id,
            chat_id=client_id, # For web chat, treat chat_id as client_id (1-on-1)
            content=content
        )

    async def send(self, msg: OutboundMessage) -> None:
        """Send message to a connected web client."""
        client_id = msg.target_id
        
        async with self._lock:
            websocket = self.active_connections.get(client_id)
        
        if websocket:
            try:
                # Send simple text for now. Future: send JSON with metadata
                await websocket.send_text(msg.content)
            except Exception as e:
                logger.error(f"Error sending to web client {client_id}: {e}")
                await self.disconnect(client_id)
        else:
            logger.warning(f"Web client {client_id} not connected, message dropped")
