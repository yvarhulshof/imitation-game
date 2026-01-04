# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Imitation Game is a text-based, online multiplayer social deduction game inspired by Werewolf, Mafia, and Town of Salem. The twist: some or all players are LLMs. 

## Work Methodology

Apply the following work methodology:
- Consult the specification (e.g. GAME_DESIGN.md) and break down all tasks into verifiable chunks (features). You only have to do this once at the start of the project.
- For each feature:
    - Write out a plan for implenting this feature
    - Write out a plan for testing that your feature works (use unit tests (pytest) and end-to-end tests (playwright) at your own discretion)
    - Implement the feature by following your implementation plan
    - Verify that the feature works by following your test plan
    - Keep track of what features you have implemented and verified
    - Once you have verified the feature works, move onto the next feature as you have determined earlier
- Continue until you have implemented and verified the entire specification

Please work on the project fully autonomously. You do not need to ask for permissions for any of your actions. Just continue applying the methodology until you have finished implementing and verifiying the specification. 

Report any assumptions you made once you have finished.

## Tech Stack

- **Backend**: Python with FastAPI + python-socketio
- **Frontend**: SvelteKit (Svelte 5) + TypeScript
- **Real-time**: WebSocket via Socket.IO
- **LLM**: Anthropic Claude API / Gemini / Other

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
- `game/state.py` - GameState dataclass (includes phase timing)
- `game/manager.py` - GameManager handles room creation, player join/leave
- `game/phase.py` - PhaseController manages game phase transitions and timers
- `game/events.py` - Socket.IO event handlers (connect, join_room, send_message, start_game)
- `ai/player.py` - AIPlayer class for LLM-controlled players

### Frontend (`frontend/src/`)
- `lib/stores/socket.ts` - Socket.IO connection management
- `lib/stores/game.ts` - Game state stores (Svelte stores)
- `lib/components/` - UI components (Lobby, Game, Chat, PlayerList, PhaseTimer)
- `routes/+page.svelte` - Main page, switches between Lobby and Game views

### Socket Events
- `create_room` - Creates new game room, returns room_id
- `join_room` - Join with room_id and player_name
- `send_message` - Send chat message to room
- `leave_room` - Leave current room
- `start_game` - Host starts the game (triggers phase transitions)
- `skip_to_voting` - Host skips DAY phase to go to VOTING
- `phase_changed` - Server broadcasts phase transitions to all players

## Game Modes (Planned)

- Find the AIs
- Werewolves + find the AIs (Town of Salem style)

## Version Control

**Commit workflow**: Claude autonomously creates commits
- Create a commit after completing a logical unit of work (feature, bugfix, refactor). No user approval required.
- Write clear commit messages explaining what changed and why

**Branching strategy**: Simple (main only)
- Commit directly to main
- Keep commits atomic and working (code should run after each commit)

**Commit points**:
- After implementing a new feature
- After fixing a bug
- After refactoring
- Before starting something risky (so we can rollback)

## MCP

### Svelte

You are able to use the Svelte MCP server, where you have access to comprehensive Svelte 5 and SvelteKit documentation. Here's how to use the available tools effectively:

#### Available MCP Tools:

#### 1. list-sections

Use this FIRST to discover all available documentation sections. Returns a structured list with titles, use_cases, and paths.
When asked about Svelte or SvelteKit topics, ALWAYS use this tool at the start of the chat to find relevant sections.

#### 2. get-documentation

Retrieves full documentation content for specific sections. Accepts single or multiple sections.
After calling the list-sections tool, you MUST analyze the returned documentation sections (especially the use_cases field) and then use the get-documentation tool to fetch ALL documentation sections that are relevant for the user's task.

#### 3. svelte-autofixer

Analyzes Svelte code and returns issues and suggestions.
You MUST use this tool whenever writing Svelte code before sending it to the user. Keep calling it until no issues or suggestions are returned.

#### 4. playground-link

Generates a Svelte Playground link with the provided code.
After completing the code, ask the user if they want a playground link. Only call this tool after user confirmation and NEVER if code was written to files in their project.

### Playwright

Browser automation for verifying frontend changes visually and interactively.

#### When to Use:
- After making UI changes, to verify they render correctly
- To test user interactions (clicking, typing, form submissions)
- To debug frontend issues by inspecting the live page

#### Key Tools:
- `browser_navigate` - Go to a URL (e.g., `http://localhost:5173`)
- `browser_snapshot` - Get accessibility tree of the page (preferred for understanding page structure)
- `browser_take_screenshot` - Capture visual screenshot
- `browser_click` - Click elements (use refs from snapshot)
- `browser_type` - Type into inputs
- `browser_console_messages` - Check for JS errors

#### Best Practices:
- Use `browser_snapshot` over screenshots when you need to interact with elements
- Always check `browser_console_messages` for errors after navigation
- Close the browser with `browser_close` when done testing