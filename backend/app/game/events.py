import time
import socketio
from app.game.manager import GameManager
from app.game.phase import PhaseController
from app.models import ChatMessage, GamePhase, Role


def register_events(
    sio: socketio.AsyncServer,
    game_manager: GameManager,
    phase_controller: PhaseController,
    ai_controller=None,
):
    @sio.event
    async def connect(sid, environ):
        print(f"Client connected: {sid}")

    @sio.event
    async def disconnect(sid):
        print(f"Client disconnected: {sid}")
        result = game_manager.disconnect_player(sid)
        if result is None:
            return

        room_id = result["room_id"]

        await sio.emit(
            "player_left",
            {"player_id": result["player_id"], "player_name": result["player_name"]},
            room=room_id,
        )

        if "new_host_id" in result:
            await sio.emit(
                "host_changed",
                {"new_host_id": result["new_host_id"]},
                room=room_id,
            )

    @sio.event
    async def create_room(sid):
        room_id = game_manager.create_room()
        await sio.enter_room(sid, room_id)
        await sio.emit("room_created", {"room_id": room_id}, to=sid)
        return {"room_id": room_id}

    @sio.event
    async def join_room(sid, data):
        room_id = data.get("room_id")
        player_name = data.get("player_name", "Anonymous")

        if not game_manager.room_exists(room_id):
            await sio.emit("error", {"message": "Room not found"}, to=sid)
            return {"success": False, "error": "Room not found"}

        game = game_manager.join_room(room_id, sid, player_name)
        await sio.enter_room(sid, room_id)

        # Notify the joining player
        await sio.emit("room_joined", {"game": game.to_dict()}, to=sid)

        # Notify others in the room
        await sio.emit(
            "player_joined",
            {"player_id": sid, "player_name": player_name},
            room=room_id,
            skip_sid=sid,
        )

        return {"success": True}

    @sio.event
    async def send_message(sid, data):
        room_id = data.get("room_id")
        content = data.get("content", "")

        game = game_manager.get_game(room_id)
        if game is None:
            return

        player = game.players.get(sid)
        if player is None:
            return

        # Dead players cannot chat
        if not player.is_alive:
            return

        # No chat during night phase
        if game.phase == GamePhase.NIGHT:
            return

        message = ChatMessage(
            player_id=sid,
            player_name=player.name,
            content=content,
            timestamp=time.time(),
        )
        game.add_message(message)

        await sio.emit("new_message", message.model_dump(), room=room_id)

    @sio.event
    async def leave_room(sid, data):
        room_id = data.get("room_id")
        game_manager.leave_room(room_id, sid)
        await sio.leave_room(sid, room_id)
        await sio.emit("player_left", {"player_id": sid}, room=room_id)

    @sio.event
    async def start_game(sid):
        room_id = game_manager.get_player_room(sid)
        if room_id is None:
            await sio.emit("error", {"message": "Not in a room"}, to=sid)
            return {"success": False, "error": "Not in a room"}

        game = game_manager.get_game(room_id)
        if game is None:
            return {"success": False, "error": "Game not found"}

        player = game.players.get(sid)
        if player is None or not player.is_host:
            await sio.emit("error", {"message": "Only the host can start the game"}, to=sid)
            return {"success": False, "error": "Not the host"}

        success = await phase_controller.start_game(room_id)
        if not success:
            await sio.emit("error", {"message": "Could not start game"}, to=sid)
            return {"success": False, "error": "Could not start game"}

        return {"success": True}

    @sio.event
    async def skip_to_voting(sid):
        room_id = game_manager.get_player_room(sid)
        if room_id is None:
            return {"success": False, "error": "Not in a room"}

        game = game_manager.get_game(room_id)
        if game is None:
            return {"success": False, "error": "Game not found"}

        player = game.players.get(sid)
        if player is None or not player.is_host:
            return {"success": False, "error": "Not the host"}

        success = await phase_controller.skip_to_voting(room_id)
        return {"success": success}

    @sio.event
    async def submit_vote(sid, data):
        target_id = data.get("target_id")
        if target_id is None:
            return {"success": False, "error": "No target specified"}

        room_id = game_manager.get_player_room(sid)
        if room_id is None:
            return {"success": False, "error": "Not in a room"}

        game = game_manager.get_game(room_id)
        if game is None:
            return {"success": False, "error": "Game not found"}

        if game.phase != GamePhase.VOTING:
            return {"success": False, "error": "Not in voting phase"}

        success = game.submit_vote(sid, target_id)
        if not success:
            return {"success": False, "error": "Invalid vote"}

        # Broadcast updated vote counts to all players
        await sio.emit(
            "vote_update",
            {"votes": game.get_vote_counts()},
            room=room_id,
        )

        return {"success": True}

    @sio.event
    async def night_action(sid, data):
        target_id = data.get("target_id")
        if target_id is None:
            return {"success": False, "error": "No target specified"}

        room_id = game_manager.get_player_room(sid)
        if room_id is None:
            return {"success": False, "error": "Not in a room"}

        game = game_manager.get_game(room_id)
        if game is None:
            return {"success": False, "error": "Game not found"}

        if game.phase != GamePhase.NIGHT:
            return {"success": False, "error": "Not in night phase"}

        player = game.players.get(sid)
        if player is None or not player.is_alive:
            return {"success": False, "error": "Cannot perform action"}

        # Handle action based on role
        if player.role == Role.WEREWOLF:
            success = game.submit_werewolf_vote(sid, target_id)
            if success:
                # Broadcast vote counts to all werewolves
                werewolf_ids = [
                    p.id for p in game.players.values()
                    if p.role == Role.WEREWOLF and p.is_alive
                ]
                for wolf_id in werewolf_ids:
                    await sio.emit(
                        "werewolf_vote_update",
                        {"votes": game.get_werewolf_vote_counts()},
                        to=wolf_id,
                    )
            return {"success": success}

        elif player.role == Role.SEER:
            success = game.submit_seer_action(sid, target_id)
            return {"success": success}

        elif player.role == Role.DOCTOR:
            success = game.submit_doctor_action(sid, target_id)
            return {"success": success}

        else:
            # Villagers have no night action
            return {"success": False, "error": "No night action available"}

    @sio.event
    async def add_ai_player(sid, data=None):
        """Add AI player(s) to the room."""
        if ai_controller is None:
            return {"success": False, "error": "AI not available"}

        room_id = game_manager.get_player_room(sid)
        if room_id is None:
            return {"success": False, "error": "Not in a room"}

        game = game_manager.get_game(room_id)
        if game is None:
            return {"success": False, "error": "Game not found"}

        player = game.players.get(sid)
        if player is None or not player.is_host:
            return {"success": False, "error": "Only the host can add AI players"}

        if game.phase != GamePhase.LOBBY:
            return {"success": False, "error": "Can only add AI players in lobby"}

        # Get count from data, default to 1 for backward compatibility
        count = 1
        if data and isinstance(data, dict):
            count = data.get("count", 1)

        # Validate count
        if not isinstance(count, int) or count < 1:
            return {"success": False, "error": "Invalid count"}
        if count > 20:
            return {"success": False, "error": "Cannot add more than 20 AI players at once"}

        # Add AI players
        added_players = []
        for _ in range(count):
            ai_player = ai_controller.add_ai_player(room_id)
            if ai_player is None:
                # Stop if we can't add more
                break

            added_players.append(ai_player)

            # Notify all players in room
            await sio.emit(
                "player_joined",
                {"player_id": ai_player.id, "player_name": ai_player.name},
                room=room_id,
            )

        if not added_players:
            return {"success": False, "error": "Could not add AI players"}

        return {
            "success": True,
            "count": len(added_players),
            "players": [p.model_dump() for p in added_players]
        }

    @sio.event
    async def remove_ai_player(sid, data):
        """Remove an AI player from the room."""
        if ai_controller is None:
            return {"success": False, "error": "AI not available"}

        ai_id = data.get("ai_id")
        if ai_id is None:
            return {"success": False, "error": "No AI player specified"}

        room_id = game_manager.get_player_room(sid)
        if room_id is None:
            return {"success": False, "error": "Not in a room"}

        game = game_manager.get_game(room_id)
        if game is None:
            return {"success": False, "error": "Game not found"}

        player = game.players.get(sid)
        if player is None or not player.is_host:
            return {"success": False, "error": "Only the host can remove AI players"}

        if game.phase != GamePhase.LOBBY:
            return {"success": False, "error": "Can only remove AI players in lobby"}

        success = ai_controller.remove_ai_player(room_id, ai_id)
        if not success:
            return {"success": False, "error": "Could not remove AI player"}

        # Notify all players in room
        await sio.emit(
            "player_left",
            {"player_id": ai_id},
            room=room_id,
        )

        return {"success": True}
