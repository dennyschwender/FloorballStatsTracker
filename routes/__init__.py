"""
Route blueprints for FloorballStatsTracker
"""
from .game_routes import game_bp
from .roster_routes import roster_bp
from .stats_routes import stats_bp
from .api_routes import api_bp

__all__ = ['game_bp', 'roster_bp', 'stats_bp', 'api_bp']
