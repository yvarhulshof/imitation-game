"""AI Player implementations - Mock and LLM-powered."""

import logging
import random
import time
import uuid
from typing import Any

from app.models import ChatMessage, Role, Team
from app.ai.llm_client import LLMClient, LLMError
from app.ai.prompts import (
    load_strategy,
    build_system_instruction,
    build_chat_decision_prompt,
    build_vote_prompt,
    build_night_action_prompt,
    build_notes_update_prompt,
)
from app.config import MAX_NOTES_TOKENS

logger = logging.getLogger(__name__)


# Random AI names
AI_NAMES = [
    "Alex", "Jordan", "Taylor", "Morgan", "Casey",
    "Riley", "Quinn", "Avery", "Blake", "Cameron",
    "Dakota", "Emery", "Finley", "Hayden", "Jamie",
]

# Pre-defined chat messages by situation (used for fallback)
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


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Rough token truncation (approximates ~4 chars per token)."""
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."


def extract_target_id(target: str, valid_ids: list[str]) -> str | None:
    """
    Extract a valid target ID from LLM response.

    Handles various formats like:
    - "ai_abc123" (exact ID)
    - "id=ai_abc123" (with prefix)
    - "Alex: id=ai_abc123" (with name prefix)
    - "TqkBFd7t1ZQWbxV7AAAF" (human player ID)
    """
    if not target:
        return None

    # Direct match
    if target in valid_ids:
        return target

    # Try to find any valid ID within the target string
    for valid_id in valid_ids:
        if valid_id in target:
            return valid_id

    # Strip common prefixes and try again
    cleaned = target.strip()
    for prefix in ["id=", "id:", "target=", "target:"]:
        if cleaned.lower().startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
            if cleaned in valid_ids:
                return cleaned

    return None


class LLMPlayer:
    """LLM-powered AI player using Gemini API."""

    def __init__(
        self,
        player_id: str,
        name: str,
        llm_client: LLMClient | None = None,
        role: Role | None = None,
        team: Team | None = None,
    ):
        self.id = player_id
        self.name = name
        self.role = role
        self.team = team
        self.llm_client = llm_client or LLMClient()
        self.notes = ""
        self.strategy = ""
        self.seer_results: list[dict] = []  # Track seer investigation results
        self.last_message_time = 0.0
        self.messages_sent = 0
        self.max_messages_per_phase = random.randint(3, 6)

    def set_role(self, role: Role, team: Team) -> None:
        """Set the AI's role and load appropriate strategy."""
        self.role = role
        self.team = team
        self.strategy = load_strategy(role)
        logger.info(f"LLMPlayer {self.name} assigned role {role.value}")

    def _build_context(
        self,
        alive_players: list[dict],
        messages: list[dict] | None = None,
        vote_counts: dict[str, int] | None = None,
        dead_players: list[dict] | None = None,
        fellow_wolves: list[str] | None = None,
        round_number: int = 1,
        phase: Any = None,
    ) -> dict[str, Any]:
        """Build context dict for prompts."""
        # Build player name lookup
        player_names = {p["id"]: p["name"] for p in alive_players}
        if dead_players:
            for p in dead_players:
                player_names[p["id"]] = p["name"]

        # Get fellow wolf names
        fellow_wolf_names = []
        if fellow_wolves:
            fellow_wolf_names = [player_names.get(wid, wid) for wid in fellow_wolves]

        return {
            "player_id": self.id,
            "player_name": self.name,
            "role": self.role,
            "team": self.team,
            "phase": phase,
            "round_number": round_number,
            "alive_players": alive_players,
            "dead_players": dead_players or [],
            "messages": messages or [],
            "vote_counts": vote_counts or {},
            "player_names": player_names,
            "fellow_wolves": fellow_wolf_names,
            "seer_results": self.seer_results,
            "messages_sent": self.messages_sent,
        }

    async def decide_chat_action(
        self,
        context: dict[str, Any],
    ) -> ChatMessage | None:
        """Decide whether to chat and generate message if so."""
        try:
            system_instruction = build_system_instruction(context)
            prompt = build_chat_decision_prompt(context, self.strategy, self.notes)

            response = await self.llm_client.generate(
                prompt=prompt,
                response_format="json",
                system_instruction=system_instruction,
            )

            if isinstance(response, dict) and response.get("send"):
                message_content = response.get("message", "")
                if message_content:
                    self.messages_sent += 1
                    self.last_message_time = time.time()
                    logger.debug(f"LLM {self.name} decided to chat: {message_content}")
                    return ChatMessage(
                        player_id=self.id,
                        player_name=self.name,
                        content=message_content,
                        timestamp=time.time(),
                    )

            return None

        except LLMError as e:
            logger.warning(f"LLM chat decision failed for {self.name}: {e}")
            return self._fallback_chat_message(context)

    async def choose_vote_target(
        self,
        context: dict[str, Any],
        valid_targets: list[dict],
    ) -> str | None:
        """Choose who to vote for using LLM reasoning."""
        if not valid_targets:
            return None

        try:
            system_instruction = build_system_instruction(context)
            prompt = build_vote_prompt(context, self.strategy, self.notes, valid_targets)

            response = await self.llm_client.generate(
                prompt=prompt,
                response_format="json",
                system_instruction=system_instruction,
            )

            if isinstance(response, dict):
                raw_target = response.get("target", "")
                reasoning = response.get("reasoning", "")
                logger.info(f"LLM {self.name} voting for {raw_target}: {reasoning}")

                # Extract valid target ID from response
                valid_ids = [t["id"] for t in valid_targets]
                target_id = extract_target_id(raw_target, valid_ids)
                if target_id:
                    return target_id
                else:
                    logger.warning(f"LLM returned invalid target {raw_target}")

        except LLMError as e:
            logger.warning(f"LLM vote decision failed for {self.name}: {e}")

        # Fallback to random
        return random.choice(valid_targets)["id"]

    async def choose_night_action_target(
        self,
        context: dict[str, Any],
        valid_targets: list[dict],
    ) -> str | None:
        """Choose night action target using LLM reasoning."""
        if not valid_targets:
            return None

        if self.role == Role.VILLAGER:
            return None  # Villagers have no night action

        try:
            system_instruction = build_system_instruction(context)
            prompt = build_night_action_prompt(
                context, self.strategy, self.notes, valid_targets
            )

            response = await self.llm_client.generate(
                prompt=prompt,
                response_format="json",
                system_instruction=system_instruction,
            )

            if isinstance(response, dict):
                raw_target = response.get("target", "")
                reasoning = response.get("reasoning", "")
                logger.info(
                    f"LLM {self.name} ({self.role.value}) targeting {raw_target}: {reasoning}"
                )

                # Extract valid target ID from response
                valid_ids = [t["id"] for t in valid_targets]
                target_id = extract_target_id(raw_target, valid_ids)
                if target_id:
                    return target_id
                else:
                    logger.warning(f"LLM returned invalid target {raw_target}")

        except LLMError as e:
            logger.warning(f"LLM night action failed for {self.name}: {e}")

        # Fallback to random
        return random.choice(valid_targets)["id"]

    async def update_notes(self, context: dict[str, Any]) -> None:
        """Update notes at end of phase using LLM."""
        try:
            prompt = build_notes_update_prompt(context, self.strategy, self.notes)

            new_notes = await self.llm_client.generate(
                prompt=prompt,
                response_format="text",
            )

            if isinstance(new_notes, str):
                self.notes = truncate_to_tokens(new_notes, MAX_NOTES_TOKENS)
                logger.debug(f"LLM {self.name} updated notes ({len(self.notes)} chars)")

        except LLMError as e:
            logger.warning(f"LLM notes update failed for {self.name}: {e}")
            # Keep existing notes on failure

    def add_seer_result(self, target_name: str, is_wolf: bool) -> None:
        """Add a seer investigation result."""
        self.seer_results.append({
            "name": target_name,
            "is_wolf": "Werewolf" if is_wolf else "Not a werewolf",
        })

    def reset_for_new_day(self) -> None:
        """Reset daily counters."""
        self.messages_sent = 0
        self.max_messages_per_phase = random.randint(3, 6)

    def _fallback_chat_message(
        self, context: dict[str, Any]
    ) -> ChatMessage | None:
        """Generate fallback chat message using templates."""
        # Only chat occasionally on fallback
        if random.random() > 0.3:
            return None

        if self.messages_sent >= self.max_messages_per_phase:
            return None

        other_names = [
            p["name"] for p in context["alive_players"] if p["id"] != self.id
        ]

        if self.team == Team.MAFIA and random.random() < 0.4 and other_names:
            target = random.choice(other_names)
            template = random.choice(WEREWOLF_CHAT_MESSAGES)
            content = template.format(player=target)
        elif random.random() < 0.3 and other_names:
            target = random.choice(other_names)
            template = random.choice(DAY_CHAT_MESSAGES["accusation"])
            content = template.format(player=target)
        else:
            content = random.choice(DAY_CHAT_MESSAGES["general"])

        self.messages_sent += 1
        self.last_message_time = time.time()

        return ChatMessage(
            player_id=self.id,
            player_name=self.name,
            content=content,
            timestamp=time.time(),
        )


class MockAIPlayer:
    """Rule-based AI player for testing without LLM API."""

    def __init__(
        self,
        player_id: str,
        name: str,
        role: Role | None = None,
        team: Team | None = None,
    ):
        self.id = player_id
        self.name = name
        self.role = role
        self.team = team
        self.last_message_time = 0.0
        self.messages_sent = 0
        self.max_messages_per_day = random.randint(2, 5)
        self.notes = ""  # Compatibility with LLMPlayer

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

    def generate_chat_message(
        self, other_players: list[str], is_accused: bool = False
    ) -> str:
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
            p
            for p in alive_players
            if p["id"] != self.id
            and (known_wolves is None or p["id"] not in known_wolves)
        ]

        if not valid_targets:
            return None

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
                p
                for p in alive_players
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
