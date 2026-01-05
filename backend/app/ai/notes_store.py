"""Notes Store - JSON file persistence for AI player notes."""

import json
import logging
import os
from pathlib import Path

from app.config import NOTES_STORAGE_DIR

logger = logging.getLogger(__name__)


class NotesStore:
    """Stores AI player notes in JSON files per game room."""

    def __init__(self, storage_dir: str | None = None):
        self.storage_dir = Path(storage_dir or NOTES_STORAGE_DIR)
        self._ensure_storage_dir()

    def _ensure_storage_dir(self) -> None:
        """Create storage directory if it doesn't exist."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_room_file(self, room_id: str) -> Path:
        """Get the file path for a room's notes."""
        return self.storage_dir / f"{room_id}.json"

    def _load_room_notes(self, room_id: str) -> dict[str, str]:
        """Load all notes for a room."""
        file_path = self._get_room_file(room_id)
        if not file_path.exists():
            return {}
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load notes for room {room_id}: {e}")
            return {}

    def _save_room_notes(self, room_id: str, notes: dict[str, str]) -> None:
        """Save all notes for a room."""
        file_path = self._get_room_file(room_id)
        try:
            with open(file_path, "w") as f:
                json.dump(notes, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save notes for room {room_id}: {e}")

    def save(self, room_id: str, player_id: str, notes: str) -> None:
        """Save notes for a specific AI player."""
        room_notes = self._load_room_notes(room_id)
        room_notes[player_id] = notes
        self._save_room_notes(room_id, room_notes)
        logger.debug(f"Saved notes for player {player_id} in room {room_id}")

    def load(self, room_id: str, player_id: str) -> str | None:
        """Load notes for a specific AI player."""
        room_notes = self._load_room_notes(room_id)
        return room_notes.get(player_id)

    def load_all(self, room_id: str) -> dict[str, str]:
        """Load all notes for a room."""
        return self._load_room_notes(room_id)

    def clear_player(self, room_id: str, player_id: str) -> None:
        """Clear notes for a specific player."""
        room_notes = self._load_room_notes(room_id)
        if player_id in room_notes:
            del room_notes[player_id]
            self._save_room_notes(room_id, room_notes)
            logger.debug(f"Cleared notes for player {player_id} in room {room_id}")

    def clear_room(self, room_id: str) -> None:
        """Clear all notes for a room (called on game end)."""
        file_path = self._get_room_file(room_id)
        if file_path.exists():
            try:
                file_path.unlink()
                logger.info(f"Cleared all notes for room {room_id}")
            except IOError as e:
                logger.error(f"Failed to clear notes for room {room_id}: {e}")
