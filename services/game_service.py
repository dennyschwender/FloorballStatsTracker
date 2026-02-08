"""
Game business logic and data management
"""
import json
from config import GAMES_FILE, PERIODS
from utils.cache import GameCache
from .file_service import safe_read_json, safe_write_json

# Initialize global game cache
game_cache = GameCache()


def load_games():
    """Load games from cache or file with safe file operations"""
    # Try to get from cache first
    cached_games = game_cache.get(GAMES_FILE)
    if cached_games is not None:
        return cached_games
    
    # Cache miss - load from file
    try:
        games = safe_read_json(GAMES_FILE)
        if games is None:
            games = []
        
        # Store in cache
        game_cache.set(GAMES_FILE, games)
        return games
    except Exception:
        return []


def save_games(games):
    """Save games with safe atomic writes and cache invalidation"""
    try:
        safe_write_json(GAMES_FILE, games)
        # Invalidate cache after write
        game_cache.invalidate()
        # Update cache with new data
        game_cache.set(GAMES_FILE, games)
    except Exception as e:
        # Fallback to simple write if atomic write fails
        with open(GAMES_FILE, 'w') as f:
            json.dump(games, f, indent=2)
        game_cache.invalidate()


def find_game_by_id(games, game_id):
    """Find a game by its ID field (not array index)"""
    for game in games:
        if game.get('id') == game_id:
            return game
    return None


def ensure_game_ids(games):
    """Ensure all games have unique IDs"""
    changed = False
    seen_ids = set()
    # Find current max id
    max_id = -1
    for i, game in enumerate(games):
        if 'id' in game:
            try:
                game_id = int(game['id'])
                max_id = max(max_id, game_id)
            except Exception:
                pass
        else:
            max_id = max(max_id, i)
    
    # Assign IDs to games without one and fix duplicates
    for i, game in enumerate(games):
        if 'id' not in game or game['id'] in seen_ids:
            # Missing ID or duplicate ID
            max_id += 1
            game['id'] = max_id
            changed = True
        seen_ids.add(game['id'])
    return changed
