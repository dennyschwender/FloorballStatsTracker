# Game Event Wizard — Design Spec

**Date:** 2026-05-22
**Status:** Approved

## Overview

During live game tracking (edit mode), a floating "＋ Event" button opens a step-by-step modal wizard. The user selects event type, provides required data (players, period, etc.) via tappable chips, and submits. A single `POST /event/<game_id>` endpoint handles all stat mutations atomically with one undo snapshot.

## Supported Event Types

- Goal (our team or opponent)
- Penalty taken
- Penalty drawn
- Save (our goalie or opponent goalie)
- Shot on goal
- Period change

## Frontend

### FAB Trigger

```html
<button id="addEventFab" class="btn btn-primary rounded-pill"
        style="position:fixed;bottom:1.5rem;right:1.5rem;z-index:1050">
  ＋ Event
</button>
```

Visible only when edit mode is active (same condition as existing edit controls). Hidden otherwise.

### Modal Shell

Single Bootstrap 5 modal (`#eventWizardModal`). Modal body content is replaced per step by JS. Back/Next/Save buttons live in the modal footer and are re-rendered each step.

### Step Machine

Pure JS in `game_details.html` nonce-protected script block. No new JS files.

```
stepMachine = {
  steps: [],       // array of step-config objects, built when modal opens
  idx: 0,          // current step index
  selections: {},  // accumulated user choices keyed by step.key
}
```

`buildSteps(eventType)` constructs the step array for the chosen event type.
`renderStep(idx)` clears modal body and renders current step using step config's `type`.

**Step config shape:**
```js
{ title: "Who scored?", type: "player-list"|"line-plusminus"|"chips"|"confirm", key: "scorer", options: [...] }
```

**Step renderers:**

| type | Renders |
|------|---------|
| `chips` | Row of tappable chip buttons (single-select unless `multiselect:true`) |
| `player-list` | Full roster as tappable chips, single-select |
| `line-plusminus` | All lines expanded; line-header chip toggles all players in that line; individual player chips toggle independently |
| `confirm` | Summary of selections + Save button |

### Wizard Steps Per Event Type

**Goal — our team:**
1. `chips` — team: "Our team" / "Opponent" (determines branch)
2. `player-list` — scorer (required, our roster)
3. `player-list` — assist (our roster + "No assist" option)
4. `line-plusminus` — on-ice players for +1 (all lines expanded by default)
5. `confirm` — summary, Save

**Goal — opponent:**
1. `chips` — team: opponent selected
2. `line-plusminus` — on-ice players for −1 (all lines expanded)
3. `player-list` — pick which of our goalies concedes the goal (roster goalies; "No goalie" option available)
4. `confirm` — summary, Save

**Penalty taken:**
1. `chips` — type: "Penalty taken" / "Penalty drawn"
2. `player-list` — pick player
3. `confirm`

**Penalty drawn:**
1. `chips` — type (drawn selected)
2. `player-list` — pick player
3. `confirm`

*(Penalty taken/drawn share the same step flow; type is chosen in step 1)*

**Save:**
1. `chips` — "Our goalie" / "Opponent goalie"
2. `confirm`

**Shot on goal:**
1. `player-list` — pick player
2. `confirm`

**Period change:**
1. `confirm` — shows "Advance from P{n} to P{n+1}?" — confirm or cancel only

### On Submit

```js
fetch('/event/' + GAME_ID, {
  method: 'POST',
  headers: {'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest'},
  body: JSON.stringify(selections)
})
```

On 2xx: close modal, show undo toast, apply partial update to UI (reuse existing `applyPartialUpdate` / score refresh logic).
On non-2xx: show error toast, keep modal open.

## Backend

### New Endpoint

```
POST /event/<int:game_id>
```

Location: `routes/game_routes.py` (new function `record_event`).
Auth: `require_edit()` decorator (same as existing action routes).
Request body: JSON.

**Payload schema per event type:**

| type | required fields | optional |
|------|----------------|---------|
| `goal` | `team` (ours/opponent), `plusminus_players` | `scorer`, `assist`, `period` |
| `penalty` | `subtype` (taken/drawn), `player` | `period` |
| `save` | `team` (ours/opponent) | `period` |
| `shot_on_goal` | `player` | `period` |
| `period_change` | — | — |

### Mutation Logic

One `undo_store.push(game_id, game)` before any mutation.

**Goal — our team:**
- `game['goals'][scorer] += 1`
- `game['assists'][assister] += 1` (if assist provided)
- `game['plusminus'][p] += 1` for each player in `plusminus_players`
- If `opponent_goalie_enabled`: `game['opponent_goalie_goals_conceded']['Opponent Goalie'] += 1`
- `recalculate_game_scores(game)`

**Goal — opponent:**
- `game['plusminus'][p] -= 1` for each player in `plusminus_players`
- If `goalie` provided: `game['goals_conceded'][goalie] += 1` + `game['result'][period]['away'] += 1`
- `recalculate_game_scores(game)`

**Penalty taken:** `game['penalties_taken'][player] += 1`

**Penalty drawn:** `game['penalties_drawn'][player] += 1`

**Save — our goalie:** `game['saves'][player] += 1`

**Save — opponent goalie:** `game['opponent_goalie_saves']['Opponent Goalie'] += 1`

**Shot on goal:** `game['shots_on_goal'][player] += 1`

**Period change:** `game['current_period'] = min(current + 1, max_periods)`

### Response

Same partial-update JSON format as existing AJAX action routes:
```json
{
  "ok": true,
  "scores": {...},
  "stats": {...}
}
```

### Error Responses

| Status | Condition |
|--------|-----------|
| 400 | Missing required field or unknown event type |
| 403 | Not authorized |
| 404 | Game not found |

## Undo

Single `undo_store.push()` before mutations = one undo reverts the entire event (all stat changes). No change to undo endpoint or TTL (60s).

## No New DB Columns

All mutations use existing JSON blob columns (`goals`, `assists`, `plusminus`, `saves`, `shots_on_goal`, `penalties_taken`, `penalties_drawn`, `goals_conceded`, `opponent_goalie_saves`, `opponent_goalie_goals_conceded`).

## Out of Scope

- Editing past events
- Event log / timeline view
- Offline queue integration (PWA offline support for wizard events)
- Opponent player tracking (no roster for opponent)
