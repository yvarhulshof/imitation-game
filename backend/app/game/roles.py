import random
from app.models import Role, Team, ROLE_TEAMS, Player


def get_role_distribution(player_count: int) -> list[Role]:
    """
    Get the list of roles to assign based on player count.

    Distribution rules:
    - 1-3 players: 1 werewolf, rest villagers (for testing)
    - 4-5 players: 1 werewolf, 1 seer, rest villagers
    - 6-7 players: 2 werewolves, 1 seer, 1 doctor, rest villagers
    - 8+ players: 2 werewolves, 1 seer, 1 doctor, rest villagers
    """
    if player_count <= 3:
        # Testing mode
        roles = [Role.WEREWOLF]
        roles.extend([Role.VILLAGER] * (player_count - 1))
    elif player_count <= 5:
        roles = [Role.WEREWOLF, Role.SEER]
        roles.extend([Role.VILLAGER] * (player_count - 2))
    else:
        # 6+ players: 2 werewolves, 1 seer, 1 doctor
        roles = [Role.WEREWOLF, Role.WEREWOLF, Role.SEER, Role.DOCTOR]
        roles.extend([Role.VILLAGER] * (player_count - 4))

    return roles


def assign_roles(players: dict[str, Player]) -> None:
    """
    Randomly assign roles to all players.
    Modifies players in place.
    """
    player_list = list(players.values())
    player_count = len(player_list)

    if player_count == 0:
        return

    roles = get_role_distribution(player_count)
    random.shuffle(roles)

    for player, role in zip(player_list, roles):
        player.role = role
        player.team = ROLE_TEAMS[role]


def get_players_by_role(players: dict[str, Player], role: Role) -> list[Player]:
    """Get all players with a specific role."""
    return [p for p in players.values() if p.role == role]


def get_players_by_team(players: dict[str, Player], team: Team) -> list[Player]:
    """Get all players on a specific team."""
    return [p for p in players.values() if p.team == team]


def get_alive_players(players: dict[str, Player]) -> list[Player]:
    """Get all living players."""
    return [p for p in players.values() if p.is_alive]


def get_alive_werewolves(players: dict[str, Player]) -> list[Player]:
    """Get all living werewolves."""
    return [p for p in players.values() if p.is_alive and p.role == Role.WEREWOLF]


def get_alive_town(players: dict[str, Player]) -> list[Player]:
    """Get all living town members."""
    return [p for p in players.values() if p.is_alive and p.team == Team.TOWN]
