# Project Slim & Improvement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove dead code and migration scripts, split the 1,398-line `game_routes.py` into focused modules, extract jsPDF JS into a static file, and sync the Copilot instructions to match current architecture.

**Architecture:** Four independent tasks in sequence — deletion first (lowest risk, establishes clean baseline), then route split, then JS extraction, then docs update. Each task ends with a passing test run and a commit.

**Tech Stack:** Python/Flask, SQLAlchemy, Jinja2, vanilla JS, jsPDF (CDN), pytest

---

## File Map

**Deleted:**
- `utils/cache.py`
- `services/file_service.py`
- `scripts/assign_season.py`, `migrate_games.py`, `migrate_json_to_sqlite.py`, `fix_remote_migration.sh`, `recalculate_game_scores.py`
- `docs/BUG_FIX_STATS_PAGE_2025.md`, `docs/TEST_UPDATES.md`
- `COMMIT_MESSAGE.txt`

**Modified (Task 1):**
- `services/__init__.py` — remove `file_service` imports
- `models/__init__.py` — remove `get_roster_file`
- `models/roster.py` — delete `get_roster_file` function
- `routes/roster_routes.py` — remove `get_roster_file` import
- `scripts/README.md` — rewritten to document only 3 remaining scripts

**Created (Task 2):**
- `routes/lineup_routes.py` — new `lineup_bp` with all lineup/export routes
- `routes/json_routes.py` — new `json_bp` with `edit_game_json`

**Modified (Task 2):**
- `routes/game_routes.py` — remove lineup, export, and json-edit routes
- `routes/__init__.py` — add `lineup_bp`, `json_bp`
- `app.py` — register `lineup_bp`, `json_bp`
- `templates/game_details.html` — update `url_for` references
- `templates/game_lineup.html` — update `url_for` references
- `templates/game_lineup_eink.html` — update `url_for` references

**Created (Task 3):**
- `static/js/lineup_pdf.js` — extracted `generatePDF()` and helpers

**Modified (Task 3):**
- `templates/game_lineup.html` — add fields to `gameData`, remove `generatePDF`, add `<script src>` tag

**Modified (Task 4):**
- `.github/copilot-instructions.md` — full rewrite

---

## Task 1: Delete Dead Code, Scripts, and Stale Docs

**Files:**
- Delete: `utils/cache.py`
- Delete: `services/file_service.py`
- Delete: `scripts/assign_season.py`, `scripts/migrate_games.py`, `scripts/migrate_json_to_sqlite.py`, `scripts/fix_remote_migration.sh`, `scripts/recalculate_game_scores.py`
- Delete: `docs/BUG_FIX_STATS_PAGE_2025.md`, `docs/TEST_UPDATES.md`
- Delete: `COMMIT_MESSAGE.txt`
- Modify: `services/__init__.py`
- Modify: `models/__init__.py`
- Modify: `models/roster.py`
- Modify: `routes/roster_routes.py`
- Modify: `scripts/README.md`

- [ ] **Step 1: Delete dead code files**

```bash
git rm utils/cache.py
git rm services/file_service.py
git rm COMMIT_MESSAGE.txt
```

- [ ] **Step 2: Remove `file_service` exports from `services/__init__.py`**

Replace the entire file with:

```python
"""
Service layer modules for FloorballStatsTracker
"""
from .game_service import load_games, save_games, find_game_by_id, ensure_game_ids
from .stats_service import (
    calculate_game_score,
    calculate_goalie_game_score,
    calculate_stats_optimized
)

__all__ = [
    'load_games',
    'save_games',
    'find_game_by_id',
    'ensure_game_ids',
    'calculate_game_score',
    'calculate_goalie_game_score',
    'calculate_stats_optimized',
]
```

- [ ] **Step 3: Delete `get_roster_file` from `models/roster.py`**

Find and remove these lines (around line 138):

```python
def get_roster_file(category, season=None):
    """DEPRECATED — do not use."""
    logger.warning("get_roster_file() is deprecated; use delete_roster_category()")
```

(Delete the entire function body including any subsequent `return` or `pass` line.)

- [ ] **Step 4: Remove `get_roster_file` from `models/__init__.py`**

Remove `get_roster_file,   # deprecated stub, kept for imports that haven't changed` from the import list and remove `'get_roster_file',` from `__all__`.

Result should look like:

```python
from .roster import (
    load_roster,
    save_roster,
    delete_roster_category,
    get_all_seasons,
    get_all_categories_with_rosters,
    get_all_rosters_with_seasons,
    get_all_tesser_values,
)
```

And in `__all__`, remove `'get_roster_file',`.

- [ ] **Step 5: Remove `get_roster_file` import from `routes/roster_routes.py`**

Change:

```python
from models.roster import (
    load_roster,
    save_roster,
    get_all_categories_with_rosters,
    get_all_seasons,
    get_all_rosters_with_seasons,
    get_all_tesser_values,
    get_roster_file,          # deprecated stub - kept for any residual calls
    delete_roster_category,
)
```

To:

```python
from models.roster import (
    load_roster,
    save_roster,
    get_all_categories_with_rosters,
    get_all_seasons,
    get_all_rosters_with_seasons,
    get_all_tesser_values,
    delete_roster_category,
)
```

- [ ] **Step 6: Delete migration scripts**

```bash
git rm scripts/assign_season.py
git rm scripts/migrate_games.py
git rm scripts/migrate_json_to_sqlite.py
git rm scripts/fix_remote_migration.sh
git rm scripts/recalculate_game_scores.py
```

- [ ] **Step 7: Rewrite `scripts/README.md`**

Replace the entire file with:

```markdown
# Scripts

Utility scripts for managing the Floorball Stats Tracker.

## backup_games.py

Creates a timestamped backup of the SQLite database.

```bash
python scripts/backup_games.py
```

Creates `gamesFiles/games_backup_YYYYMMDD_HHMMSS.db` (or `.json` for legacy installs).
Run before major updates, data migrations, or at the start of each season.

## docker_deploy.sh

Pulls the latest code and rebuilds the Docker container on the server.

```bash
bash scripts/docker_deploy.sh
```

## server_diagnostic.sh

Runs health checks on the server: process status, port binding, log tail, disk usage.

```bash
bash scripts/server_diagnostic.sh
```
```

- [ ] **Step 8: Delete stale docs**

```bash
git rm docs/BUG_FIX_STATS_PAGE_2025.md
git rm docs/TEST_UPDATES.md
```

- [ ] **Step 9: Run tests to confirm nothing broke**

```bash
pytest tests/ -v
```

Expected: all tests pass. If any test imports `safe_read_json`, `safe_write_json`, or `get_roster_file`, update that import in the test file.

- [ ] **Step 10: Commit**

```bash
git add -u
git commit -m "chore: remove dead code, migration scripts, and stale docs"
```

---

## Task 2: Split `game_routes.py` into Three Focused Modules

**Files:**
- Create: `routes/lineup_routes.py`
- Create: `routes/json_routes.py`
- Modify: `routes/game_routes.py`
- Modify: `routes/__init__.py`
- Modify: `app.py`
- Modify: `templates/game_details.html`
- Modify: `templates/game_lineup.html`
- Modify: `templates/game_lineup_eink.html`

### Step 1: Create `routes/lineup_routes.py`

- [ ] **Step 1: Create `routes/lineup_routes.py`**

Create the file with the content cut from `game_routes.py` (lines 846–1398):

```python
"""
Lineup viewing and export routes blueprint
"""
import io
from flask import Blueprint, request, render_template, send_file
from services.game_service import load_games, find_game_by_id
from models.roster import load_roster

lineup_bp = Blueprint('lineup', __name__)


def _lineup_context(game_id):
    """Shared helper: load game + roster for lineup views."""
    games = load_games()
    game = find_game_by_id(games, game_id)
    if not game:
        return None, None, None
    roster = []
    if game.get('team'):
        season = game.get('season', '')
        roster = load_roster(game['team'], season) if season else load_roster(game['team'])
    player_map = {}
    for player in roster:
        key = f"{player['number']} - {player['surname']} {player['name']}"
        player_map[key] = player
    return game, roster, player_map


# ── Device profiles for e-reader PDF export ────────────────────────────────
_EINK_DEVICES = {
    'tolino': dict(
        label='Tolino Shine',
        page_w=90, page_h=122, margin=7,
        title_fs=20, vs_fs=13, section_fs=16,
        meta_fs=12, player_fs=14,
        toc_title_fs=13, toc_item_fs=12,
        num_w=14, meta_label_w=18,
        cell_pad=5, hr_thick=1.5,
        spec_spacer=5,
        epub_vw=600, epub_vh=800,
        epub_title_fs=28, epub_vs_fs=16, epub_section_fs=20,
        epub_meta_fs=14, epub_player_fs=15, epub_toc_fs=13,
        epub_pad=8, epub_row_pad=3,
        epub_lines_per_page=1,
    ),
    'xteink': dict(
        label='Xteink X4',
        page_w=65, page_h=87, margin=5,
        title_fs=14, vs_fs=9, section_fs=11,
        meta_fs=9, player_fs=10,
        toc_title_fs=9, toc_item_fs=9,
        num_w=10, meta_label_w=13,
        cell_pad=3, hr_thick=1.0,
        spec_spacer=3,
        epub_vw=400, epub_vh=533,
        epub_title_fs=17, epub_vs_fs=10, epub_section_fs=13,
        epub_meta_fs=10, epub_player_fs=11, epub_toc_fs=10,
        epub_pad=5, epub_row_pad=1,
        epub_lines_per_page=2,
        epub_page_groups=[
            ['line:0', 'line:1', 'line:2'],
            ['line:3', 'goalies'],
            ['pp1', 'pp2', '6vs5'],
            ['bp1', 'bp2', 'stress_line'],
        ],
    ),
}


@lineup_bp.route('/game/<int:game_id>/lineup')
def view_game_lineup(game_id):
    game, roster, player_map = _lineup_context(game_id)
    if game is None:
        return "Game not found", 404
    return render_template('game_lineup.html', game=game, roster=roster, player_map=player_map)


@lineup_bp.route('/game/<int:game_id>/lineup/eink')
def view_game_lineup_eink(game_id):
    """E-ink friendly paginated lineup view."""
    game, roster, player_map = _lineup_context(game_id)
    if game is None:
        return "Game not found", 404
    return render_template('game_lineup_eink.html', game=game, roster=roster, player_map=player_map)
```

Then copy the `download_lineup_pdf` function (lines 929–1106) and `download_lineup_epub` function (lines 1109–1398) from `game_routes.py` into this file, changing `@game_bp.route` to `@lineup_bp.route` on each.

- [ ] **Step 2: Create `routes/json_routes.py`**

```python
"""
Direct JSON editing route blueprint
"""
import json
from flask import Blueprint, request, render_template, redirect, url_for, abort
from services.game_service import load_games, save_games, find_game_by_id
from utils.auth_helpers import require_manage

json_bp = Blueprint('json', __name__)


@json_bp.route('/game/<int:game_id>/edit_json', methods=['GET', 'POST'])
def edit_game_json(game_id):
    guard = require_manage()
    if guard:
        return guard
    games = load_games()
    game = find_game_by_id(games, game_id)
    if not game:
        abort(404)

    if request.method == 'POST':
        try:
            json_data = request.form.get('json_data', '{}')
            updated_game = json.loads(json_data)
            updated_game['id'] = game_id
            for i, game_item in enumerate(games):
                if game_item.get('id') == game_id:
                    games[i] = updated_game
                    break
            save_games(games)
            return redirect(url_for('game.game_details', game_id=game_id))
        except json.JSONDecodeError as e:
            error_message = f"Invalid JSON: {str(e)}"
            return render_template(
                'edit_game_json.html',
                game=game,
                game_id=game_id,
                json_data=request.form.get('json_data', ''),
                error=error_message
            )

    json_data = json.dumps(game, indent=2, ensure_ascii=False)
    return render_template(
        'edit_game_json.html',
        game=game,
        game_id=game_id,
        json_data=json_data
    )
```

- [ ] **Step 3: Remove the extracted routes from `routes/game_routes.py`**

Delete lines 799–1398 (everything from `@game_bp.route('/game/<int:game_id>/edit_json'` to the end of the file). Also remove the `import io` and `import json` lines at the top if they are no longer used in the remaining file (check — `json` is used in `edit_game_json` which is now gone; `io` was only used by the export functions which are now gone).

Verify the final import block at the top of `game_routes.py` is:

```python
"""
Game management routes blueprint
"""
import hmac
from datetime import datetime
from flask import Blueprint, request, render_template, redirect, url_for, session, g, abort
from config import REQUIRED_PIN, ADMIN_PIN, PERIODS
from services.game_service import (
    load_games, save_games, find_game_by_id, ensure_game_ids,
    ensure_game_stats, ensure_player_stats, build_formation_from_form,
    delete_game_by_id,
)
from services.stats_service import recalculate_game_scores
from models.roster import load_roster, get_all_seasons
from utils.auth_helpers import require_edit, require_manage
from extensions import limiter

game_bp = Blueprint('game', __name__)
```

- [ ] **Step 4: Update `routes/__init__.py`**

```python
"""
Route blueprints for FloorballStatsTracker
"""
from .game_routes import game_bp
from .roster_routes import roster_bp
from .stats_routes import stats_bp
from .api_routes import api_bp
from .admin_routes import admin_bp
from .lineup_routes import lineup_bp
from .json_routes import json_bp

__all__ = ['game_bp', 'roster_bp', 'stats_bp', 'api_bp', 'admin_bp', 'lineup_bp', 'json_bp']
```

- [ ] **Step 5: Register new blueprints in `app.py`**

Change:

```python
from routes import game_bp, roster_bp, stats_bp, api_bp, admin_bp
```

To:

```python
from routes import game_bp, roster_bp, stats_bp, api_bp, admin_bp, lineup_bp, json_bp
```

And add registrations after the existing ones:

```python
    app.register_blueprint(game_bp)
    app.register_blueprint(roster_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(lineup_bp)
    app.register_blueprint(json_bp)
```

- [ ] **Step 6: Update `url_for` references in `templates/game_details.html`**

Change all `url_for('game.view_game_lineup', ...)` → `url_for('lineup.view_game_lineup', ...)`
Change all `url_for('game.view_game_lineup_eink', ...)` → `url_for('lineup.view_game_lineup_eink', ...)`
Change all `url_for('game.download_lineup_pdf', ...)` → `url_for('lineup.download_lineup_pdf', ...)`
Change all `url_for('game.download_lineup_epub', ...)` → `url_for('lineup.download_lineup_epub', ...)`
Change `url_for('game.edit_game_json', ...)` → `url_for('json.edit_game_json', ...)`

Affected lines (from earlier grep): 114, 121, 122, 131, 132, 135, 136, 153.

- [ ] **Step 7: Update `url_for` references in `templates/game_lineup.html`**

Change `url_for('game.download_lineup_pdf', ...)` → `url_for('lineup.download_lineup_pdf', ...)`
Change `url_for('game.download_lineup_epub', ...)` → `url_for('lineup.download_lineup_epub', ...)`
Change `url_for('game.view_game_lineup_eink', ...)` → `url_for('lineup.view_game_lineup_eink', ...)`

Affected lines (from earlier grep): 564, 565, 567, 568, 1176.

- [ ] **Step 8: Update `url_for` references in `templates/game_lineup_eink.html`**

Change all `url_for('game.download_lineup_pdf', ...)` → `url_for('lineup.download_lineup_pdf', ...)`
Change all `url_for('game.download_lineup_epub', ...)` → `url_for('lineup.download_lineup_epub', ...)`

Affected lines (from earlier grep): 474, 476, 481, 483.

- [ ] **Step 9: Run tests**

```bash
pytest tests/ -v
```

Expected: all tests pass. Tests use hardcoded URL paths (`/game/1001/edit_json`, `/game/{id}/lineup`) so they are not affected by blueprint renaming.

Also start the dev server briefly and load `/game/1/lineup` in a browser to confirm `url_for` references resolve correctly:

```bash
FLOORBALL_PIN=test123 FLASK_SECRET_KEY=test SESSION_COOKIE_SECURE=False python app.py
```

- [ ] **Step 10: Commit**

```bash
git add routes/lineup_routes.py routes/json_routes.py routes/game_routes.py \
        routes/__init__.py app.py \
        templates/game_details.html templates/game_lineup.html templates/game_lineup_eink.html
git commit -m "refactor: split game_routes.py into lineup_routes and json_routes"
```

---

## Task 3: Extract jsPDF Logic to `static/js/lineup_pdf.js`

**Files:**
- Create: `static/js/lineup_pdf.js`
- Modify: `templates/game_lineup.html`

The `generatePDF()` function in `game_lineup.html` currently reads game metadata directly from Jinja2 template literals (e.g. `'{{ game.home_team }}'`). To move it to a static file, those values must first be added to the `gameData` JS object that is already defined in the inline `<script nonce>` block.

- [ ] **Step 1: Expand `gameData` in `templates/game_lineup.html`**

Find the existing inline `gameData` definition (around line 585) and add the metadata fields:

```js
const gameData = {
    lines: {{ game.lines | default([]) | tojson }},
    goalies: {{ game.goalies | default([]) | tojson }},
    pp1: {{ game.pp1 | default([]) | tojson }},
    pp2: {{ game.pp2 | default([]) | tojson }},
    bp1: {{ game.bp1 | default([]) | tojson }},
    bp2: {{ game.bp2 | default([]) | tojson }},
    sixvsfive: {{ game['6vs5'] | default([]) | tojson }},
    stressLine: {{ game.stress_line | default([]) | tojson }},
    homeTeam: {{ game.home_team | tojson }},
    awayTeam: {{ game.away_team | tojson }},
    date: {{ game.date | default('') | tojson }},
    team: {{ game.team | default('') | tojson }},
    referee1: {{ game.referee1 | default('') | tojson }},
    referee2: {{ game.referee2 | default('') | tojson }}
};
```

- [ ] **Step 2: Create `static/js/lineup_pdf.js`**

Create the file. It reads from `window.gameData` and `window.playerData` (both set in the inline script block before this file is loaded by event trigger):

```js
/**
 * Client-side PDF generation for the lineup page.
 * Depends on: jsPDF (window.jspdf), jsPDF-AutoTable
 * Reads: window.gameData, window.playerData (set in game_lineup.html inline script)
 */

function generatePDF() {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF('p', 'mm', 'a4');

    const currentFormat = document.getElementById('formatSelect').value;

    const homeTeam = gameData.homeTeam;
    const awayTeam = gameData.awayTeam;
    const gameDate = gameData.date;
    const team = gameData.team;
    const referee1 = gameData.referee1;
    const referee2 = gameData.referee2;
    const referees = [referee1, referee2].filter(r => r).join(', ');

    let yPos = 15;
```

Then paste the rest of the `generatePDF()` body from the template (everything from `if (currentFormat === 'format-1') {` through `window.open(doc.output('bloburl'), '_blank');`) and close with `}`.

The full function body is lines 1364–1757 of `game_lineup.html`. The only change needed is replacing the 6 Jinja2 template-literal lines (`const homeTeam = '{{ game.home_team }}';` etc.) with reads from `gameData` as shown above — the rest of the function body is pure JS and can be copied verbatim.

- [ ] **Step 3: Remove `generatePDF` from `templates/game_lineup.html`**

In the bottom `<script nonce="{{ g.csp_nonce }}">` block (around line 1170), delete the entire `generatePDF()` function — from `// Generate PDF` comment through `window.open(doc.output('bloburl'), '_blank');` and its closing `}`.

The `// Wire up controls` section and all `addEventListener` calls stay in the template.

- [ ] **Step 4: Add `<script>` tag for `lineup_pdf.js` in `templates/game_lineup.html`**

Find the jsPDF CDN script tag (search for `jspdf` in the `<head>`) and add the static file load immediately after it:

```html
<script src="{{ url_for('static', filename='js/lineup_pdf.js') }}"></script>
```

No nonce needed — the CSP `script-src 'self'` directive already permits files served from the same origin.

- [ ] **Step 5: Verify**

Start the dev server:

```bash
FLOORBALL_PIN=test123 FLASK_SECRET_KEY=test SESSION_COOKIE_SECURE=False python app.py
```

Navigate to a lineup page, open browser console (no errors), then click "Generate PDF". Verify a PDF opens in a new tab.

- [ ] **Step 6: Commit**

```bash
git add static/js/lineup_pdf.js templates/game_lineup.html
git commit -m "refactor: extract jsPDF generation to static/js/lineup_pdf.js"
```

---

## Task 4: Rewrite `.github/copilot-instructions.md`

**Files:**
- Modify: `.github/copilot-instructions.md`

- [ ] **Step 1: Rewrite the file**

Replace the entire file with:

```markdown
# FloorballStatsTracker — Copilot Instructions

Flask web app for tracking floorball game statistics. PIN-based auth, SQLite via SQLAlchemy, Bootstrap 5 UI, bilingual (EN/IT).

## Running the App

```bash
# Dev server
FLOORBALL_PIN=yourpin FLASK_SECRET_KEY=secret SESSION_COOKIE_SECURE=False python app.py

# Tests
pytest tests/ -v
pytest tests/test_season_functionality.py -v   # single file

# Production
gunicorn -b 0.0.0.0:5000 app:app

# Docker (recommended for production)
docker compose up -d --build
```

Required env vars: `FLOORBALL_PIN` (min 6 chars), `FLASK_SECRET_KEY`.
Optional: `ADMIN_PIN` (elevated access, must differ from `FLOORBALL_PIN`), `SESSION_COOKIE_SECURE=False` for local dev.

## Architecture

**Application factory** in `app.py` (`create_app()`). Five blueprints:
- `game_bp` — game CRUD, stat tracking (`routes/game_routes.py`)
- `lineup_bp` — lineup views, PDF/EPUB export (`routes/lineup_routes.py`)
- `json_bp` — direct JSON editor (`routes/json_routes.py`)
- `roster_bp` — roster CRUD, bulk import (`routes/roster_routes.py`)
- `stats_bp` — aggregated statistics (`routes/stats_routes.py`)
- `admin_bp` — user/permission management (`routes/admin_routes.py`)

Business logic in `services/`: `game_service.py`, `stats_service.py`.

**Database:** SQLAlchemy + SQLite (`gamesFiles/floorball.db`). Player stats stored as JSON text columns in `GameRecord` — intentional for the scale. Key models: `GameRecord`, `RosterPlayer`, `User`, `TeamPermission`, `TeamSettings`.

**Auth:** Two parallel paths — (1) PIN session via `FLOORBALL_PIN` env var, (2) username/password user accounts with per-team RBAC roles (`viewer`/`editor`/`admin`). `utils/auth_helpers.py` provides `require_edit()` and `require_manage()` decorators that check both paths.

**Translations:** All EN/IT strings in `config.py` `TRANSLATIONS` dict. Templates access via `g.t` (set in `before_request`).

## CSP Constraint — Critical

The CSP header uses a per-request nonce (`g.csp_nonce`). **Inline event handlers (`onclick=`, `onchange=` HTML attributes) are blocked.** Always use `addEventListener` calls inside a `<script nonce="{{ g.csp_nonce }}">` block instead.

## Key Patterns

- **Season-based data:** Games and rosters carry a `season` field (e.g. `"2025-26"`). Roster files: `rosters/roster_{SEASON}_{CATEGORY}.json`.
- **Real-time stat tracking:** `game_details.html` updates stats via JavaScript without page reload.
- **jsPDF export:** `static/js/lineup_pdf.js` handles client-side PDF generation, reading from `window.gameData` set in the inline script block of `game_lineup.html`.
- **Bootstrap 5 from CDN:** Requires internet. `cdn.jsdelivr.net` and `cdnjs.cloudflare.com` are in the CSP allowlist.
```

- [ ] **Step 2: Commit**

```bash
git add .github/copilot-instructions.md
git commit -m "docs: rewrite copilot instructions to match current architecture"
```

---

## Final Verification

- [ ] **Run full test suite**

```bash
pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Push to main**

```bash
git push origin main
```
