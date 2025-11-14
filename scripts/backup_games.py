import shutil
import os
from datetime import datetime


def backup_games():
    src = os.path.join(os.path.dirname(__file__), 'gamesFiles', 'games.json')
    if not os.path.exists(src):
        print("No games.json found to backup.")
        return
    backup_dir = os.path.join(os.path.dirname(__file__), 'gamesFiles')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    dst = os.path.join(backup_dir, f'games_backup_{timestamp}.json')
    shutil.copy2(src, dst)
    print(f"Backup created: {dst}")


if __name__ == "__main__":
    backup_games()
