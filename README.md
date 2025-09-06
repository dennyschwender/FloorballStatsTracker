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

### Run with Docker Compose

1. Start the app:

   ```sh
   docker compose up --build
   ```

2. Stop the app:

   ```sh
   docker compose down
   ```

The app will be available at <http://localhost:5000>

## Usage

- Create, modify, and switch between games
- Add/remove stats for players and goalies
- Delete or reset games
- All data is saved in `games.json` in the project directory
