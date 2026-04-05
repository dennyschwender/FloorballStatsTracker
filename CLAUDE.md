# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run dev server
python app.py

# Run tests (pytest.ini excludes test_web_pages.py and test_app_info.py)
pytest tests/ -v

# Run a single test file
pytest tests/test_season_functionality.py -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Production
gunicorn -b 0.0.0.0:5000 app:app

# Docker (production deployment)
docker compose up -d --build
```

**Required env vars** (set in `.env`):
- `FLOORBALL_PIN` — main access PIN (min 6 chars)
- `FLASK_SECRET_KEY` — session secret
- `SESSION_COOKIE_SECURE=False` for local dev (True in production)
- `ADMIN_PIN` — optional elevated-access PIN (must differ from FLOORBALL_PIN)

## Architecture

### Application Structure

Flask application factory in `app.py` (`create_app()`). Seven blueprints registered at startup:
- `game_bp` — core game CRUD and stat tracking (`routes/game_routes.py`)
- `roster_bp` — roster CRUD and bulk import (`routes/roster_routes.py`)
- `stats_bp` — aggregated statistics display (`routes/stats_routes.py`)
- `admin_bp` — user/permission management, app settings (`routes/admin_routes.py`)
- `api_bp` — minimal internal API (`routes/api_routes.py`)
- `lineup_bp` — lineup views and PDF/EPUB export (`routes/lineup_routes.py`)
- `json_bp` — direct JSON game editor (`routes/json_routes.py`)

Business logic lives in `services/`: `game_service.py`, `stats_service.py`.

### Database

SQLAlchemy + SQLite (`gamesFiles/floorball.db`). Key models in `models/`:
- `GameRecord` — game metadata plus JSON text columns for player stats (goals, assists, plus/minus, saves, etc.), lines, formations
- `RosterPlayer` — composite PK `(player_id, season, category)`
- `User` / `TeamPermission` — user accounts with per-team RBAC roles (viewer/editor/admin)
- `TeamSettings` — key-value table for app-wide settings (e.g. current season)

Player stats are stored as JSON blobs in SQL columns, not normalized rows — this is intentional for the scale (small team use).

### Authentication & Authorization

Two parallel auth paths coexist:
1. **PIN sessions** — `FLOORBALL_PIN` env var grants access; `ADMIN_PIN` grants admin
2. **User accounts** — username/password with bcrypt, roles stored in `TeamPermission`

Session flags: `authenticated`, `is_admin_session`, `user_id`, `lang`.

`utils/auth_helpers.py` provides `require_edit()` and `require_manage()` decorators that check both paths. A wildcard category `'*'` in `TeamPermission` grants a role across all teams.

### CSP / Security Headers

`app.py` generates a per-request nonce (`g.csp_nonce`) and applies it to the `Content-Security-Policy` header via `@after_request`. All `<script>` tags in templates must use `nonce="{{ g.csp_nonce }}"`. **Inline event handlers (`onclick=`, `onchange=` attributes) are blocked by CSP** — use `addEventListener` in the nonce-protected script block instead.

### Configuration & Translations

`config.py` is the central config file: validates env vars, defines `CATEGORIES`, `PERIODS`, Flask config dict, and the `TRANSLATIONS` dict with all EN/IT UI strings (~200+ keys). Templates access translations via `g.t` (set by a `before_request` hook).

### Templates

Bootstrap 5 (CDN) with Jinja2. `base.html` provides the nav and language toggle. Notable templates:
- `game_details.html` — real-time stat tracking via JavaScript (no page refresh)
- `game_lineup.html` — lineup builder with print/PDF export (jsPDF via CDN)
- `game_lineup_eink.html` — simplified e-ink optimized view
- `stats.html` — sortable, filterable stats table

### Tests

`tests/conftest.py` sets env vars, creates a temporary SQLite DB per session, and provides `client` (pre-authenticated), `clean_db` (auto-truncates between tests), and `app_ctx` fixtures. CSRF is disabled in test mode.
