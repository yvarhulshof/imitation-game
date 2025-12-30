import secrets
from app.game.state import GameState
from app.models import Player, PlayerType


class GameManager:
    def __init__(self):
        self.games: dict[str, GameState] = {}

    def create_room(self) -> str:
        room_id = secrets.token_urlsafe(6)
        self.games[room_id] = GameState(room_id=room_id)
        return room_id

    def get_game(self, room_id: str) -> GameState | None:
        return self.games.get(room_id)

    def join_room(
        self, room_id: str, player_id: str, player_name: str
    ) -> GameState | None:
        game = self.get_game(room_id)
        if game is None:
            return None

        is_host = len(game.players) == 0
        player = Player(
            id=player_id,
            name=player_name,
            player_type=PlayerType.HUMAN,
            is_host=is_host,
        )
        game.add_player(player)
        return game

    def leave_room(self, room_id: str, player_id: str) -> None:
        game = self.get_game(room_id)
        if game:
            game.remove_player(player_id)
            if len(game.players) == 0:
                del self.games[room_id]

    def room_exists(self, room_id: str) -> bool:
        return room_id in self.games

    def get_player_room(self, player_id: str) -> str | None:
        """Find which room a player is in."""
        for room_id, game in self.games.items():
            if player_id in game.players:
                return room_id
        return None

    def disconnect_player(self, player_id: str) -> dict | None:
        """Remove player from their room. Returns info for event emission."""
        room_id = self.get_player_room(player_id)
        if room_id is None:
            return None

        game = self.games[room_id]
        player = game.players[player_id]
        was_host = player.is_host
        player_name = player.name

        game.remove_player(player_id)

        result = {
            "player_id": player_id,
            "player_name": player_name,
            "room_id": room_id,
        }

        if len(game.players) == 0:
            del self.games[room_id]
            return result

        if was_host:
            new_host = next(iter(game.players.values()))
            new_host.is_host = True
            result["new_host_id"] = new_host.id

        return result
