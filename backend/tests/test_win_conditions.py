"""Tests for game win conditions."""

import pytest
from app.game.state import GameState
from app.models import Player, PlayerType, Role, Team, GamePhase


def create_player(
    player_id: str,
    name: str,
    role: Role,
    is_alive: bool = True,
) -> Player:
    """Helper to create a player with a role."""
    from app.models import ROLE_TEAMS
    return Player(
        id=player_id,
        name=name,
        player_type=PlayerType.HUMAN,
        is_alive=is_alive,
        role=role,
        team=ROLE_TEAMS[role],
    )


class TestGetAlivePlayers:
    """Tests for player counting methods."""

    def test_get_alive_werewolves(self):
        """Should return only alive werewolves."""
        game = GameState(room_id="test")
        game.players = {
            "w1": create_player("w1", "Wolf1", Role.WEREWOLF, is_alive=True),
            "w2": create_player("w2", "Wolf2", Role.WEREWOLF, is_alive=False),
            "v1": create_player("v1", "Villager1", Role.VILLAGER, is_alive=True),
        }

        wolves = game.get_alive_werewolves()
        assert len(wolves) == 1
        assert wolves[0].id == "w1"

    def test_get_alive_town(self):
        """Should return only alive town members."""
        game = GameState(room_id="test")
        game.players = {
            "w1": create_player("w1", "Wolf1", Role.WEREWOLF, is_alive=True),
            "v1": create_player("v1", "Villager1", Role.VILLAGER, is_alive=True),
            "v2": create_player("v2", "Villager2", Role.VILLAGER, is_alive=False),
            "s1": create_player("s1", "Seer", Role.SEER, is_alive=True),
            "d1": create_player("d1", "Doctor", Role.DOCTOR, is_alive=True),
        }

        town = game.get_alive_town()
        assert len(town) == 3
        assert all(p.team == Team.TOWN for p in town)


class TestTownWins:
    """Tests for town victory condition."""

    def test_town_wins_when_all_werewolves_dead(self):
        """Town wins when all werewolves are eliminated."""
        game = GameState(room_id="test")
        game.players = {
            "w1": create_player("w1", "Wolf1", Role.WEREWOLF, is_alive=False),
            "w2": create_player("w2", "Wolf2", Role.WEREWOLF, is_alive=False),
            "v1": create_player("v1", "Villager1", Role.VILLAGER, is_alive=True),
            "v2": create_player("v2", "Villager2", Role.VILLAGER, is_alive=True),
        }

        assert game.check_town_wins() is True
        assert game.check_mafia_wins() is False
        assert game.check_win_condition() == Team.TOWN

    def test_town_wins_when_last_werewolf_eliminated(self):
        """Town wins when the last werewolf is eliminated."""
        game = GameState(room_id="test")
        game.players = {
            "w1": create_player("w1", "Wolf1", Role.WEREWOLF, is_alive=False),
            "v1": create_player("v1", "Villager1", Role.VILLAGER, is_alive=True),
        }

        assert game.check_town_wins() is True
        assert game.check_win_condition() == Team.TOWN

    def test_town_wins_even_with_dead_town_members(self):
        """Town wins even if some town members died."""
        game = GameState(room_id="test")
        game.players = {
            "w1": create_player("w1", "Wolf1", Role.WEREWOLF, is_alive=False),
            "v1": create_player("v1", "Villager1", Role.VILLAGER, is_alive=True),
            "v2": create_player("v2", "Villager2", Role.VILLAGER, is_alive=False),
            "s1": create_player("s1", "Seer", Role.SEER, is_alive=False),
        }

        assert game.check_town_wins() is True
        assert game.check_win_condition() == Team.TOWN


class TestMafiaWins:
    """Tests for mafia victory condition."""

    def test_mafia_wins_when_werewolves_equal_town(self):
        """Mafia wins when werewolves equal remaining town (can't be outvoted)."""
        game = GameState(room_id="test")
        game.players = {
            "w1": create_player("w1", "Wolf1", Role.WEREWOLF, is_alive=True),
            "v1": create_player("v1", "Villager1", Role.VILLAGER, is_alive=True),
        }

        assert game.check_mafia_wins() is True
        assert game.check_town_wins() is False
        assert game.check_win_condition() == Team.MAFIA

    def test_mafia_wins_when_werewolves_exceed_town(self):
        """Mafia wins when werewolves outnumber town."""
        game = GameState(room_id="test")
        game.players = {
            "w1": create_player("w1", "Wolf1", Role.WEREWOLF, is_alive=True),
            "w2": create_player("w2", "Wolf2", Role.WEREWOLF, is_alive=True),
            "v1": create_player("v1", "Villager1", Role.VILLAGER, is_alive=True),
        }

        assert game.check_mafia_wins() is True
        assert game.check_win_condition() == Team.MAFIA

    def test_mafia_wins_when_all_town_dead(self):
        """Mafia wins when all town members are dead."""
        game = GameState(room_id="test")
        game.players = {
            "w1": create_player("w1", "Wolf1", Role.WEREWOLF, is_alive=True),
            "v1": create_player("v1", "Villager1", Role.VILLAGER, is_alive=False),
            "v2": create_player("v2", "Villager2", Role.VILLAGER, is_alive=False),
        }

        assert game.check_mafia_wins() is True
        assert game.check_win_condition() == Team.MAFIA


class TestNoWinCondition:
    """Tests for ongoing game (no winner yet)."""

    def test_no_winner_when_town_outnumbers_wolves(self):
        """No winner when town still outnumbers werewolves."""
        game = GameState(room_id="test")
        game.players = {
            "w1": create_player("w1", "Wolf1", Role.WEREWOLF, is_alive=True),
            "v1": create_player("v1", "Villager1", Role.VILLAGER, is_alive=True),
            "v2": create_player("v2", "Villager2", Role.VILLAGER, is_alive=True),
        }

        assert game.check_town_wins() is False
        assert game.check_mafia_wins() is False
        assert game.check_win_condition() is None

    def test_no_winner_early_game(self):
        """No winner in typical early game state."""
        game = GameState(room_id="test")
        game.players = {
            "w1": create_player("w1", "Wolf1", Role.WEREWOLF, is_alive=True),
            "w2": create_player("w2", "Wolf2", Role.WEREWOLF, is_alive=True),
            "v1": create_player("v1", "Villager1", Role.VILLAGER, is_alive=True),
            "v2": create_player("v2", "Villager2", Role.VILLAGER, is_alive=True),
            "v3": create_player("v3", "Villager3", Role.VILLAGER, is_alive=True),
            "s1": create_player("s1", "Seer", Role.SEER, is_alive=True),
            "d1": create_player("d1", "Doctor", Role.DOCTOR, is_alive=True),
        }

        assert game.check_win_condition() is None

    def test_game_continues_after_one_death(self):
        """Game continues after first elimination."""
        game = GameState(room_id="test")
        game.players = {
            "w1": create_player("w1", "Wolf1", Role.WEREWOLF, is_alive=True),
            "w2": create_player("w2", "Wolf2", Role.WEREWOLF, is_alive=True),
            "v1": create_player("v1", "Villager1", Role.VILLAGER, is_alive=False),  # eliminated
            "v2": create_player("v2", "Villager2", Role.VILLAGER, is_alive=True),
            "v3": create_player("v3", "Villager3", Role.VILLAGER, is_alive=True),
            "s1": create_player("s1", "Seer", Role.SEER, is_alive=True),
        }

        assert game.check_win_condition() is None


class TestEdgeCases:
    """Edge case tests."""

    def test_town_wins_priority_over_mafia(self):
        """If all wolves are dead and town = 0, town should win (wolves died first)."""
        # This is an edge case - if both conditions are technically true,
        # we check town wins first (all wolves dead)
        game = GameState(room_id="test")
        game.players = {
            "w1": create_player("w1", "Wolf1", Role.WEREWOLF, is_alive=False),
        }

        # No alive wolves means town wins (even if no town members alive)
        assert game.check_town_wins() is True
        assert game.check_win_condition() == Team.TOWN

    def test_multiple_power_roles(self):
        """Game with seer and doctor in play."""
        game = GameState(room_id="test")
        game.players = {
            "w1": create_player("w1", "Wolf1", Role.WEREWOLF, is_alive=True),
            "s1": create_player("s1", "Seer", Role.SEER, is_alive=True),
            "d1": create_player("d1", "Doctor", Role.DOCTOR, is_alive=True),
            "v1": create_player("v1", "Villager1", Role.VILLAGER, is_alive=True),
        }

        # 1 wolf vs 3 town - game continues
        assert game.check_win_condition() is None

        # Kill town members
        game.players["s1"].is_alive = False
        game.players["d1"].is_alive = False
        # Now 1 wolf vs 1 villager - mafia wins
        assert game.check_win_condition() == Team.MAFIA
