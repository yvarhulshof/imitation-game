# LLM AI Player Implementation Plan

## Overview

Replace the random/template-based `MockAIPlayer` logic with LLM-powered decision making using Gemini API. The AI will use a static strategy document + dynamic notes architecture.

## Current State

- `MockAIPlayer` in `backend/app/ai/player.py` has 4 decision points using random logic
- `AIController` in `backend/app/ai/controller.py` already handles async phase-based triggering
- Game state provides full context (players, messages, votes, phase info)
- `google-genai` package installed, needs API key configuration

## Files to Create

| File | Purpose |
|------|---------|
| `backend/app/ai/llm_client.py` | Gemini API wrapper with retry/timeout logic |
| `backend/app/ai/prompts.py` | Prompt templates for each decision type |
| `backend/app/ai/notes_store.py` | JSON file persistence for AI notes |
| `backend/app/ai/strategies/base.md` | Universal strategy document |
| `backend/app/ai/strategies/werewolf.md` | Werewolf-specific tactics |
| `backend/app/ai/strategies/villager.md` | Villager-specific tactics |
| `backend/app/ai/strategies/seer.md` | Seer-specific tactics |
| `backend/app/ai/strategies/doctor.md` | Doctor-specific tactics |

## Files to Modify

| File | Changes |
|------|---------|
| `backend/app/ai/player.py` | Replace `MockAIPlayer` methods with LLM calls |
| `backend/app/ai/controller.py` | Add notes management, pass context to AI methods |
| `backend/app/models.py` | Add `notes` field to track AI dynamic notes |
| `backend/.env` | Add `GOOGLE_API_KEY` |

---

## Implementation Steps

### Step 1: LLM Client (`llm_client.py`)

Create a wrapper class for Gemini API calls:

```python
class LLMClient:
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash")
    async def generate(self, prompt: str, response_format: str = "json") -> dict | str
    # - Timeout: 10 seconds
    # - Retries: 2 with exponential backoff
    # - JSON parsing with fallback
```

### Step 2: Prompt Templates (`prompts.py`)

Define prompt builders for each decision type:

```python
def build_night_action_prompt(context, strategy, notes, valid_targets) -> str
def build_chat_decision_prompt(context, strategy, notes) -> str
def build_vote_prompt(context, strategy, notes, valid_targets) -> str
def build_notes_update_prompt(context, strategy, current_notes) -> str
```

Each prompt follows the structure from the spec:
- System instruction (role, game rules)
- Strategy document
- Current notes
- Game state (formatted player context)
- Task-specific instruction
- Response format

### Step 3: Strategy Documents

Create markdown files with:
- General reasoning guidelines
- Role-specific tactics
- Note-taking protocol

Example structure for `werewolf.md`:
```markdown
# Werewolf Strategy

## Objectives
- Eliminate town players without being detected
- Coordinate with fellow werewolves

## Day Phase Tactics
- Blend in with town discussions
- Occasionally accuse others to deflect suspicion
- Defend teammates subtly

## Voting Tactics
- Vote with the majority when possible
- Avoid voting patterns that link you to other wolves

## Night Phase
- Target players who are suspicious of you
- Avoid obvious targets (vocal accusers)
```

### Step 4: Modify `MockAIPlayer` → `LLMPlayer`

Replace random logic with LLM calls:

**a) `choose_night_action_target()`**
```python
async def choose_night_action_target(self, context, valid_targets) -> str:
    prompt = build_night_action_prompt(context, self.strategy, self.notes, valid_targets)
    response = await self.llm_client.generate(prompt, response_format="json")
    # Parse {"target": "player_id", "reasoning": "..."}
    # Fallback to random if parsing fails
    return response["target"]
```

**b) `decide_chat_action()`** (replaces `should_chat` + `generate_chat_message`)
```python
async def decide_chat_action(self, context) -> ChatMessage | None:
    prompt = build_chat_decision_prompt(context, self.strategy, self.notes)
    response = await self.llm_client.generate(prompt, response_format="json")
    # Parse {"send": true/false, "message": "...", "reasoning": "..."}
    if response["send"]:
        return ChatMessage(player_id=self.id, player_name=self.name,
                          content=response["message"], timestamp=time.time())
    return None
```

**c) `choose_vote_target()`**
```python
async def choose_vote_target(self, context, valid_targets) -> str:
    prompt = build_vote_prompt(context, self.strategy, self.notes, valid_targets)
    response = await self.llm_client.generate(prompt, response_format="json")
    # Parse {"target": "player_id", "reasoning": "..."}
    return response["target"]
```

**d) `update_notes()`** (new method)
```python
async def update_notes(self, context) -> None:
    prompt = build_notes_update_prompt(context, self.strategy, self.notes)
    new_notes = await self.llm_client.generate(prompt, response_format="text")
    self.notes = truncate_to_tokens(new_notes, max_tokens=2000)
```

### Step 5: Notes Persistence (`notes_store.py`)

```python
class NotesStore:
    def __init__(self, storage_dir: str = "data/ai_notes")
    def save(self, room_id: str, player_id: str, notes: str) -> None
    def load(self, room_id: str, player_id: str) -> str | None
    def clear_room(self, room_id: str) -> None  # Called on game end
```

- Store notes as JSON: `data/ai_notes/{room_id}.json`
- Structure: `{"player_id": "notes content", ...}`

### Step 6: Update `AIController`

Modify to:
1. Initialize `LLMPlayer` instead of `MockAIPlayer`
2. Load strategy documents based on role
3. Build context dict before each AI decision
4. Call `update_notes()` at end of each phase
5. Stagger LLM calls by 0.5-1s between AI players
6. Load/save notes via `NotesStore`

**Context builder:**
```python
def build_player_context(self, ai_player, game) -> dict:
    return {
        "role": ai_player.role,
        "team": ai_player.team,
        "alive_players": [p for p in game.players.values() if p.is_alive],
        "chat_history": game.messages,  # Full history
        "phase": game.phase,
        "round_number": game.round_number,
        "vote_counts": game.get_vote_counts() if game.phase == GamePhase.VOTING else {},
        "voting_history": self.voting_history.get(game.room_id, {}),
    }
```

### Step 7: Error Handling & Fallbacks

- Wrap all LLM calls in try/except
- On failure: log warning, fall back to random choice
- Track consecutive failures per AI (circuit breaker pattern)

---

## Testing Plan

1. **Unit tests** (`test_llm_client.py`):
   - Mock Gemini API responses
   - Test retry logic
   - Test JSON parsing with malformed responses

2. **Integration tests** (`test_llm_player.py`):
   - Test each decision method with mocked LLM
   - Verify context is correctly formatted
   - Verify fallback behavior

3. **Manual E2E test**:
   - Run game with 1 human + 3 AI players
   - Verify AI chat is coherent
   - Verify AI votes make sense based on chat

---

## Configuration

Add to `.env`:
```
GOOGLE_API_KEY=your-api-key-here
```

Add to `backend/app/config.py` (or create):
```python
LLM_MODEL = "gemini-2.0-flash"
LLM_TIMEOUT = 10
LLM_MAX_RETRIES = 2
CHAT_POLL_INTERVAL = 5
MAX_NOTES_TOKENS = 2000
```

---

## Implementation Order

1. `backend/app/ai/llm_client.py` - API wrapper (can test independently)
2. `backend/app/ai/notes_store.py` - JSON persistence for notes
3. `backend/app/ai/strategies/*.md` - Role-specific strategy documents
4. `backend/app/ai/prompts.py` - Prompt templates
5. `backend/app/ai/player.py` - Replace MockAIPlayer with LLMPlayer
6. `backend/app/ai/controller.py` - Context building, notes management, staggered calls
7. Manual E2E testing with real game

---

## Design Decisions

1. **Chat history**: Pass full history to LLM - won't hit token limits for typical games
2. **Notes persistence**: Persist to JSON file (per game room) for server restart survival
3. **Rate limiting**: Stagger LLM calls by 0.5-1s between AI players to avoid rate limits and create natural timing
