# Floorball Stats Tracker (Python/Flask)

## Features

- Track floorball game stats: plus/minus, goals, assists, saves, goals conceded
- Manage multiple games, teams, and categories
- Responsive web UI for mobile and desktop
- Grouped action dropdowns for players and goalies
- Local JSON file storage (no cloud required)

## Setup

1. Clone the repo.
2. Install dependencies:

   ```sh
   pip install -r requirements.txt
   ```

3. Run the app locally:

   ```sh
   python app.py
   ```

## Docker

### Run with Docker

1. Build the image:

   ```sh
   docker build -t floorball-stats-tracker .
   ```

2. Run the container:

   ```sh
   docker run -p 5000:5000 -v $(pwd)/games.json:/app/games.json floorball-stats-tracker
   ```

---

## Website Usage Guide

### Access & Security

- On first access, you must enter the PIN (default: 1234, or set via `FLOORBALL_PIN` environment variable).

### Homepage (`/`)

- **Create New Game**: Start a new game by entering teams, date, lines, and goalies.
- **Category Filter**: Filter games by team/category using the dropdown.
- **Go to Latest Game**: Jump to the most recent game for the selected category.
- **Stats**: Go to the stats overview page.
- **Game List**: See all games, with date and teams. Click "View" to see details.

### Game Details (`/game/<id>`)

- **Game Info**: See date, teams, and category.
- **Edit/Modify Game**: Change teams, date, lines, or goalies.
- **Reset Stats**: Reset all stats for this game.
- **Dropdown Actions**: For each player and goalie, use dropdowns to add/remove plus/minus, goals, assists, saves, and goals conceded.
- **Persistent Edit Mode**: If you enter edit mode, it stays active until you leave the page.

### Create/Modify Game (`/create_game`, `/modify_game/<id>`)

- Enter or update all game info: category, teams, date, lines, and goalies.
- Save or cancel changes. You can also delete a game from the modify page.

### Stats Page (`/stats`)

- **Category Filter**: Filter stats by team/category.
- **Plus/Minus Table**: Each row is a player, each column is a game (ordered by date), with a total at the end.
- **Goals/Assists Table**: Each row is a player, each column is a game (goals/assists in one cell), with totals at the end.
- **Compact Layout**: Tables are compact and responsive, with game headers in the format `dd.mm.yyyy - HOME vs AWAY`.

### PIN Page (`/` on first access)

- Enter the PIN to access the site. PIN can be changed via environment variable.

---

## Data Storage

- All data is stored in `gamesFiles/games.json` by default. You can mount a volume in Docker to persist data.

## Support

- For issues or feature requests, open an issue on GitHub.
