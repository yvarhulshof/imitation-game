# LLM Implementation

## Overview

The goal of AI players is to win the game by applying a strategy. Each AI player has:

1. **Static Strategy Document** - Role-specific reasoning guidelines loaded at game start
2. **Dynamic Notes** - A scratchpad the AI updates throughout the game to track hypotheses, observations, and plans

The static strategy document includes a protocol for how the AI should update its notes.

## Architecture

### Player Context

All LLM decision functions receive a player context containing:

- Role and team
- Living players list
- Full chat history (truncated if exceeding token limit)
- Current phase and round number
- Vote tallies (during voting phase)
- Voting history (all rounds)

### Static Strategy Document

- **Location**: `backend/app/ai/strategies/{role}.md`
- **Loaded**: Once at game start
- **Contents**:
  - General reasoning guidelines
  - Role-specific tactics (e.g., when to reveal, how to deflect suspicion)
  - Note-taking protocol

### Dynamic Notes

- **Storage**: In-memory dict per player
- **Updated**: After each phase via LLM call
- **Contents**: Current hypotheses, suspicion levels, planned actions

## Game Loop Integration

### Night Phase

**Function**: `choose_night_action_target(context, strategy, notes, valid_targets) -> target_id`

The AI selects a target for its night action (if applicable) based on its role, strategy, and accumulated knowledge.

### Day Phase

**Function**: `decide_chat_action(context, strategy, notes) -> ChatMessage | None`

Called every `CHAT_POLL_INTERVAL` seconds (default: 5). The AI decides whether to send a message and what to say based on:
- Recent chat activity
- Its strategic goals
- Whether it has something meaningful to contribute

Returns `None` if the AI decides not to speak.

### Voting Phase

**Function**: `choose_vote_target(context, strategy, notes, valid_targets) -> target_id`

The AI selects who to vote for based on accumulated suspicions, chat analysis, and strategic considerations.

### Notes Update

**Function**: `update_notes(context, strategy, current_notes) -> new_notes`

Called at the end of each phase. The AI summarizes new information and updates its hypotheses.

## API Configuration

| Setting | Value |
|---------|-------|
| Provider | Google Gemini |
| Model | `gemini-2.0-flash` |
| Timeout | 10 seconds |
| Retries | 2 (exponential backoff) |
| Fallback | Random valid choice |

**Environment variable**: `GOOGLE_API_KEY`

## Error Handling

- **Timeout/API error**: Retry up to 2 times with exponential backoff
- **All retries failed**: Fall back to random choice, log warning
- **Invalid response format**: Parse error → retry once, then fallback
- **Rate limiting**: Implement request queue with delays between AI players

## Prompt Structure

Each prompt follows this structure:

```
[System] You are playing a social deduction game. Your role is {role}.

[Strategy Document]
{static_strategy}

[Your Notes]
{dynamic_notes}

[Game State]
{player_context}

[Task]
{specific_instruction}

[Response Format]
{expected_format}
```

Response format varies by function:
- **Night/Vote actions**: JSON `{"target": "player_id", "reasoning": "..."}`
- **Chat messages**: JSON `{"send": true/false, "message": "...", "reasoning": "..."}`
- **Notes update**: Free-form text (max 2000 tokens)
