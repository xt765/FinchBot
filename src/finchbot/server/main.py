from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pathlib import Path
from loguru import logger
import asyncio

from finchbot.config.loader import load_config
from finchbot.channels.bus import MessageBus
from finchbot.channels.manager import ChannelManager
from finchbot.server.loop import AgentLoop
from finchbot.channels.implementations.web import WebChannel

# Global instances (to be accessed by routes)
# In a larger app, we might use dependency injection or app.state
bus = None
manager = None
loop = None
web_channel = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global bus, manager, loop, web_channel
    
    # 1. Load Config
    logger.info("Loading configuration...")
    # Assuming standard config loading. 
    # TODO: Allow passing config path via env var or similar if needed.
    config = load_config()
    
    # TODO: Make workspace configurable
    workspace = Path("./finchbot_workspace").resolve()
    workspace.mkdir(exist_ok=True)
    
    # 2. Init Components
    bus = MessageBus()
    manager = ChannelManager(config, bus)
    loop = AgentLoop(bus, config, workspace)
    
    # 3. Register Channels
    # WebChannel is special as it needs direct access from routes
    web_channel = WebChannel(config, bus)
    manager.register_channel("web", web_channel)
    
    # Register other channels here in future phases
    # e.g., if config.channels.discord.enabled: ...
    
    # 4. Start Services
    # Start loop first to be ready for messages
    await loop.start()
    # Start channels
    await manager.start_all()
    
    logger.info("FinchBot Server started successfully")
    
    yield
    
    # 5. Shutdown
    logger.info("Shutting down FinchBot Server...")
    await manager.stop_all()
    await loop.stop()

app = FastAPI(title="FinchBot Server", lifespan=lifespan)

@app.websocket("/ws/chat/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    WebSocket endpoint for chat.
    Connects to the WebChannel instance.
    """
    if not web_channel:
        await websocket.close(code=1011, reason="Server initializing")
        return
        
    await web_channel.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            await web_channel.handle_incoming(client_id, data)
    except WebSocketDisconnect:
        await web_channel.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
        await web_channel.disconnect(client_id)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    channels = list(manager.channels.keys()) if manager else []
    return {
        "status": "ok", 
        "channels": channels,
        "agent_active": loop._running if loop else False
    }
