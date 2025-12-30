from enum import Enum
from pydantic import BaseModel


class PlayerType(str, Enum):
    HUMAN = "human"
    AI = "ai"


class GamePhase(str, Enum):
    LOBBY = "lobby"
    DAY = "day"
    NIGHT = "night"
    VOTING = "voting"
    ENDED = "ended"


class Player(BaseModel):
    id: str
    name: str
    player_type: PlayerType
    is_alive: bool = True
    is_host: bool = False


class ChatMessage(BaseModel):
    player_id: str
    player_name: str
    content: str
    timestamp: float
