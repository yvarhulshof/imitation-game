"""Tests for GameManager disconnect handling."""

import pytest
from app.game.manager import GameManager


class TestPlayerRoomTracking:
    """Test that GameManager tracks which room each player is in."""

    def test_get_player_room_returns_room_id_after_join(self):
        """After joining, we can find which room the player is in."""
        manager = GameManager()
        room_id = manager.create_room()
        manager.join_room(room_id, "player-1", "Alice")

        assert manager.get_player_room("player-1") == room_id

    def test_get_player_room_returns_none_for_unknown_player(self):
        """Unknown players return None."""
        manager = GameManager()

        assert manager.get_player_room("unknown") is None

    def test_get_player_room_returns_none_after_leave(self):
        """After leaving, player-room mapping is removed."""
        manager = GameManager()
        room_id = manager.create_room()
        manager.join_room(room_id, "player-1", "Alice")
        manager.leave_room(room_id, "player-1")

        assert manager.get_player_room("player-1") is None

    def test_tracks_multiple_players_in_same_room(self):
        """Multiple players in same room are tracked correctly."""
        manager = GameManager()
        room_id = manager.create_room()
        manager.join_room(room_id, "player-1", "Alice")
        manager.join_room(room_id, "player-2", "Bob")

        assert manager.get_player_room("player-1") == room_id
        assert manager.get_player_room("player-2") == room_id

    def test_tracks_players_across_different_rooms(self):
        """Players in different rooms are tracked correctly."""
        manager = GameManager()
        room_1 = manager.create_room()
        room_2 = manager.create_room()
        manager.join_room(room_1, "player-1", "Alice")
        manager.join_room(room_2, "player-2", "Bob")

        assert manager.get_player_room("player-1") == room_1
        assert manager.get_player_room("player-2") == room_2


class TestDisconnectPlayer:
    """Test disconnect_player method that handles cleanup by sid."""

    def test_disconnect_removes_player_from_room(self):
        """Disconnecting removes player from their room."""
        manager = GameManager()
        room_id = manager.create_room()
        manager.join_room(room_id, "player-1", "Alice")
        manager.join_room(room_id, "player-2", "Bob")

        result = manager.disconnect_player("player-1")

        game = manager.get_game(room_id)
        assert game is not None
        assert "player-1" not in game.players
        assert "player-2" in game.players
        assert result is not None
        assert result["room_id"] == room_id

    def test_disconnect_returns_none_for_unknown_player(self):
        """Disconnecting unknown player returns None."""
        manager = GameManager()

        result = manager.disconnect_player("unknown")

        assert result is None

    def test_disconnect_cleans_up_empty_room(self):
        """When last player disconnects, room is deleted."""
        manager = GameManager()
        room_id = manager.create_room()
        manager.join_room(room_id, "player-1", "Alice")

        manager.disconnect_player("player-1")

        assert manager.get_game(room_id) is None

    def test_disconnect_returns_player_info(self):
        """Disconnect returns info about the disconnected player."""
        manager = GameManager()
        room_id = manager.create_room()
        manager.join_room(room_id, "player-1", "Alice")

        result = manager.disconnect_player("player-1")

        assert result["player_id"] == "player-1"
        assert result["player_name"] == "Alice"
        assert result["room_id"] == room_id


class TestHostTransfer:
    """Test that host is transferred when host disconnects."""

    def test_host_transferred_when_host_disconnects(self):
        """When host leaves, another player becomes host."""
        manager = GameManager()
        room_id = manager.create_room()
        manager.join_room(room_id, "host-player", "Alice")
        manager.join_room(room_id, "player-2", "Bob")

        result = manager.disconnect_player("host-player")

        game = manager.get_game(room_id)
        assert game is not None
        # Bob should now be host
        assert game.players["player-2"].is_host is True
        assert result["new_host_id"] == "player-2"

    def test_no_host_transfer_when_non_host_disconnects(self):
        """When non-host leaves, host remains unchanged."""
        manager = GameManager()
        room_id = manager.create_room()
        manager.join_room(room_id, "host-player", "Alice")
        manager.join_room(room_id, "player-2", "Bob")

        result = manager.disconnect_player("player-2")

        game = manager.get_game(room_id)
        assert game.players["host-player"].is_host is True
        assert result.get("new_host_id") is None

    def test_no_host_transfer_when_room_becomes_empty(self):
        """When last player leaves, no host transfer needed."""
        manager = GameManager()
        room_id = manager.create_room()
        manager.join_room(room_id, "player-1", "Alice")

        result = manager.disconnect_player("player-1")

        assert result.get("new_host_id") is None
