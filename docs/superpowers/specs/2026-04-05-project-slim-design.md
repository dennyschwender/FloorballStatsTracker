# Project Slim & Improvement Design

**Date:** 2026-04-05
**Scope:** Dead code removal, migration script deletion, route split, JS extraction, copilot instructions sync

---

## 1. Deletions

### Dead code
- `utils/cache.py` — `GameCache` is a no-op stub for the deprecated JSON backend. Delete file and any `__init__` exports.
- `services/file_service.py` — `safe_read_json`/`safe_write_json` are exported but nothing calls them (SQLAlchemy handles all persistence). Delete file and remove from `services/__init__.py`.
- `models/roster.py`: `get_roster_file` function — explicitly marked deprecated, only imported in `roster_routes.py` "for residual calls" that don't exist. Delete function, remove from `models/__init__.py` and the import in `roster_routes.py`.
- `COMMIT_MESSAGE.txt` — stale artifact in repo root. Delete.

### Migration scripts (one-time, already executed)
Delete from `scripts/`:
- `assign_season.py`
- `migrate_games.py`
- `migrate_json_to_sqlite.py`
- `fix_remote_migration.sh`
- `recalculate_game_scores.py`
- `README.md` — rewrite to document only the 3 remaining scripts (`backup_games.py`, `docker_deploy.sh`, `server_diagnostic.sh`)

### Stale documentation
- `docs/BUG_FIX_STATS_PAGE_2025.md` — internal post-mortem, no value to contributors
- `docs/TEST_UPDATES.md` — internal notes, superseded by actual tests

---

## 2. Route Split

`routes/game_routes.py` (1,398 lines) is split into three focused files. All URLs remain identical — no breaking changes to clients or tests.

### `routes/game_routes.py` (~600 lines, keeps `game_bp`)
Retains:
- Login / logout
- Game list (`GET /`)
- Game create / modify / delete
- `player_action`, `line_action`, `goalie_action`, `opponent_goalie_action`
- `set_period`, `reset_game`
- `game_details` view

### `routes/lineup_routes.py` (~500 lines, new `lineup_bp`)
Extracts:
- `GET /game/<id>/lineup` → `view_game_lineup`
- `GET /game/<id>/lineup/eink` → `view_game_lineup_eink`
- `GET /game/<id>/lineup/pdf` → `download_lineup_pdf`
- `GET /game/<id>/lineup/epub` → `download_lineup_epub`

Registered in `app.py` alongside existing blueprints. URL prefix preserved.

### `routes/json_routes.py` (~100 lines, new `json_bp`)
Extracts:
- `GET/POST /game/<id>/edit_json` → `edit_game_json`

Registered in `app.py`. URL preserved.

### `routes/__init__.py`
Updated to export `lineup_bp` and `json_bp` alongside existing blueprints.

---

## 3. Extract jsPDF JS

The `generatePDF()` function and all its helpers (~500 lines) are currently inline in `templates/game_lineup.html` inside a nonce-protected `<script>` block. They move to `static/js/lineup_pdf.js`.

**What moves to `static/js/lineup_pdf.js`:**
- `generatePDF()` and all format-specific rendering functions (format-1, format-2, format-3)
- `drawFormation()` helper
- Category summary generation

**What stays inline in the template:**
- The `<script nonce="{{ g.csp_nonce }}">` block containing `playerData`, `gameData` constants (require Jinja2 variables)
- All `addEventListener` wiring

**Loading in template:**
```html
<script src="{{ url_for('static', filename='js/lineup_pdf.js') }}"></script>
```
No nonce needed — `script-src 'self'` already permits static files. Load order is safe since `generatePDF` is only called on button click, not on page load.

**Result:** `game_lineup.html` shrinks from ~1,786 to ~1,280 lines. `lineup_pdf.js` is pure JS, independently editable.

---

## 4. Sync `.github/copilot-instructions.md`

The file is rewritten to remove all references to the old architecture and match current reality:

**Remove:**
- References to `games.json`, `sheets_service.py`, Google Sheets integration
- "No test suite — manual testing only" (21 test modules exist)
- Incorrect default PINs (`1717`/`1234`)
- Old monolithic `app.py` structure description
- Stale file listing in "Common Commands Reference"

**Add/update:**
- Blueprint architecture (5 blueprints, services layer, SQLAlchemy)
- Test commands: `pytest tests/ -v`, single file: `pytest tests/test_X.py -v`
- CSP nonce constraint: no inline event handlers, use `addEventListener` in nonce-protected blocks
- Dual auth paths: PIN sessions + user accounts with per-team RBAC
- Season-based data organization
- Translations in `config.py`, accessed as `g.t` in templates

The file remains in `.github/` for Copilot. Content mirrors CLAUDE.md accuracy with no contradictions.

---

## Non-goals

- No changes to URL structure
- No changes to database schema or models
- No changes to `scripts/backup_games.py`, `docker_deploy.sh`, `server_diagnostic.sh`
- No refactoring of `stats_service.py`, `game_service.py`, or any template other than `game_lineup.html`
- No new features
