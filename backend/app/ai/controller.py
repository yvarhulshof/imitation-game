"""AI Controller - Manages AI player behavior during game phases."""

import asyncio
import logging
import random
import time
from typing import Union

import socketio

from app.ai.llm_client import LLMClient
from app.ai.notes_store import NotesStore
from app.ai.player import LLMPlayer, MockAIPlayer, generate_ai_id, get_random_name
from app.config import AI_CHAT_STAGGER_MIN, AI_CHAT_STAGGER_MAX, GOOGLE_API_KEY
from app.game.manager import GameManager
from app.models import ChatMessage, GamePhase, Player, PlayerType, Role

logger = logging.getLogger(__name__)

# Type alias for AI player (can be either LLM or Mock)
AIPlayerType = Union[LLMPlayer, MockAIPlayer]


class AIController:
    """Controls AI player behavior during game phases."""

    def __init__(self, sio: socketio.AsyncServer, game_manager: GameManager):
        self.sio = sio
        self.game_manager = game_manager
        # room_id -> {player_id: AIPlayerType}
        self.ai_players: dict[str, dict[str, AIPlayerType]] = {}
        # room_id -> asyncio.Task (for chat loops)
        self.chat_tasks: dict[str, asyncio.Task] = {}
        # room_id -> asyncio.Task (for scheduled actions)
        self.action_tasks: dict[str, list[asyncio.Task]] = {}
        # Shared LLM client for all AI players
        self.llm_client = LLMClient() if GOOGLE_API_KEY else None
        # Notes persistence
        self.notes_store = NotesStore()
        # Use LLM mode if API key is configured
        self.use_llm = bool(GOOGLE_API_KEY)

        if self.use_llm:
            logger.info("AI Controller initialized with LLM mode")
        else:
            logger.info("AI Controller initialized with Mock mode (no API key)")

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

        # Create AI player instance (LLM or Mock based on config)
        if room_id not in self.ai_players:
            self.ai_players[room_id] = {}

        if self.use_llm:
            ai_player = LLMPlayer(ai_id, ai_name, llm_client=self.llm_client)
            # Load any existing notes
            existing_notes = self.notes_store.load(room_id, ai_id)
            if existing_notes:
                ai_player.notes = existing_notes
        else:
            ai_player = MockAIPlayer(ai_id, ai_name)

        self.ai_players[room_id][ai_id] = ai_player

        logger.info(f"Added {'LLM' if self.use_llm else 'Mock'} AI player {ai_name} ({ai_id}) to room {room_id}")
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
            # Clear notes for removed player
            self.notes_store.clear_player(room_id, ai_id)

        return True

    def on_game_start(self, room_id: str) -> None:
        """Called when a game starts - set AI roles from game state."""
        game = self.game_manager.get_game(room_id)
        if game is None:
            return

        if room_id not in self.ai_players:
            return

        # Update AI players with their assigned roles
        for ai_id, ai_player in self.ai_players[room_id].items():
            player = game.players.get(ai_id)
            if player and player.role and player.team:
                ai_player.set_role(player.role, player.team)
                logger.info(f"AI {ai_player.name} assigned role {player.role.value}")

    async def on_phase_change(self, room_id: str, new_phase: GamePhase, phase_duration: int = 0) -> None:
        """Called when phase changes - trigger AI actions.

        Args:
            room_id: The room ID
            new_phase: The new phase
            phase_duration: Duration of the phase in seconds (for scheduling actions)
        """
        if room_id not in self.ai_players:
            return

        if new_phase == GamePhase.DAY:
            # Reset daily counters
            for ai_player in self.ai_players[room_id].values():
                ai_player.reset_for_new_day()
            # Start chat task for AI players
            await self._start_chat_loop(room_id)

        elif new_phase == GamePhase.VOTING:
            # Stop chat and schedule votes to happen during the phase
            self._stop_chat_loop(room_id)
            self._schedule_ai_votes(room_id, phase_duration)

        elif new_phase == GamePhase.NIGHT:
            # Schedule notes updates in background (non-blocking)
            self._schedule_notes_updates(room_id)
            # Schedule night actions during the phase
            self._schedule_ai_night_actions(room_id, phase_duration)

        elif new_phase == GamePhase.ENDED:
            # Cleanup
            self._stop_chat_loop(room_id)
            self._cancel_action_tasks(room_id)
            await self._update_ai_notes(room_id)  # Final notes update
            self._save_all_notes(room_id)

    def _build_player_context(
        self,
        ai_player: AIPlayerType,
        game,
        additional_context: dict | None = None,
    ) -> dict:
        """Build context dict for AI player decisions."""
        # Get alive players
        alive_players = [
            {"id": p.id, "name": p.name}
            for p in game.players.values()
            if p.is_alive
        ]

        # Get dead players
        dead_players = [
            {"id": p.id, "name": p.name}
            for p in game.players.values()
            if not p.is_alive
        ]

        # Get fellow wolves (if werewolf)
        fellow_wolves = []
        if ai_player.role == Role.WEREWOLF:
            fellow_wolves = [
                p.id for p in game.players.values()
                if p.role == Role.WEREWOLF and p.is_alive and p.id != ai_player.id
            ]

        # Get messages as dicts
        messages = [
            {
                "player_id": m.player_id,
                "player_name": m.player_name,
                "content": m.content,
                "timestamp": m.timestamp,
            }
            for m in game.messages
        ]

        context = {
            "player_id": ai_player.id,
            "player_name": ai_player.name,
            "role": ai_player.role,
            "team": ai_player.team,
            "phase": game.phase,
            "round_number": game.round_number,
            "alive_players": alive_players,
            "dead_players": dead_players,
            "messages": messages,
            "vote_counts": game.get_vote_counts() if game.phase == GamePhase.VOTING else {},
            "player_names": {p["id"]: p["name"] for p in alive_players + dead_players},
            "fellow_wolves": fellow_wolves,
            "messages_sent": ai_player.messages_sent,
        }

        # Add seer results if LLMPlayer
        if isinstance(ai_player, LLMPlayer):
            context["seer_results"] = ai_player.seer_results

        # Merge additional context
        if additional_context:
            context.update(additional_context)

        return context

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
                    # Random interval between chat checks
                    await asyncio.sleep(random.uniform(10, 15))

                    game = self.game_manager.get_game(room_id)
                    if game is None or game.phase != GamePhase.DAY:
                        break

                    # Let each AI decide if they want to chat
                    for ai_id, ai_player in list(self.ai_players.get(room_id, {}).items()):
                        player = game.players.get(ai_id)
                        if player is None or not player.is_alive:
                            continue

                        # Stagger between AI players
                        await asyncio.sleep(
                            random.uniform(AI_CHAT_STAGGER_MIN, AI_CHAT_STAGGER_MAX)
                        )

                        # Re-check game state
                        game = self.game_manager.get_game(room_id)
                        if game is None or game.phase != GamePhase.DAY:
                            break

                        message = await self._get_ai_chat_message(
                            ai_player, game, phase_start
                        )

                        if message:
                            game.add_message(message)
                            await self.sio.emit(
                                "new_message",
                                message.model_dump(),
                                room=room_id,
                            )
                            logger.debug(f"AI {ai_player.name} sent: {message.content}")

            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error in AI chat loop: {e}", exc_info=True)

        task = asyncio.create_task(chat_loop())
        self.chat_tasks[room_id] = task

    async def _get_ai_chat_message(
        self,
        ai_player: AIPlayerType,
        game,
        phase_start: float,
    ) -> ChatMessage | None:
        """Get chat message from AI player (LLM or Mock)."""
        current_time = time.time()

        if isinstance(ai_player, LLMPlayer):
            # Build context and use LLM
            context = self._build_player_context(ai_player, game)
            return await ai_player.decide_chat_action(context)
        else:
            # Use mock logic
            if ai_player.should_chat(current_time, phase_start):
                other_names = [
                    p.name for p in game.players.values()
                    if p.id != ai_player.id and p.is_alive
                ]
                message_content = ai_player.generate_chat_message(other_names)

                ai_player.last_message_time = current_time
                ai_player.messages_sent += 1

                return ChatMessage(
                    player_id=ai_player.id,
                    player_name=ai_player.name,
                    content=message_content,
                    timestamp=current_time,
                )
        return None

    def _stop_chat_loop(self, room_id: str) -> None:
        """Stop the AI chat task for a room."""
        if room_id in self.chat_tasks:
            self.chat_tasks[room_id].cancel()
            del self.chat_tasks[room_id]

    def _cancel_action_tasks(self, room_id: str) -> None:
        """Cancel all scheduled action tasks for a room."""
        if room_id in self.action_tasks:
            for task in self.action_tasks[room_id]:
                if not task.done():
                    task.cancel()
            del self.action_tasks[room_id]

    def _schedule_ai_votes(self, room_id: str, phase_duration: int) -> None:
        """Schedule AI votes to happen during the voting phase.

        AIs will submit votes at random times between 50-90% of the phase duration.
        This prevents blocking at phase start and allows votes to be submitted
        naturally throughout the phase.
        """
        self._cancel_action_tasks(room_id)  # Clear any existing tasks

        if room_id not in self.ai_players:
            return

        game = self.game_manager.get_game(room_id)
        if game is None:
            return

        if room_id not in self.action_tasks:
            self.action_tasks[room_id] = []

        # Schedule each AI to vote at a random time during the phase
        for ai_id, ai_player in self.ai_players[room_id].items():
            player = game.players.get(ai_id)
            if player is None or not player.is_alive:
                continue

            # Random delay between 50-90% of phase duration
            delay = random.uniform(phase_duration * 0.5, phase_duration * 0.9)

            async def submit_vote_task(ai_id=ai_id, ai_player=ai_player):
                try:
                    await asyncio.sleep(delay)

                    # Check game state is still valid
                    game = self.game_manager.get_game(room_id)
                    if game is None or game.phase != GamePhase.VOTING:
                        return

                    player = game.players.get(ai_id)
                    if player is None or not player.is_alive:
                        return

                    # Get valid vote targets
                    await self._submit_single_ai_vote(room_id, game, ai_player)

                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error(f"Error in scheduled AI vote for {ai_player.name}: {e}", exc_info=True)

            task = asyncio.create_task(submit_vote_task())
            self.action_tasks[room_id].append(task)

    def _schedule_ai_night_actions(self, room_id: str, phase_duration: int) -> None:
        """Schedule AI night actions to happen during the night phase.

        AIs will submit actions at random times between 40-80% of the phase duration.
        """
        self._cancel_action_tasks(room_id)  # Clear any existing tasks

        if room_id not in self.ai_players:
            return

        game = self.game_manager.get_game(room_id)
        if game is None:
            return

        if room_id not in self.action_tasks:
            self.action_tasks[room_id] = []

        # Schedule each AI to act at a random time during the phase
        for ai_id, ai_player in self.ai_players[room_id].items():
            player = game.players.get(ai_id)
            if player is None or not player.is_alive:
                continue

            # Skip villagers (no night action)
            if ai_player.role == Role.VILLAGER:
                continue

            # Random delay between 40-80% of phase duration
            delay = random.uniform(phase_duration * 0.4, phase_duration * 0.8)

            async def submit_action_task(ai_id=ai_id, ai_player=ai_player):
                try:
                    await asyncio.sleep(delay)

                    # Check game state is still valid
                    game = self.game_manager.get_game(room_id)
                    if game is None or game.phase != GamePhase.NIGHT:
                        return

                    player = game.players.get(ai_id)
                    if player is None or not player.is_alive:
                        return

                    # Submit night action
                    await self._submit_single_ai_night_action(room_id, game, ai_player)

                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error(f"Error in scheduled AI night action for {ai_player.name}: {e}", exc_info=True)

            task = asyncio.create_task(submit_action_task())
            self.action_tasks[room_id].append(task)

    async def _submit_single_ai_vote(self, room_id: str, game, ai_player: AIPlayerType) -> None:
        """Submit a vote for a single AI player."""
        # Get alive players
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

        # Get valid targets (exclude self and fellow wolves if wolf)
        if ai_player.team and ai_player.team.value == "mafia":
            valid_targets = [
                p for p in alive_players
                if p["id"] != ai_player.id and p["id"] not in wolf_ids
            ]
        else:
            valid_targets = [
                p for p in alive_players
                if p["id"] != ai_player.id
            ]

        if not valid_targets:
            return

        # Get vote target
        if isinstance(ai_player, LLMPlayer):
            context = self._build_player_context(ai_player, game)
            target_id = await ai_player.choose_vote_target(context, valid_targets)
        else:
            known_wolves = wolf_ids if ai_player.team and ai_player.team.value == "mafia" else None
            target_id = ai_player.choose_vote_target(alive_players, known_wolves)

        if target_id:
            success = game.submit_vote(ai_player.id, target_id)
            if success:
                logger.info(f"AI {ai_player.name} voted for {target_id}")
                await self.sio.emit(
                    "vote_update",
                    {"votes": game.get_vote_counts()},
                    room=room_id,
                )

    async def _submit_single_ai_night_action(self, room_id: str, game, ai_player: AIPlayerType) -> None:
        """Submit a night action for a single AI player."""
        # Get alive players
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

        # Get valid targets based on role
        if ai_player.role == Role.WEREWOLF:
            valid_targets = [
                p for p in alive_players
                if p["id"] != ai_player.id and p["id"] not in wolf_ids
            ]
        elif ai_player.role == Role.SEER:
            valid_targets = [
                p for p in alive_players
                if p["id"] != ai_player.id
            ]
        elif ai_player.role == Role.DOCTOR:
            valid_targets = alive_players  # Can protect anyone including self
        else:
            return

        if not valid_targets:
            return

        # Get target
        if isinstance(ai_player, LLMPlayer):
            context = self._build_player_context(ai_player, game)
            target_id = await ai_player.choose_night_action_target(context, valid_targets)
        else:
            fellow_wolves = wolf_ids if ai_player.role == Role.WEREWOLF else None
            target_id = ai_player.choose_night_action_target(alive_players, fellow_wolves)

        if target_id is None:
            return

        # Submit action based on role
        success = False
        if ai_player.role == Role.WEREWOLF:
            success = game.submit_werewolf_vote(ai_player.id, target_id)
            if success:
                # Broadcast to other werewolves
                for wid in wolf_ids:
                    if wid in game.players:
                        await self.sio.emit(
                            "werewolf_vote_update",
                            {"votes": game.get_werewolf_vote_counts()},
                            to=wid,
                        )

        elif ai_player.role == Role.SEER:
            success = game.submit_seer_action(ai_player.id, target_id)
            if success and isinstance(ai_player, LLMPlayer):
                # Track seer result
                target_player = game.players.get(target_id)
                if target_player:
                    is_wolf = target_player.role == Role.WEREWOLF
                    ai_player.add_seer_result(target_player.name, is_wolf)

        elif ai_player.role == Role.DOCTOR:
            success = game.submit_doctor_action(ai_player.id, target_id)

        if success:
            logger.info(f"AI {ai_player.name} ({ai_player.role.value}) targeted {target_id}")

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

        # Process each AI player with stagger
        for ai_id, ai_player in self.ai_players[room_id].items():
            player = game.players.get(ai_id)
            if player is None or not player.is_alive:
                continue

            # Stagger AI votes
            await asyncio.sleep(
                random.uniform(AI_CHAT_STAGGER_MIN, AI_CHAT_STAGGER_MAX)
            )

            # Check game state still valid
            game = self.game_manager.get_game(room_id)
            if game is None or game.phase != GamePhase.VOTING:
                break

            # Get valid targets (exclude self and fellow wolves if wolf)
            if ai_player.team and ai_player.team.value == "mafia":
                valid_targets = [
                    p for p in alive_players
                    if p["id"] != ai_player.id and p["id"] not in wolf_ids
                ]
            else:
                valid_targets = [
                    p for p in alive_players
                    if p["id"] != ai_player.id
                ]

            if not valid_targets:
                continue

            # Get vote target
            if isinstance(ai_player, LLMPlayer):
                context = self._build_player_context(ai_player, game)
                target_id = await ai_player.choose_vote_target(context, valid_targets)
            else:
                known_wolves = wolf_ids if ai_player.team and ai_player.team.value == "mafia" else None
                target_id = ai_player.choose_vote_target(alive_players, known_wolves)

            if target_id:
                success = game.submit_vote(ai_player.id, target_id)
                if success:
                    logger.info(f"AI {ai_player.name} voted for {target_id}")
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

        # Process each AI player with stagger
        for ai_id, ai_player in self.ai_players[room_id].items():
            player = game.players.get(ai_id)
            if player is None or not player.is_alive:
                continue

            # Skip villagers (no night action)
            if ai_player.role == Role.VILLAGER:
                continue

            # Stagger AI actions
            # NOTE: commented out, seems to be unnecessary and annoying
            # await asyncio.sleep(
            #     random.uniform(AI_CHAT_STAGGER_MIN, AI_CHAT_STAGGER_MAX)
            # )

            # Check game state still valid
            game = self.game_manager.get_game(room_id)
            if game is None or game.phase != GamePhase.NIGHT:
                break

            # Get valid targets based on role
            if ai_player.role == Role.WEREWOLF:
                valid_targets = [
                    p for p in alive_players
                    if p["id"] != ai_player.id and p["id"] not in wolf_ids
                ]
            elif ai_player.role == Role.SEER:
                valid_targets = [
                    p for p in alive_players
                    if p["id"] != ai_player.id
                ]
            elif ai_player.role == Role.DOCTOR:
                valid_targets = alive_players  # Can protect anyone including self
            else:
                continue

            if not valid_targets:
                continue

            # Get target
            if isinstance(ai_player, LLMPlayer):
                context = self._build_player_context(ai_player, game)
                target_id = await ai_player.choose_night_action_target(context, valid_targets)
            else:
                fellow_wolves = wolf_ids if ai_player.role == Role.WEREWOLF else None
                target_id = ai_player.choose_night_action_target(alive_players, fellow_wolves)

            if target_id is None:
                continue

            # Submit action based on role
            success = False
            if ai_player.role == Role.WEREWOLF:
                success = game.submit_werewolf_vote(ai_player.id, target_id)
                if success:
                    # Broadcast to other werewolves
                    for wid in wolf_ids:
                        if wid in game.players:
                            await self.sio.emit(
                                "werewolf_vote_update",
                                {"votes": game.get_werewolf_vote_counts()},
                                to=wid,
                            )

            elif ai_player.role == Role.SEER:
                success = game.submit_seer_action(ai_player.id, target_id)
                if success and isinstance(ai_player, LLMPlayer):
                    # Track seer result
                    target_player = game.players.get(target_id)
                    if target_player:
                        is_wolf = target_player.role == Role.WEREWOLF
                        ai_player.add_seer_result(target_player.name, is_wolf)

            elif ai_player.role == Role.DOCTOR:
                success = game.submit_doctor_action(ai_player.id, target_id)

            if success:
                logger.info(f"AI {ai_player.name} ({ai_player.role.value}) targeted {target_id}")

    async def _update_ai_notes(self, room_id: str) -> None:
        """Update notes for all LLM AI players (blocking - only use at game end)."""
        if not self.use_llm:
            return

        game = self.game_manager.get_game(room_id)
        if game is None:
            return

        if room_id not in self.ai_players:
            return

        for ai_id, ai_player in self.ai_players[room_id].items():
            if isinstance(ai_player, LLMPlayer):
                player = game.players.get(ai_id)
                if player is None:
                    continue

                # Stagger note updates
                #NOTE: commented out, seems to be unnecessary and annoying
                # await asyncio.sleep(
                #     random.uniform(AI_CHAT_STAGGER_MIN, AI_CHAT_STAGGER_MAX)
                # )

                context = self._build_player_context(ai_player, game)
                await ai_player.update_notes(context)

                # Save notes to store
                self.notes_store.save(room_id, ai_id, ai_player.notes)

    async def _update_single_ai_notes(self, room_id: str, ai_id: str, ai_player: LLMPlayer) -> None:
        """Update notes for a single AI player."""
        try:
            game = self.game_manager.get_game(room_id)
            if game is None:
                return

            context = self._build_player_context(ai_player, game)
            await ai_player.update_notes(context)

            # Save notes to store
            self.notes_store.save(room_id, ai_id, ai_player.notes)
        except Exception as e:
            logger.warning(f"Failed to update notes for {ai_player.name}: {e}")

    def _schedule_notes_updates(self, room_id: str) -> None:
        """Schedule AI notes updates as background task (non-blocking).

        Notes are updated in parallel using asyncio.gather() and run as a
        background task during the NIGHT phase. This prevents blocking the
        phase transition while still ensuring notes are fresh for the next
        DAY phase.
        """
        if not self.use_llm:
            return

        game = self.game_manager.get_game(room_id)
        if game is None:
            return

        async def update_all_notes():
            try:
                # Gather all update tasks
                tasks = []
                for ai_id, ai_player in self.ai_players.get(room_id, {}).items():
                    if isinstance(ai_player, LLMPlayer):
                        player = game.players.get(ai_id)
                        if player is not None:
                            tasks.append(self._update_single_ai_notes(room_id, ai_id, ai_player))

                # Run all in parallel
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                    logger.info(f"Updated notes for {len(tasks)} AI players in room {room_id}")

            except Exception as e:
                logger.error(f"Error updating AI notes: {e}", exc_info=True)

        # Schedule as background task
        asyncio.create_task(update_all_notes())

    def _save_all_notes(self, room_id: str) -> None:
        """Save all AI notes for a room."""
        if room_id not in self.ai_players:
            return

        for ai_id, ai_player in self.ai_players[room_id].items():
            if hasattr(ai_player, 'notes') and ai_player.notes:
                self.notes_store.save(room_id, ai_id, ai_player.notes)

    def cleanup_room(self, room_id: str) -> None:
        """Clean up AI resources when a room is deleted."""
        self._stop_chat_loop(room_id)
        self._cancel_action_tasks(room_id)
        self.ai_players.pop(room_id, None)
        # Optionally clear notes (or keep for analysis)
        self.notes_store.clear_room(room_id)
