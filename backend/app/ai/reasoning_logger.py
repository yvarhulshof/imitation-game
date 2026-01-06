import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from app.ai.dashboard import AIDashboard


class ReasoningLogger:
    """Structured logger for AI reasoning and decisions."""

    def __init__(self, logs_dir: str = "logs", dashboard: "AIDashboard | None" = None):
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.room_loggers: dict[str, logging.Logger] = {}
        self.dashboard = dashboard

    def get_room_logger(self, room_id: str) -> logging.Logger:
        """Get or create a logger for a specific room."""
        if room_id not in self.room_loggers:
            logger = logging.getLogger(f"reasoning.{room_id}")
            logger.setLevel(logging.INFO)
            logger.propagate = False  # Don't propagate to root logger

            # File handler for this room
            log_file = self.logs_dir / f"room_{room_id}.jsonl"
            handler = logging.FileHandler(log_file)
            handler.setFormatter(JSONFormatter())
            logger.addHandler(handler)

            self.room_loggers[room_id] = logger

        return self.room_loggers[room_id]

    def log_decision(
        self,
        room_id: str,
        player_id: str,
        player_name: str,
        decision_type: str,  # 'chat', 'vote', 'night_action'
        phase: str,
        round_num: int,
        reasoning: str,
        choice: Any = None,
        prompt: str | None = None,
        response: Any | None = None,
        duration_ms: float | None = None,
        **extra_context
    ):
        """Log an AI decision with full context."""
        logger = self.get_room_logger(room_id)

        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "room_id": room_id,
            "player_id": player_id,
            "player_name": player_name,
            "decision_type": decision_type,
            "phase": phase,
            "round": round_num,
            "reasoning": reasoning,
            "choice": choice,
            "duration_ms": duration_ms,
        }

        if prompt:
            record["prompt"] = prompt
        if response:
            record["response"] = response

        record.update(extra_context)

        logger.info(json.dumps(record))

        # Update dashboard
        if self.dashboard:
            self.dashboard.add_thought(room_id, record)

    def log_notes_update(
        self,
        room_id: str,
        player_id: str,
        player_name: str,
        phase: str,
        round_num: int,
        notes: str,
        prompt: str | None = None
    ):
        """Log notes update with full content."""
        logger = self.get_room_logger(room_id)

        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "room_id": room_id,
            "player_id": player_id,
            "player_name": player_name,
            "event_type": "notes_update",
            "phase": phase,
            "round": round_num,
            "notes": notes,
            "notes_length": len(notes),
        }

        if prompt:
            record["prompt"] = prompt

        logger.info(json.dumps(record))

        # Update dashboard
        if self.dashboard:
            self.dashboard.add_thought(room_id, record)

    def cleanup_room(self, room_id: str):
        """Close and remove logger for a room."""
        if room_id in self.room_loggers:
            logger = self.room_loggers[room_id]
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
            del self.room_loggers[room_id]

        # Clean up dashboard
        if self.dashboard:
            self.dashboard.clear_room(room_id)


class JSONFormatter(logging.Formatter):
    """Format log records as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        # The message should already be JSON from log_decision/log_notes_update
        return record.getMessage()
