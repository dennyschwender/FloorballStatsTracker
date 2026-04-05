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

**Application factory** in `app.py` (`create_app()`). Seven blueprints:
- `game_bp` — game CRUD, stat tracking (`routes/game_routes.py`)
- `lineup_bp` — lineup views, PDF/EPUB export (`routes/lineup_routes.py`)
- `json_bp` — direct JSON game editor (`routes/json_routes.py`)
- `roster_bp` — roster CRUD, bulk import (`routes/roster_routes.py`)
- `stats_bp` — aggregated statistics (`routes/stats_routes.py`)
- `admin_bp` — user/permission management (`routes/admin_routes.py`)
- `api_bp` — minimal internal API (`routes/api_routes.py`)

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
