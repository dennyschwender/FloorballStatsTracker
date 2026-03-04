"""
Authentication and authorisation helpers.

These functions check the current Flask session / g context to determine
whether the calling user may perform a given action on a given team.

Logic:
- Requests authenticated via PIN (session['is_admin_session']=True) or test
  sessions (authenticated + no user_id) → full admin access everywhere.
- Requests authenticated via username/password → check User.has_role().
- Unauthenticated → deny everything (should not reach here normally).
"""
from flask import session, g
from functools import wraps
from flask import abort


def _is_admin_session() -> bool:
    """Return True for PIN-session or legacy test sessions."""
    # PIN-login sets is_admin_session; test sessions have authenticated but no user_id
    return bool(
        session.get('is_admin_session') or
        (session.get('authenticated') and not session.get('user_id'))
    )


def current_can_view(category: str) -> bool:
    """Return True if the current session may view data for *category*."""
    if not session.get('authenticated'):
        return False
    if _is_admin_session():
        return True
    user = getattr(g, 'current_user', None)
    if user is None:
        return False
    return user.has_role(category, 'viewer')


def current_can_edit(category: str) -> bool:
    """Return True if the current session may edit data for *category*."""
    if not session.get('authenticated'):
        return False
    if _is_admin_session():
        return True
    user = getattr(g, 'current_user', None)
    if user is None:
        return False
    return user.has_role(category, 'editor')


def current_is_admin() -> bool:
    """Return True if the current session has admin privileges."""
    if not session.get('authenticated'):
        return False
    if _is_admin_session():
        return True
    user = getattr(g, 'current_user', None)
    return bool(user and user.is_admin)


def require_edit(game_dict: dict):
    """Abort 403 if the current session cannot edit the given game's team.

    Call this at the top of any game-write route after fetching the game:

        game = find_game_by_id(games, game_id)
        require_edit(game)
    """
    category = game_dict.get('team', '')
    if not current_can_edit(category):
        abort(403)
