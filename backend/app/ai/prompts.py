"""Prompt Templates - Builders for each LLM decision type."""

from typing import Any
from pathlib import Path

from app.models import Role, GamePhase


def load_strategy(role: Role) -> str:
    """Load strategy document for a role."""
    strategies_dir = Path(__file__).parent / "strategies"

    # Load base strategy
    base_path = strategies_dir / "base.md"
    base_strategy = base_path.read_text() if base_path.exists() else ""

    # Load role-specific strategy
    role_file_map = {
        Role.VILLAGER: "villager.md",
        Role.WEREWOLF: "werewolf.md",
        Role.SEER: "seer.md",
        Role.DOCTOR: "doctor.md",
    }

    role_file = role_file_map.get(role)
    role_strategy = ""
    if role_file:
        role_path = strategies_dir / role_file
        if role_path.exists():
            role_strategy = role_path.read_text()

    return f"{base_strategy}\n\n---\n\n{role_strategy}"


def format_player_context(context: dict[str, Any]) -> str:
    """Format game context for prompt inclusion."""
    lines = []

    # Basic info
    lines.append(f"Your name: {context['player_name']}")
    lines.append(f"Your role: {context['role'].value}")
    lines.append(f"Your team: {context['team'].value}")
    lines.append(f"Current phase: {context['phase'].value}")
    lines.append(f"Round number: {context['round_number']}")
    lines.append("")

    # Alive players
    lines.append("Alive players:")
    for p in context["alive_players"]:
        marker = "(you)" if p["id"] == context["player_id"] else ""
        lines.append(f"  - {p['name']} {marker}")
    lines.append("")

    # Dead players (if any)
    dead_players = context.get("dead_players", [])
    if dead_players:
        lines.append("Dead players:")
        for p in dead_players:
            lines.append(f"  - {p['name']}")
        lines.append("")

    # Fellow werewolves (if werewolf)
    if context["role"] == Role.WEREWOLF:
        fellow_wolves = context.get("fellow_wolves", [])
        if fellow_wolves:
            lines.append("Fellow werewolves:")
            for name in fellow_wolves:
                lines.append(f"  - {name}")
            lines.append("")

    # Recent chat history
    messages = context.get("messages", [])
    if messages:
        lines.append("Recent chat:")
        for msg in messages[-20:]:  # Last 20 messages
            lines.append(f"  [{msg['player_name']}]: {msg['content']}")
        lines.append("")

    # Voting info (if voting phase)
    vote_counts = context.get("vote_counts", {})
    if vote_counts:
        lines.append("Current vote counts:")
        for target_id, count in vote_counts.items():
            target_name = context.get("player_names", {}).get(target_id, target_id)
            lines.append(f"  - {target_name}: {count} votes")
        lines.append("")

    # Seer investigation results (if seer)
    seer_results = context.get("seer_results", [])
    if seer_results:
        lines.append("Your investigation results:")
        for result in seer_results:
            lines.append(f"  - {result['name']}: {result['is_wolf']}")
        lines.append("")

    return "\n".join(lines)


def build_system_instruction(context: dict[str, Any]) -> str:
    """Build the system instruction for all prompts."""
    return f"""You are {context['player_name']}, playing a social deduction game similar to Werewolf/Mafia.

Your role is {context['role'].value} on team {context['team'].value}.

Rules:
- Town wins if all werewolves are eliminated
- Werewolves win if they equal or outnumber town
- Be natural and human-like in your responses
- Stay in character at all times
- Keep messages concise (1-2 sentences typically)"""


def build_chat_decision_prompt(context: dict[str, Any], strategy: str, notes: str) -> str:
    """Build prompt for deciding whether and what to chat."""
    player_context = format_player_context(context)

    return f"""# Strategy Guide
{strategy}

# Your Notes
{notes if notes else "(No notes yet)"}

# Current Game State
{player_context}

# Your Task
Decide whether to send a chat message right now. Consider:
- The flow of conversation
- Whether you have something valuable to add
- Not chatting too frequently (you've sent {context.get('messages_sent', 0)} messages this phase)
- Staying in character and being natural

Respond with a JSON object:
{{
    "send": true or false,
    "message": "Your message content if send is true, otherwise empty string",
    "reasoning": "Brief internal reasoning (1 sentence)"
}}"""


def build_vote_prompt(
    context: dict[str, Any],
    strategy: str,
    notes: str,
    valid_targets: list[dict],
) -> str:
    """Build prompt for choosing a vote target."""
    player_context = format_player_context(context)

    targets_list = "\n".join([f"  - {t['name']}: id={t['id']}" for t in valid_targets])

    return f"""# Strategy Guide
{strategy}

# Your Notes
{notes if notes else "(No notes yet)"}

# Current Game State
{player_context}

# Valid Vote Targets (use the id value, not the name)
{targets_list}

# Your Task
Choose who to vote for elimination. Consider:
- Evidence from chat discussions
- Voting patterns you've observed
- Your strategic goals based on your role
- Who is most likely to be a threat to your team

IMPORTANT: You MUST use the exact id value (like "ai_abc123" or "xyz789") from the targets list, NOT the player's name.

Respond with a JSON object:
{{
    "target": "the exact id value from the list above",
    "reasoning": "Brief internal reasoning for this choice (1-2 sentences)"
}}"""


def build_night_action_prompt(
    context: dict[str, Any],
    strategy: str,
    notes: str,
    valid_targets: list[dict],
) -> str:
    """Build prompt for choosing a night action target."""
    player_context = format_player_context(context)

    targets_list = "\n".join([f"  - {t['name']}: id={t['id']}" for t in valid_targets])

    action_description = {
        Role.WEREWOLF: "Choose a player to kill tonight",
        Role.SEER: "Choose a player to investigate (learn if they are a werewolf)",
        Role.DOCTOR: "Choose a player to protect from the werewolf kill tonight",
    }

    action = action_description.get(context["role"], "Choose a target for your night action")

    return f"""# Strategy Guide
{strategy}

# Your Notes
{notes if notes else "(No notes yet)"}

# Current Game State
{player_context}

# Valid Targets (use the id value, not the name)
{targets_list}

# Your Task
{action}

Consider:
- Information gathered during the day
- Strategic value of each target
- Your role's specific objectives
- Who the other team might target (for Doctor)

IMPORTANT: You MUST use the exact id value (like "ai_abc123" or "xyz789") from the targets list, NOT the player's name.

Respond with a JSON object:
{{
    "target": "the exact id value from the list above",
    "reasoning": "Brief internal reasoning for this choice (1-2 sentences)"
}}"""


def build_notes_update_prompt(
    context: dict[str, Any],
    strategy: str,
    current_notes: str,
) -> str:
    """Build prompt for updating AI notes at end of phase."""
    player_context = format_player_context(context)

    # Get phase-specific events
    phase_events = []
    if context.get("elimination_result"):
        phase_events.append(f"Elimination: {context['elimination_result']}")
    if context.get("night_death"):
        phase_events.append(f"Night kill: {context['night_death']}")
    if context.get("seer_result"):
        phase_events.append(f"Your investigation: {context['seer_result']}")
    if context.get("save_result"):
        phase_events.append(f"Your protection: {context['save_result']}")

    events_text = "\n".join(phase_events) if phase_events else "No major events"

    return f"""# Your Current Notes
{current_notes if current_notes else "(Empty - first note-taking)"}

# What Just Happened
{events_text}

# Current Game State
{player_context}

# Your Task
Update your notes for the next phase. Your notes should include:
- Suspicion levels for each player (scale: trusted / neutral / suspicious / very suspicious)
- Key observations from this phase (voting patterns, accusations, defenses)
- Your current strategy thoughts
- Any claims or reveals made

Keep notes concise but comprehensive. Maximum ~500 words.
Write your updated notes as plain text (not JSON)."""
