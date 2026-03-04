"""
Per-team configurable settings stored as key/value pairs.

Setting keys and their default values
--------------------------------------
track_block_shots   1    Show/track blocked shots for this team
track_stolen_balls  1    Show/track stolen balls for this team
show_advanced_stats 1    Show advanced stats (median, avg) in GS page
show_formations     1    Show formation configuration in game view
"""
from .database import db

# Defaults – used when no row exists for a given (category, key)
DEFAULTS: dict[str, str] = {
    'track_block_shots': '1',
    'track_stolen_balls': '1',
    'show_advanced_stats': '1',
    'show_formations': '1',
}


class TeamSettings(db.Model):
    __tablename__ = 'team_settings'

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.Text, nullable=False)
    setting_key = db.Column(db.Text, nullable=False)
    setting_value = db.Column(db.Text, nullable=False, default='1')

    __table_args__ = (
        db.UniqueConstraint('category', 'setting_key', name='uq_cat_key'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'category': self.category,
            'setting_key': self.setting_key,
            'setting_value': self.setting_value,
        }


# ── Convenience helpers ───────────────────────────────────────────────────────

def get_setting(category: str, key: str) -> str:
    """Return the setting value for *category*/*key*, falling back to default."""
    row = TeamSettings.query.filter_by(category=category, setting_key=key).first()
    if row is not None:
        return row.setting_value
    return DEFAULTS.get(key, '0')


def get_all_settings(category: str) -> dict[str, str]:
    """Return all settings for *category* (merged with defaults for missing keys)."""
    rows = TeamSettings.query.filter_by(category=category).all()
    result = dict(DEFAULTS)
    for row in rows:
        result[row.setting_key] = row.setting_value
    return result


# ── Global / app-level settings ───────────────────────────────────────────────
_APP_CATEGORY = '_app'


def get_current_season() -> str:
    """Return the configured current season (empty string if not set)."""
    row = TeamSettings.query.filter_by(
        category=_APP_CATEGORY, setting_key='current_season'
    ).first()
    return row.setting_value if row else ''


def set_current_season(value: str) -> None:
    """Persist the current season (call db.session.commit() afterwards)."""
    row = TeamSettings.query.filter_by(
        category=_APP_CATEGORY, setting_key='current_season'
    ).first()
    if row is None:
        row = TeamSettings(
            category=_APP_CATEGORY,
            setting_key='current_season',
            setting_value=value,
        )
        db.session.add(row)
    else:
        row.setting_value = value


def set_setting(category: str, key: str, value: str) -> None:
    """Upsert a team setting (does NOT commit)."""
    row = TeamSettings.query.filter_by(category=category, setting_key=key).first()
    if row is None:
        row = TeamSettings(category=category, setting_key=key, setting_value=value)
        db.session.add(row)
    else:
        row.setting_value = value
