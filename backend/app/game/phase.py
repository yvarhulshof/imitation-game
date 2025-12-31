import asyncio
import time
import logging
import socketio
from app.game.manager import GameManager
from app.models import GamePhase

logger = logging.getLogger(__name__)


# Phase durations in seconds
PHASE_DURATIONS = {
    GamePhase.DAY: 90,
    GamePhase.VOTING: 30,
    GamePhase.NIGHT: 30,
}


class PhaseController:
    def __init__(self, sio: socketio.AsyncServer, game_manager: GameManager):
        self.sio = sio
        self.game_manager = game_manager
        self.phase_tasks: dict[str, asyncio.Task] = {}

    async def start_game(self, room_id: str) -> bool:
        """Start the game and transition to DAY phase."""
        game = self.game_manager.get_game(room_id)
        if game is None:
            return False

        if game.phase != GamePhase.LOBBY:
            return False

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

                next_phase = self._get_next_phase(game.phase)
                logger.info(f"Transitioning from {game.phase} to {next_phase} in room {room_id}")
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
