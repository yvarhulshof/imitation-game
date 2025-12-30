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
