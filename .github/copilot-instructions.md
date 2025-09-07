# FloorballStatsTracker Copilot Instructions

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Overview

FloorballStatsTracker is a Flask-based Python web application for tracking floorball game statistics, including player and goalie stats, period-based results, and team management. The app features a Bootstrap UI, PIN-based authentication, and optional Google Sheets integration.

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

## Codebase Structure

### Key Files
- `app.py`: Main Flask application (550+ lines)
- `sheets_service.py`: Google Sheets integration
- `requirements.txt`: Python dependencies
- `gamesFiles/games.json`: Game data storage (auto-created)
- `templates/`: HTML templates (Bootstrap-based UI)
- `Dockerfile` and `docker-compose.yml`: Container deployment

### Important Directories
```
/home/runner/work/FloorballStatsTracker/FloorballStatsTracker/
├── app.py                 # Main Flask app
├── sheets_service.py      # Google Sheets integration  
├── requirements.txt       # Dependencies
├── Dockerfile            # Container build
├── docker-compose.yml    # Container orchestration
├── templates/            # HTML templates
│   ├── index.html        # Main dashboard
│   ├── game_details.html # Game stats interface
│   ├── game_form.html    # Game creation/edit
│   ├── pin.html          # PIN login
│   └── stats.html        # Statistics overview
└── gamesFiles/           # Data directory (auto-created)
    └── games.json        # Game data storage
```

### Core Functionality
- **Game Management**: Create, modify, delete games with teams and player lineups
- **Stats Tracking**: Plus/minus, goals, assists for players and goalies per period
- **Data Storage**: JSON file-based storage (gamesFiles/games.json)
- **Authentication**: PIN-based access control
- **UI**: Mobile-friendly Bootstrap interface

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