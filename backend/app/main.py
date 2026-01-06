import logging
import socketio
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console
        logging.FileHandler(logs_dir / "game.log")  # File
    ]
)

# Debug logging for phase transitions
logging.getLogger("app.game.phase").setLevel(logging.DEBUG)

from app.game.manager import GameManager
from app.game.phase import PhaseController
from app.game.events import register_events
from app.ai.controller import AIController
from app.ai.reasoning_logger import ReasoningLogger
from app.ai.dashboard import AIDashboard

# Create Socket.IO server
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=["http://localhost:5173", "http://localhost:5174"],  # Svelte dev server
)

# Create FastAPI app
app = FastAPI(title="Imitation Game API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Game state manager
game_manager = GameManager()

# Create dashboard
dashboard = AIDashboard(output_dir=str(logs_dir / "dashboard"))

# Create reasoning logger (with dashboard)
reasoning_logger = ReasoningLogger(
    logs_dir=str(logs_dir / "reasoning"),
    dashboard=dashboard
)

# AI controller (with reasoning logger)
ai_controller = AIController(sio, game_manager, reasoning_logger=reasoning_logger)

# Phase controller (with AI integration)
phase_controller = PhaseController(sio, game_manager, ai_controller)

# Register socket events
register_events(sio, game_manager, phase_controller, ai_controller)

# Wrap FastAPI with Socket.IO
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
