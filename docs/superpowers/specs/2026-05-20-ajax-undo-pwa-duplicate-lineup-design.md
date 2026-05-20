# Design: AJAX Actions, Undo, PWA Offline, Duplicate Lineup

**Date:** 2026-05-20
**Status:** Approved
**Scope:** FloorballStatsTracker — 4 features targeting live game-tracking UX

---

## Context

The app is used rinkside on a Lenovo Tab P11 Pro (~800px CSS viewport). Every stat action (Goal, Assist, SOG, etc.) currently causes a full page reload via `<a href>` GET links. The 4 features below eliminate that friction and add resilience for unreliable gym WiFi.

---

## Feature 1 — AJAX Actions (no page reload)

### Goal
Replace full-page reloads on stat actions with in-place DOM updates via `fetch`.

### Backend

All 4 action routes accept a JSON response branch triggered by `X-Requested-With: XMLHttpRequest` header:

```
GET /action/<game_id>/<player>?action=goal
GET /action_line/<game_id>/<line_idx>?action=plus
GET /action_goalie/<game_id>/<goalie>?action=save
GET /action_opponent_goalie/<game_id>?action=goal_conceded
```

When header present, return:
```json
{
  "ok": true,
  "player": "Torriani Luca",
  "stat": "goals",
  "value": 3,
  "stats": {
    "goals": {"PlayerName": N, ...},
    "assists": {...},
    "plusminus": {...},
    "shots_on_goal": {...},
    "penalties_taken": {...},
    "penalties_drawn": {...},
    "block_shots": {...},
    "stolen_balls": {...},
    "game_scores": {...}
  },
  "result": {"1": {"home": N, "away": N}, ...}
}
```

Redirect fallback (no header) remains unchanged.

### Frontend (`game_details.html`)

- Action buttons keep `data-action-url` attribute (populated from existing href)
- `href` removed from action `<a>` elements to prevent navigation
- Single JS function `handleAction(url)`:
  1. Adds `X-Requested-With` header to fetch
  2. Dims button during request
  3. On success: updates affected player's `<td>` cells + score summary
  4. On network error: queues action (see Feature 3) or shows retry toast
- Score summary (`result-summary` div) re-renders from `result` in JSON response
- Period buttons remain standard links (page reload acceptable for period change)

### Error handling
- HTTP 4xx/5xx: show toast "Action failed" with retry button
- Network error: hand off to offline queue (Feature 3)

---

## Feature 2 — Undo (one level)

### Goal
Allow undoing the last stat action per game within 5 seconds via a toast.

### Backend

**New file: `services/undo_store.py`**
```python
_undo_stack: dict[int, dict] = {}   # game_id → snapshot

def push(game_id: int, snapshot: dict) -> None: ...
def pop(game_id: int) -> dict | None: ...
```

Snapshot contains `deepcopy` of: `goals`, `assists`, `plusminus`, `shots_on_goal`, `unforced_errors`, `penalties_taken`, `penalties_drawn`, `block_shots`, `stolen_balls`, `saves`, `goals_conceded`, `opponent_goalie_saves`, `opponent_goalie_goals_conceded`, `game_scores`, `goalie_game_scores`, `result`.

All 4 action routes call `push(game_id, snapshot)` before mutating.

**New route:**
```
GET /undo/<game_id>
```
- Requires edit permission (same guard as action routes)
- Pops snapshot, writes fields back to game, saves
- Returns same JSON shape as action routes (full `stats` + `result`)
- Returns `{"ok": false, "error": "nothing_to_undo"}` if stack empty

### Frontend

After every successful AJAX action, show floating undo toast (bottom-right):
```
⟲ Undo [goal]    ✕
```
- Auto-dismisses after 5s (CSS transition)
- Click "Undo": calls `/undo/<game_id>` with AJAX, updates DOM same path as action
- Only one toast alive at a time — new action replaces previous undo opportunity
- Toast not shown after undo itself (no undo-of-undo)
- Toast removed on period change

### CSS
Toast positioned `fixed; bottom: 1rem; right: 1rem; z-index: 1050` — above table, below modals.

---

## Feature 3 — PWA / Offline Mode

### Goal
App works fully offline for the active game. Actions recorded offline are queued and synced on reconnect.

### Service Worker (`static/sw.js`)

**Caches:**
- `app-shell-v1`: Bootstrap CSS/JS CDNs, Bootstrap Icons CDN, favicon — cached on `install`
- `game-page-v1`: Last-visited game page HTML — updated on every successful network fetch

**Fetch strategy:**
- Game pages (`/game/<id>`): network-first, fall back to cache
- Static assets: cache-first
- Action endpoints (`/action/*`, `/undo/*`): never cached — pass through to offline queue handler if network fails

**Registration (`base.html`):**
```html
<script nonce="{{ g.csp_nonce }}">
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js');
  }
</script>
```

Note: SW served from `/sw.js` (Flask static route) to get root scope.

### Offline Action Queue (`static/js/offline-queue.js`)

**Storage:** IndexedDB database `floorball-offline`, store `action-queue`.
Schema: `{id: autoincrement, url: string, headers: object, timestamp: number}`

**On action fetch failure (network error):**
1. Store action in IndexedDB
2. Apply action optimistically to DOM (increment the stat cell locally)
3. Show toast: "Offline — action saved, will sync on reconnect"

**On `window.addEventListener('online')`:**
1. Read all queued actions in order (by `id` ascending)
2. Replay each via `fetch` sequentially (order matters — stats are additive)
3. Remove each from IndexedDB after confirmed `ok: true`
4. After queue empty: fetch fresh game data, update DOM
5. Show toast: "Back online — N actions synced"

**On failed sync item:** stop queue, show "Sync failed at action N — tap to retry". Prevents out-of-order corruption.

### Manifest (`static/site.webmanifest`)

Update:
```json
{
  "theme_color": "#212529",
  "background_color": "#212529",
  "display": "standalone",
  "start_url": "/"
}
```

Add icons: generate `android-chrome-192x192.png` and `android-chrome-512x512.png` from existing favicon using Python Pillow (already a dependency).

### Icon generation

One-off script or part of build: resize `favicon-32x32.png` → 192×192 and 512×512 PNGs placed in `static/`.

### Constraints
- Offline works for one game at a time (last visited)
- No full offline DB — server is source of truth on reconnect
- CSRF tokens in offline queue: stored with action URL at queue time, may expire. On 400 CSRF error during sync: reload page to get fresh token, retry queue.

---

## Feature 4 — Duplicate Lineup

### Goal
Pre-fill player selection on game creation from the most recent game with the same team/season.

### Backend

**New endpoint (`routes/api_routes.py`):**
```
GET /api/last_game_lineup?season=<season>&category=<category>
```

Logic:
1. Load all games
2. Filter by `game['team'] == category` and `game.get('season') == season`
3. Sort by date descending, take first
4. Return `lines` + `goalies` arrays

Response:
```json
{
  "found": true,
  "date": "2026-01-24",
  "lines": [["Player A", "Player B", ...], ...],
  "goalies": ["Goalie Name"]
}
```
or `{"found": false}` if no matching game.

Requires `authenticated` session (view permission sufficient).

### Frontend (`game_form.html`)

- "Copy lineup from last game" button appears after both season + category are selected (event listener on both selects)
- Button disabled until both fields have values
- On click: `fetch('/api/last_game_lineup?season=X&category=Y')`
  - Success + found: pre-fills line player inputs with returned player names; button label → "✓ Lineup copied from [date]"
  - Success + not found: button label → "No previous game found"
  - Network error: button label → "Failed to load — retry"
- Players remain editable after copy

### Scope
Lines array + goalies array only. No scores, stats, formations, or dates copied.

---

## Files Changed / Created

| File | Change |
|------|--------|
| `routes/game_routes.py` | Add JSON branch to 4 action routes + `/undo/<game_id>` route |
| `services/undo_store.py` | New: in-memory undo stack |
| `routes/api_routes.py` | Add `GET /api/last_game_lineup` |
| `templates/game_details.html` | Replace action link `href` with `data-action-url`; add AJAX + undo toast JS |
| `templates/game_form.html` | Add "Copy lineup" button + JS |
| `templates/base.html` | Add SW registration script |
| `static/sw.js` | New: service worker |
| `static/js/offline-queue.js` | New: IndexedDB action queue |
| `static/site.webmanifest` | Update theme_color, add start_url |
| `static/android-chrome-192x192.png` | New: generated from favicon |
| `static/android-chrome-512x512.png` | New: generated from favicon |

---

## Dependencies / Order

Feature 1 (AJAX) must land before Feature 3 (PWA) — offline queue intercepts the same fetch calls.
Feature 2 (Undo) depends on Feature 1 (needs AJAX response to show toast).
Feature 4 (Duplicate) is independent.

Implementation order: **1 → 2 → 4 → 3**
