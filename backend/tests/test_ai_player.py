"""Tests for AI player functionality."""

import pytest
from app.ai.player import (
    MockAIPlayer,
    generate_ai_id,
    get_random_name,
    AI_NAMES,
    DAY_CHAT_MESSAGES,
)
from app.models import Role, Team


class TestAIIdGeneration:
    """Tests for AI ID generation."""

    def test_generate_ai_id_has_prefix(self):
        """AI IDs should have 'ai_' prefix."""
        ai_id = generate_ai_id()
        assert ai_id.startswith("ai_")

    def test_generate_ai_id_unique(self):
        """Each generated ID should be unique."""
        ids = [generate_ai_id() for _ in range(100)]
        assert len(set(ids)) == 100


class TestAINameGeneration:
    """Tests for AI name generation."""

    def test_get_random_name_from_pool(self):
        """Should return a name from the AI names pool."""
        name = get_random_name([])
        assert name in AI_NAMES

    def test_get_random_name_avoids_duplicates(self):
        """Should not return names already in use."""
        existing = ["Alex", "Jordan", "Taylor"]
        name = get_random_name(existing)
        assert name not in existing

    def test_get_random_name_fallback(self):
        """Should fallback to numbered names if pool exhausted."""
        existing = AI_NAMES.copy()
        name = get_random_name(existing)
        assert name.startswith("Player")


class TestMockAIPlayer:
    """Tests for MockAIPlayer behavior."""

    def test_create_mock_ai_player(self):
        """Should create AI player with correct attributes."""
        player = MockAIPlayer("ai_123", "Alex")
        assert player.id == "ai_123"
        assert player.name == "Alex"
        assert player.role is None
        assert player.team is None

    def test_set_role(self):
        """Should set role and team."""
        player = MockAIPlayer("ai_123", "Alex")
        player.set_role(Role.WEREWOLF, Team.MAFIA)
        assert player.role == Role.WEREWOLF
        assert player.team == Team.MAFIA

    def test_reset_for_new_day(self):
        """Should reset daily counters."""
        player = MockAIPlayer("ai_123", "Alex")
        player.messages_sent = 5
        player.reset_for_new_day()
        assert player.messages_sent == 0


class TestMockAIPlayerChat:
    """Tests for AI chat message generation."""

    def test_generate_chat_message_returns_string(self):
        """Should return a non-empty string."""
        player = MockAIPlayer("ai_123", "Alex")
        player.set_role(Role.VILLAGER, Team.TOWN)
        message = player.generate_chat_message(["Bob", "Charlie"])
        assert isinstance(message, str)
        assert len(message) > 0

    def test_generate_defense_message_when_accused(self):
        """Should return a defense message when accused."""
        player = MockAIPlayer("ai_123", "Alex")
        player.set_role(Role.VILLAGER, Team.TOWN)
        message = player.generate_chat_message(["Bob"], is_accused=True)
        assert message in DAY_CHAT_MESSAGES["defense"]

    def test_should_chat_respects_message_limit(self):
        """Should return False when max messages reached."""
        player = MockAIPlayer("ai_123", "Alex")
        player.max_messages_per_day = 3
        player.messages_sent = 3
        assert player.should_chat(100.0, 0.0) is False

    def test_should_chat_respects_interval(self):
        """Should return False when called too soon after last message."""
        player = MockAIPlayer("ai_123", "Alex")
        player.last_message_time = 100.0
        # Only 1 second since last message - should be False
        assert player.should_chat(101.0, 0.0) is False


class TestMockAIPlayerVoting:
    """Tests for AI voting behavior."""

    def test_choose_vote_target_excludes_self(self):
        """Should not vote for itself."""
        player = MockAIPlayer("ai_123", "Alex")
        player.set_role(Role.VILLAGER, Team.TOWN)

        alive_players = [
            {"id": "ai_123", "name": "Alex"},
            {"id": "p1", "name": "Bob"},
            {"id": "p2", "name": "Charlie"},
        ]

        for _ in range(20):
            target = player.choose_vote_target(alive_players)
            assert target != "ai_123"

    def test_werewolf_vote_excludes_fellow_wolves(self):
        """Werewolves should not vote for fellow wolves."""
        player = MockAIPlayer("ai_wolf", "WolfAlex")
        player.set_role(Role.WEREWOLF, Team.MAFIA)

        alive_players = [
            {"id": "ai_wolf", "name": "WolfAlex"},
            {"id": "wolf2", "name": "WolfBob"},
            {"id": "p1", "name": "Charlie"},
            {"id": "p2", "name": "David"},
        ]

        known_wolves = ["ai_wolf", "wolf2"]

        for _ in range(20):
            target = player.choose_vote_target(alive_players, known_wolves)
            assert target not in known_wolves

    def test_choose_vote_returns_none_if_no_valid_targets(self):
        """Should return None if no valid targets."""
        player = MockAIPlayer("ai_123", "Alex")
        player.set_role(Role.VILLAGER, Team.TOWN)

        alive_players = [{"id": "ai_123", "name": "Alex"}]
        target = player.choose_vote_target(alive_players)
        assert target is None


class TestMockAIPlayerNightActions:
    """Tests for AI night action behavior."""

    def test_werewolf_targets_non_wolves(self):
        """Werewolf should target non-wolves."""
        player = MockAIPlayer("ai_wolf", "WolfAlex")
        player.set_role(Role.WEREWOLF, Team.MAFIA)

        alive_players = [
            {"id": "ai_wolf", "name": "WolfAlex"},
            {"id": "wolf2", "name": "WolfBob"},
            {"id": "p1", "name": "Charlie"},
        ]

        fellow_wolves = ["ai_wolf", "wolf2"]

        for _ in range(20):
            target = player.choose_night_action_target(alive_players, fellow_wolves)
            assert target not in fellow_wolves

    def test_seer_cannot_investigate_self(self):
        """Seer should not investigate itself."""
        player = MockAIPlayer("ai_seer", "SeerAlex")
        player.set_role(Role.SEER, Team.TOWN)

        alive_players = [
            {"id": "ai_seer", "name": "SeerAlex"},
            {"id": "p1", "name": "Bob"},
        ]

        for _ in range(20):
            target = player.choose_night_action_target(alive_players)
            assert target != "ai_seer"

    def test_doctor_can_protect_self(self):
        """Doctor should be able to protect itself."""
        player = MockAIPlayer("ai_doc", "DocAlex")
        player.set_role(Role.DOCTOR, Team.TOWN)

        alive_players = [{"id": "ai_doc", "name": "DocAlex"}]

        # With only self as target, should return self
        target = player.choose_night_action_target(alive_players)
        assert target == "ai_doc"

    def test_villager_has_no_night_action(self):
        """Villager should return None for night action."""
        player = MockAIPlayer("ai_123", "Alex")
        player.set_role(Role.VILLAGER, Team.TOWN)

        alive_players = [
            {"id": "ai_123", "name": "Alex"},
            {"id": "p1", "name": "Bob"},
        ]

        target = player.choose_night_action_target(alive_players)
        assert target is None
