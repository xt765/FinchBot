import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from loguru import logger
import asyncio

from finchbot.config.loader import load_config
from finchbot.channels.bus import MessageBus
from finchbot.channels.manager import ChannelManager
from finchbot.server.loop import AgentLoop
from finchbot.channels.implementations.web import WebChannel

bus = None
manager = None
loop = None
web_channel = None

STATIC_DIR = Path(os.getenv("STATIC_DIR", Path(__file__).parent.parent.parent.parent / "web" / "dist"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    global bus, manager, loop, web_channel
    
    logger.info("Loading configuration...")
    config = load_config()
    
    workspace = Path("./finchbot_workspace").resolve()
    workspace.mkdir(exist_ok=True)
    
    bus = MessageBus()
    manager = ChannelManager(config, bus)
    loop = AgentLoop(bus, config, workspace)
    
    web_channel = WebChannel(config, bus)
    manager.register_channel("web", web_channel)
    
    await loop.start()
    await manager.start_all()
    
    logger.info("FinchBot Server started successfully")
    
    yield
    
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

@app.get("/api/info")
async def api_info():
    """API info endpoint."""
    return {
        "name": "FinchBot",
        "version": "0.1.0",
        "description": "Lightweight AI Agent Framework"
    }

if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """Serve SPA - return index.html for all non-API routes."""
        file_path = STATIC_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")
