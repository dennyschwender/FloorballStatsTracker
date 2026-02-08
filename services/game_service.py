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


def ensure_game_stats(game):
    """Ensure all stat dictionaries exist in game
    
    Args:
        game: Game dictionary to ensure stats for
        
    Returns:
        The game dictionary with all stat dictionaries initialized
    """
    stat_keys = ['plusminus', 'goals', 'assists', 'unforced_errors', 
                 'shots_on_goal', 'penalties_taken', 'penalties_drawn',
                 'saves', 'goals_conceded']
    for stat in stat_keys:
        if stat not in game or not isinstance(game[stat], dict):
            game[stat] = {}
    return game


def ensure_player_stats(game, player):
    """Ensure player has all stat entries initialized to 0
    
    Args:
        game: Game dictionary containing stat dictionaries
        player: Player name to initialize stats for
        
    Returns:
        The game dictionary with player stats initialized
    """
    for stat in ['plusminus', 'goals', 'assists', 'unforced_errors', 
                 'shots_on_goal', 'penalties_taken', 'penalties_drawn']:
        if stat in game and player not in game[stat]:
            game[stat][player] = 0
    return game


def build_formation_from_form(request_form, formation_keys, player_map):
    """Extract formation data from form request with position-based ordering
    
    Args:
        request_form: Flask request.form object
        formation_keys: List of keys to extract (e.g., ['pp1', 'pp2'])
        player_map: Dict mapping player IDs to player data dicts
        
    Returns:
        Dict mapping formation keys to lists of player names, ordered by position
    """
    formations = {}
    for key in formation_keys:
        formation_players_with_position = []
        # Collect all form fields for this formation
        for player_id in player_map.keys():
            position_value = request_form.get(f'{key}_{player_id}', '').strip()
            if position_value:
                player = player_map.get(player_id)
                if player:
                    try:
                        pos_num = int(position_value)
                        formation_players_with_position.append({
                            'position': pos_num,
                            'name': f"{player['number']} - {player['surname']} {player['name']}"
                        })
                    except ValueError:
                        pass
        
        # Sort by position number and extract names
        formation_players_with_position.sort(key=lambda x: x['position'])
        formation_players = [p['name'] for p in formation_players_with_position]
        formations[key] = formation_players
    return formations
