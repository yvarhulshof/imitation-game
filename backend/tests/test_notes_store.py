"""Tests for NotesStore functionality."""

import json
import os
import pytest
import tempfile
from pathlib import Path

from app.ai.notes_store import NotesStore


@pytest.fixture
def temp_storage_dir():
    """Create a temporary directory for test storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def notes_store(temp_storage_dir):
    """Create a NotesStore with temporary directory."""
    return NotesStore(storage_dir=temp_storage_dir)


class TestNotesStoreInit:
    """Tests for NotesStore initialization."""

    def test_creates_storage_directory(self, temp_storage_dir):
        """Should create storage directory if it doesn't exist."""
        new_dir = os.path.join(temp_storage_dir, "nested", "notes")
        store = NotesStore(storage_dir=new_dir)
        assert os.path.exists(new_dir)

    def test_uses_existing_directory(self, temp_storage_dir):
        """Should work with existing directory."""
        store = NotesStore(storage_dir=temp_storage_dir)
        assert store.storage_dir == Path(temp_storage_dir)


class TestNotesStoreSaveLoad:
    """Tests for saving and loading notes."""

    def test_save_and_load_notes(self, notes_store):
        """Should save and load notes correctly."""
        notes_store.save("room_123", "player_1", "Player 1 is suspicious")

        loaded = notes_store.load("room_123", "player_1")
        assert loaded == "Player 1 is suspicious"

    def test_load_nonexistent_notes(self, notes_store):
        """Should return None for nonexistent notes."""
        loaded = notes_store.load("room_123", "nonexistent")
        assert loaded is None

    def test_save_multiple_players(self, notes_store):
        """Should save notes for multiple players in same room."""
        notes_store.save("room_123", "player_1", "Notes for player 1")
        notes_store.save("room_123", "player_2", "Notes for player 2")

        assert notes_store.load("room_123", "player_1") == "Notes for player 1"
        assert notes_store.load("room_123", "player_2") == "Notes for player 2"

    def test_save_overwrites_existing(self, notes_store):
        """Should overwrite existing notes."""
        notes_store.save("room_123", "player_1", "Initial notes")
        notes_store.save("room_123", "player_1", "Updated notes")

        loaded = notes_store.load("room_123", "player_1")
        assert loaded == "Updated notes"

    def test_load_all_room_notes(self, notes_store):
        """Should load all notes for a room."""
        notes_store.save("room_123", "p1", "Notes 1")
        notes_store.save("room_123", "p2", "Notes 2")
        notes_store.save("room_123", "p3", "Notes 3")

        all_notes = notes_store.load_all("room_123")
        assert len(all_notes) == 3
        assert all_notes["p1"] == "Notes 1"
        assert all_notes["p2"] == "Notes 2"
        assert all_notes["p3"] == "Notes 3"

    def test_load_all_empty_room(self, notes_store):
        """Should return empty dict for room with no notes."""
        all_notes = notes_store.load_all("nonexistent_room")
        assert all_notes == {}


class TestNotesStoreClear:
    """Tests for clearing notes."""

    def test_clear_player_notes(self, notes_store):
        """Should clear notes for specific player."""
        notes_store.save("room_123", "player_1", "Notes for player 1")
        notes_store.save("room_123", "player_2", "Notes for player 2")

        notes_store.clear_player("room_123", "player_1")

        assert notes_store.load("room_123", "player_1") is None
        assert notes_store.load("room_123", "player_2") == "Notes for player 2"

    def test_clear_room_notes(self, notes_store, temp_storage_dir):
        """Should clear all notes for a room."""
        notes_store.save("room_123", "player_1", "Notes 1")
        notes_store.save("room_123", "player_2", "Notes 2")

        notes_store.clear_room("room_123")

        # File should be deleted
        room_file = Path(temp_storage_dir) / "room_123.json"
        assert not room_file.exists()

        # Loading should return empty/None
        assert notes_store.load("room_123", "player_1") is None
        assert notes_store.load_all("room_123") == {}

    def test_clear_nonexistent_room(self, notes_store):
        """Should not raise error when clearing nonexistent room."""
        # Should not raise
        notes_store.clear_room("nonexistent_room")


class TestNotesStoreRoomIsolation:
    """Tests for room isolation."""

    def test_rooms_are_isolated(self, notes_store):
        """Notes in different rooms should be isolated."""
        notes_store.save("room_1", "player_1", "Room 1 notes")
        notes_store.save("room_2", "player_1", "Room 2 notes")

        assert notes_store.load("room_1", "player_1") == "Room 1 notes"
        assert notes_store.load("room_2", "player_1") == "Room 2 notes"

    def test_clear_room_doesnt_affect_others(self, notes_store):
        """Clearing one room shouldn't affect others."""
        notes_store.save("room_1", "player_1", "Room 1 notes")
        notes_store.save("room_2", "player_1", "Room 2 notes")

        notes_store.clear_room("room_1")

        assert notes_store.load("room_1", "player_1") is None
        assert notes_store.load("room_2", "player_1") == "Room 2 notes"


class TestNotesStoreFilePersistence:
    """Tests for file persistence."""

    def test_notes_persist_to_file(self, temp_storage_dir):
        """Notes should persist in JSON files."""
        store1 = NotesStore(storage_dir=temp_storage_dir)
        store1.save("room_abc", "player_1", "Persistent notes")

        # Create new store instance pointing to same directory
        store2 = NotesStore(storage_dir=temp_storage_dir)
        loaded = store2.load("room_abc", "player_1")

        assert loaded == "Persistent notes"

    def test_file_format_is_json(self, notes_store, temp_storage_dir):
        """Stored files should be valid JSON."""
        notes_store.save("room_xyz", "p1", "Test notes")

        room_file = Path(temp_storage_dir) / "room_xyz.json"
        with open(room_file, "r") as f:
            data = json.load(f)

        assert data == {"p1": "Test notes"}

    def test_handles_special_characters(self, notes_store):
        """Should handle notes with special characters."""
        special_notes = 'Notes with "quotes" and newlines\nand unicode: 🐺'
        notes_store.save("room_123", "player_1", special_notes)

        loaded = notes_store.load("room_123", "player_1")
        assert loaded == special_notes
