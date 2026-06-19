# FloorballStatsTracker

Flask + SQLite web app for tracking floorball game stats. Bilingual (EN/IT).

## Quick start

```bash
export FLOORBALL_PIN=testpin123 FLASK_SECRET_KEY=dev
python app.py
```

## Required env vars

- `FLOORBALL_PIN` — min 6 chars, no default
- `FLASK_SECRET_KEY` — rejected if == `dev_secret`
- `SESSION_COOKIE_SECURE` — defaults to `True`, set `False` for dev HTTP
- `ADMIN_PIN` — optional, must differ from FLOORBALL_PIN, min 6 chars

## Commands

| Action | Command |
|--------|---------|
| Run dev | `python app.py` |
| Run tests | `python -m pytest -q` |
| Run all (no skip) | `python -m pytest --ignore= --ignore= -q` |
| Single test file | `python -m pytest tests/test_actions.py -q` |
| Lint | `ruff check .` |
| Format | `black .` |
| Import sort | `isort .` |
| Docker | `docker-compose up -d` |
| Production | `gunicorn -b 0.0.0.0:5000 app:app` |

## Tests

- **21 test files** in `tests/`
- `pytest.ini` skips `test_web_pages.py` and `test_app_info.py` by default
- `conftest.py` sets env vars, uses a temp SQLite DB, truncates tables between tests
- Client fixture authenticates with `authenticated=True` + `is_admin_session=True`, CSRF disabled
- CI runs `python -m pytest -q` on Python 3.10 and 3.11

## Architecture

- **Entrypoint**: `app.py` → `create_app()` factory
- **Blueprints**: `game_bp`, `roster_bp`, `stats_bp`, `api_bp`, `admin_bp` in `routes/`
- **Models** (SQLAlchemy): `GameRecord`, `RosterPlayer`, `User`, `TeamPermission`, `TeamSettings`
- **Services**: `services/game_service.py` (CRUD), `services/stats_service.py` (calc)
- **Auth**: PIN (env var) + optional user login with roles (viewer < editor < admin)
- **I18n dicts** live in `config.py` — add keys to both `en` and `it` blocks
- **Data**: SQLite at `gamesFiles/floorball.db`. Stat dicts stored as JSON text columns in `games` table
- **CSP**: nonce-based; Flask routes use `{{ csp_nonce() }}` in `<script>` tags
- **Rate limiting**: Flask-Limiter on login routes (10/min per IP)

## Key conventions

- All stat dicts keyed by `"{number} - {surname} {name}"` (e.g. `"10 - Smith John"`)
- Player IDs are UUIDs unique per (season, category) — composite PK
- New scalar columns on `games` table: add to `_NEW_TEXT_COLUMNS` in `app.py` for auto-migration
- New stat columns: add to `_STAT_COLS` in `models/game_model.py`
- Formations stored as JSON in `formations` column: `pp1`, `pp2`, `bp1`, `bp2`, `6vs5`, `stress_line`
- CSV bulk import format: `Number, Surname, Name, Position, Tesser, Nickname`

## Gotchas

- Do NOT set `FLASK_SECRET_KEY=dev_secret` — production config.py rejects it
- CSRF is auto-disabled in TESTING mode (`conftest.py`)
- Docker runs as non-root `appuser`, needs `gamesFiles/` write permission
- Session timeout = 2 hours
- Opponent goalie tracking is opt-in per game (`opponent_goalie_enabled`)