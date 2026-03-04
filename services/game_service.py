"""
Game business logic and data management (SQLite-backed).

Public API is identical to the old JSON-based version so that existing routes
work unchanged.  New public symbols:

* ``get_game(game_id)`` - fetch a single game by ID without loading all games.
* ``save_game(game)``   - upsert a single game dict.
"""
import logging
from config import PERIODS
from models.database import db
from models.game_model import GameRecord
from services.stats_service import recalculate_game_scores  # re-exported

logger = logging.getLogger(__name__)


def _upsert_game(game_dict):
    """Insert or update a single GameRecord row from a game dict."""
    game_id = game_dict.get('id')
    if game_id is None:
        raise ValueError('game dict missing "id" field')
    row = db.session.get(GameRecord, game_id)
    if row is None:
        row = GameRecord(id=game_id)
        db.session.add(row)
    row.update_from_dict(game_dict)


def load_games():
    """Load all games from the database as a list of dicts."""
    try:
        rows = GameRecord.query.all()
        return [row.to_dict() for row in rows]
    except Exception:
        logger.exception('load_games failed')
        return []


def get_game(game_id):
    """Fetch a single game by ID.  Returns the game dict or None."""
    try:
        row = db.session.get(GameRecord, game_id)
        return row.to_dict() if row else None
    except Exception:
        logger.exception('get_game(%s) failed', game_id)
        return None


def save_game(game_dict):
    """Upsert a single game dict into the database."""
    try:
        _upsert_game(game_dict)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception('save_game failed for id=%s', game_dict.get('id'))
        raise


def save_games(games):
    """Upsert a list of game dicts (backward-compatible bulk save).

    All existing routes call this after modifying one game.  Every game is
    upserted in a single transaction so the write is atomic.
    """
    try:
        for game_dict in games:
            _upsert_game(game_dict)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception('save_games failed')
        raise


def delete_game_by_id(game_id):
    """Permanently remove a game from the database."""
    try:
        row = db.session.get(GameRecord, game_id)
        if row:
            db.session.delete(row)
            db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception('delete_game_by_id(%s) failed', game_id)
        raise


def find_game_by_id(games, game_id):
    """Find a game by ID in an in-memory list (backward-compatible helper).

    For new code prefer ``get_game(game_id)`` to avoid loading all games.
    """
    for game in games:
        if game.get('id') == game_id:
            return game
    return None


def ensure_game_ids(games):
    """Ensure all games in *games* have a unique integer ID.

    Returns True if any game was modified so the caller knows to persist.
    """
    changed = False
    seen_ids = set()
    max_id = -1
    for game in games:
        if 'id' in game:
            try:
                max_id = max(max_id, int(game['id']))
            except (TypeError, ValueError):
                pass
    for game in games:
        raw_id = game.get('id')
        if raw_id is None or raw_id in seen_ids:
            max_id += 1
            game['id'] = max_id
            changed = True
        seen_ids.add(game['id'])
    return changed


def ensure_game_stats(game):
    """Ensure all stat dicts exist in the game dict (initialise missing ones to {})."""
    stat_keys = [
        'plusminus', 'goals', 'assists', 'unforced_errors',
        'shots_on_goal', 'penalties_taken', 'penalties_drawn',
        'saves', 'goals_conceded', 'game_scores', 'goalie_game_scores',
        'block_shots', 'stolen_balls',
    ]
    for stat in stat_keys:
        if stat not in game or not isinstance(game[stat], dict):
            game[stat] = {}
    return game


def ensure_player_stats(game, player):
    """Ensure *player* has all skater stat entries initialised to 0."""
    for stat in [
        'plusminus', 'goals', 'assists', 'unforced_errors',
        'shots_on_goal', 'penalties_taken', 'penalties_drawn',
        'block_shots', 'stolen_balls',
    ]:
        if stat in game and player not in game[stat]:
            game[stat][player] = 0
    return game


def build_formation_from_form(request_form, formation_keys, player_map):
    """Extract formation data from a form request with position-based ordering."""
    formations = {}
    for key in formation_keys:
        players_with_pos = []
        for player_id, player in player_map.items():
            pos_val = request_form.get(f'{key}_{player_id}', '').strip()
            if pos_val:
                try:
                    pos_num = int(pos_val)
                    players_with_pos.append({
                        'position': pos_num,
                        'name': f"{player['number']} - {player['surname']} {player['name']}",
                    })
                except ValueError:
                    pass
        players_with_pos.sort(key=lambda x: x['position'])
        formations[key] = [p['name'] for p in players_with_pos]
    return formations
