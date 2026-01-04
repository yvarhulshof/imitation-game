"""AI Controller - Manages AI player behavior during game phases."""

import asyncio
import time
import logging
import random
import socketio
from app.ai.player import MockAIPlayer, generate_ai_id, get_random_name
from app.game.manager import GameManager
from app.models import Player, PlayerType, GamePhase, Role, ChatMessage, ROLE_TEAMS

logger = logging.getLogger(__name__)


class AIController:
    """Controls AI player behavior during game phases."""

    def __init__(self, sio: socketio.AsyncServer, game_manager: GameManager):
        self.sio = sio
        self.game_manager = game_manager
        # room_id -> {player_id: MockAIPlayer}
        self.ai_players: dict[str, dict[str, MockAIPlayer]] = {}
        # room_id -> asyncio.Task (for chat loops)
        self.chat_tasks: dict[str, asyncio.Task] = {}

    def add_ai_player(self, room_id: str) -> Player | None:
        """Add an AI player to a room."""
        game = self.game_manager.get_game(room_id)
        if game is None:
            return None

        if game.phase != GamePhase.LOBBY:
            return None  # Can only add AI in lobby

        # Get existing names
        existing_names = [p.name for p in game.players.values()]

        # Generate AI player
        ai_id = generate_ai_id()
        ai_name = get_random_name(existing_names)

        # Create Player model
        player = Player(
            id=ai_id,
            name=ai_name,
            player_type=PlayerType.AI,
            is_alive=True,
            is_host=False,
        )

        # Add to game state
        game.add_player(player)

        # Create MockAIPlayer for behavior
        if room_id not in self.ai_players:
            self.ai_players[room_id] = {}

        mock_ai = MockAIPlayer(ai_id, ai_name)
        self.ai_players[room_id][ai_id] = mock_ai

        logger.info(f"Added AI player {ai_name} ({ai_id}) to room {room_id}")
        return player

    def remove_ai_player(self, room_id: str, ai_id: str) -> bool:
        """Remove an AI player from a room."""
        game = self.game_manager.get_game(room_id)
        if game is None:
            return False

        if ai_id not in game.players:
            return False

        game.remove_player(ai_id)

        if room_id in self.ai_players:
            self.ai_players[room_id].pop(ai_id, None)

        return True

    def on_game_start(self, room_id: str) -> None:
        """Called when a game starts - set AI roles from game state."""
        game = self.game_manager.get_game(room_id)
        if game is None:
            return

        if room_id not in self.ai_players:
            return

        # Update AI players with their assigned roles
        for ai_id, mock_ai in self.ai_players[room_id].items():
            player = game.players.get(ai_id)
            if player and player.role and player.team:
                mock_ai.set_role(player.role, player.team)
                logger.info(f"AI {mock_ai.name} assigned role {player.role.value}")

    async def on_phase_change(self, room_id: str, new_phase: GamePhase) -> None:
        """Called when phase changes - trigger AI actions."""
        if room_id not in self.ai_players:
            return

        if new_phase == GamePhase.DAY:
            # Start chat task for AI players
            await self._start_chat_loop(room_id)
            # Reset daily counters
            for mock_ai in self.ai_players[room_id].values():
                mock_ai.reset_for_new_day()

        elif new_phase == GamePhase.VOTING:
            # Stop chat and submit votes
            self._stop_chat_loop(room_id)
            await self._submit_ai_votes(room_id)

        elif new_phase == GamePhase.NIGHT:
            # Submit night actions
            await self._submit_ai_night_actions(room_id)

        elif new_phase == GamePhase.ENDED:
            # Cleanup
            self._stop_chat_loop(room_id)

    async def _start_chat_loop(self, room_id: str) -> None:
        """Start a background task for AI chat during DAY phase."""
        self._stop_chat_loop(room_id)  # Cancel any existing

        async def chat_loop():
            game = self.game_manager.get_game(room_id)
            if game is None:
                return

            phase_start = time.time()

            try:
                while True:
                    await asyncio.sleep(random.uniform(3, 8))

                    game = self.game_manager.get_game(room_id)
                    if game is None or game.phase != GamePhase.DAY:
                        break

                    current_time = time.time()

                    # Let each AI decide if they want to chat
                    for ai_id, mock_ai in list(self.ai_players.get(room_id, {}).items()):
                        player = game.players.get(ai_id)
                        if player is None or not player.is_alive:
                            continue

                        if mock_ai.should_chat(current_time, phase_start):
                            # Get other player names for potential mentions
                            other_names = [
                                p.name for p in game.players.values()
                                if p.id != ai_id and p.is_alive
                            ]

                            message_content = mock_ai.generate_chat_message(other_names)

                            message = ChatMessage(
                                player_id=ai_id,
                                player_name=mock_ai.name,
                                content=message_content,
                                timestamp=current_time,
                            )
                            game.add_message(message)

                            await self.sio.emit(
                                "new_message",
                                message.model_dump(),
                                room=room_id,
                            )

                            mock_ai.last_message_time = current_time
                            mock_ai.messages_sent += 1
                            logger.debug(f"AI {mock_ai.name} sent: {message_content}")

            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error in AI chat loop: {e}", exc_info=True)

        task = asyncio.create_task(chat_loop())
        self.chat_tasks[room_id] = task

    def _stop_chat_loop(self, room_id: str) -> None:
        """Stop the AI chat task for a room."""
        if room_id in self.chat_tasks:
            self.chat_tasks[room_id].cancel()
            del self.chat_tasks[room_id]

    async def _submit_ai_votes(self, room_id: str) -> None:
        """Have AI players submit their votes."""
        game = self.game_manager.get_game(room_id)
        if game is None:
            return

        if room_id not in self.ai_players:
            return

        # Get list of alive players
        alive_players = [
            {"id": p.id, "name": p.name}
            for p in game.players.values()
            if p.is_alive
        ]

        # Get wolf IDs for coordination
        wolf_ids = [
            p.id for p in game.players.values()
            if p.role == Role.WEREWOLF and p.is_alive
        ]

        # Stagger AI votes
        for ai_id, mock_ai in self.ai_players[room_id].items():
            player = game.players.get(ai_id)
            if player is None or not player.is_alive:
                continue

            # Wait a random time before voting
            await asyncio.sleep(random.uniform(2, 10))

            # Check game state still valid
            game = self.game_manager.get_game(room_id)
            if game is None or game.phase != GamePhase.VOTING:
                break

            # Wolves know each other
            known_wolves = wolf_ids if mock_ai.team == "mafia" else None

            target_id = mock_ai.choose_vote_target(alive_players, known_wolves)
            if target_id:
                success = game.submit_vote(ai_id, target_id)
                if success:
                    logger.info(f"AI {mock_ai.name} voted for {target_id}")
                    await self.sio.emit(
                        "vote_update",
                        {"votes": game.get_vote_counts()},
                        room=room_id,
                    )

    async def _submit_ai_night_actions(self, room_id: str) -> None:
        """Have AI players submit their night actions."""
        game = self.game_manager.get_game(room_id)
        if game is None:
            return

        if room_id not in self.ai_players:
            return

        # Get list of alive players
        alive_players = [
            {"id": p.id, "name": p.name}
            for p in game.players.values()
            if p.is_alive
        ]

        # Get wolf IDs
        wolf_ids = [
            p.id for p in game.players.values()
            if p.role == Role.WEREWOLF and p.is_alive
        ]

        # Stagger AI actions
        for ai_id, mock_ai in self.ai_players[room_id].items():
            player = game.players.get(ai_id)
            if player is None or not player.is_alive:
                continue

            # Wait a random time before acting
            await asyncio.sleep(random.uniform(1, 5))

            # Check game state still valid
            game = self.game_manager.get_game(room_id)
            if game is None or game.phase != GamePhase.NIGHT:
                break

            fellow_wolves = wolf_ids if mock_ai.role == Role.WEREWOLF else None

            target_id = mock_ai.choose_night_action_target(alive_players, fellow_wolves)
            if target_id is None:
                continue

            # Submit action based on role
            success = False
            if mock_ai.role == Role.WEREWOLF:
                success = game.submit_werewolf_vote(ai_id, target_id)
                if success:
                    # Broadcast to other werewolves
                    for wolf_id in wolf_ids:
                        if wolf_id in game.players:
                            await self.sio.emit(
                                "werewolf_vote_update",
                                {"votes": game.get_werewolf_vote_counts()},
                                to=wolf_id,
                            )
            elif mock_ai.role == Role.SEER:
                success = game.submit_seer_action(ai_id, target_id)
            elif mock_ai.role == Role.DOCTOR:
                success = game.submit_doctor_action(ai_id, target_id)

            if success:
                logger.info(f"AI {mock_ai.name} ({mock_ai.role.value}) targeted {target_id}")

    def cleanup_room(self, room_id: str) -> None:
        """Clean up AI resources when a room is deleted."""
        self._stop_chat_loop(room_id)
        self.ai_players.pop(room_id, None)
