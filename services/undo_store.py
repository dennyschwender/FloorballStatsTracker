"""In-memory single-level undo stack, one slot per game.

Thread-safe via a module-level lock. Lost on server restart —
acceptable: undo is only meaningful during live in-game tracking.
Snapshots expire after TTL_SECONDS to avoid stale undos.
"""
import threading
import time
from copy import deepcopy

_lock = threading.Lock()
_stack: dict[int, dict] = {}
_timestamps: dict[int, float] = {}

TTL_SECONDS = 60

_SNAPSHOT_FIELDS = [
    'goals', 'assists', 'plusminus', 'shots_on_goal', 'unforced_errors',
    'penalties_taken', 'penalties_drawn', 'block_shots', 'stolen_balls',
    'saves', 'goals_conceded', 'game_scores', 'goalie_game_scores',
    'opponent_goalie_saves', 'opponent_goalie_goals_conceded', 'result',
    'current_period',
]


def push(game_id: int, game: dict) -> None:
    """Snapshot current stat state before a mutation."""
    snapshot = {field: deepcopy(game.get(field, {})) for field in _SNAPSHOT_FIELDS}
    with _lock:
        _stack[game_id] = snapshot
        _timestamps[game_id] = time.monotonic()


def pop(game_id: int) -> dict | None:
    """Return and remove the snapshot, or None if nothing stored or expired."""
    with _lock:
        ts = _timestamps.get(game_id)
        if ts is None or (time.monotonic() - ts) > TTL_SECONDS:
            _stack.pop(game_id, None)
            _timestamps.pop(game_id, None)
            return None
        _timestamps.pop(game_id, None)
        return _stack.pop(game_id, None)


def clear(game_id: int) -> None:
    """Discard any stored snapshot for game_id."""
    with _lock:
        _stack.pop(game_id, None)
        _timestamps.pop(game_id, None)
