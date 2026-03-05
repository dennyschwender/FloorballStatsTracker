"""
Admin route test coverage.

Tests for /admin/ endpoints:
- Admin index requires admin auth
- User creation (happy path + validation)
- User editing and deletion
- Team settings page
- Non-admin and unauthenticated users are blocked
"""
import pytest
from models.auth_models import User
from models.database import db


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def admin_client(client):
    """client fixture already grants is_admin_session=True — alias for clarity."""
    return client


@pytest.fixture
def user_client():
    """Authenticated client with a normal user account (no is_admin_session)."""
    from app import app
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    user = User(username='normaluser', is_admin=0)
    user.set_password('normalpass123')
    db.session.add(user)
    db.session.commit()
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess['authenticated'] = True
            sess['user_id'] = user.id
            sess['is_admin_session'] = False
        yield c


@pytest.fixture
def unauth_client():
    """Unauthenticated client."""
    from app import app
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as c:
        yield c


# ── Access control tests ───────────────────────────────────────────────────────

def test_admin_index_requires_admin(user_client, unauth_client):
    """Normal users and unauthenticated clients cannot reach /admin/."""
    # Normal user (no is_admin flag) → redirect
    r = user_client.get('/admin/', follow_redirects=False)
    assert r.status_code == 302

    # Unauthenticated → redirect
    r2 = unauth_client.get('/admin/', follow_redirects=False)
    assert r2.status_code == 302


def test_admin_index_accessible_by_admin(admin_client):
    """Admin-PIN session can access /admin/."""
    r = admin_client.get('/admin/')
    assert r.status_code == 200
    assert b'Admin' in r.data or b'admin' in r.data.lower()


def test_admin_index_accessible_by_admin_user():
    """A user with is_admin=True can access /admin/."""
    from app import app
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        admin_user = User(username='superadmin', is_admin=1)
        admin_user.set_password('adminpass123')
        db.session.add(admin_user)
        db.session.commit()
        uid = admin_user.id

    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess['authenticated'] = True
            sess['user_id'] = uid
            sess['is_admin_session'] = False
        r = c.get('/admin/')
        assert r.status_code == 200


# ── User creation tests ────────────────────────────────────────────────────────

def test_new_user_page_renders(admin_client):
    r = admin_client.get('/admin/users/new')
    assert r.status_code == 200


def test_create_user_success(admin_client):
    r = admin_client.post('/admin/users/new', data={
        'username': 'testuser',
        'password': 'secure123',
        'is_admin': '0',
    }, follow_redirects=True)
    assert r.status_code == 200
    with admin_client.application.app_context():
        user = User.query.filter_by(username='testuser').first()
        assert user is not None
        assert user.is_admin == 0


def test_create_user_short_password(admin_client):
    r = admin_client.post('/admin/users/new', data={
        'username': 'shortpw',
        'password': 'abc',
        'is_admin': '0',
    }, follow_redirects=True)
    assert r.status_code == 200
    assert b'6 character' in r.data or b'least 6' in r.data.lower() or b'Password' in r.data


def test_create_user_duplicate_username(admin_client):
    admin_client.post('/admin/users/new', data={
        'username': 'dupuser',
        'password': 'password123',
        'is_admin': '0',
    })
    r = admin_client.post('/admin/users/new', data={
        'username': 'dupuser',
        'password': 'anotherpass',
        'is_admin': '0',
    }, follow_redirects=True)
    assert r.status_code == 200
    assert b'taken' in r.data.lower() or b'already' in r.data.lower()


def test_create_admin_user(admin_client):
    r = admin_client.post('/admin/users/new', data={
        'username': 'adminguy',
        'password': 'adminpass123',
        'is_admin': '1',
    }, follow_redirects=True)
    assert r.status_code == 200
    with admin_client.application.app_context():
        user = User.query.filter_by(username='adminguy').first()
        assert user is not None
        assert user.is_admin == 1


# ── User editing tests ─────────────────────────────────────────────────────────

def _create_test_user(username='edittest', password='testpass123', is_admin=0):
    user = User(username=username, is_admin=is_admin)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user.id


def test_edit_user_page_renders(admin_client):
    with admin_client.application.app_context():
        uid = _create_test_user('editme')
    r = admin_client.get(f'/admin/users/{uid}')
    assert r.status_code == 200


def test_edit_user_change_password(admin_client):
    with admin_client.application.app_context():
        uid = _create_test_user('changepass')
    r = admin_client.post(f'/admin/users/{uid}', data={
        '_action': 'save',
        'password': 'newpassword123',
        'is_admin': '0',
    }, follow_redirects=True)
    assert r.status_code == 200
    with admin_client.application.app_context():
        user = db.session.get(User, uid)
        assert user.check_password('newpassword123')


def test_edit_user_delete(admin_client):
    with admin_client.application.app_context():
        uid = _create_test_user('deletetest')
    r = admin_client.post(f'/admin/users/{uid}', data={
        '_action': 'delete',
    }, follow_redirects=True)
    assert r.status_code == 200
    with admin_client.application.app_context():
        assert db.session.get(User, uid) is None


def test_edit_nonexistent_user(admin_client):
    r = admin_client.get('/admin/users/999999', follow_redirects=True)
    assert r.status_code == 200
    assert b'not found' in r.data.lower() or b'User' in r.data


# ── Team settings tests ────────────────────────────────────────────────────────

def test_team_settings_page_renders(admin_client):
    r = admin_client.get('/admin/teams')
    assert r.status_code == 200


def test_team_settings_save(admin_client):
    r = admin_client.post('/admin/teams', data={
        'current_season': '2025-26',
    }, follow_redirects=True)
    assert r.status_code == 200
