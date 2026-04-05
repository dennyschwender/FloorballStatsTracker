"""
Roster data model and management functions (SQLite-backed).

Public API is identical to the old JSON/file-based version so that existing
routes continue to work without changes.
"""
import logging
from models.database import db
from models.game_model import RosterPlayer
from utils.security import validate_category, validate_season

logger = logging.getLogger(__name__)


def _check_category(category):
    if not category or not validate_category(category):
        raise ValueError("Invalid category")


def _check_season(season):
    if season and not validate_season(season):
        raise ValueError("Invalid season format")


def load_roster(category=None, season=None):
    """Load roster for a specific category/season.  Returns list of player dicts."""
    if not category:
        return []
    try:
        _check_category(category)
        _check_season(season)
        q = RosterPlayer.query.filter_by(category=category, season=season or "")
        rows = q.all()
        return [r.to_dict() for r in rows]
    except ValueError:
        raise
    except Exception:
        logger.exception("load_roster failed for category=%s season=%s", category, season)
        return []


def save_roster(roster, category, season=None):
    """Replace the entire roster for a (category, season) with roster.

    Deletes existing rows then inserts the new list in one transaction.
    """
    _check_category(category)
    _check_season(season)
    safe_season = season or ""
    try:
        RosterPlayer.query.filter_by(category=category, season=safe_season).delete()
        for player in roster:
            row = RosterPlayer(
                player_id=str(player.get("id", "")),
                season=safe_season,
                category=category,
                number=str(player.get("number", "")),
                surname=str(player.get("surname", "")),
                name=str(player.get("name", "")),
                nickname=str(player.get("nickname", "")),
                position=str(player.get("position", "A")),
                tesser=str(player.get("tesser", "")),
                hidden=1 if player.get("hidden") else 0,
            )
            db.session.add(row)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("save_roster failed for category=%s season=%s", category, season)
        raise


def delete_roster_category(category, season=None):
    """Remove every player in a (category, season) roster from the database."""
    _check_category(category)
    safe_season = season or ""
    try:
        deleted = RosterPlayer.query.filter_by(
            category=category, season=safe_season
        ).delete()
        db.session.commit()
        return deleted > 0
    except Exception:
        db.session.rollback()
        logger.exception("delete_roster_category failed")
        raise


def get_all_seasons():
    """Return sorted list (descending) of all unique season strings."""
    try:
        rows = db.session.query(RosterPlayer.season).distinct().all()
        return sorted({r[0] for r in rows if r[0]}, reverse=True)
    except Exception:
        logger.exception("get_all_seasons failed")
        return []


def get_all_categories_with_rosters(season=None):
    """Return sorted list of categories that have at least one player."""
    try:
        q = db.session.query(RosterPlayer.category).distinct()
        if season and season.strip():
            q = q.filter(RosterPlayer.season == season)
        rows = q.all()
        return sorted({r[0] for r in rows if r[0]})
    except Exception:
        logger.exception("get_all_categories_with_rosters failed")
        return []


def get_all_rosters_with_seasons():
    """Return list of dicts [{season, category}, ...] sorted by season desc."""
    try:
        rows = (
            db.session.query(RosterPlayer.season, RosterPlayer.category)
            .distinct()
            .all()
        )
        result = [{"season": r[0], "category": r[1]} for r in rows]
        result.sort(key=lambda x: (x["season"], x["category"]), reverse=True)
        return result
    except Exception:
        logger.exception("get_all_rosters_with_seasons failed")
        return []


def get_all_tesser_values():
    """Return sorted list of all unique tesser values across all rosters."""
    try:
        rows = db.session.query(RosterPlayer.tesser).distinct().all()
        return sorted({r[0] for r in rows if r[0]})
    except Exception:
        logger.exception("get_all_tesser_values failed")
        return []


