import random
import uuid
from app.models import ChatMessage, Role, Team


# Random AI names
AI_NAMES = [
    "Alex", "Jordan", "Taylor", "Morgan", "Casey",
    "Riley", "Quinn", "Avery", "Blake", "Cameron",
    "Dakota", "Emery", "Finley", "Hayden", "Jamie",
]

# Pre-defined chat messages by situation
DAY_CHAT_MESSAGES = {
    "general": [
        "Anyone have any suspicions?",
        "I'm not sure who to trust here...",
        "Let's think about this logically.",
        "Something feels off today.",
        "Who's been acting weird?",
        "I have a bad feeling about this.",
        "We need to find the wolves.",
        "Stay focused everyone.",
        "Don't let them trick us.",
        "What do you all think?",
    ],
    "accusation": [
        "I think {player} is suspicious.",
        "Has anyone else noticed {player} being quiet?",
        "{player} seems nervous to me.",
        "I'm getting bad vibes from {player}.",
        "Why is {player} so defensive?",
    ],
    "defense": [
        "I'm definitely not a wolf!",
        "Why would you suspect me?",
        "I've been helping the town this whole time.",
        "That's a ridiculous accusation.",
        "You're barking up the wrong tree.",
    ],
    "agreement": [
        "I agree, that's suspicious.",
        "Good point, I was thinking the same.",
        "Yeah, let's look into that.",
        "That makes sense to me.",
    ],
}

WEREWOLF_CHAT_MESSAGES = [
    "We should vote for {player}.",
    "What about {player}? They seem suspicious.",
    "I think {player} could be the seer.",
    "Let's stay under the radar.",
]


def generate_ai_id() -> str:
    """Generate a unique ID for an AI player."""
    return f"ai_{uuid.uuid4().hex[:8]}"


def get_random_name(existing_names: list[str]) -> str:
    """Get a random name not already in use."""
    available = [n for n in AI_NAMES if n not in existing_names]
    if not available:
        return f"Player{random.randint(100, 999)}"
    return random.choice(available)


class MockAIPlayer:
    """Rule-based AI player for testing without LLM API."""

    def __init__(self, player_id: str, name: str, role: Role | None = None, team: Team | None = None):
        self.id = player_id
        self.name = name
        self.role = role
        self.team = team
        self.last_message_time = 0.0
        self.messages_sent = 0
        self.max_messages_per_day = random.randint(2, 5)

    def set_role(self, role: Role, team: Team) -> None:
        """Set the AI's role after game starts."""
        self.role = role
        self.team = team

    def should_chat(self, current_time: float, phase_start_time: float) -> bool:
        """Decide if AI should send a chat message."""
        if self.messages_sent >= self.max_messages_per_day:
            return False

        time_since_last = current_time - self.last_message_time
        time_since_phase_start = current_time - phase_start_time

        # Wait at least 5-15 seconds between messages
        min_interval = random.uniform(5, 15)
        if time_since_last < min_interval:
            return False

        # Random chance to chat (higher early in phase)
        if time_since_phase_start < 30:
            return random.random() < 0.3
        return random.random() < 0.15

    def generate_chat_message(self, other_players: list[str], is_accused: bool = False) -> str:
        """Generate a chat message based on game state."""
        if is_accused:
            return random.choice(DAY_CHAT_MESSAGES["defense"])

        # Werewolves sometimes subtly accuse others
        if self.team == Team.MAFIA and random.random() < 0.4 and other_players:
            target = random.choice(other_players)
            template = random.choice(WEREWOLF_CHAT_MESSAGES)
            return template.format(player=target)

        # General chat or accusation
        if random.random() < 0.3 and other_players:
            target = random.choice(other_players)
            template = random.choice(DAY_CHAT_MESSAGES["accusation"])
            return template.format(player=target)

        return random.choice(DAY_CHAT_MESSAGES["general"])

    def choose_vote_target(
        self,
        alive_players: list[dict],
        known_wolves: list[str] | None = None,
    ) -> str | None:
        """Choose who to vote for during voting phase."""
        # Filter out self and fellow wolves
        valid_targets = [
            p for p in alive_players
            if p["id"] != self.id
            and (known_wolves is None or p["id"] not in known_wolves)
        ]

        if not valid_targets:
            return None

        # Town: random vote (could be smarter with chat analysis later)
        # Wolves: vote for town members
        return random.choice(valid_targets)["id"]

    def choose_night_action_target(
        self,
        alive_players: list[dict],
        fellow_wolves: list[str] | None = None,
    ) -> str | None:
        """Choose a target for night action based on role."""
        if self.role == Role.WEREWOLF:
            # Target non-wolves
            valid_targets = [
                p for p in alive_players
                if p["id"] != self.id
                and (fellow_wolves is None or p["id"] not in fellow_wolves)
            ]
        elif self.role == Role.SEER:
            # Investigate anyone but self
            valid_targets = [p for p in alive_players if p["id"] != self.id]
        elif self.role == Role.DOCTOR:
            # Protect anyone (including self)
            valid_targets = alive_players
        else:
            return None  # Villagers have no action

        if not valid_targets:
            return None

        return random.choice(valid_targets)["id"]

    def reset_for_new_day(self) -> None:
        """Reset daily counters."""
        self.messages_sent = 0
        self.max_messages_per_day = random.randint(2, 5)


# Keep original AIPlayer for future LLM integration
class AIPlayer:
    """LLM-powered AI player (requires API key)."""

    def __init__(self, name: str, personality: str = ""):
        self.name = name
        self.personality = personality or "You are a player in a social deduction game."
        self.message_history: list[ChatMessage] = []

    async def generate_response(self, messages: list[ChatMessage]) -> str:
        # Placeholder - would use LLM API here
        raise NotImplementedError("LLM integration not configured")
