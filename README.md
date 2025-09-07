# Floorball Stats Tracker

A web app for tracking floorball game statistics, including player and goalie stats, period-based results, and team management. Built with Flask and Bootstrap.

## Features & Actions

### Game Management

- **Create Game**: Add a new game with teams, date, lines, and goalies.
- **Modify Game**: Edit teams, date, lines, and goalies for an existing game.
- **Delete Game**: Remove a game from the database (irreversible).
- **Reset Stats**: Reset all player, goalie, and period stats for a game to zero.
- **Switch Between Games**: Filter and switch between games by team/category.

### Player Actions (per game)

- **Plus/Minus**: Increment or decrement a player's plus/minus stat.
- **Goals**: Add or remove a goal for a player (affects period result).
- **Assists**: Add or remove an assist for a player.
- **Line Actions**: Apply plus/minus, goal, or assist to all players in a line at once.

### Goalie Actions (per game)

- **Goalie Plus/Minus**: Increment or decrement a goalie's plus/minus stat.
- **Saves**: Add or remove a save for a goalie.
- **Goals Conceded**: Add or remove a goal conceded for a goalie (affects period result).
- **Assists**: Add or remove an assist for a goalie.

### Period & Result Tracking

- **Set Period**: Switch the current period (1, 2, 3, OT) for stat entry.
- **Period Results**: Track home/away goals for each period; summary and breakdown shown in game details.
- **Reset Results**: Reset all period results to zero with the reset action.

### Stats & Overview

- **Stats Page**: View all games, filter by team/category, and see per-player plus/minus, goals, assists, and total points.
- **Totals**: See per-player totals and per-game breakdowns for all tracked stats.

### Security & Access

- **PIN Login**: Access to the app is protected by a PIN code (set via environment variable `FLOORBALL_PIN`).

### UI/UX

- **Mobile Friendly**: Responsive Bootstrap UI for desktop and mobile.
- **Edit Mode**: Toggle edit mode for in-game stat entry and period switching.
- **Dropdown Actions**: Use dropdowns for quick stat entry and line/goalie actions.

## Running the App

1. Install requirements: `pip install -r requirements.txt`
2. Run: `python app.py`
3. Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

## Docker Support

- Use the provided `Dockerfile` and `docker-compose.yml` for containerized deployment.

## Data Storage

- All game data is stored in `gamesFiles/games.json`.

---

For any issues or feature requests, please open an issue or contact the maintainer.
