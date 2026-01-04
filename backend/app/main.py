import logging
import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logging.getLogger("app.game.phase").setLevel(logging.DEBUG)

from app.game.manager import GameManager
from app.game.phase import PhaseController
from app.game.events import register_events
from app.ai.controller import AIController

# Create Socket.IO server
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=["http://localhost:5173"],  # Svelte dev server
)

# Create FastAPI app
app = FastAPI(title="Imitation Game API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Game state manager
game_manager = GameManager()

# AI controller
ai_controller = AIController(sio, game_manager)

# Phase controller (with AI integration)
phase_controller = PhaseController(sio, game_manager, ai_controller)

# Register socket events
register_events(sio, game_manager, phase_controller, ai_controller)

# Wrap FastAPI with Socket.IO
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
