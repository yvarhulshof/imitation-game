"""Tests for LLMPlayer functionality."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from app.ai.player import LLMPlayer, truncate_to_tokens
from app.ai.llm_client import LLMClient, LLMError
from app.models import Role, Team, GamePhase


class TestTruncateTokens:
    """Tests for token truncation utility."""

    def test_short_text_unchanged(self):
        """Short text should remain unchanged."""
        text = "Short text"
        result = truncate_to_tokens(text, max_tokens=100)
        assert result == text

    def test_long_text_truncated(self):
        """Long text should be truncated."""
        text = "a" * 1000  # 1000 chars
        result = truncate_to_tokens(text, max_tokens=100)  # ~400 chars
        assert len(result) <= 403  # 400 + "..."
        assert result.endswith("...")

    def test_exact_limit(self):
        """Text at exact limit should remain unchanged."""
        text = "a" * 400  # Exactly 100 tokens worth
        result = truncate_to_tokens(text, max_tokens=100)
        assert result == text


class TestLLMPlayerInit:
    """Tests for LLMPlayer initialization."""

    def test_create_with_defaults(self):
        """Should create player with default LLM client."""
        player = LLMPlayer("ai_123", "TestBot")
        assert player.id == "ai_123"
        assert player.name == "TestBot"
        assert player.role is None
        assert player.team is None
        assert player.notes == ""
        assert player.strategy == ""

    def test_create_with_custom_client(self):
        """Should accept custom LLM client."""
        mock_client = MagicMock(spec=LLMClient)
        player = LLMPlayer("ai_123", "TestBot", llm_client=mock_client)
        assert player.llm_client == mock_client


class TestLLMPlayerSetRole:
    """Tests for role assignment."""

    def test_set_role_loads_strategy(self):
        """Setting role should load appropriate strategy."""
        player = LLMPlayer("ai_123", "TestBot")
        player.set_role(Role.WEREWOLF, Team.MAFIA)

        assert player.role == Role.WEREWOLF
        assert player.team == Team.MAFIA
        assert "Werewolf Strategy" in player.strategy

    def test_set_role_villager(self):
        """Should load villager strategy."""
        player = LLMPlayer("ai_123", "TestBot")
        player.set_role(Role.VILLAGER, Team.TOWN)

        assert "Villager Strategy" in player.strategy

    def test_set_role_seer(self):
        """Should load seer strategy."""
        player = LLMPlayer("ai_123", "TestBot")
        player.set_role(Role.SEER, Team.TOWN)

        assert "Seer Strategy" in player.strategy

    def test_set_role_doctor(self):
        """Should load doctor strategy."""
        player = LLMPlayer("ai_123", "TestBot")
        player.set_role(Role.DOCTOR, Team.TOWN)

        assert "Doctor Strategy" in player.strategy


class TestLLMPlayerBuildContext:
    """Tests for context building."""

    def test_build_context_includes_player_info(self):
        """Should include player's own info."""
        player = LLMPlayer("ai_123", "TestBot")
        player.set_role(Role.WEREWOLF, Team.MAFIA)

        context = player._build_context(
            alive_players=[
                {"id": "ai_123", "name": "TestBot"},
                {"id": "p1", "name": "Alice"},
            ],
            phase=GamePhase.DAY,
        )

        assert context["player_id"] == "ai_123"
        assert context["player_name"] == "TestBot"
        assert context["role"] == Role.WEREWOLF
        assert context["team"] == Team.MAFIA

    def test_build_context_includes_messages(self):
        """Should include chat messages."""
        player = LLMPlayer("ai_123", "TestBot")
        player.set_role(Role.VILLAGER, Team.TOWN)

        messages = [
            {"player_id": "p1", "player_name": "Alice", "content": "Hello!", "timestamp": 100},
        ]

        context = player._build_context(
            alive_players=[{"id": "ai_123", "name": "TestBot"}],
            messages=messages,
        )

        assert len(context["messages"]) == 1
        assert context["messages"][0]["content"] == "Hello!"


def make_full_context(**overrides):
    """Create a full context dict with all required keys."""
    base = {
        "player_id": "ai_123",
        "player_name": "TestBot",
        "role": Role.VILLAGER,
        "team": Team.TOWN,
        "phase": GamePhase.DAY,
        "round_number": 1,
        "alive_players": [{"id": "ai_123", "name": "TestBot"}],
        "dead_players": [],
        "messages": [],
        "vote_counts": {},
        "player_names": {"ai_123": "TestBot"},
        "fellow_wolves": [],
        "seer_results": [],
        "messages_sent": 0,
    }
    base.update(overrides)
    return base


class TestLLMPlayerChat:
    """Tests for chat decision and generation."""

    @pytest.mark.asyncio
    async def test_decide_chat_sends_message(self):
        """Should return message when LLM decides to chat."""
        mock_client = MagicMock(spec=LLMClient)
        mock_client.generate = AsyncMock(return_value={
            "send": True,
            "message": "Anyone suspicious?",
            "reasoning": "Starting conversation",
        })

        player = LLMPlayer("ai_123", "TestBot", llm_client=mock_client)
        player.set_role(Role.VILLAGER, Team.TOWN)

        context = make_full_context()

        message = await player.decide_chat_action(context)

        assert message is not None
        assert message.content == "Anyone suspicious?"
        assert message.player_id == "ai_123"
        assert player.messages_sent == 1

    @pytest.mark.asyncio
    async def test_decide_chat_no_message(self):
        """Should return None when LLM decides not to chat."""
        mock_client = MagicMock(spec=LLMClient)
        mock_client.generate = AsyncMock(return_value={
            "send": False,
            "message": "",
            "reasoning": "Nothing to add",
        })

        player = LLMPlayer("ai_123", "TestBot", llm_client=mock_client)
        player.set_role(Role.VILLAGER, Team.TOWN)

        context = make_full_context()

        message = await player.decide_chat_action(context)

        assert message is None
        assert player.messages_sent == 0

    @pytest.mark.asyncio
    async def test_decide_chat_fallback_on_error(self):
        """Should use fallback when LLM fails."""
        mock_client = MagicMock(spec=LLMClient)
        mock_client.generate = AsyncMock(side_effect=LLMError("API error"))

        player = LLMPlayer("ai_123", "TestBot", llm_client=mock_client)
        player.set_role(Role.VILLAGER, Team.TOWN)

        context = make_full_context(
            alive_players=[
                {"id": "ai_123", "name": "TestBot"},
                {"id": "p1", "name": "Alice"},
            ],
            player_names={"ai_123": "TestBot", "p1": "Alice"},
        )

        # Fallback is random, might return None or a message
        # Just verify it doesn't raise
        message = await player.decide_chat_action(context)
        # Message is either None or a valid ChatMessage


class TestLLMPlayerVoting:
    """Tests for vote decision."""

    @pytest.mark.asyncio
    async def test_choose_vote_target(self):
        """Should choose a valid vote target."""
        mock_client = MagicMock(spec=LLMClient)
        mock_client.generate = AsyncMock(return_value={
            "target": "p1",
            "reasoning": "Suspicious behavior",
        })

        player = LLMPlayer("ai_123", "TestBot", llm_client=mock_client)
        player.set_role(Role.VILLAGER, Team.TOWN)

        context = make_full_context(
            alive_players=[
                {"id": "ai_123", "name": "TestBot"},
                {"id": "p1", "name": "Alice"},
                {"id": "p2", "name": "Bob"},
            ],
            player_names={"ai_123": "TestBot", "p1": "Alice", "p2": "Bob"},
        )

        valid_targets = [
            {"id": "p1", "name": "Alice"},
            {"id": "p2", "name": "Bob"},
        ]

        target = await player.choose_vote_target(context, valid_targets)

        assert target == "p1"

    @pytest.mark.asyncio
    async def test_choose_vote_validates_target(self):
        """Should fallback to random if LLM returns invalid target."""
        mock_client = MagicMock(spec=LLMClient)
        mock_client.generate = AsyncMock(return_value={
            "target": "invalid_id",
            "reasoning": "Made up target",
        })

        player = LLMPlayer("ai_123", "TestBot", llm_client=mock_client)
        player.set_role(Role.VILLAGER, Team.TOWN)

        context = make_full_context(
            alive_players=[
                {"id": "ai_123", "name": "TestBot"},
                {"id": "p1", "name": "Alice"},
                {"id": "p2", "name": "Bob"},
            ],
            player_names={"ai_123": "TestBot", "p1": "Alice", "p2": "Bob"},
        )

        valid_targets = [
            {"id": "p1", "name": "Alice"},
            {"id": "p2", "name": "Bob"},
        ]

        target = await player.choose_vote_target(context, valid_targets)

        # Should fallback to a valid target
        assert target in ["p1", "p2"]

    @pytest.mark.asyncio
    async def test_choose_vote_empty_targets(self):
        """Should return None for empty targets."""
        player = LLMPlayer("ai_123", "TestBot")
        player.set_role(Role.VILLAGER, Team.TOWN)

        context = make_full_context()
        target = await player.choose_vote_target(context, [])

        assert target is None


class TestLLMPlayerNightAction:
    """Tests for night action decision."""

    @pytest.mark.asyncio
    async def test_werewolf_choose_target(self):
        """Werewolf should choose a kill target."""
        mock_client = MagicMock(spec=LLMClient)
        mock_client.generate = AsyncMock(return_value={
            "target": "p1",
            "reasoning": "Likely the seer",
        })

        player = LLMPlayer("ai_wolf", "WolfBot", llm_client=mock_client)
        player.set_role(Role.WEREWOLF, Team.MAFIA)

        context = make_full_context(
            player_id="ai_wolf",
            player_name="WolfBot",
            role=Role.WEREWOLF,
            team=Team.MAFIA,
            phase=GamePhase.NIGHT,
            alive_players=[
                {"id": "ai_wolf", "name": "WolfBot"},
                {"id": "p1", "name": "Alice"},
            ],
            player_names={"ai_wolf": "WolfBot", "p1": "Alice"},
        )

        valid_targets = [{"id": "p1", "name": "Alice"}]

        target = await player.choose_night_action_target(context, valid_targets)

        assert target == "p1"

    @pytest.mark.asyncio
    async def test_villager_no_night_action(self):
        """Villager should return None for night action."""
        player = LLMPlayer("ai_123", "TestBot")
        player.set_role(Role.VILLAGER, Team.TOWN)

        context = make_full_context(phase=GamePhase.NIGHT)
        valid_targets = [{"id": "p1", "name": "Alice"}]

        target = await player.choose_night_action_target(context, valid_targets)

        assert target is None


class TestLLMPlayerNotes:
    """Tests for notes management."""

    @pytest.mark.asyncio
    async def test_update_notes(self):
        """Should update notes from LLM response."""
        mock_client = MagicMock(spec=LLMClient)
        mock_client.generate = AsyncMock(return_value="Alice is suspicious based on voting pattern")

        player = LLMPlayer("ai_123", "TestBot", llm_client=mock_client)
        player.set_role(Role.VILLAGER, Team.TOWN)

        context = make_full_context()

        await player.update_notes(context)

        assert "Alice is suspicious" in player.notes

    @pytest.mark.asyncio
    async def test_update_notes_preserves_on_error(self):
        """Should preserve existing notes on LLM error."""
        mock_client = MagicMock(spec=LLMClient)
        mock_client.generate = AsyncMock(side_effect=LLMError("API error"))

        player = LLMPlayer("ai_123", "TestBot", llm_client=mock_client)
        player.set_role(Role.VILLAGER, Team.TOWN)
        player.notes = "Original notes"

        context = make_full_context()

        await player.update_notes(context)

        assert player.notes == "Original notes"

    def test_add_seer_result(self):
        """Should track seer investigation results."""
        player = LLMPlayer("ai_seer", "SeerBot")
        player.set_role(Role.SEER, Team.TOWN)

        player.add_seer_result("Alice", is_wolf=False)
        player.add_seer_result("Bob", is_wolf=True)

        assert len(player.seer_results) == 2
        assert player.seer_results[0] == {"name": "Alice", "is_wolf": "Not a werewolf"}
        assert player.seer_results[1] == {"name": "Bob", "is_wolf": "Werewolf"}


class TestLLMPlayerResetForNewDay:
    """Tests for daily reset."""

    def test_reset_counters(self):
        """Should reset message counters."""
        player = LLMPlayer("ai_123", "TestBot")
        player.messages_sent = 5

        player.reset_for_new_day()

        assert player.messages_sent == 0
        assert player.max_messages_per_phase >= 3
        assert player.max_messages_per_phase <= 6
