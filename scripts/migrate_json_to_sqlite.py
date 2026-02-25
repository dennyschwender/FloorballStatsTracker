#!/usr/bin/env python3
"""
Migrate existing JSON data to the SQLite database.

Run once after upgrading to the SQLite-backed version:

    python scripts/migrate_json_to_sqlite.py

Safe to re-run: games and roster players whose IDs already exist in the DB are
skipped (no duplicates created).  Pass --force to wipe and re-import everything.
"""
import argparse
import json
import os
import sys

# Ensure project root is importable
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)

from app import app, db                # noqa: E402  – needs ROOT on path
from models.game_model import GameRecord, RosterPlayer  # noqa: E402


GAMES_FILE = os.path.join(ROOT, 'gamesFiles', 'games.json')
ROSTERS_DIR = os.path.join(ROOT, 'rosters')


# ──────────────────────────────────────────────────────────────────────────────

def migrate_games(force: bool = False) -> tuple[int, int]:
    """Import games from games.json into the DB.

    Returns (imported, skipped) counts.
    """
    if not os.path.exists(GAMES_FILE):
        print(f'  [games] {GAMES_FILE} not found – nothing to migrate.')
        return 0, 0

    with open(GAMES_FILE) as f:
        games = json.load(f)

    if not isinstance(games, list):
        print('  [games] Unexpected format in games.json – skipping.')
        return 0, 0

    imported = skipped = 0
    for game_dict in games:
        gid = game_dict.get('id')
        if gid is None:
            print(f'  [games] Skipping game with no id: {game_dict.get("home_team")} vs {game_dict.get("away_team")}')
            skipped += 1
            continue

        existing = db.session.get(GameRecord, gid)
        if existing and not force:
            skipped += 1
            continue
        if existing and force:
            db.session.delete(existing)
            db.session.flush()

        row = GameRecord(id=gid)
        row.update_from_dict(game_dict)
        db.session.add(row)
        imported += 1

    db.session.commit()
    return imported, skipped


def migrate_rosters(force: bool = False) -> tuple[int, int]:
    """Import all roster JSON files from the rosters/ directory into the DB.

    Each file is named:
    - ``roster_SEASON_CATEGORY.json``  (new format with season)
    - ``roster_CATEGORY.json``         (legacy format without season)

    Returns (imported, skipped) counts.
    """
    if not os.path.isdir(ROSTERS_DIR):
        print(f'  [rosters] {ROSTERS_DIR} not found – nothing to migrate.')
        return 0, 0

    imported = skipped = 0

    for filename in sorted(os.listdir(ROSTERS_DIR)):
        if not (filename.startswith('roster_') and filename.endswith('.json')):
            continue

        base = filename[len('roster_'):-len('.json')]
        parts = base.split('_', 1)
        if len(parts) == 2:
            season, category = parts
        else:
            season, category = '', parts[0]

        filepath = os.path.join(ROSTERS_DIR, filename)
        try:
            with open(filepath) as f:
                players = json.load(f)
        except Exception as exc:
            print(f'  [rosters] Failed to read {filename}: {exc}')
            continue

        if not isinstance(players, list):
            print(f'  [rosters] Unexpected format in {filename} – skipping.')
            continue

        for player in players:
            pid = str(player.get('id', ''))
            if not pid:
                skipped += 1
                continue

            existing = RosterPlayer.query.filter_by(
                player_id=pid, season=season, category=category
            ).first()

            if existing and not force:
                skipped += 1
                continue
            if existing and force:
                db.session.delete(existing)
                db.session.flush()

            row = RosterPlayer(
                player_id=pid,
                season=season,
                category=category,
                number=str(player.get('number', '')),
                surname=str(player.get('surname', '')),
                name=str(player.get('name', '')),
                nickname=str(player.get('nickname', '')),
                position=str(player.get('position', 'A')),
                tesser=str(player.get('tesser', '')),
                hidden=1 if player.get('hidden') else 0,
            )
            db.session.add(row)
            imported += 1

    db.session.commit()
    return imported, skipped


# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--force', action='store_true',
                        help='Delete and re-import records that already exist in the DB.')
    args = parser.parse_args()

    print('FloorballStatsTracker – JSON → SQLite migration')
    print('=' * 55)

    with app.app_context():
        db.create_all()  # ensure schema exists

        print('\nMigrating games …')
        g_imp, g_skip = migrate_games(force=args.force)
        print(f'  imported: {g_imp}  skipped: {g_skip}')

        print('\nMigrating rosters …')
        r_imp, r_skip = migrate_rosters(force=args.force)
        print(f'  imported: {r_imp}  skipped: {r_skip}')

    print('\nDone.')


if __name__ == '__main__':
    main()
