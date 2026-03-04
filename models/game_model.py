"""
SQLAlchemy ORM models for games and roster players.

Data design
-----------
* GameRecord maps 1:1 to the legacy game dict that routes/services pass around.
  Scalar game metadata is stored in proper columns; player stat dicts and
  structural arrays (lines, goalies, formations, result) are stored as JSON
  text columns so no join is needed when hydrating/dehydrating a game.

* RosterPlayer stores every player entry.  Because player IDs are only unique
  per (season, category) in the legacy JSON files, the PK is the triple
  (player_id, season, category).
"""
import json
from .database import db

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

FORMATION_KEYS = ['pp1', 'pp2', 'bp1', 'bp2', '6vs5', 'stress_line']

_STAT_COLS = [
    'plusminus', 'goals', 'assists', 'unforced_errors',
    'shots_on_goal', 'penalties_taken', 'penalties_drawn',
    'saves', 'goals_conceded', 'goalie_plusminus',
    'game_scores', 'goalie_game_scores',
    'opponent_goalie_saves', 'opponent_goalie_goals_conceded',
    'block_shots', 'stolen_balls',
]


# ──────────────────────────────────────────────────────────────────────────────
# Game model
# ──────────────────────────────────────────────────────────────────────────────

class GameRecord(db.Model):
    __tablename__ = 'games'

    # ── Scalar metadata ────────────────────────────────────────────────────
    id = db.Column(db.Integer, primary_key=True)
    season = db.Column(db.Text, default='', nullable=False)
    team = db.Column(db.Text, default='', nullable=False)
    home_team = db.Column(db.Text, default='', nullable=False)
    away_team = db.Column(db.Text, default='', nullable=False)
    date = db.Column(db.Text, default='', nullable=False)
    referee1 = db.Column(db.Text, default='', nullable=False)
    referee2 = db.Column(db.Text, default='', nullable=False)
    current_period = db.Column(db.Text, default='1', nullable=False)
    opponent_goalie_enabled = db.Column(db.Integer, default=0, nullable=False)
    exclude_from_stats = db.Column(db.Integer, default=0, nullable=False)

    # ── Structural JSON columns ────────────────────────────────────────────
    lines = db.Column(db.Text, default='[]', nullable=False)
    goalies = db.Column(db.Text, default='[]', nullable=False)
    result = db.Column(db.Text, default='{}', nullable=False)
    formations = db.Column(db.Text, default='{}', nullable=False)

    # ── Per-player stat JSON columns (dict keyed by player name) ──────────
    plusminus = db.Column(db.Text, default='{}', nullable=False)
    goals = db.Column(db.Text, default='{}', nullable=False)
    assists = db.Column(db.Text, default='{}', nullable=False)
    unforced_errors = db.Column(db.Text, default='{}', nullable=False)
    shots_on_goal = db.Column(db.Text, default='{}', nullable=False)
    penalties_taken = db.Column(db.Text, default='{}', nullable=False)
    penalties_drawn = db.Column(db.Text, default='{}', nullable=False)
    saves = db.Column(db.Text, default='{}', nullable=False)
    goals_conceded = db.Column(db.Text, default='{}', nullable=False)
    goalie_plusminus = db.Column(db.Text, default='{}', nullable=False)
    game_scores = db.Column(db.Text, default='{}', nullable=False)
    goalie_game_scores = db.Column(db.Text, default='{}', nullable=False)
    opponent_goalie_saves = db.Column(db.Text, default='{}', nullable=False)
    opponent_goalie_goals_conceded = db.Column(db.Text, default='{}', nullable=False)
    block_shots = db.Column(db.Text, default='{}', nullable=False)
    stolen_balls = db.Column(db.Text, default='{}', nullable=False)

    # ── Catch-all for any non-standard fields ──────────────────────────────
    extra_data = db.Column(db.Text, default='{}', nullable=False)

    def __init__(self, id: int | None = None, **kwargs):
        super().__init__(**kwargs)
        if id is not None:
            self.id = id

    # ── Hydration helpers ─────────────────────────────────────────────────

    def to_dict(self):
        """Return the full legacy game dict that routes/services expect."""
        game = {
            'id': self.id,
            'season': self.season or '',
            'team': self.team or '',
            'home_team': self.home_team or '',
            'away_team': self.away_team or '',
            'date': self.date or '',
            'referee1': self.referee1 or '',
            'referee2': self.referee2 or '',
            'current_period': self.current_period or '1',
            'opponent_goalie_enabled': bool(self.opponent_goalie_enabled),
            'exclude_from_stats': bool(self.exclude_from_stats),
            'lines': json.loads(self.lines or '[]'),
            'goalies': json.loads(self.goalies or '[]'),
            'result': json.loads(self.result or '{}'),
        }
        # Stat dicts
        for col in _STAT_COLS:
            game[col] = json.loads(getattr(self, col) or '{}')
        # Expand formations dict into top-level keys
        formations = json.loads(self.formations or '{}')
        for fk in FORMATION_KEYS:
            game[fk] = formations.get(fk, [])
        # Merge any extra/non-standard fields
        extra = json.loads(self.extra_data or '{}')
        for k, v in extra.items():
            if k not in game:
                game[k] = v
        return game

    def update_from_dict(self, game_dict):
        """Update all columns from a game dict (does NOT commit)."""
        self.season = game_dict.get('season', '') or ''
        self.team = game_dict.get('team', '') or ''
        self.home_team = game_dict.get('home_team', '') or ''
        self.away_team = game_dict.get('away_team', '') or ''
        self.date = game_dict.get('date', '') or ''
        self.referee1 = game_dict.get('referee1', '') or ''
        self.referee2 = game_dict.get('referee2', '') or ''
        self.current_period = game_dict.get('current_period', '1') or '1'
        self.opponent_goalie_enabled = 1 if game_dict.get('opponent_goalie_enabled') else 0
        self.exclude_from_stats = 1 if game_dict.get('exclude_from_stats') else 0
        self.lines = json.dumps(game_dict.get('lines', []))
        self.goalies = json.dumps(game_dict.get('goalies', []))
        self.result = json.dumps(game_dict.get('result', {}))
        self.formations = json.dumps(
            {fk: game_dict.get(fk, []) for fk in FORMATION_KEYS}
        )
        for col in _STAT_COLS:
            setattr(self, col, json.dumps(game_dict.get(col, {})))
        # Collect any remaining non-standard fields into extra_data
        known_keys = {
            'id', 'season', 'team', 'home_team', 'away_team', 'date',
            'referee1', 'referee2', 'current_period', 'opponent_goalie_enabled',
            'exclude_from_stats', 'lines', 'goalies', 'result', 'formations',
        } | set(_STAT_COLS) | set(FORMATION_KEYS)
        extra = {k: v for k, v in game_dict.items() if k not in known_keys}
        self.extra_data = json.dumps(extra)


# ──────────────────────────────────────────────────────────────────────────────
# Roster model
# ──────────────────────────────────────────────────────────────────────────────

class RosterPlayer(db.Model):
    __tablename__ = 'roster_players'

    # Composite PK: IDs are only unique per (season, category) in legacy data
    player_id = db.Column(db.Text, nullable=False)
    season = db.Column(db.Text, nullable=False, default='')
    category = db.Column(db.Text, nullable=False)

    number = db.Column(db.Text, default='', nullable=False)
    surname = db.Column(db.Text, default='', nullable=False)
    name = db.Column(db.Text, default='', nullable=False)
    nickname = db.Column(db.Text, default='', nullable=False)
    position = db.Column(db.Text, default='A', nullable=False)
    tesser = db.Column(db.Text, default='', nullable=False)
    hidden = db.Column(db.Integer, default=0, nullable=False)

    __table_args__ = (
        db.PrimaryKeyConstraint('player_id', 'season', 'category'),
    )

    def __init__(
        self,
        player_id: str = '',
        season: str = '',
        category: str = '',
        number: str = '',
        surname: str = '',
        name: str = '',
        nickname: str = '',
        position: str = 'A',
        tesser: str = '',
        hidden: int = 0,
    ):
        super().__init__()
        self.player_id = player_id
        self.season = season
        self.category = category
        self.number = number
        self.surname = surname
        self.name = name
        self.nickname = nickname
        self.position = position
        self.tesser = tesser
        self.hidden = hidden

    def to_dict(self):
        return {
            'id': self.player_id,
            'number': self.number or '',
            'surname': self.surname or '',
            'name': self.name or '',
            'nickname': self.nickname or '',
            'position': self.position or 'A',
            'tesser': self.tesser or '',
            'hidden': bool(self.hidden),
        }
