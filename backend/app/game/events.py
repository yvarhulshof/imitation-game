import time
import socketio
from app.game.manager import GameManager
from app.models import ChatMessage


def register_events(sio: socketio.AsyncServer, game_manager: GameManager):
    @sio.event
    async def connect(sid, environ):
        print(f"Client connected: {sid}")

    @sio.event
    async def disconnect(sid):
        print(f"Client disconnected: {sid}")
        # TODO: Clean up player from any rooms they were in

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
