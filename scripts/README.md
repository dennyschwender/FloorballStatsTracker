# Scripts

Utility scripts for managing the Floorball Stats Tracker.

## backup_games.py

Creates a timestamped backup of `gamesFiles/games.json` by copying it to `gamesFiles/games_backup_YYYYMMDD_HHMMSS.json`.

```bash
python scripts/backup_games.py
```

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
