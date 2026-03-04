"""
Authentication and authorisation helpers.

Three-layer security model:
  Public        — routes explicitly listed as allowed; no session required.
  Authenticated — global PIN session or logged-in user account.
  Admin         — admin PIN session or user account with is_admin=True.

Logic:
- Admin-PIN sessions (session['is_admin_session']=True) → full admin access.
- Global-PIN sessions (authenticated, no user_id, is_admin_session=False)
  → full view/edit access but NOT admin access.
- Test sessions (authenticated + no user_id + no is_admin_session)
  → treated same as global-PIN: full view/edit, no admin.
- Username/password sessions → permissions derived from User.has_role().
- Unauthenticated → deny everything (public routes bypass require_login).
"""
from flask import session, g
from functools import wraps
from flask import abort


def _is_admin_session() -> bool:
    """Return True only when the session was explicitly elevated to admin.

    This is set to True only when logging in with the ADMIN_PIN or when
    an admin user logs in via username/password (handled in current_is_admin).
    Global-PIN sessions have is_admin_session=False.
    """
    return bool(session.get('is_admin_session'))


def _is_global_pin_session() -> bool:
    """Return True for global-PIN sessions and test sessions.

    These sessions have authenticated=True but carry no user_id.
    They get full view/edit rights but NOT admin rights.
    """
    return bool(session.get('authenticated') and not session.get('user_id'))


def current_can_view(category: str) -> bool:
    """Return True if the current session may view data for *category*."""
    if not session.get('authenticated'):
        return False
    if _is_admin_session() or _is_global_pin_session():
        return True
    user = getattr(g, 'current_user', None)
    if user is None:
        return False
    return user.has_role(category, 'viewer')


def current_can_edit(category: str) -> bool:
    """Return True if the current session may edit data for *category*."""
    if not session.get('authenticated'):
        return False
    if _is_admin_session() or _is_global_pin_session():
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
