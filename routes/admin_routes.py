"""
Admin routes: user management, team permissions, team settings.
All routes require is_admin_session (admin PIN) or a user account with is_admin=True.
Global-PIN sessions do NOT have access to admin routes.
"""
from flask import (
    Blueprint, request, render_template, redirect, url_for,
    session, flash, g,
)
from models.database import db
from models.auth_models import User, TeamPermission
from models.team_settings import TeamSettings, DEFAULTS, get_all_settings, set_setting, get_current_season, set_current_season
from models.roster import get_all_categories_with_rosters


def _roster_categories() -> list[str]:
    """Return the distinct team/category names that have at least one roster file.
    Falls back to the config CATEGORIES list if no rosters exist yet.
    """
    from config import CATEGORIES as _fallback
    cats = get_all_categories_with_rosters()
    return cats if cats else _fallback

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# ── Auth guard ─────────────────────────────────────────────────────────────────

def _require_admin():
    """Return a redirect response if the caller is not an admin, else None."""
    if not session.get('authenticated'):
        return redirect(url_for('game.index'))
    # Admin-PIN sessions (is_admin_session=True) have admin access
    if session.get('is_admin_session'):
        return None
    user_id = session.get('user_id')
    if user_id:
        user = db.session.get(User, user_id)
        if user and user.is_admin:
            return None
    return redirect(url_for('game.index'))


# ── User list ──────────────────────────────────────────────────────────────────

@admin_bp.route('/')
def index():
    guard = _require_admin()
    if guard:
        return guard
    users = User.query.order_by(User.username).all()
    return render_template('admin/index.html', users=users)


# ── Create user ────────────────────────────────────────────────────────────────

@admin_bp.route('/users/new', methods=['GET', 'POST'])
def new_user():
    guard = _require_admin()
    if guard:
        return guard

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        is_admin = request.form.get('is_admin') == '1'

        if not username or not password:
            flash('Username and password are required.', 'danger')
        elif len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
        elif User.query.filter_by(username=username).first():
            flash('Username already taken.', 'danger')
        else:
            user = User(username=username, is_admin=1 if is_admin else 0)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash(f'User "{username}" created.', 'success')
            return redirect(url_for('admin.edit_user', user_id=user.id))

    return render_template('admin/user_form.html', user=None, categories=_roster_categories())


# ── Edit / delete user ─────────────────────────────────────────────────────────

@admin_bp.route('/users/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    guard = _require_admin()
    if guard:
        return guard
    user = db.session.get(User, user_id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin.index'))

    if request.method == 'POST':
        action = request.form.get('_action', 'save')
        if action == 'delete':
            db.session.delete(user)
            db.session.commit()
            flash(f'User "{user.username}" deleted.', 'success')
            return redirect(url_for('admin.index'))

        new_password = request.form.get('password', '').strip()
        is_admin = request.form.get('is_admin') == '1'
        user.is_admin = 1 if is_admin else 0
        if new_password:
            if len(new_password) < 6:
                flash('Password must be at least 6 characters.', 'danger')
                return render_template('admin/user_form.html', user=user, categories=_roster_categories())
            user.set_password(new_password)

        # Rebuild permissions
        TeamPermission.query.filter_by(user_id=user.id).delete()
        for cat in _roster_categories() + ['*']:
            role = request.form.get(f'perm_{cat}', '')
            if role in ('viewer', 'editor', 'admin'):
                perm = TeamPermission(user_id=user.id, category=cat, role=role)
                db.session.add(perm)

        db.session.commit()
        flash('Changes saved.', 'success')
        return redirect(url_for('admin.edit_user', user_id=user.id))

    return render_template('admin/user_form.html', user=user, categories=_roster_categories())


# ── Team settings ──────────────────────────────────────────────────────────────

@admin_bp.route('/teams', methods=['GET', 'POST'])
def team_settings():
    guard = _require_admin()
    if guard:
        return guard

    if request.method == 'POST':
        for cat in _roster_categories():
            for key in DEFAULTS:
                val = '1' if request.form.get(f'{cat}_{key}') == '1' else '0'
                set_setting(cat, key, val)
        # Save current season global setting
        current_season = request.form.get('current_season', '')
        set_current_season(current_season)
        db.session.commit()
        flash('Team settings saved.', 'success')
        return redirect(url_for('admin.team_settings'))

    # Build settings dict per category
    cats = _roster_categories()
    settings_by_cat = {cat: get_all_settings(cat) for cat in cats}
    from models.roster import get_all_seasons
    return render_template(
        'admin/team_settings.html',
        categories=cats,
        settings_by_cat=settings_by_cat,
        setting_keys=list(DEFAULTS.keys()),
        all_seasons=get_all_seasons(),
        current_season=get_current_season(),
    )
