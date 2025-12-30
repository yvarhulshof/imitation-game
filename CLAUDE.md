# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Imitation Game is a text-based, online multiplayer social deduction game inspired by Werewolf, Mafia, and Town of Salem. The twist: some or all players are LLMs. Players must deduce both roles and which players are AI.

## Tech Stack

- **Backend**: Python with FastAPI + python-socketio
- **Frontend**: SvelteKit (Svelte 5) + TypeScript
- **Real-time**: WebSocket via Socket.IO
- **LLM**: Anthropic Claude API

## Development Commands

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:socket_app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Frontend runs on http://localhost:5173, backend on http://localhost:8000.

## Architecture

### Backend (`backend/app/`)
- `main.py` - FastAPI + Socket.IO server setup
- `models.py` - Pydantic models (Player, ChatMessage, GamePhase)
- `game/state.py` - GameState dataclass
- `game/manager.py` - GameManager handles room creation, player join/leave
- `game/events.py` - Socket.IO event handlers (connect, join_room, send_message)
- `ai/player.py` - AIPlayer class for LLM-controlled players

### Frontend (`frontend/src/`)
- `lib/stores/socket.ts` - Socket.IO connection management
- `lib/stores/game.ts` - Game state stores (Svelte stores)
- `lib/components/` - UI components (Lobby, Game, Chat, PlayerList)
- `routes/+page.svelte` - Main page, switches between Lobby and Game views

### Socket Events
- `create_room` - Creates new game room, returns room_id
- `join_room` - Join with room_id and player_name
- `send_message` - Send chat message to room
- `leave_room` - Leave current room

## Game Modes (Planned)

- Find the AIs
- Werewolves + find the AIs (Town of Salem style)

## Knowledge Transfer

The user wants to fully understand the codebase. Use these approaches:

1. **On-demand**: When the user asks about a specific part, explain it thoroughly
2. **Build-driven**: When working on features, explain relevant sections of the code as we touch them

**Tracking**: `ARCHITECTURE.md` contains detailed explanations of all components with checkboxes. When explaining a section:
- Mark the checkbox as done: `- [x]`
- Add an entry to the Session Log table at the bottom

Always ensure the user understands the code before moving on.

## Version Control

**Commit workflow**: I propose, user approves
- Propose a commit after completing a logical unit of work (feature, bugfix, refactor)
- Wait for user approval before committing
- Write clear commit messages explaining what changed and why

**Branching strategy**: Simple (main only)
- Commit directly to main
- Keep commits atomic and working (code should run after each commit)

**Commit points**:
- After implementing a new feature
- After fixing a bug
- After refactoring
- Before starting something risky (so we can rollback)
