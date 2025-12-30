from dataclasses import dataclass, field
from app.models import Player, ChatMessage, GamePhase


@dataclass
class GameState:
    room_id: str
    phase: GamePhase = GamePhase.LOBBY
    players: dict[str, Player] = field(default_factory=dict)
    messages: list[ChatMessage] = field(default_factory=list)
    round_number: int = 0

    def add_player(self, player: Player) -> None:
        self.players[player.id] = player

    def remove_player(self, player_id: str) -> None:
        self.players.pop(player_id, None)

    def add_message(self, message: ChatMessage) -> None:
        self.messages.append(message)

    def get_player_list(self) -> list[dict]:
        return [p.model_dump() for p in self.players.values()]

    def to_dict(self) -> dict:
        return {
            "room_id": self.room_id,
            "phase": self.phase.value,
            "players": self.get_player_list(),
            "round_number": self.round_number,
        }
