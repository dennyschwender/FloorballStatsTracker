"""
Route blueprints for FloorballStatsTracker
"""
from .game_routes import game_bp
from .roster_routes import roster_bp
from .stats_routes import stats_bp
from .api_routes import api_bp
from .admin_routes import admin_bp
from .lineup_routes import lineup_bp
from .json_routes import json_bp

__all__ = ['game_bp', 'roster_bp', 'stats_bp', 'api_bp', 'admin_bp', 'lineup_bp', 'json_bp']
