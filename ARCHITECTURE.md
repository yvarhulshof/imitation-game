# Architecture Documentation

This document explains the Imitation Game codebase and tracks what has been discussed. Each section has a checkbox to mark when we've covered it together.

---

## Table of Contents

1. [High-Level Overview](#high-level-overview)
2. [Backend Architecture](#backend-architecture)
   - [Server Setup (main.py)](#server-setup-mainpy)
   - [Data Models (models.py)](#data-models-modelspy)
   - [Game State (game/state.py)](#game-state-gamestatepy)
   - [Game Manager (game/manager.py)](#game-manager-gamemanagerpy)
   - [Socket Events (game/events.py)](#socket-events-gameeventspy)
   - [AI Player (ai/player.py)](#ai-player-aiplayerpy)
3. [Frontend Architecture](#frontend-architecture)
   - [Socket Store (stores/socket.ts)](#socket-store-storessocketts)
   - [Game Store (stores/game.ts)](#game-store-storesgamets)
   - [Lobby Component](#lobby-component)
   - [Game Component](#game-component)
   - [Chat Component](#chat-component)
   - [PlayerList Component](#playerlist-component)
4. [Data Flow](#data-flow)
   - [Room Creation Flow](#room-creation-flow)
   - [Joining a Room Flow](#joining-a-room-flow)
   - [Messaging Flow](#messaging-flow)
5. [Planned Features](#planned-features)

---

## High-Level Overview

- [ ] **Discussed**

### What is this project?

A text-based multiplayer social deduction game (like Werewolf/Mafia) where some players are secretly AI. Players must:
1. Deduce each other's roles (Werewolf, Villager, etc.)
2. Figure out which players are human vs AI

### Tech Stack

```
┌─────────────────┐         WebSocket          ┌─────────────────┐
│    Frontend     │ ◄──────(Socket.IO)───────► │    Backend      │
│  SvelteKit 5    │                            │  FastAPI        │
│  TypeScript     │                            │  python-socketio│
└─────────────────┘                            └────────┬────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │  Claude API     │
                                               │  (AI Players)   │
                                               └─────────────────┘
```

### Directory Structure

```
imitation-game/
├── backend/
│   └── app/
│       ├── main.py          # Server entry point
│       ├── models.py        # Pydantic data models
│       ├── game/
│       │   ├── state.py     # GameState dataclass
│       │   ├── manager.py   # GameManager (room management)
│       │   └── events.py    # Socket.IO event handlers
│       └── ai/
│           └── player.py    # AIPlayer class
│
└── frontend/
    └── src/
        ├── routes/
        │   └── +page.svelte  # Main page (Lobby or Game)
        └── lib/
            ├── stores/
            │   ├── socket.ts # Socket.IO connection
            │   └── game.ts   # Game state stores
            └── components/
                ├── Lobby.svelte
                ├── Game.svelte
                ├── Chat.svelte
                └── PlayerList.svelte
```

---

## Backend Architecture

### Server Setup (main.py)

- [ ] **Discussed**

**Purpose**: Creates and configures the FastAPI + Socket.IO server.

**Key concepts**:

1. **Two servers in one**: FastAPI handles HTTP routes, Socket.IO handles WebSocket events
2. **ASGI wrapping**: Socket.IO wraps FastAPI so both share the same port

```python
# Socket.IO server (handles real-time events)
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=["http://localhost:5173"],
)

# FastAPI app (handles HTTP routes like /health)
app = FastAPI(title="Imitation Game API")

# Wrap them together - Socket.IO forwards non-WebSocket requests to FastAPI
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)
```

**Why this pattern?**
- Socket.IO: Real-time bidirectional communication (chat, game events)
- FastAPI: Could be used for REST endpoints (future: user auth, game history)
- `socket_app` is what uvicorn actually runs

**Global state**:
```python
game_manager = GameManager()  # Single instance managing all game rooms
register_events(sio, game_manager)  # Connects Socket.IO events to game logic
```

---

### Data Models (models.py)

- [ ] **Discussed**

**Purpose**: Defines the data structures used throughout the backend.

**Why Pydantic?**
- Automatic validation
- Easy serialization to JSON (for sending to frontend)
- Type hints for IDE support

#### PlayerType Enum

```python
class PlayerType(str, Enum):
    HUMAN = "human"
    AI = "ai"
```

Inherits from `str` so when serialized, it becomes `"human"` or `"ai"` (not `PlayerType.HUMAN`).

#### GamePhase Enum

```python
class GamePhase(str, Enum):
    LOBBY = "lobby"      # Waiting for players
    DAY = "day"          # Discussion phase
    NIGHT = "night"      # Werewolves act (not yet implemented)
    VOTING = "voting"    # Vote to eliminate (not yet implemented)
    ENDED = "ended"      # Game over
```

Currently only `LOBBY` is used. Other phases are placeholders.

#### Player Model

```python
class Player(BaseModel):
    id: str              # Socket.IO session ID (sid)
    name: str            # Display name chosen by player
    player_type: PlayerType
    is_alive: bool = True
    is_host: bool = False
```

- `id` is the Socket.IO `sid` - unique per connection
- `is_host` is True for the first player to join a room

#### ChatMessage Model

```python
class ChatMessage(BaseModel):
    player_id: str       # Who sent it
    player_name: str     # Display name (denormalized for convenience)
    content: str         # Message text
    timestamp: float     # Unix timestamp (time.time())
```

`player_name` is stored directly to avoid lookups when displaying messages.

---

### Game State (game/state.py)

- [ ] **Discussed**

**Purpose**: Holds all data for a single game room.

**Why dataclass (not Pydantic)?**
- `GameState` is internal server state, not sent over network directly
- Dataclass is lighter weight for mutable state
- `to_dict()` handles serialization when needed

```python
@dataclass
class GameState:
    room_id: str
    phase: GamePhase = GamePhase.LOBBY
    players: dict[str, Player] = field(default_factory=dict)  # id -> Player
    messages: list[ChatMessage] = field(default_factory=list)
    round_number: int = 0
```

**Important**: `field(default_factory=dict)` is required for mutable defaults in dataclasses. Without it, all instances would share the same dict!

**Methods**:

```python
def add_player(self, player: Player) -> None:
    self.players[player.id] = player  # Dict keyed by socket ID for O(1) lookup

def remove_player(self, player_id: str) -> None:
    self.players.pop(player_id, None)  # .pop with default avoids KeyError

def get_player_list(self) -> list[dict]:
    return [p.model_dump() for p in self.players.values()]  # For JSON serialization

def to_dict(self) -> dict:
    # Only sends what frontend needs (not message history)
    return {
        "room_id": self.room_id,
        "phase": self.phase.value,      # .value gives string, not Enum
        "players": self.get_player_list(),
        "round_number": self.round_number,
    }
```

---

### Game Manager (game/manager.py)

- [ ] **Discussed**

**Purpose**: Manages all game rooms. Think of it as the "lobby of lobbies".

```python
class GameManager:
    def __init__(self):
        self.games: dict[str, GameState] = {}  # room_id -> GameState
```

Single dict holds all active games. No persistence - games are lost on server restart.

#### create_room()

```python
def create_room(self) -> str:
    room_id = secrets.token_urlsafe(6)  # e.g., "aB3_xY"
    self.games[room_id] = GameState(room_id=room_id)
    return room_id
```

- `secrets.token_urlsafe(6)` generates 8 URL-safe characters (6 bytes = 8 base64 chars)
- Short enough to share verbally, long enough to not guess

#### join_room()

```python
def join_room(self, room_id: str, player_id: str, player_name: str) -> GameState | None:
    game = self.get_game(room_id)
    if game is None:
        return None

    is_host = len(game.players) == 0  # First player becomes host
    player = Player(
        id=player_id,
        name=player_name,
        player_type=PlayerType.HUMAN,  # Always human (AI added differently)
        is_host=is_host,
    )
    game.add_player(player)
    return game
```

Returns the `GameState` so caller can emit it to the player.

#### leave_room()

```python
def leave_room(self, room_id: str, player_id: str) -> None:
    game = self.get_game(room_id)
    if game:
        game.remove_player(player_id)
        if len(game.players) == 0:
            del self.games[room_id]  # Clean up empty rooms
```

Auto-deletes rooms when last player leaves.

---

### Socket Events (game/events.py)

- [x] **Discussed**

**Purpose**: Handles all real-time communication between clients and server.

**Pattern**: `register_events()` receives the Socket.IO server and GameManager, then defines event handlers as nested functions.

```python
def register_events(sio: socketio.AsyncServer, game_manager: GameManager):
    @sio.event
    async def connect(sid, environ):
        print(f"Client connected: {sid}")
```

#### Event: connect / disconnect

```python
@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")

@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")
    # TODO: Clean up player from any rooms they were in
```

`sid` (session ID) uniquely identifies a WebSocket connection.

**Known issue**: Disconnect doesn't clean up the player from rooms yet.

#### Event: create_room

```python
@sio.event
async def create_room(sid):
    room_id = game_manager.create_room()
    await sio.enter_room(sid, room_id)  # Socket.IO "room" for broadcasting
    await sio.emit("room_created", {"room_id": room_id}, to=sid)
    return {"room_id": room_id}
```

**Socket.IO rooms**: A room is a broadcast group. `sio.enter_room(sid, room_id)` adds this connection to the room. Later, `emit(..., room=room_id)` sends to all connections in that room.

**Return value**: Socket.IO supports acknowledgements - the return value is sent back to the client's callback.

#### Event: join_room

```python
@sio.event
async def join_room(sid, data):
    room_id = data.get("room_id")
    player_name = data.get("player_name", "Anonymous")

    if not game_manager.room_exists(room_id):
        await sio.emit("error", {"message": "Room not found"}, to=sid)
        return {"success": False, "error": "Room not found"}

    game = game_manager.join_room(room_id, sid, player_name)
    await sio.enter_room(sid, room_id)

    # Tell the new player about the game state
    await sio.emit("room_joined", {"game": game.to_dict()}, to=sid)

    # Tell existing players someone joined
    await sio.emit(
        "player_joined",
        {"player_id": sid, "player_name": player_name},
        room=room_id,
        skip_sid=sid,  # Don't send to the joining player
    )

    return {"success": True}
```

**Two emits**:
1. `room_joined` to the new player with full game state
2. `player_joined` to everyone else with just the new player info

`skip_sid=sid` prevents sending to the originating socket.

#### Event: send_message

```python
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
```

**Broadcast**: `room=room_id` sends to everyone in the room, including the sender. The sender sees their own message come back, confirming it was received.

---

### AI Player (ai/player.py)

- [ ] **Discussed**

**Purpose**: Generates AI responses using Claude API.

**Status**: Implemented but not yet integrated into game flow.

```python
class AIPlayer:
    def __init__(self, name: str, personality: str = ""):
        self.name = name
        self.personality = personality or "You are a player in a social deduction game."
        self.client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY env var
        self.message_history: list[ChatMessage] = []
```

#### generate_response()

```python
async def generate_response(self, messages: list[ChatMessage]) -> str:
    # Build conversation context from last 20 messages
    conversation = "\n".join(
        f"{msg.player_name}: {msg.content}" for msg in messages[-20:]
    )

    system_prompt = f"""You are {self.name}, a player in a social deduction game...
Your goal is to participate naturally in the conversation.
Never reveal that you are an AI."""

    response = self.client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=150,              # Keep responses short
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": f"Here's the recent chat:\n\n{conversation}\n\nWrite your next message...",
            }
        ],
    )

    return response.content[0].text
```

**Design decisions**:
- Only last 20 messages to keep context window small and responses fast
- `max_tokens=150` forces concise responses (1-2 sentences)
- System prompt tells AI to act natural and hide its AI nature

**Not yet implemented**:
- When/how AI decides to speak
- Integration with game events
- Multiple AI personalities

---

## Frontend Architecture

### Socket Store (stores/socket.ts)

- [ ] **Discussed**

**Purpose**: Manages the WebSocket connection lifecycle.

```typescript
import { io, Socket } from 'socket.io-client';
import { writable } from 'svelte/store';

const SOCKET_URL = 'http://localhost:8000';

export const socket = writable<Socket | null>(null);
export const connected = writable(false);
```

**Svelte stores**: Writable stores are reactive - when updated, any component using them re-renders.

#### initSocket()

```typescript
export function initSocket(): Socket {
    const newSocket = io(SOCKET_URL, {
        transports: ['websocket']  // Skip HTTP long-polling, go straight to WebSocket
    });

    newSocket.on('connect', () => {
        connected.set(true);       // Update reactive store
        console.log('Connected to server');
    });

    newSocket.on('disconnect', () => {
        connected.set(false);
        console.log('Disconnected from server');
    });

    socket.set(newSocket);
    return newSocket;
}
```

**Why `transports: ['websocket']`?** Socket.IO normally tries HTTP long-polling first, then upgrades. This skips that for faster connection.

#### getSocket()

```typescript
export function getSocket(): Socket | null {
    let s: Socket | null = null;
    socket.subscribe((value) => (s = value))();  // Immediately unsubscribe
    return s;
}
```

**Synchronous store access**: Normally you'd use `$socket` in Svelte components. This helper lets non-reactive code get the current value. The `()` at the end calls the unsubscribe function returned by `subscribe`.

---

### Game Store (stores/game.ts)

- [ ] **Discussed**

**Purpose**: Holds all game-related state.

```typescript
// TypeScript interfaces mirror backend Pydantic models
export interface Player {
    id: string;
    name: string;
    player_type: 'human' | 'ai';
    is_alive: boolean;
    is_host: boolean;
}

export interface ChatMessage {
    player_id: string;
    player_name: string;
    content: string;
    timestamp: number;
}

export interface GameState {
    room_id: string;
    phase: 'lobby' | 'day' | 'night' | 'voting' | 'ended';
    players: Player[];
    round_number: number;
}
```

**Stores**:

```typescript
export const gameState = writable<GameState | null>(null);  // Current game
export const messages = writable<ChatMessage[]>([]);        // Chat history
export const playerName = writable<string>('');             // Local player's name
export const currentRoom = writable<string | null>(null);   // Room ID if in a room
```

**Separation**: `messages` is separate from `gameState` because messages update frequently and we don't want to trigger full game state re-renders.

---

### Lobby Component

- [ ] **Discussed**

**Purpose**: Entry point - create or join a game room.

**File**: `frontend/src/lib/components/Lobby.svelte`

#### Svelte 5 Runes

```typescript
let nameInput = $state('');    // Reactive state (Svelte 5 syntax)
let roomInput = $state('');
let error = $state('');
```

`$state()` is Svelte 5's new reactivity primitive, replacing `let x = ''` with `$:` dependencies.

#### createRoom()

```typescript
function createRoom() {
    if (!nameInput.trim()) {
        error = 'Please enter your name';
        return;
    }

    const socket = getSocket();
    if (!socket) return;

    playerName.set(nameInput.trim());

    // Create room, then immediately join it
    socket.emit('create_room', {}, (response: { room_id: string }) => {
        currentRoom.set(response.room_id);
        socket.emit('join_room', {
            room_id: response.room_id,
            player_name: nameInput.trim()
        }, () => {});
    });
}
```

**Callback pattern**: `socket.emit(event, data, callback)` - callback receives the server's return value.

#### Event Listeners with $effect

```typescript
$effect(() => {
    const socket = getSocket();
    if (!socket) return;

    socket.on('room_joined', (data: { game: GameState }) => {
        gameState.set(data.game);
        currentRoom.set(data.game.room_id);
        messages.set([]);  // Clear old messages
    });

    socket.on('player_joined', (data) => {
        gameState.update((state) => {
            if (!state) return state;
            return {
                ...state,
                players: [...state.players, {
                    id: data.player_id,
                    name: data.player_name,
                    player_type: 'human',
                    is_alive: true,
                    is_host: false
                }]
            };
        });
    });

    // Cleanup on component destroy
    return () => {
        socket.off('room_joined');
        socket.off('player_joined');
        // ...
    };
});
```

`$effect()` runs on mount and when dependencies change. Returning a function provides cleanup.

---

### Game Component

- [ ] **Discussed**

**Purpose**: Container for the in-game UI.

**File**: `frontend/src/lib/components/Game.svelte`

```svelte
<div class="game-container">
    <header>
        <h1>Imitation Game</h1>
        {#if $currentRoom}
            <span class="room-code">Room: {$currentRoom}</span>
        {/if}
        {#if $gameState}
            <span class="phase">{$gameState.phase}</span>
        {/if}
    </header>

    <main>
        <aside>
            <PlayerList />
        </aside>

        <section class="chat-section">
            <Chat />
        </section>
    </main>
</div>
```

**Layout**: CSS flexbox - sidebar (PlayerList) + main area (Chat).

**`$` prefix**: In Svelte, `$storeName` auto-subscribes to a store and gives you the current value.

---

### Chat Component

- [ ] **Discussed**

**Purpose**: Displays messages and handles input.

**File**: `frontend/src/lib/components/Chat.svelte`

#### Auto-scroll

```typescript
let chatContainer: HTMLDivElement;

$effect(() => {
    if ($messages && chatContainer) {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
});
```

Whenever `$messages` changes, scroll to bottom.

#### sendMessage()

```typescript
function sendMessage() {
    if (!messageInput.trim()) return;

    const socket = getSocket();
    if (socket && $currentRoom) {
        socket.emit('send_message', {
            room_id: $currentRoom,
            content: messageInput.trim()
        });
        messageInput = '';
    }
}
```

**Optimistic update?** No - we wait for `new_message` event from server. This ensures message order is server-authoritative.

#### Keyboard handling

```typescript
function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}
```

Enter sends, Shift+Enter for newline (though input doesn't support multiline currently).

---

### PlayerList Component

- [ ] **Discussed**

**Purpose**: Shows all players in the room.

**File**: `frontend/src/lib/components/PlayerList.svelte`

```svelte
{#each $gameState.players as player (player.id)}
    <li class:host={player.is_host} class:dead={!player.is_alive}>
        {player.name}
        {#if player.is_host}<span class="badge">Host</span>{/if}
    </li>
{/each}
```

**`class:name={condition}`**: Svelte shorthand for conditional CSS classes.

**`(player.id)`**: Keyed each block - helps Svelte track which DOM elements to update.

---

## Data Flow

### Room Creation Flow

- [ ] **Discussed**

```
┌──────────┐                    ┌──────────┐
│  Client  │                    │  Server  │
└────┬─────┘                    └────┬─────┘
     │                               │
     │  emit('create_room', {})      │
     │ ─────────────────────────────►│
     │                               │ GameManager.create_room()
     │                               │ sio.enter_room(sid, room_id)
     │  callback({ room_id })        │
     │ ◄─────────────────────────────│
     │                               │
     │  emit('join_room', {...})     │
     │ ─────────────────────────────►│
     │                               │ GameManager.join_room()
     │  emit('room_joined', {game})  │
     │ ◄─────────────────────────────│
     │                               │
     │  currentRoom.set(room_id)     │
     │  gameState.set(game)          │
     │                               │
```

---

### Joining a Room Flow

- [ ] **Discussed**

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│ Client A │     │  Server  │     │ Client B │
│  (host)  │     │          │     │  (joins) │
└────┬─────┘     └────┬─────┘     └────┬─────┘
     │                │                │
     │                │  emit('join_room', {room_id, name})
     │                │ ◄──────────────│
     │                │                │
     │                │ GameManager.join_room()
     │                │ sio.enter_room(sid, room_id)
     │                │                │
     │                │  emit('room_joined', {game})
     │                │ ──────────────►│ Updates gameState
     │                │                │
     │  emit('player_joined', {...})   │
     │ ◄──────────────│                │
     │                │                │
     │ Updates        │                │
     │ gameState      │                │
```

---

### Messaging Flow

- [ ] **Discussed**

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│ Client A │     │  Server  │     │ Client B │
└────┬─────┘     └────┬─────┘     └────┬─────┘
     │                │                │
     │  emit('send_message', {...})    │
     │ ──────────────►│                │
     │                │                │
     │                │ Creates ChatMessage
     │                │ game.add_message()
     │                │                │
     │  emit('new_message', msg)       │
     │ ◄──────────────┼───────────────►│
     │                │                │
     │ messages.update()  messages.update()
     │ (sees own msg) │                │
```

All clients (including sender) receive the message via broadcast.

---

## Planned Features

- [ ] **Discussed**

### Not Yet Implemented

1. **Game phases**: Day/night cycles, voting
2. **Role assignment**: Werewolf, Villager, Seer, etc.
3. **AI player integration**: Triggering AI responses, timing
4. **"Who is AI?" voting**: End-game reveal
5. **Disconnect handling**: Clean up players who leave
6. **Host controls**: Start game, kick players, settings
7. **Multiple game modes**: Per notes.txt

### Technical Debt

- `events.py:15`: TODO for disconnect cleanup
- No input validation/sanitization
- No rate limiting
- No persistence (games lost on restart)

---

## Session Log

Track our discussion sessions here:

| Date | Sections Covered | Notes |
|------|------------------|-------|
| | | |

