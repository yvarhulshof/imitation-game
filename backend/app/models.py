from enum import Enum
from typing import Optional
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


class Role(str, Enum):
    VILLAGER = "villager"
    WEREWOLF = "werewolf"
    SEER = "seer"
    DOCTOR = "doctor"


class Team(str, Enum):
    TOWN = "town"
    MAFIA = "mafia"


# Map roles to teams
ROLE_TEAMS = {
    Role.VILLAGER: Team.TOWN,
    Role.WEREWOLF: Team.MAFIA,
    Role.SEER: Team.TOWN,
    Role.DOCTOR: Team.TOWN,
}


class Player(BaseModel):
    id: str
    name: str
    player_type: PlayerType
    is_alive: bool = True
    is_host: bool = False
    role: Optional[Role] = None
    team: Optional[Team] = None


class ChatMessage(BaseModel):
    player_id: str
    player_name: str
    content: str
    timestamp: float
