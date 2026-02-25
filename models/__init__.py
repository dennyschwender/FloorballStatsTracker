"""
Data models for FloorballStatsTracker
"""
from .database import db  # noqa: F401 — must be imported before models
from .game_model import GameRecord, RosterPlayer  # register SQLAlchemy models

from .roster import (
    load_roster,
    save_roster,
    get_roster_file,   # deprecated stub, kept for imports that haven't changed
    delete_roster_category,
    get_all_seasons,
    get_all_categories_with_rosters,
    get_all_rosters_with_seasons,
    get_all_tesser_values,
)

__all__ = [
    'db',
    'GameRecord',
    'RosterPlayer',
    'load_roster',
    'save_roster',
    'get_roster_file',
    'delete_roster_category',
    'get_all_seasons',
    'get_all_categories_with_rosters',
    'get_all_rosters_with_seasons',
    'get_all_tesser_values',
]
