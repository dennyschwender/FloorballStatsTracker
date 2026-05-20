# AJAX Actions, Undo, and PWA Offline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace full-page reloads on stat actions with in-place AJAX updates, add single-level undo toast, and enable full offline operation with IndexedDB action queueing.

**Architecture:** Action routes return JSON when `X-Requested-With: XMLHttpRequest` header present. Frontend intercepts action clicks via `fetch()`, updates only affected DOM cells. Undo uses a module-level in-memory dict keyed by game_id. Service worker caches app shell + last game page; IndexedDB queues failed actions and replays on `window.online`.

**Tech Stack:** Flask `jsonify`, Python `copy.deepcopy`, `threading.Lock`, Vanilla JS `fetch` API, IndexedDB, Service Worker Cache API, Pillow (already installed) for icon generation.

**Implementation order:** Tasks 1-6 (AJAX) then Tasks 7-9 (Undo) then Tasks 10-13 (PWA). Each group is independently shippable.

---

## File Map

| File | Action |
|------|--------|
| `routes/game_routes.py` | Add `jsonify` import, `_game_stats_response()` helper, JSON branch to 4 action routes, `/undo/<game_id>` route |
| `services/undo_store.py` | Create: thread-safe in-memory undo stack |
| `templates/game_details.html` | Add `data-player`/`data-stat` attrs to stat cells, `ajax-action` class to buttons, AJAX + undo toast JS |
| `templates/base.html` | Add SW registration script and offline-queue.js include |
| `static/sw.js` | Create: service worker with cache strategies |
| `static/js/offline-queue.js` | Create: IndexedDB action queue + sync on reconnect |
| `static/site.webmanifest` | Update theme_color, add start_url |
| `static/android-chrome-192x192.png` | Generate from existing favicon |
| `static/android-chrome-512x512.png` | Generate from existing favicon |
| `scripts/generate_icons.py` | One-off icon generation script |
| `tests/test_ajax_actions.py` | Create: JSON response tests |
| `tests/test_undo.py` | Create: undo endpoint tests |

---

## Task 1: Add JSON response helper to game_routes.py

**Files:**
- Modify: `routes/game_routes.py` (line 6 imports, after imports block)

- [ ] **Step 1: Add `jsonify` to Flask import**

Change line 6 from:
```python
from flask import Blueprint, request, render_template, redirect, url_for, session, g, abort
```
to:
```python
from flask import Blueprint, request, render_template, redirect, url_for, session, g, abort, jsonify
```

- [ ] **Step 2: Add helper constant and function after the imports block**

After the last `from ...` import line (around line 14), add:
```python
_STAT_FIELDS = [
    'goals', 'assists', 'plusminus', 'shots_on_goal', 'unforced_errors',
    'penalties_taken', 'penalties_drawn', 'block_shots', 'stolen_balls',
    'saves', 'goals_conceded', 'game_scores', 'goalie_game_scores',
    'opponent_goalie_saves', 'opponent_goalie_goals_conceded',
]


def _game_stats_response(game):
    """Return JSON-serialisable dict of all game stats + result."""
    return {
        'ok': True,
        'stats': {field: game.get(field, {}) for field in _STAT_FIELDS},
        'result': game.get('result', {}),
    }
```

- [ ] **Step 3: Verify app still starts**

```bash
python -c "from routes.game_routes import game_bp; print('ok')"
```
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add routes/game_routes.py
git commit -m "feat(api): add JSON response helper to game_routes"
```

---

## Task 2: Add JSON branch to player_action (line ~435)

**Files:**
- Modify: `routes/game_routes.py`

- [ ] **Step 1: Add `is_ajax` flag at top of `player_action`**

In `player_action` (line ~435), immediately after `action = request.args.get('action')`, add:
```python
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
```

- [ ] **Step 2: Replace the final redirect block with JSON-or-redirect**

The current end of `player_action` looks like:
```python
    if request.args.get('edit') == '1':
        return redirect(url_for('game.game_details', game_id=game_id, edit=1))
    return redirect(url_for('game.game_details', game_id=game_id))
```

Replace it with:
```python
    if is_ajax:
        return jsonify(_game_stats_response(game))
    if request.args.get('edit') == '1':
        return redirect(url_for('game.game_details', game_id=game_id, edit=1))
    return redirect(url_for('game.game_details', game_id=game_id))
```

- [ ] **Step 3: Verify existing tests still pass**

```bash
pytest tests/test_actions.py -v -k "player"
```
Expected: all player action tests PASS (non-AJAX path unchanged).

- [ ] **Step 4: Commit**

```bash
git add routes/game_routes.py
git commit -m "feat(api): add JSON response branch to player_action"
```

---

## Task 3: Add JSON branch to line_action, goalie_action, opponent_goalie_action

**Files:**
- Modify: `routes/game_routes.py`

Apply the same two-change pattern from Task 2 to the remaining three routes:

- [ ] **Step 1: Apply to `line_action` (line ~531)**

After `action = request.args.get('action')`, add:
```python
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
```
Replace the final redirect block with:
```python
    if is_ajax:
        return jsonify(_game_stats_response(game))
    if request.args.get('edit') == '1':
        return redirect(url_for('game.game_details', game_id=game_id, edit=1))
    return redirect(url_for('game.game_details', game_id=game_id))
```

- [ ] **Step 2: Apply same pattern to `goalie_action` (line ~592)**

Identical changes.

- [ ] **Step 3: Apply same pattern to `opponent_goalie_action` (line ~652)**

Identical changes.

- [ ] **Step 4: Run all action tests**

```bash
pytest tests/test_actions.py -v
```
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add routes/game_routes.py
git commit -m "feat(api): add JSON response branch to line, goalie, opponent_goalie actions"
```

---

## Task 4: Write tests for JSON action responses

**Files:**
- Create: `tests/test_ajax_actions.py`

- [ ] **Step 1: Check how test_actions.py defines its helpers**

Read the top of `tests/test_actions.py` to find `_write_games`, `_read_games`, `make_sample_game` — they are module-level helper functions in that file.

- [ ] **Step 2: Write test file**

```python
"""Tests for AJAX (JSON) responses from action routes."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from test_actions import _write_games, _read_games, make_sample_game  # noqa: E402

AJAX = {'X-Requested-With': 'XMLHttpRequest'}


def test_player_action_returns_json_on_ajax(client):
    _write_games([make_sample_game()])

    rv = client.get('/action/0/P1?action=goal', headers=AJAX)

    assert rv.status_code == 200
    assert rv.is_json
    data = rv.get_json()
    assert data['ok'] is True
    assert 'stats' in data
    assert 'result' in data
    assert data['stats']['goals'].get('P1', 0) == 1


def test_player_action_no_ajax_still_redirects(client):
    _write_games([make_sample_game()])

    rv = client.get('/action/0/P1?action=goal')

    assert rv.status_code == 302


def test_ajax_response_contains_required_stat_fields(client):
    _write_games([make_sample_game()])

    rv = client.get('/action/0/P1?action=assist', headers=AJAX)
    data = rv.get_json()

    for field in ('goals', 'assists', 'plusminus', 'shots_on_goal', 'game_scores'):
        assert field in data['stats'], f"Missing stat field: {field}"
    assert 'result' in data


def test_goalie_action_returns_json_on_ajax(client):
    _write_games([make_sample_game()])

    rv = client.get('/action_goalie/0/G1?action=save', headers=AJAX)

    assert rv.status_code == 200
    data = rv.get_json()
    assert data['ok'] is True
    assert data['stats']['saves'].get('G1', 0) == 1


def test_line_action_returns_json_on_ajax(client):
    _write_games([make_sample_game()])

    rv = client.get('/action_line/0/0?action=plus', headers=AJAX)

    assert rv.status_code == 200
    data = rv.get_json()
    assert data['ok'] is True
```

- [ ] **Step 3: Run tests**

```bash
pytest tests/test_ajax_actions.py -v
```
Expected: all 5 PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_ajax_actions.py
git commit -m "test: add AJAX JSON response tests for action routes"
```

---

## Task 5: Add data attributes to stat cells in game_details.html

**Files:**
- Modify: `templates/game_details.html`

- [ ] **Step 1: Add `id="score-summary"` to score summary div (line ~85)**

```html
<!-- BEFORE: -->
<div class="result-summary bg-light border rounded px-3 py-2 ms-md-3" style="min-width: 320px;">
<!-- AFTER: -->
<div class="result-summary bg-light border rounded px-3 py-2 ms-md-3" id="score-summary" style="min-width: 320px;">
```

- [ ] **Step 2: Add `data-player` and `data-stat` to the 5 primary stat cells in the player row loop**

Find these cells (currently around lines 247-264) and add the two data attributes:

```html
<!-- plusminus: -->
<td class="text-center" data-player="{{ player }}" data-stat="plusminus"><span class="fw-bold">...

<!-- goals: -->
<td class="text-center" data-player="{{ player }}" data-stat="goals"><span class="fw-bold">...

<!-- assists: -->
<td class="text-center" data-player="{{ player }}" data-stat="assists"><span class="fw-bold">...

<!-- unforced_errors: -->
<td class="text-center" data-player="{{ player }}" data-stat="unforced_errors"><span class="fw-bold">...

<!-- shots_on_goal: -->
<td class="text-center" data-player="{{ player }}" data-stat="shots_on_goal"><span class="fw-bold">...
```

- [ ] **Step 3: Add data attributes to the 4 `stat-secondary` cells**

```html
<td class="text-center stat-secondary" data-player="{{ player }}" data-stat="penalties_taken">...
<td class="text-center stat-secondary" data-player="{{ player }}" data-stat="penalties_drawn">...
<td class="text-center stat-secondary" data-player="{{ player }}" data-stat="block_shots">...
<td class="text-center stat-secondary" data-player="{{ player }}" data-stat="stolen_balls">...
```

- [ ] **Step 4: Verify template regression tests pass**

```bash
pytest tests/test_template_regression.py -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add templates/game_details.html
git commit -m "feat(ui): add data-player/data-stat attributes to game_details stat cells"
```

---

## Task 6: Add AJAX handler JS to game_details.html

**Files:**
- Modify: `templates/game_details.html`

- [ ] **Step 1: Add `ajax-action` class to all action link buttons**

In the player action button group (lines ~275-340), add class `ajax-action` to every `<a>` that calls an action route. Example pattern — apply to ALL action `<a>` elements in player, goalie, and opponent-goalie sections:

```html
<!-- BEFORE: -->
<a href="/action/{{ game_id }}/{{ player }}?action=goal..."
    class="btn btn-primary quick-action-btn" title="...">⚽</a>
<!-- AFTER: -->
<a href="/action/{{ game_id }}/{{ player }}?action=goal..."
    class="btn btn-primary quick-action-btn ajax-action" title="...">⚽</a>
```

Apply `ajax-action` to every `<a>` in `.action-buttons`, `.goalie-action-buttons`, and `.opponent-goalie-action-dropdown` that links to `/action*` paths. Do NOT add it to period buttons or navigation links.

- [ ] **Step 2: Add AJAX + undo toast JS block in `{% block scripts %}`**

Insert a new `<script>` block in `{% block scripts %}` BEFORE the existing script. Build all DOM elements programmatically (no `innerHTML`) to avoid XSS:

```html
<script nonce="{{ g.csp_nonce }}">
(function () {
    'use strict';

    var GAME_ID = {{ game_id }};

    // ── Stat cell update ─────────────────────────────────────────────────────
    function updateStatCells(stats) {
        Object.keys(stats).forEach(function (field) {
            var fieldData = stats[field];
            if (!fieldData || typeof fieldData !== 'object') return;
            Object.keys(fieldData).forEach(function (player) {
                var selector = 'td[data-stat="' + CSS.escape(field) + '"][data-player="' + CSS.escape(player) + '"] span';
                var cell = document.querySelector(selector);
                if (cell) cell.textContent = String(fieldData[player]);
            });
        });
    }

    // ── Score summary update ─────────────────────────────────────────────────
    function updateScore(result) {
        var summary = document.getElementById('score-summary');
        if (!summary || !result) return;
        var periods = ['1', '2', '3', 'OT'];
        var homeTotal = 0, awayTotal = 0, parts = [];
        periods.forEach(function (p) {
            var pd = result[p] || {home: 0, away: 0};
            homeTotal += (pd.home || 0);
            awayTotal += (pd.away || 0);
            parts.push((p === 'OT' ? 'OT' : 'P' + p) + ':' + (pd.home || 0) + '-' + (pd.away || 0));
        });
        var homeSpan = summary.querySelector('.text-primary');
        var awaySpan = summary.querySelector('.text-danger');
        var periodDiv = summary.querySelector('.text-muted');
        if (homeSpan) homeSpan.textContent = String(homeTotal);
        if (awaySpan) awaySpan.textContent = String(awayTotal);
        if (periodDiv) periodDiv.textContent = '(' + parts.join(' | ') + ')';
    }

    // Expose for offline-queue.js use
    window.updateStatCells = updateStatCells;
    window.updateScore = updateScore;

    // ── Toast utility ─────────────────────────────────────────────────────────
    var _toastEl = null;
    window.showToast = function (msg, type, duration) {
        if (_toastEl) { _toastEl.remove(); _toastEl = null; }
        var el = document.createElement('div');
        el.className = 'alert alert-' + (type || 'info') + ' py-2 px-3 mb-0';
        el.style.cssText = 'position:fixed;bottom:1rem;right:1rem;z-index:1055;min-width:220px;';
        el.textContent = msg;
        document.body.appendChild(el);
        _toastEl = el;
        if (duration) {
            setTimeout(function () { if (_toastEl === el) { el.remove(); _toastEl = null; } }, duration);
        }
    };

    // ── Undo toast ────────────────────────────────────────────────────────────
    var _undoTimer = null;
    function showUndoToast(actionName) {
        if (_toastEl) { _toastEl.remove(); _toastEl = null; }
        if (_undoTimer) { clearTimeout(_undoTimer); _undoTimer = null; }

        var wrapper = document.createElement('div');
        wrapper.className = 'alert alert-secondary py-2 px-3 mb-0 d-flex align-items-center gap-3';
        wrapper.style.cssText = 'position:fixed;bottom:1rem;right:1rem;z-index:1055;min-width:240px;';

        var label = document.createElement('span');
        label.textContent = '\u238C Undo ' + actionName;
        wrapper.appendChild(label);

        var undoBtn = document.createElement('button');
        undoBtn.type = 'button';
        undoBtn.className = 'btn btn-sm btn-outline-light ms-auto';
        undoBtn.textContent = 'Undo';
        wrapper.appendChild(undoBtn);

        var closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.className = 'btn-close btn-close-white ms-1';
        closeBtn.setAttribute('aria-label', 'Close');
        wrapper.appendChild(closeBtn);

        document.body.appendChild(wrapper);
        _toastEl = wrapper;

        undoBtn.addEventListener('click', function () {
            wrapper.remove(); _toastEl = null;
            if (_undoTimer) { clearTimeout(_undoTimer); _undoTimer = null; }
            fetch('/undo/' + GAME_ID, {
                headers: {'X-Requested-With': 'XMLHttpRequest'},
                credentials: 'same-origin'
            })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.ok) {
                    updateStatCells(data.stats);
                    updateScore(data.result);
                } else {
                    window.showToast('Nothing to undo', 'warning', 3000);
                }
            });
        });

        closeBtn.addEventListener('click', function () {
            wrapper.remove(); _toastEl = null;
            if (_undoTimer) { clearTimeout(_undoTimer); _undoTimer = null; }
        });

        _undoTimer = setTimeout(function () {
            if (_toastEl === wrapper) { wrapper.remove(); _toastEl = null; }
            _undoTimer = null;
        }, 5000);
    }

    // ── Core action fetch ─────────────────────────────────────────────────────
    function handleAction(url, btn) {
        if (btn) { btn.style.opacity = '0.5'; btn.style.pointerEvents = 'none'; }

        return fetch(url, {
            headers: {'X-Requested-With': 'XMLHttpRequest'},
            credentials: 'same-origin'
        })
        .then(function (res) {
            if (!res.ok) throw new Error('HTTP ' + res.status);
            return res.json();
        })
        .then(function (data) {
            if (!data.ok) throw new Error('Server error');
            if (btn) { btn.style.opacity = ''; btn.style.pointerEvents = ''; }
            updateStatCells(data.stats);
            updateScore(data.result);
            return data;
        })
        .catch(function (err) {
            if (btn) { btn.style.opacity = ''; btn.style.pointerEvents = ''; }
            if (window.offlineQueue) {
                window.offlineQueue.enqueue(url);
                window.showToast('Offline \u2014 action queued', 'warning', 4000);
            } else {
                window.showToast('Action failed \u2014 check connection', 'danger', 4000);
            }
            throw err;
        });
    }

    // ── Intercept ajax-action clicks ──────────────────────────────────────────
    document.addEventListener('click', function (e) {
        var btn = e.target.closest('a.ajax-action');
        if (!btn) return;
        e.preventDefault();
        var url = btn.getAttribute('href');
        handleAction(url, btn)
            .then(function (data) {
                var params = new URLSearchParams(new URL(url, location.href).search);
                showUndoToast(params.get('action') || 'action');
            })
            .catch(function () {});
    });
})();
</script>
```

- [ ] **Step 3: Manual browser test**

Navigate to `/game/1?edit=1`, click Goal on a player. Verify:
- No page reload
- Stat cell updates in place
- Undo toast appears for 5s
- Clicking Undo reverts the stat

- [ ] **Step 4: Commit**

```bash
git add templates/game_details.html
git commit -m "feat(ui): add AJAX action handling + undo toast to game_details"
```

---

## Task 7: Create services/undo_store.py

**Files:**
- Create: `services/undo_store.py`

- [ ] **Step 1: Write the module**

```python
"""In-memory single-level undo stack, one slot per game.

Thread-safe via a module-level lock. Lost on server restart —
acceptable: undo is only meaningful during live in-game tracking.
"""
import threading
from copy import deepcopy

_lock = threading.Lock()
_stack: dict[int, dict] = {}

_SNAPSHOT_FIELDS = [
    'goals', 'assists', 'plusminus', 'shots_on_goal', 'unforced_errors',
    'penalties_taken', 'penalties_drawn', 'block_shots', 'stolen_balls',
    'saves', 'goals_conceded', 'game_scores', 'goalie_game_scores',
    'opponent_goalie_saves', 'opponent_goalie_goals_conceded', 'result',
]


def push(game_id: int, game: dict) -> None:
    """Snapshot current stat state before a mutation."""
    snapshot = {field: deepcopy(game.get(field, {})) for field in _SNAPSHOT_FIELDS}
    with _lock:
        _stack[game_id] = snapshot


def pop(game_id: int) -> dict | None:
    """Return and remove the snapshot, or None if nothing stored."""
    with _lock:
        return _stack.pop(game_id, None)


def clear(game_id: int) -> None:
    """Discard any stored snapshot for game_id."""
    with _lock:
        _stack.pop(game_id, None)
```

- [ ] **Step 2: Verify import**

```bash
python -c "from services.undo_store import push, pop, clear; print('ok')"
```
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add services/undo_store.py
git commit -m "feat: add in-memory undo store service"
```

---

## Task 8: Wire undo push into action routes + add /undo/<game_id> route

**Files:**
- Modify: `routes/game_routes.py`

- [ ] **Step 1: Add undo_store import**

After the existing `from services...` imports (around line 13), add:
```python
from services import undo_store
```

- [ ] **Step 2: Add `undo_store.push()` before mutation in all 4 action routes**

In each of the 4 action routes (`player_action`, `line_action`, `goalie_action`, `opponent_goalie_action`), add this line immediately after the `is_ajax = ...` line:
```python
    undo_store.push(game_id, game)
```

This must come BEFORE any mutation of `game` so the snapshot captures the pre-action state.

- [ ] **Step 3: Add /undo/<game_id> route**

After the `opponent_goalie_action` function, add:

```python
@game_bp.route('/undo/<int:game_id>')
def undo_action(game_id):
    """Restore game stats to the state before the last action."""
    games = load_games()
    game = find_game_by_id(games, game_id)
    if not game:
        abort(404)
    require_edit(game)

    snapshot = undo_store.pop(game_id)
    if snapshot is None:
        return jsonify({'ok': False, 'error': 'nothing_to_undo'})

    for field, value in snapshot.items():
        game[field] = value

    save_games(games)
    return jsonify(_game_stats_response(game))
```

Note: `require_edit(game)` follows the same pattern as the other action routes — check how it is called in `player_action` and replicate exactly. If it returns a response on failure (not None), add a guard: `guard = require_edit(game); if guard: return guard`.

- [ ] **Step 4: Run all action + AJAX tests**

```bash
pytest tests/test_actions.py tests/test_ajax_actions.py -v
```
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add routes/game_routes.py
git commit -m "feat: wire undo push into action routes and add /undo/<game_id> route"
```

---

## Task 9: Write undo endpoint tests

**Files:**
- Create: `tests/test_undo.py`

- [ ] **Step 1: Write tests**

```python
"""Tests for /undo/<game_id> endpoint."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from test_actions import _write_games, _read_games, make_sample_game  # noqa: E402
from services import undo_store

AJAX = {'X-Requested-With': 'XMLHttpRequest'}


def test_undo_reverses_last_goal(client):
    _write_games([make_sample_game()])
    undo_store.clear(0)

    client.get('/action/0/P1?action=goal', headers=AJAX)
    assert _read_games()[0]['goals'].get('P1', 0) == 1

    rv = client.get('/undo/0', headers=AJAX)
    assert rv.status_code == 200
    assert rv.get_json()['ok'] is True
    assert _read_games()[0]['goals'].get('P1', 0) == 0


def test_undo_returns_full_stats(client):
    _write_games([make_sample_game()])
    undo_store.clear(0)

    client.get('/action/0/P1?action=assist', headers=AJAX)
    rv = client.get('/undo/0', headers=AJAX)
    data = rv.get_json()

    assert 'stats' in data
    assert 'result' in data
    assert 'goals' in data['stats']


def test_undo_nothing_returns_error(client):
    _write_games([make_sample_game()])
    undo_store.clear(0)

    rv = client.get('/undo/0', headers=AJAX)
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['ok'] is False
    assert data['error'] == 'nothing_to_undo'


def test_undo_only_one_level(client):
    _write_games([make_sample_game()])
    undo_store.clear(0)

    client.get('/action/0/P1?action=goal', headers=AJAX)
    client.get('/action/0/P1?action=goal', headers=AJAX)  # second replaces first snapshot

    # First undo: back to 1 goal
    client.get('/undo/0', headers=AJAX)
    assert _read_games()[0]['goals'].get('P1', 0) == 1

    # Second undo: nothing stored
    rv = client.get('/undo/0', headers=AJAX)
    assert rv.get_json()['error'] == 'nothing_to_undo'
```

- [ ] **Step 2: Run tests**

```bash
pytest tests/test_undo.py -v
```
Expected: all 4 PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_undo.py
git commit -m "test: add undo endpoint tests"
```

---

## Task 10: Generate PWA icons + update manifest

**Files:**
- Create: `scripts/generate_icons.py`
- Create: `static/android-chrome-192x192.png`
- Create: `static/android-chrome-512x512.png`
- Modify: `static/site.webmanifest`

- [ ] **Step 1: Create icon generation script**

```python
#!/usr/bin/env python3
"""Generate PWA icons from existing favicon. Run once from project root."""
from pathlib import Path
from PIL import Image

STATIC = Path(__file__).parent.parent / 'static'
src = STATIC / 'favicon-32x32.png'

for size in (192, 512):
    img = Image.open(src).resize((size, size), Image.LANCZOS)
    dest = STATIC / f'android-chrome-{size}x{size}.png'
    img.save(dest)
    print(f'Generated {dest}')
```

- [ ] **Step 2: Run it**

```bash
python scripts/generate_icons.py
```
Expected:
```
Generated .../static/android-chrome-192x192.png
Generated .../static/android-chrome-512x512.png
```

- [ ] **Step 3: Update site.webmanifest**

Replace the full content of `static/site.webmanifest` with:
```json
{
    "name": "Floorball Stats Tracker",
    "short_name": "Floorball Stats",
    "icons": [
        {
            "src": "/static/android-chrome-192x192.png",
            "sizes": "192x192",
            "type": "image/png"
        },
        {
            "src": "/static/android-chrome-512x512.png",
            "sizes": "512x512",
            "type": "image/png"
        }
    ],
    "theme_color": "#212529",
    "background_color": "#212529",
    "display": "standalone",
    "start_url": "/"
}
```

- [ ] **Step 4: Commit**

```bash
git add static/android-chrome-192x192.png static/android-chrome-512x512.png static/site.webmanifest scripts/generate_icons.py
git commit -m "feat(pwa): generate PWA icons and update manifest"
```

---

## Task 11: Create service worker

**Files:**
- Create: `static/sw.js`
- Modify: `app.py`

The SW must be served from `/sw.js` (not `/static/sw.js`) to get root-level scope.

- [ ] **Step 1: Add Flask route for /sw.js in app.py**

Inside `create_app()`, after the blueprints are registered, add:
```python
from flask import send_from_directory as _sfd

@app.route('/sw.js')
def service_worker():
    return _sfd(app.static_folder, 'sw.js', mimetype='application/javascript')
```

- [ ] **Step 2: Create static/sw.js**

```javascript
'use strict';

var SHELL_CACHE = 'app-shell-v1';
var GAME_CACHE = 'game-page-v1';

var SHELL_ASSETS = [
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
    '/static/site.webmanifest',
    '/static/android-chrome-192x192.png',
    '/static/favicon-32x32.png'
];

self.addEventListener('install', function (e) {
    e.waitUntil(
        caches.open(SHELL_CACHE)
            .then(function (cache) { return cache.addAll(SHELL_ASSETS); })
            .then(function () { return self.skipWaiting(); })
    );
});

self.addEventListener('activate', function (e) {
    e.waitUntil(
        caches.keys().then(function (keys) {
            return Promise.all(
                keys
                    .filter(function (k) { return k !== SHELL_CACHE && k !== GAME_CACHE; })
                    .map(function (k) { return caches.delete(k); })
            );
        }).then(function () { return self.clients.claim(); })
    );
});

self.addEventListener('fetch', function (e) {
    var url = new URL(e.request.url);

    // Action + undo endpoints: pass through, never cache
    if (url.pathname.startsWith('/action') || url.pathname.startsWith('/undo')) {
        return;
    }

    // Static assets: cache-first
    if (url.pathname.startsWith('/static/') ||
        SHELL_ASSETS.indexOf(e.request.url) !== -1) {
        e.respondWith(
            caches.match(e.request).then(function (hit) {
                return hit || fetch(e.request);
            })
        );
        return;
    }

    // Game detail pages: network-first, cache on success for offline fallback
    if (url.pathname.match(/^\/game\/\d+/)) {
        e.respondWith(
            fetch(e.request)
                .then(function (res) {
                    var clone = res.clone();
                    caches.open(GAME_CACHE).then(function (c) { c.put(e.request, clone); });
                    return res;
                })
                .catch(function () { return caches.match(e.request); })
        );
        return;
    }

    // Everything else: network-first, no caching
    e.respondWith(
        fetch(e.request).catch(function () { return caches.match(e.request); })
    );
});
```

- [ ] **Step 3: Verify /sw.js is reachable**

```bash
python -c "
from app import app
with app.test_client() as c:
    rv = c.get('/sw.js')
    print(rv.status_code, rv.content_type)
"
```
Expected: `200 application/javascript`

- [ ] **Step 4: Commit**

```bash
git add static/sw.js app.py
git commit -m "feat(pwa): add service worker with app-shell and game-page cache strategies"
```

---

## Task 12: Create offline action queue

**Files:**
- Create: `static/js/offline-queue.js`

- [ ] **Step 1: Create the module**

```javascript
'use strict';

(function () {
    var DB_NAME = 'floorball-offline';
    var STORE_NAME = 'action-queue';
    var _db = null;

    function openDB() {
        if (_db) return Promise.resolve(_db);
        return new Promise(function (resolve, reject) {
            var req = indexedDB.open(DB_NAME, 1);
            req.onupgradeneeded = function (e) {
                e.target.result.createObjectStore(STORE_NAME, {keyPath: 'id', autoIncrement: true});
            };
            req.onsuccess = function (e) { _db = e.target.result; resolve(_db); };
            req.onerror = function () { reject(req.error); };
        });
    }

    function enqueue(url) {
        return openDB().then(function (db) {
            return new Promise(function (resolve, reject) {
                var tx = db.transaction(STORE_NAME, 'readwrite');
                tx.objectStore(STORE_NAME).add({url: url, timestamp: Date.now()});
                tx.oncomplete = resolve;
                tx.onerror = function () { reject(tx.error); };
            });
        });
    }

    function remove(id) {
        return new Promise(function (resolve, reject) {
            var tx = _db.transaction(STORE_NAME, 'readwrite');
            tx.objectStore(STORE_NAME).delete(id);
            tx.oncomplete = resolve;
            tx.onerror = function () { reject(tx.error); };
        });
    }

    function getAll() {
        return openDB().then(function (db) {
            return new Promise(function (resolve, reject) {
                var items = [];
                var tx = db.transaction(STORE_NAME, 'readonly');
                var req = tx.objectStore(STORE_NAME).openCursor();
                req.onsuccess = function (e) {
                    var cursor = e.target.result;
                    if (cursor) { items.push(cursor.value); cursor.continue(); }
                    else { resolve(items); }
                };
                req.onerror = function () { reject(req.error); };
            });
        });
    }

    function syncQueue() {
        getAll().then(function (items) {
            if (!items.length) return;

            var chain = Promise.resolve();
            var synced = 0;

            items.forEach(function (item) {
                chain = chain.then(function () {
                    return fetch(item.url, {
                        headers: {'X-Requested-With': 'XMLHttpRequest'},
                        credentials: 'same-origin'
                    })
                    .then(function (res) { return res.json(); })
                    .then(function (data) {
                        if (!data.ok) throw new Error('server_error');
                        synced++;
                        return remove(item.id);
                    });
                });
            });

            chain.then(function () {
                if (synced > 0 && window.showToast) {
                    window.showToast(synced + ' offline action' + (synced > 1 ? 's' : '') + ' synced', 'success', 4000);
                }
                // Best-effort reload of displayed stats
                if (window.location.pathname.match(/^\/game\/\d+/)) {
                    fetch(window.location.href, {
                        headers: {'X-Requested-With': 'XMLHttpRequest'},
                        credentials: 'same-origin'
                    })
                    .then(function (r) { return r.json(); })
                    .then(function (data) {
                        if (data.stats && window.updateStatCells) window.updateStatCells(data.stats);
                        if (data.result && window.updateScore) window.updateScore(data.result);
                    })
                    .catch(function () {});
                }
            }).catch(function (err) {
                if (window.showToast) {
                    window.showToast('Sync failed \u2014 will retry on next reconnect', 'danger', 5000);
                }
                console.error('Offline sync error:', err);
            });
        });
    }

    window.offlineQueue = {enqueue: enqueue};

    window.addEventListener('online', syncQueue);
    window.addEventListener('DOMContentLoaded', function () {
        if (navigator.onLine) syncQueue();
    });
})();
```

- [ ] **Step 2: Commit**

```bash
git add static/js/offline-queue.js
git commit -m "feat(pwa): add IndexedDB offline action queue with sync-on-reconnect"
```

---

## Task 13: Register SW + load offline-queue.js in base.html

**Files:**
- Modify: `templates/base.html`

- [ ] **Step 1: Add offline-queue.js and SW registration before closing `</body>`**

In `templates/base.html`, just before `</body>`, add after the existing `{% block scripts %}{% endblock %}`:

```html
<script src="/static/js/offline-queue.js" nonce="{{ g.csp_nonce }}"></script>
<script nonce="{{ g.csp_nonce }}">
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/sw.js').catch(function (err) {
            console.warn('SW registration failed:', err);
        });
    }
</script>
```

- [ ] **Step 2: Run full test suite**

```bash
pytest tests/ -v --ignore=tests/test_web_pages.py --ignore=tests/test_app_info.py
```
Expected: all PASS, no regressions.

- [ ] **Step 3: Manual end-to-end browser test**

1. Open `https://floorballstats.mennylenderr.ch/game/1?edit=1`
2. DevTools → Application → Service Workers: verify SW is registered and active
3. Application → Cache Storage: verify `app-shell-v1` contains Bootstrap assets
4. Record a Goal: no page reload, cell updates, undo toast appears
5. Click Undo: stat reverts
6. DevTools → Network → set Offline
7. Record a Goal: optimistic DOM update, "Offline — action queued" toast
8. Check Application → IndexedDB → `floorball-offline` → `action-queue`: entry visible
9. DevTools → Network → back Online
10. Queued action syncs, "1 offline action synced" toast, stat correct

- [ ] **Step 4: Commit**

```bash
git add templates/base.html
git commit -m "feat(pwa): register service worker and load offline queue in base template"
```
