# Game Mechanisms Design Document

## Current State

**Implemented:**
- Room management (create, join, leave, host transfer)
- Real-time chat
- Socket.IO infrastructure
- AI player class (can call Claude API, but not integrated)
- Basic UI (Lobby, Game view, Chat, PlayerList)

**Not Implemented:**
- All game logic (phases, roles, voting, win conditions)
- AI integration into game flow

---

## Scope

This document covers **Classic Werewolf** with AI-controlled players mixed in.

### Future Work (Not In Scope)
> **AI Detection Mode:** A game mode where players guess which other players are AI will be implemented later. Do not consider this feature until explicitly requested.

---

## Mechanisms to Implement

### 1. Game Configuration & Start

**Host controls in lobby:**
- Configure AI player count (0 to N)
- Start game button (minimum 4 players)

**Player composition:**
- Human players join via lobby
- AI players added by host configuration
- AI players indistinguishable from humans in UI (same display)

### 2. Role System

**Roles:**
| Role | Team | Night Action |
|------|------|--------------|
| Villager | Town | None |
| Werewolf | Mafia | Kill one player (group vote) |
| Seer | Town | See one player's role |
| Doctor | Town | Protect one player from death |

**Role distribution (example for 7 players):**
- 2 Werewolves
- 1 Seer
- 1 Doctor
- 3 Villagers

**Data model additions:**
```python
class Role(str, Enum):
    VILLAGER = "villager"
    WEREWOLF = "werewolf"
    SEER = "seer"
    DOCTOR = "doctor"

class Team(str, Enum):
    TOWN = "town"
    MAFIA = "mafia"

# Add to Player model
role: Optional[Role] = None
team: Optional[Team] = None
```

### 3. Phase System

**Phase flow:**
```
LOBBY → DAY → VOTING → (elimination) → NIGHT → (kills) → DAY → ...
                                                              ↓
                                                           ENDED
```

**Phase details:**

| Phase | Duration | What Happens |
|-------|----------|--------------|
| LOBBY | Until host starts | Players join, host configures, chat |
| DAY | 90 seconds | Discussion via chat |
| VOTING | 30 seconds | Vote to eliminate one player |
| NIGHT | 30 seconds | Werewolves pick kill target, Seer/Doctor act |
| ENDED | N/A | Display winners, reveal all roles |

**Transitions:**
- LOBBY → DAY: Host clicks "Start Game", roles assigned
- DAY → VOTING: Timer expires or host triggers
- VOTING → NIGHT: Votes counted, player eliminated (if majority)
- NIGHT → DAY: Actions resolved, deaths announced
- Any → ENDED: Win condition met

### 4. Voting System (Day Elimination)

**Mechanics:**
- Each living player votes for one other living player (or abstains)
- Plurality wins (most votes = eliminated)
- Ties = no elimination
- Dead players cannot vote

**Backend state:**
```python
@dataclass
class VoteState:
    votes: dict[str, str]  # voter_id → target_id
    deadline: float        # timestamp when voting ends
```

**Events:**
- `submit_vote(target_id)` - Player submits vote
- `vote_update` - Broadcast current vote counts
- `player_eliminated(player_id, role)` - Announce elimination

### 5. Night Actions

**Werewolf Kill:**
- All werewolves see each other
- Each werewolf votes on a target
- Majority target dies at dawn (unless protected)

**Seer Peek:**
- Choose one living player
- Learn their role (private message)

**Doctor Protect:**
- Choose one living player (can be self)
- That player survives werewolf attack tonight

**Resolution order:**
1. Doctor protection applied
2. Werewolf kill attempted
3. Seer peek revealed
4. Dawn: announce deaths (if any)

### 6. Win Conditions

**Town wins:** All werewolves are dead
**Mafia wins:** Werewolves ≥ remaining town (wolves can't be outvoted)

Check after:
- Day voting elimination
- Night kill resolution

### 7. AI Player Integration

**Creation:**
- Host selects AI count in lobby
- AI players created with random names
- Added to game with `player_type: AI`

**Behavior by phase:**

| Phase | AI Behavior |
|-------|-------------|
| DAY | Generate chat messages (staggered timing) |
| VOTING | Analyze chat, submit vote |
| NIGHT | If werewolf: vote on target. If Seer/Doctor: pick target |

**AI prompting context:**
- Role and team
- Living players list
- Recent chat history (last 20 messages)
- Current phase
- Vote tallies (during voting)

**AIPlayer class updates:**
```python
class AIPlayer:
    role: Role
    team: Team

    async def generate_message(self, game_state) -> str
    async def generate_vote(self, candidates: list[Player]) -> str
    async def generate_night_action(self, targets: list[Player]) -> str
```

### 8. Socket Events

**New events (Backend → Frontend):**
| Event | Payload | When |
|-------|---------|------|
| `game_started` | `{players, your_role, your_team}` | Game begins |
| `phase_changed` | `{phase, duration, ends_at}` | Phase transition |
| `vote_update` | `{votes: {target_id: count}}` | Vote submitted |
| `player_eliminated` | `{player_id, role}` | Voting concluded |
| `night_result` | `{deaths: [{id, role}]}` | Dawn |
| `seer_result` | `{target_id, role}` | To seer only |
| `game_ended` | `{winner, players_with_roles}` | Game over |

**New events (Frontend → Backend):**
| Event | Payload | When |
|-------|---------|------|
| `start_game` | `{ai_count}` | Host starts |
| `submit_vote` | `{target_id}` | During voting |
| `night_action` | `{target_id}` | During night (power roles) |

### 9. Frontend UI Updates

**Lobby additions:**
- AI player count selector (slider or +/- buttons)
- "Start Game" button (host only, 4+ players)
- Player count display

**Day phase:**
- Phase timer countdown
- "Start Vote" button (host can skip discussion)

**Voting phase:**
- Vote buttons next to each living player name
- Live vote tally display
- "Abstain" option
- Timer countdown

**Night phase:**
- Role-specific action panel:
  - Werewolves: target selection (see other wolves)
  - Seer: player selection for peek
  - Doctor: player selection for protection
  - Villagers: "Waiting for night to end..."
- Timer countdown

**Game end:**
- Winner announcement (Town/Mafia)
- Full player list with revealed roles
- "Return to Lobby" button

---

## Implementation Order

1. **Phase system** - State machine, timers, transitions
2. **Role assignment** - Distribute roles on game start
3. **Day/Voting cycle** - Timer, vote submission, elimination
4. **Night actions** - Werewolf kill, Seer, Doctor
5. **Win conditions** - Check after eliminations/kills
6. **AI integration** - Create AI players, generate responses/votes
7. **Frontend UI** - Phase-specific views and controls
