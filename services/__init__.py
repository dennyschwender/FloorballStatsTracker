"""
Service layer modules for FloorballStatsTracker
"""
from .file_service import safe_read_json, safe_write_json
from .game_service import load_games, save_games, find_game_by_id, ensure_game_ids
from .stats_service import (
    calculate_game_score,
    calculate_goalie_game_score,
    calculate_stats_optimized
)

__all__ = [
    'safe_read_json',
    'safe_write_json',
    'load_games',
    'save_games',
    'find_game_by_id',
    'ensure_game_ids',
    'calculate_game_score',
    'calculate_goalie_game_score',
    'calculate_stats_optimized',
]
