# FloorballStatsTracker Copilot Instructions

## Overview

Flask-based web app for comprehensive floorball game tracking with **season management**, **multi-language support** (EN/IT), and **roster organization**. Features PIN-based auth, real-time stats, and optional Google Sheets integration. Mobile-responsive Bootstrap UI with JSON file storage.

## Working Effectively

### Bootstrap and Dependencies
- **Python Version**: Requires Python 3.11+ (tested with Python 3.12.3)
- **Install Dependencies**: `pip3 install -r requirements.txt` -- takes 30 seconds
- **Create Data Directory**: `mkdir -p gamesFiles`

### Running the Application
- **Development Server**: `python3 app.py` -- starts immediately
- **Alternative**: `flask --app app.py run --port 5001` -- starts immediately
- **Production**: `gunicorn -b 0.0.0.0:5000 app:app`
- **Environment Variables**:
  - `FLOORBALL_PIN`: PIN for app access (default: 1717)
  - `FLASK_SECRET_KEY`: Session secret (default: dev_secret)
  - Optional Google Sheets: `GOOGLE_APPLICATION_CREDENTIALS`, `SPREADSHEET_ID`

### Docker Support
- **Build**: `docker build -t floorball-stats-tracker .`
- **KNOWN ISSUE**: Docker build may fail in sandboxed environments due to SSL certificate verification errors when accessing PyPI
- **Run with Docker Compose**: `docker-compose up`

## Validation

### Manual Testing Scenarios
Always manually validate changes by running through these complete scenarios:

1. **PIN Authentication Test**:
   - Start the app and navigate to http://127.0.0.1:5000
   - Enter PIN "1717" to access the application
   - Verify successful login redirects to main dashboard

2. **Game Creation Workflow**:
   - Click "Create New Game"
   - Fill in team/category, home team, away team, date
   - Add players to lines and goalie names
   - Submit form and verify game creation

3. **Stats Tracking Test**:
   - Create a game and navigate to game details
   - Test adding goals, assists, plus/minus for players
   - Test goalie saves and goals conceded
   - Verify period tracking and results display

4. **Navigation Test**:
   - Test switching between games
   - Visit Stats page to view aggregated statistics
   - Test filtering games by team/category

### Code Validation
- **Syntax Check**: `python3 -m py_compile app.py && python3 -m py_compile sheets_service.py`
- **No existing linting configuration** - basic syntax validation only
- **No test suite exists** - manual testing is required

## Architecture

### Key Files
- `app.py` - Main Flask app (550+ lines), all routes and business logic
- `sheets_service.py` - Optional Google Sheets integration
- `gamesFiles/games.json` - Game data storage (auto-created)
- `rosters/roster_{SEASON}_{CATEGORY}.json` - Season-based roster files
- `templates/` - Jinja2 templates with Bootstrap 5 UI

### Core Features
- **Season Management**: Multi-season support with automatic detection, season-based filtering for games/stats/rosters
- **Game Tracking**: Create/modify/delete games with period-based scoring (1, 2, 3, OT)
- **Player Stats**: Plus/minus, goals, assists, unforced errors per game and period
- **Goalie Stats**: Saves, goals conceded, save percentage calculations
- **Roster Management**: Season-based rosters with bulk CSV import, position tracking (A/C/D/P)
- **Lineup Builder**: 4 playing lines, special formations (PP1/2, BP1/2, 6vs5, Stress), category counters (U18/U21/etc.)
- **Bilingual UI**: English and Italian language toggle
- **Authentication**: PIN-based access (env var `FLOORBALL_PIN`, default: 1234)

## Key Patterns

### Season-Based Data Organization
- Games: Stored in `games.json` with `season` field (e.g., "2024-25")
- Rosters: Separate files `roster_{SEASON}_{CATEGORY}.json` in `rosters/` directory
- Stats filtering: UI dropdowns filter by season, then by team/category within season
- Migration tool: `scripts/migrate_to_seasons.py` converts old data to season structure

### Real-Time Stats Updates
When goals/assists added in `game_details.html`, JavaScript immediately:
1. Updates player stat displays
2. Recalculates period scores
3. Updates running totals
No page refresh needed - all via inline JavaScript event handlers.

### Roster Import Format
Bulk import accepts CSV or formatted text:
```
Number, Name, Surname, Nickname, Position, Category
1,John,Doe,Johnny,A,U21
```
Parsed in `app.py` route `/roster/<season>/<category>/import`.

### Google Sheets Integration (Optional)
If `GOOGLE_APPLICATION_CREDENTIALS` and `SPREADSHEET_ID` env vars set:
- Pushes game results to Google Sheets after game completion
- Uses service account auth (no OAuth flow)
- Implemented in `sheets_service.py:upload_game_to_sheets()`

## Project Conventions

- **Single JSON file storage** - Not for high-concurrency, suitable for team use (5-20 concurrent users)
- **Auto-generated game IDs** - Timestamp-based, ensure uniqueness within single process
- **No test suite** - Manual validation required, see testing scenarios in instructions
- **Bootstrap from CDN** - Requires internet, templates load CSS/JS from cdn.jsdelivr.net
- **Bilingual from templates** - Language strings in Jinja2 templates, not in database
- **Docker SSL issue** - Builds may fail in sandboxed environments accessing PyPI

## Common Commands Reference

### Repository Root Contents
```
total 64
-rw-r--r-- 1 runner docker  2565 README.md
-rw-r--r-- 1 runner docker 17656 app.py
-rw-r--r-- 1 runner docker   108 requirements.txt
-rw-r--r-- 1 runner docker  1084 sheets_service.py
-rw-r--r-- 1 runner docker   505 Dockerfile
-rw-r--r-- 1 runner docker   265 docker-compose.yml
drwxr-xr-x 2 runner docker  4096 templates
drwxr-xr-x 3 runner docker  4096 .github
```

### Dependencies (requirements.txt)
```
Flask
google-auth
google-auth-oauthlib
google-auth-httplib2
google-api-python-client
python-dotenv
gunicorn
```

## Development Guidelines

### Making Changes
- **Always test PIN authentication** after any authentication-related changes
- **Test game creation workflow** after modifying game creation logic
- **Verify data persistence** by checking gamesFiles/games.json after operations
- **Test responsive UI** - the app is designed to be mobile-friendly

### Data Handling
- Game data is stored in `gamesFiles/games.json`
- The app auto-creates this file if it doesn't exist
- Each game has an auto-generated ID for tracking
- Player stats are tracked per game and period

### Environment Setup Notes
- The app runs on Flask's development server by default
- Default PIN is 1717 but should be changed via environment variable in production
- Google Sheets integration is optional and requires service account credentials
- Bootstrap CSS is loaded from CDN (requires internet access)

### Known Limitations
- Docker builds may fail in environments with SSL certificate restrictions
- No automated test suite - manual validation required
- No linting configuration - basic syntax checking only
- Single JSON file storage (not suitable for high-concurrency scenarios)