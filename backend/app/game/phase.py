import asyncio
import time
import logging
import socketio
from app.game.manager import GameManager
from app.game.roles import assign_roles, get_players_by_role
from app.models import GamePhase, Role, Team

logger = logging.getLogger(__name__)


# Phase durations in seconds
# NOTE: set to 10 for dev purposes
PHASE_DURATIONS = {
    # GamePhase.DAY: 90,
    # GamePhase.VOTING: 30,
    # GamePhase.NIGHT: 30,
    GamePhase.DAY: 10,
    GamePhase.VOTING: 10,
    GamePhase.NIGHT: 10,
}


class PhaseController:
    def __init__(self, sio: socketio.AsyncServer, game_manager: GameManager, ai_controller=None):
        self.sio = sio
        self.game_manager = game_manager
        self.ai_controller = ai_controller
        self.phase_tasks: dict[str, asyncio.Task] = {}

    async def start_game(self, room_id: str) -> bool:
        """Start the game and transition to DAY phase."""
        game = self.game_manager.get_game(room_id)
        if game is None:
            return False

        if game.phase != GamePhase.LOBBY:
            return False

        # Assign roles to all players
        assign_roles(game.players)
        logger.info(f"Roles assigned for room {room_id}")

        # Get werewolf IDs for werewolf players to know each other
        werewolves = get_players_by_role(game.players, Role.WEREWOLF)
        werewolf_ids = [w.id for w in werewolves]

        # Send each player their role privately
        for player_id, player in game.players.items():
            role_info = {
                "role": player.role.value,
                "team": player.team.value,
            }
            # Werewolves get to know other werewolves
            if player.role == Role.WEREWOLF:
                role_info["werewolf_ids"] = werewolf_ids

            await self.sio.emit("game_started", role_info, to=player_id)

        # Notify AI controller of game start
        if self.ai_controller:
            self.ai_controller.on_game_start(room_id)

        game.round_number = 1
        await self.transition_to(room_id, GamePhase.DAY)
        return True

    async def transition_to(self, room_id: str, phase: GamePhase) -> None:
        """Transition to a new phase and schedule the next transition."""
        game = self.game_manager.get_game(room_id)
        if game is None:
            return

        # Remove reference to completed/old task (don't cancel - it might be the caller)
        if room_id in self.phase_tasks:
            del self.phase_tasks[room_id]

        # Clear votes when entering voting phase
        if phase == GamePhase.VOTING:
            game.clear_votes()

        # Clear night actions when entering night phase
        if phase == GamePhase.NIGHT:
            game.clear_night_actions()

        # Update game state
        game.phase = phase
        duration = PHASE_DURATIONS.get(phase, 0)
        game.phase_duration = duration

        if duration > 0:
            game.phase_ends_at = time.time() + duration
        else:
            game.phase_ends_at = None

        # Emit phase change to all players
        await self.sio.emit(
            "phase_changed",
            {
                "phase": phase.value,
                "duration": duration,
                "ends_at": game.phase_ends_at,
                "round_number": game.round_number,
            },
            room=room_id,
        )

        # Notify AI controller of phase change
        if self.ai_controller:
            await self.ai_controller.on_phase_change(room_id, phase)

        # Schedule next phase transition
        if duration > 0:
            await self._schedule_next_phase(room_id, duration)

    async def _schedule_next_phase(self, room_id: str, delay: int) -> None:
        """Schedule the next phase transition after delay seconds."""

        async def transition_after_delay():
            try:
                logger.info(f"Scheduling next phase in {delay}s for room {room_id}")
                await asyncio.sleep(delay)

                # Remove self from tasks before transitioning (prevents self-cancellation)
                if room_id in self.phase_tasks:
                    del self.phase_tasks[room_id]

                game = self.game_manager.get_game(room_id)
                if game is None:
                    logger.warning(f"Game not found for room {room_id}")
                    return

                current_phase = game.phase
                next_phase = self._get_next_phase(current_phase)
                logger.info(f"Transitioning from {current_phase} to {next_phase} in room {room_id}")

                game_ended = False

                # Resolve votes when leaving voting phase
                if current_phase == GamePhase.VOTING:
                    game_ended = await self._resolve_votes(room_id, game)

                # Resolve night actions when leaving night phase
                if current_phase == GamePhase.NIGHT:
                    game_ended = await self._resolve_night_actions(room_id, game)

                # Don't transition if game has ended
                if game_ended:
                    return

                if next_phase == GamePhase.DAY:
                    game.round_number += 1

                await self.transition_to(room_id, next_phase)
            except asyncio.CancelledError:
                logger.info(f"Phase task cancelled for room {room_id}")
            except Exception as e:
                logger.error(f"Error in phase transition: {e}", exc_info=True)

        task = asyncio.create_task(transition_after_delay())
        self.phase_tasks[room_id] = task

    def _get_next_phase(self, current: GamePhase) -> GamePhase:
        """Get the next phase in the game flow."""
        phase_flow = {
            GamePhase.DAY: GamePhase.VOTING,
            GamePhase.VOTING: GamePhase.NIGHT,
            GamePhase.NIGHT: GamePhase.DAY,
        }
        return phase_flow.get(current, GamePhase.ENDED)

    async def _check_and_end_game(self, room_id: str, game) -> bool:
        """Check win conditions and end game if a team has won.

        Returns True if game ended, False otherwise.
        """
        winner = game.check_win_condition()
        if winner is None:
            return False

        logger.info(f"Game ended in room {room_id}. Winner: {winner.value}")

        # Prepare all player info with roles revealed
        players_info = [
            {
                "id": p.id,
                "name": p.name,
                "role": p.role.value if p.role else None,
                "team": p.team.value if p.team else None,
                "is_alive": p.is_alive,
            }
            for p in game.players.values()
        ]

        # Emit game_ended event to all players
        await self.sio.emit(
            "game_ended",
            {
                "winner": winner.value,
                "players": players_info,
            },
            room=room_id,
        )

        # Cancel any pending phase tasks
        if room_id in self.phase_tasks:
            self.phase_tasks[room_id].cancel()
            del self.phase_tasks[room_id]

        # Transition to ENDED phase (no timer)
        game.phase = GamePhase.ENDED
        game.phase_ends_at = None
        game.phase_duration = 0

        await self.sio.emit(
            "phase_changed",
            {
                "phase": GamePhase.ENDED.value,
                "duration": 0,
                "ends_at": None,
                "round_number": game.round_number,
            },
            room=room_id,
        )

        return True

    async def _resolve_votes(self, room_id: str, game) -> bool:
        """Resolve votes and eliminate a player if there's a majority.

        Returns True if game ended, False otherwise.
        """
        target_id = game.get_elimination_target()

        if target_id is None:
            # No elimination (tie or no votes)
            logger.info(f"No elimination in room {room_id} (tie or no votes)")
            await self.sio.emit(
                "player_eliminated",
                {"eliminated": None, "reason": "No majority vote"},
                room=room_id,
            )
            return False

        target = game.players.get(target_id)
        if target is None:
            return False

        # Eliminate the player
        target.is_alive = False
        logger.info(f"Player {target.name} eliminated in room {room_id}")

        await self.sio.emit(
            "player_eliminated",
            {
                "eliminated": {
                    "id": target.id,
                    "name": target.name,
                    "role": target.role.value if target.role else None,
                    "team": target.team.value if target.team else None,
                },
                "reason": "Voted out by the village",
            },
            room=room_id,
        )

        # Check win conditions after elimination
        return await self._check_and_end_game(room_id, game)

    async def _resolve_night_actions(self, room_id: str, game) -> bool:
        """Resolve night actions: doctor protection, werewolf kill, seer peek.

        Returns True if game ended, False otherwise.
        """
        # 1. Get doctor's protection target
        protected_id = game.doctor_target

        # 2. Get werewolf kill target (plurality)
        kill_target_id = game.get_werewolf_kill_target()

        # 3. Send seer result (private) if seer investigated someone
        if game.seer_target:
            seer = None
            for p in game.players.values():
                if p.role == Role.SEER and p.is_alive:
                    seer = p
                    break

            target = game.players.get(game.seer_target)
            if seer and target:
                await self.sio.emit(
                    "seer_result",
                    {
                        "target_id": target.id,
                        "target_name": target.name,
                        "role": target.role.value if target.role else None,
                    },
                    to=seer.id,
                )
                logger.info(f"Seer peeked at {target.name} ({target.role}) in room {room_id}")

        # 4. Apply werewolf kill (if not protected)
        deaths = []
        if kill_target_id:
            if kill_target_id == protected_id:
                logger.info(f"Doctor saved {game.players.get(kill_target_id).name} in room {room_id}")
            else:
                target = game.players.get(kill_target_id)
                if target and target.is_alive:
                    target.is_alive = False
                    deaths.append({
                        "id": target.id,
                        "name": target.name,
                        "role": target.role.value if target.role else None,
                    })
                    logger.info(f"Werewolves killed {target.name} in room {room_id}")

        # 5. Emit night_result to all players
        await self.sio.emit(
            "night_result",
            {"deaths": deaths},
            room=room_id,
        )

        # 6. Check win conditions after night kill
        return await self._check_and_end_game(room_id, game)

    async def skip_to_voting(self, room_id: str) -> bool:
        """Allow host to skip DAY phase and go directly to voting."""
        game = self.game_manager.get_game(room_id)
        if game is None:
            return False

        if game.phase != GamePhase.DAY:
            return False

        # Cancel the pending DAY timer
        if room_id in self.phase_tasks:
            self.phase_tasks[room_id].cancel()
            del self.phase_tasks[room_id]

        await self.transition_to(room_id, GamePhase.VOTING)
        return True

    def cleanup_room(self, room_id: str) -> None:
        """Clean up phase tasks when a room is deleted."""
        if room_id in self.phase_tasks:
            self.phase_tasks[room_id].cancel()
            del self.phase_tasks[room_id]
