import time
from dataclasses import dataclass, field
from app.models import Player, ChatMessage, GamePhase, Team, Role


@dataclass
class GameState:
    room_id: str
    phase: GamePhase = GamePhase.LOBBY
    players: dict[str, Player] = field(default_factory=dict)
    messages: list[ChatMessage] = field(default_factory=list)
    round_number: int = 0
    phase_ends_at: float | None = None
    phase_duration: int = 0
    # Voting state: voter_id -> target_id
    votes: dict[str, str] = field(default_factory=dict)
    # Night actions state
    werewolf_votes: dict[str, str] = field(default_factory=dict)  # wolf_id -> target_id
    seer_target: str | None = None
    doctor_target: str | None = None

    def clear_votes(self) -> None:
        """Clear all votes for a new voting phase."""
        self.votes.clear()

    def clear_night_actions(self) -> None:
        """Clear all night actions for a new night phase."""
        self.werewolf_votes.clear()
        self.seer_target = None
        self.doctor_target = None

    def submit_werewolf_vote(self, wolf_id: str, target_id: str) -> bool:
        """Submit a werewolf kill vote. Returns True if valid."""
        wolf = self.players.get(wolf_id)
        target = self.players.get(target_id)

        if wolf is None or target is None:
            return False
        if not wolf.is_alive or not target.is_alive:
            return False
        # Can't target fellow werewolves
        if target.role and target.role.value == "werewolf":
            return False

        self.werewolf_votes[wolf_id] = target_id
        return True

    def submit_seer_action(self, seer_id: str, target_id: str) -> bool:
        """Submit seer investigation. Returns True if valid."""
        seer = self.players.get(seer_id)
        target = self.players.get(target_id)

        if seer is None or target is None:
            return False
        if not seer.is_alive or not target.is_alive:
            return False
        if seer_id == target_id:
            return False

        self.seer_target = target_id
        return True

    def submit_doctor_action(self, doctor_id: str, target_id: str) -> bool:
        """Submit doctor protection. Returns True if valid."""
        doctor = self.players.get(doctor_id)
        target = self.players.get(target_id)

        if doctor is None or target is None:
            return False
        if not doctor.is_alive or not target.is_alive:
            return False
        # Doctor can protect self

        self.doctor_target = target_id
        return True

    def get_werewolf_kill_target(self) -> str | None:
        """Get the werewolf kill target (plurality vote, None on tie)."""
        if not self.werewolf_votes:
            return None

        counts: dict[str, int] = {}
        for target_id in self.werewolf_votes.values():
            counts[target_id] = counts.get(target_id, 0) + 1

        max_votes = max(counts.values())
        targets_with_max = [t for t, c in counts.items() if c == max_votes]

        # Tie = no kill (or pick first, but let's say no kill for simplicity)
        if len(targets_with_max) > 1:
            return None

        return targets_with_max[0]

    def get_werewolf_vote_counts(self) -> dict[str, int]:
        """Get werewolf vote counts per target."""
        counts: dict[str, int] = {}
        for target_id in self.werewolf_votes.values():
            counts[target_id] = counts.get(target_id, 0) + 1
        return counts

    def submit_vote(self, voter_id: str, target_id: str) -> bool:
        """Submit a vote. Returns True if valid."""
        voter = self.players.get(voter_id)
        target = self.players.get(target_id)

        if voter is None or target is None:
            return False
        if not voter.is_alive or not target.is_alive:
            return False
        if voter_id == target_id:
            return False

        self.votes[voter_id] = target_id
        return True

    def get_vote_counts(self) -> dict[str, int]:
        """Get vote counts per target."""
        counts: dict[str, int] = {}
        for target_id in self.votes.values():
            counts[target_id] = counts.get(target_id, 0) + 1
        return counts

    def get_elimination_target(self) -> str | None:
        """Get the player to eliminate (plurality, None on tie)."""
        counts = self.get_vote_counts()
        if not counts:
            return None

        max_votes = max(counts.values())
        targets_with_max = [t for t, c in counts.items() if c == max_votes]

        # Tie = no elimination
        if len(targets_with_max) > 1:
            return None

        return targets_with_max[0]

    def is_phase_expired(self) -> bool:
        if self.phase_ends_at is None:
            return False
        return time.time() >= self.phase_ends_at

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
            "phase_ends_at": self.phase_ends_at,
            "phase_duration": self.phase_duration,
        }

    def get_alive_players_by_team(self, team: Team) -> list[Player]:
        """Get all alive players on a specific team."""
        return [p for p in self.players.values() if p.is_alive and p.team == team]

    def get_alive_werewolves(self) -> list[Player]:
        """Get all alive werewolves."""
        return [p for p in self.players.values() if p.is_alive and p.role == Role.WEREWOLF]

    def get_alive_town(self) -> list[Player]:
        """Get all alive town members."""
        return [p for p in self.players.values() if p.is_alive and p.team == Team.TOWN]

    def check_town_wins(self) -> bool:
        """Town wins if all werewolves are dead."""
        return len(self.get_alive_werewolves()) == 0

    def check_mafia_wins(self) -> bool:
        """Mafia wins if werewolves >= remaining town (wolves can't be outvoted)."""
        alive_wolves = len(self.get_alive_werewolves())
        alive_town = len(self.get_alive_town())
        return alive_wolves >= alive_town

    def check_win_condition(self) -> Team | None:
        """Check if either team has won. Returns winning team or None."""
        # Check town wins first (all werewolves dead)
        if self.check_town_wins():
            return Team.TOWN
        # Check mafia wins (werewolves >= town)
        if self.check_mafia_wins():
            return Team.MAFIA
        return None
