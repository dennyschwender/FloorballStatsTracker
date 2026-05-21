# Duplicate Game Lineup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add a "Copy lineup from last game" button to the new-game form that pre-fills player selection and line assignments from the most recent game with the same team and season.

**Architecture:** New `GET /api/last_game_lineup` endpoint filters games by team+season, sorts by date desc, returns `lines` + `goalies` arrays. Frontend button fetches the endpoint and drives the existing convocato checkbox + position-input machinery already present on the form.

**Tech Stack:** Flask `jsonify`, `session`, Python stdlib `sorted`, Vanilla JS `fetch` API. No new dependencies.

---

## File Map

| File | Action |
|------|--------|
| `routes/api_routes.py` | Add `session` to Flask imports; add `GET /api/last_game_lineup` route |
| `templates/game_form.html` | Add "Copy lineup" button HTML (new-game only) + fetch + populate JS |
| `tests/test_duplicate_lineup.py` | Create: endpoint unit tests |

---

## Task 1: Backend endpoint `/api/last_game_lineup`

**Files:**
- Modify: `routes/api_routes.py` (line 4 imports + new route at end of file)
- Test: `tests/test_duplicate_lineup.py`

- [x] **Step 1: Write failing tests**

Create `tests/test_duplicate_lineup.py`:

```python
import pytest
import json


def test_last_game_lineup_missing_params(client):
    """Both season and category are required."""
    rv = client.get('/api/last_game_lineup')
    assert rv.status_code == 400
    data = rv.get_json()
    assert 'error' in data

    rv = client.get('/api/last_game_lineup?season=2025-26')
    assert rv.status_code == 400

    rv = client.get('/api/last_game_lineup?category=U21')
    assert rv.status_code == 400


def test_last_game_lineup_no_games(client, clean_db):
    """Returns found=false when no matching game exists."""
    rv = client.get('/api/last_game_lineup?season=2025-26&category=U21')
    assert rv.status_code == 200
    data = rv.get_json()
    assert data == {'found': False}


def test_last_game_lineup_found(client, clean_db):
    """Returns lines + goalies from most recent matching game."""
    from services.game_service import save_game
    from datetime import date

    # Older game — should NOT be returned
    save_game({
        'date': '2026-01-10',
        'season': '2025-26',
        'team': 'U21',
        'home_team': 'Team A',
        'away_team': 'Team B',
        'lines': [['7 - Rossi Marco', '9 - Bianchi Luca']],
        'goalies': ['1 - Verdi Paolo'],
    })

    # Newer game — SHOULD be returned
    save_game({
        'date': '2026-02-15',
        'season': '2025-26',
        'team': 'U21',
        'home_team': 'Team A',
        'away_team': 'Team C',
        'lines': [['7 - Rossi Marco', '10 - Neri Giorgio'], ['9 - Bianchi Luca']],
        'goalies': ['1 - Verdi Paolo'],
    })

    rv = client.get('/api/last_game_lineup?season=2025-26&category=U21')
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['found'] is True
    assert data['date'] == '2026-02-15'
    assert data['lines'] == [['7 - Rossi Marco', '10 - Neri Giorgio'], ['9 - Bianchi Luca']]
    assert data['goalies'] == ['1 - Verdi Paolo']


def test_last_game_lineup_wrong_season(client, clean_db):
    """Does not return games from a different season."""
    from services.game_service import save_game

    save_game({
        'date': '2026-01-10',
        'season': '2024-25',
        'team': 'U21',
        'home_team': 'A',
        'away_team': 'B',
        'lines': [['7 - Rossi Marco']],
        'goalies': [],
    })

    rv = client.get('/api/last_game_lineup?season=2025-26&category=U21')
    assert rv.status_code == 200
    assert rv.get_json() == {'found': False}


def test_last_game_lineup_wrong_category(client, clean_db):
    """Does not return games from a different category."""
    from services.game_service import save_game

    save_game({
        'date': '2026-01-10',
        'season': '2025-26',
        'team': 'U18',
        'home_team': 'A',
        'away_team': 'B',
        'lines': [['7 - Rossi Marco']],
        'goalies': [],
    })

    rv = client.get('/api/last_game_lineup?season=2025-26&category=U21')
    assert rv.status_code == 200
    assert rv.get_json() == {'found': False}


def test_last_game_lineup_requires_auth(app):
    """Unauthenticated request returns 401."""
    with app.test_client() as unauthed:
        rv = unauthed.get('/api/last_game_lineup?season=2025-26&category=U21')
        assert rv.status_code == 401
```

- [x] **Step 2: Run tests to verify they fail**

```
pytest tests/test_duplicate_lineup.py -v
```

Expected: all fail with `404` or `ImportError` (route does not exist yet).

- [x] **Step 3: Add `session` to Flask import in `api_routes.py`**

Line 4, change:
```python
from flask import Blueprint, request, jsonify
```
to:
```python
from flask import Blueprint, request, jsonify, session
```

- [x] **Step 4: Add the endpoint at the end of `api_routes.py`**

```python
@api_bp.route('/last_game_lineup')
def last_game_lineup():
    """Return lines + goalies from the most recent game for a given season/category.

    Query parameters:
    - season (required)
    - category (required)

    Requires authenticated session.
    """
    if not session.get('authenticated'):
        return jsonify({'error': 'unauthorized'}), 401

    season = request.args.get('season', '').strip()
    category = request.args.get('category', '').strip()

    if not season:
        return jsonify({'error': 'season parameter is required'}), 400
    if not category:
        return jsonify({'error': 'category parameter is required'}), 400

    from services.game_service import load_games

    games = load_games()
    matching = [
        g for g in games
        if g.get('team') == category and g.get('season') == season
    ]

    if not matching:
        return jsonify({'found': False})

    latest = sorted(matching, key=lambda g: g.get('date', ''), reverse=True)[0]

    return jsonify({
        'found': True,
        'date': latest.get('date', ''),
        'lines': latest.get('lines', []),
        'goalies': latest.get('goalies', []),
    })
```

- [x] **Step 5: Run tests to verify they pass**

```
pytest tests/test_duplicate_lineup.py -v
```

Expected: all 6 tests pass.

- [x] **Step 6: Run full test suite to verify no regression**

```
pytest tests/ -v
```

Expected: all existing tests still pass.

- [x] **Step 7: Commit**

```bash
git add routes/api_routes.py tests/test_duplicate_lineup.py
git commit -m "feat(api): add GET /api/last_game_lineup endpoint"
```

---

## Task 2: Frontend "Copy lineup" button and JS

**Files:**
- Modify: `templates/game_form.html` (after `<h4>{{ g.t['lineup'] }}</h4>`, and in `{% block scripts %}`)

- [x] **Step 1: Add button HTML**

In `templates/game_form.html`, find the lineup section heading (line ~587):
```html
<h4>{{ g.t['lineup'] }}</h4>
```

Insert the following block **immediately after** that `<h4>` line, inside `{% if not modify %}...{% endif %}` guard so the button only appears for new game creation:

```html
{% if not modify %}
<div id="copyLineupContainer" class="mb-3" style="display:none;">
    <button type="button" id="copyLineupBtn" class="btn btn-outline-secondary btn-sm">
        &#x21ba; Copy lineup from last game
    </button>
    <span id="copyLineupStatus" class="ms-2 text-muted small"></span>
</div>
{% endif %}
```

- [x] **Step 2: Add JS for button visibility + fetch + populate**

In `{% block scripts %}`, inside the `document.addEventListener('DOMContentLoaded', ...)` block, **after** the existing `populateExistingGameData()` call (near the very end of the DOMContentLoaded handler), add:

```javascript
// ---- Copy lineup from last game ----
(function () {
    var copyContainer = document.getElementById('copyLineupContainer');
    var copyBtn = document.getElementById('copyLineupBtn');
    var copyStatus = document.getElementById('copyLineupStatus');
    if (!copyContainer || !copyBtn) return;

    var seasonEl = document.getElementById('season');
    var teamEl = document.getElementById('team');

    function updateCopyBtnVisibility() {
        var season = seasonEl ? seasonEl.value : '';
        var category = teamEl ? teamEl.value : '';
        copyContainer.style.display = (season && category) ? '' : 'none';
    }

    if (seasonEl) { seasonEl.addEventListener('change', updateCopyBtnVisibility); }
    if (teamEl) { teamEl.addEventListener('change', updateCopyBtnVisibility); }
    updateCopyBtnVisibility();

    copyBtn.addEventListener('click', function () {
        var season = seasonEl ? seasonEl.value : '';
        var category = teamEl ? teamEl.value : '';
        if (!season || !category) return;

        copyBtn.disabled = true;
        copyStatus.textContent = 'Loading\u2026';

        fetch('/api/last_game_lineup?season=' + encodeURIComponent(season) + '&category=' + encodeURIComponent(category))
            .then(function (res) { return res.json(); })
            .then(function (data) {
                copyBtn.disabled = false;
                if (!data.found) {
                    copyStatus.textContent = 'No previous game found';
                    return;
                }
                applyLineupData(data);
                copyStatus.textContent = '\u2713 Lineup copied from ' + data.date;
            })
            .catch(function () {
                copyBtn.disabled = false;
                copyStatus.textContent = 'Failed to load \u2014 retry';
            });
    });

    function applyLineupData(data) {
        if (!currentRoster || currentRoster.length === 0) return;

        // Build name→id map (same format as populateExistingGameData)
        var nameToIdMap = {};
        currentRoster.forEach(function (player) {
            var fullName = player.number + ' - ' + player.surname + ' ' + player.name;
            nameToIdMap[fullName] = player.id;
        });

        isPopulatingData = true;

        // Check convocato checkboxes
        (data.lines || []).forEach(function (line) {
            line.forEach(function (playerName) {
                var pid = nameToIdMap[playerName];
                if (!pid) return;
                var cb = document.getElementById('convocato_' + pid);
                if (cb) { cb.checked = true; }
            });
        });
        (data.goalies || []).forEach(function (goalieName) {
            var pid = nameToIdMap[goalieName];
            if (!pid) return;
            var cb = document.getElementById('convocato_' + pid);
            if (cb) { cb.checked = true; }
        });

        // Rebuild line sections with checked players
        if (typeof rebuildLineAndFormationSectionsWithoutInit === 'function') {
            rebuildLineAndFormationSectionsWithoutInit(currentRoster);
        }

        // Set position values in line inputs
        (data.lines || []).forEach(function (linePlayers, lineIndex) {
            var lineNum = lineIndex + 1;
            linePlayers.forEach(function (playerName, position) {
                var pid = nameToIdMap[playerName];
                if (!pid) return;
                var input = document.querySelector('input[name="l' + lineNum + '_' + pid + '"]');
                if (input) { input.value = String(position + 1); }
            });
        });

        // Set goalie inputs
        (data.goalies || []).forEach(function (goalieName, index) {
            var goalieNum = index + 1;
            var pid = nameToIdMap[goalieName];
            if (!pid) return;
            var hidden = document.getElementById('goalie' + goalieNum);
            if (hidden) { hidden.value = pid; }
            var radio = document.querySelector('input[name="goalie' + goalieNum + '"][value="' + pid + '"]');
            if (radio) { radio.checked = true; }
        });

        isPopulatingData = false;

        if (typeof updateCategoryCounter === 'function') { updateCategoryCounter(); }
    }
}());
// ---- end copy lineup ----
```

- [x] **Step 3: Manually verify in browser**

1. Start dev server: `python app.py`
2. Open new game form at `http://localhost:5000/game/new` (or equivalent)
3. Confirm "Copy lineup" button is **hidden** before season/category are selected
4. Select a season → button still hidden (category not yet selected)
5. Select a category → button appears
6. Click button when no prior game exists → status shows "No previous game found"
7. Create a game with a lineup, then open new-game form again → clicking the button pre-fills convocato checkboxes and line positions from that game

- [x] **Step 4: Commit**

```bash
git add templates/game_form.html
git commit -m "feat(ui): add copy-lineup-from-last-game button to new game form"
```

---

## Self-Review

**Spec coverage:**
- `GET /api/last_game_lineup?season=X&category=Y` — Task 1 ✓
- Filter by `game['team'] == category` and `game.get('season') == season` — Task 1 Step 4 ✓
- Sort by date descending, take first — Task 1 Step 4 ✓
- Return `found`, `date`, `lines`, `goalies` — Task 1 Step 4 ✓
- `{found: false}` when no match — Task 1 Step 4 ✓
- Requires authenticated session — Task 1 Step 4 (401 check) ✓
- Button appears after both season + category selected — Task 2 Step 2 ✓
- Button disabled until both fields have values — Task 2 Step 2 (hidden, not just disabled) ✓
- On success + found: pre-fill lines + goalies — Task 2 Step 2 `applyLineupData` ✓
- On success + not found: show "No previous game found" — Task 2 Step 2 ✓
- On network error: show "Failed to load — retry" — Task 2 Step 2 `.catch` ✓
- Players remain editable after copy — no locking applied ✓
- New game creation only — `{% if not modify %}` guard ✓

**Placeholder scan:** None found.

**Type consistency:** `data.lines` and `data.goalies` used consistently as arrays matching the backend response shape.
