"""Tests for night action functionality."""

import pytest
from app.game.state import GameState
from app.models import Player, PlayerType, GamePhase, Role, Team, ROLE_TEAMS


def create_test_game_with_players():
    """Create a game with a standard set of players for testing."""
    game = GameState(room_id="test-room")
    game.phase = GamePhase.NIGHT

    # Create players with roles
    players = [
        Player(id="wolf1", name="Wolf1", player_type=PlayerType.HUMAN, role=Role.WEREWOLF, team=Team.MAFIA),
        Player(id="wolf2", name="Wolf2", player_type=PlayerType.HUMAN, role=Role.WEREWOLF, team=Team.MAFIA),
        Player(id="seer", name="Seer", player_type=PlayerType.HUMAN, role=Role.SEER, team=Team.TOWN),
        Player(id="doctor", name="Doctor", player_type=PlayerType.HUMAN, role=Role.DOCTOR, team=Team.TOWN),
        Player(id="villager1", name="Villager1", player_type=PlayerType.HUMAN, role=Role.VILLAGER, team=Team.TOWN),
        Player(id="villager2", name="Villager2", player_type=PlayerType.HUMAN, role=Role.VILLAGER, team=Team.TOWN),
    ]

    for p in players:
        game.add_player(p)

    return game


class TestWerewolfVote:
    """Test werewolf voting functionality."""

    def test_werewolf_can_vote_to_kill_villager(self):
        """Werewolf can vote to kill a villager."""
        game = create_test_game_with_players()

        result = game.submit_werewolf_vote("wolf1", "villager1")

        assert result is True
        assert game.werewolf_votes["wolf1"] == "villager1"

    def test_werewolf_cannot_vote_to_kill_fellow_werewolf(self):
        """Werewolf cannot target another werewolf."""
        game = create_test_game_with_players()

        result = game.submit_werewolf_vote("wolf1", "wolf2")

        assert result is False
        assert "wolf1" not in game.werewolf_votes

    def test_dead_werewolf_cannot_vote(self):
        """Dead werewolf cannot submit a vote."""
        game = create_test_game_with_players()
        game.players["wolf1"].is_alive = False

        result = game.submit_werewolf_vote("wolf1", "villager1")

        assert result is False

    def test_werewolf_cannot_target_dead_player(self):
        """Werewolf cannot target a dead player."""
        game = create_test_game_with_players()
        game.players["villager1"].is_alive = False

        result = game.submit_werewolf_vote("wolf1", "villager1")

        assert result is False

    def test_werewolf_can_change_vote(self):
        """Werewolf can change their vote."""
        game = create_test_game_with_players()

        game.submit_werewolf_vote("wolf1", "villager1")
        game.submit_werewolf_vote("wolf1", "villager2")

        assert game.werewolf_votes["wolf1"] == "villager2"

    def test_multiple_werewolves_can_vote(self):
        """Multiple werewolves can each submit votes."""
        game = create_test_game_with_players()

        game.submit_werewolf_vote("wolf1", "villager1")
        game.submit_werewolf_vote("wolf2", "villager1")

        assert game.werewolf_votes["wolf1"] == "villager1"
        assert game.werewolf_votes["wolf2"] == "villager1"


class TestWerewolfKillTarget:
    """Test werewolf kill target resolution."""

    def test_majority_vote_determines_target(self):
        """When werewolves agree, that player is the target."""
        game = create_test_game_with_players()
        game.submit_werewolf_vote("wolf1", "villager1")
        game.submit_werewolf_vote("wolf2", "villager1")

        target = game.get_werewolf_kill_target()

        assert target == "villager1"

    def test_tie_results_in_no_kill(self):
        """When votes are tied, no one is killed."""
        game = create_test_game_with_players()
        game.submit_werewolf_vote("wolf1", "villager1")
        game.submit_werewolf_vote("wolf2", "villager2")

        target = game.get_werewolf_kill_target()

        assert target is None

    def test_no_votes_means_no_kill(self):
        """When no votes are submitted, no one is killed."""
        game = create_test_game_with_players()

        target = game.get_werewolf_kill_target()

        assert target is None

    def test_single_vote_determines_target(self):
        """With one werewolf voting, that vote determines target."""
        game = create_test_game_with_players()
        game.submit_werewolf_vote("wolf1", "seer")

        target = game.get_werewolf_kill_target()

        assert target == "seer"


class TestSeerAction:
    """Test seer investigation functionality."""

    def test_seer_can_investigate_player(self):
        """Seer can investigate any living player."""
        game = create_test_game_with_players()

        result = game.submit_seer_action("seer", "wolf1")

        assert result is True
        assert game.seer_target == "wolf1"

    def test_seer_cannot_investigate_self(self):
        """Seer cannot investigate themselves."""
        game = create_test_game_with_players()

        result = game.submit_seer_action("seer", "seer")

        assert result is False
        assert game.seer_target is None

    def test_dead_seer_cannot_investigate(self):
        """Dead seer cannot investigate."""
        game = create_test_game_with_players()
        game.players["seer"].is_alive = False

        result = game.submit_seer_action("seer", "wolf1")

        assert result is False

    def test_seer_cannot_investigate_dead_player(self):
        """Seer cannot investigate a dead player."""
        game = create_test_game_with_players()
        game.players["wolf1"].is_alive = False

        result = game.submit_seer_action("seer", "wolf1")

        assert result is False

    def test_seer_can_change_target(self):
        """Seer can change their investigation target."""
        game = create_test_game_with_players()

        game.submit_seer_action("seer", "wolf1")
        game.submit_seer_action("seer", "doctor")

        assert game.seer_target == "doctor"


class TestDoctorAction:
    """Test doctor protection functionality."""

    def test_doctor_can_protect_player(self):
        """Doctor can protect any living player."""
        game = create_test_game_with_players()

        result = game.submit_doctor_action("doctor", "villager1")

        assert result is True
        assert game.doctor_target == "villager1"

    def test_doctor_can_protect_self(self):
        """Doctor can protect themselves."""
        game = create_test_game_with_players()

        result = game.submit_doctor_action("doctor", "doctor")

        assert result is True
        assert game.doctor_target == "doctor"

    def test_dead_doctor_cannot_protect(self):
        """Dead doctor cannot protect anyone."""
        game = create_test_game_with_players()
        game.players["doctor"].is_alive = False

        result = game.submit_doctor_action("doctor", "villager1")

        assert result is False

    def test_doctor_cannot_protect_dead_player(self):
        """Doctor cannot protect a dead player."""
        game = create_test_game_with_players()
        game.players["villager1"].is_alive = False

        result = game.submit_doctor_action("doctor", "villager1")

        assert result is False

    def test_doctor_can_change_target(self):
        """Doctor can change their protection target."""
        game = create_test_game_with_players()

        game.submit_doctor_action("doctor", "villager1")
        game.submit_doctor_action("doctor", "seer")

        assert game.doctor_target == "seer"


class TestClearNightActions:
    """Test clearing night actions between phases."""

    def test_clear_night_actions_resets_all(self):
        """Clear night actions resets all night state."""
        game = create_test_game_with_players()
        game.submit_werewolf_vote("wolf1", "villager1")
        game.submit_seer_action("seer", "wolf1")
        game.submit_doctor_action("doctor", "seer")

        game.clear_night_actions()

        assert game.werewolf_votes == {}
        assert game.seer_target is None
        assert game.doctor_target is None


class TestVoteCounts:
    """Test vote counting functionality."""

    def test_werewolf_vote_counts(self):
        """Get accurate werewolf vote counts."""
        game = create_test_game_with_players()
        game.submit_werewolf_vote("wolf1", "villager1")
        game.submit_werewolf_vote("wolf2", "villager1")

        counts = game.get_werewolf_vote_counts()

        assert counts == {"villager1": 2}

    def test_day_vote_counts(self):
        """Get accurate day vote counts."""
        game = create_test_game_with_players()
        game.phase = GamePhase.VOTING
        game.submit_vote("villager1", "wolf1")
        game.submit_vote("villager2", "wolf1")
        game.submit_vote("seer", "wolf2")

        counts = game.get_vote_counts()

        assert counts == {"wolf1": 2, "wolf2": 1}


class TestDayVoting:
    """Test day voting functionality."""

    def test_player_can_vote(self):
        """Player can vote to eliminate someone."""
        game = create_test_game_with_players()
        game.phase = GamePhase.VOTING

        result = game.submit_vote("villager1", "wolf1")

        assert result is True
        assert game.votes["villager1"] == "wolf1"

    def test_player_cannot_vote_for_self(self):
        """Player cannot vote for themselves."""
        game = create_test_game_with_players()
        game.phase = GamePhase.VOTING

        result = game.submit_vote("villager1", "villager1")

        assert result is False

    def test_dead_player_cannot_vote(self):
        """Dead players cannot vote."""
        game = create_test_game_with_players()
        game.phase = GamePhase.VOTING
        game.players["villager1"].is_alive = False

        result = game.submit_vote("villager1", "wolf1")

        assert result is False

    def test_elimination_target_plurality(self):
        """Elimination target is determined by plurality."""
        game = create_test_game_with_players()
        game.phase = GamePhase.VOTING
        game.submit_vote("villager1", "wolf1")
        game.submit_vote("villager2", "wolf1")
        game.submit_vote("doctor", "wolf2")

        target = game.get_elimination_target()

        assert target == "wolf1"

    def test_elimination_tie_means_no_elimination(self):
        """Tied votes result in no elimination."""
        game = create_test_game_with_players()
        game.phase = GamePhase.VOTING
        game.submit_vote("villager1", "wolf1")
        game.submit_vote("villager2", "wolf2")

        target = game.get_elimination_target()

        assert target is None
