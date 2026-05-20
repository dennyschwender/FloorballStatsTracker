import pytest
import json
from app import app as flask_app


def test_last_game_lineup_missing_params(client):
    """Both season and category are required."""
    rv = client.get('/api/last_game_lineup')
    assert rv.status_code == 400
    data = rv.get_json()
    assert 'error' in data

    rv = client.get('/api/last_game_lineup?season=2025-26')
    assert rv.status_code == 400

    rv = client.get('/api/last_game_lineup?category=U21')
    assert rv.status_code == 400


def test_last_game_lineup_no_games(client):
    """Returns found=false when no matching game exists."""
    rv = client.get('/api/last_game_lineup?season=2025-26&category=U21')
    assert rv.status_code == 200
    data = rv.get_json()
    assert data == {'found': False}


def test_last_game_lineup_found(client):
    """Returns lines + goalies from most recent matching game."""
    from services.game_service import save_game

    # Older game — should NOT be returned
    save_game({
        'id': 1001,
        'date': '2026-01-10',
        'season': '2025-26',
        'team': 'U21',
        'home_team': 'Team A',
        'away_team': 'Team B',
        'lines': [['7 - Rossi Marco', '9 - Bianchi Luca']],
        'goalies': ['1 - Verdi Paolo'],
    })

    # Newer game — SHOULD be returned
    save_game({
        'id': 1002,
        'date': '2026-02-15',
        'season': '2025-26',
        'team': 'U21',
        'home_team': 'Team A',
        'away_team': 'Team C',
        'lines': [['7 - Rossi Marco', '10 - Neri Giorgio'], ['9 - Bianchi Luca']],
        'goalies': ['1 - Verdi Paolo'],
    })

    rv = client.get('/api/last_game_lineup?season=2025-26&category=U21')
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['found'] is True
    assert data['date'] == '2026-02-15'
    assert data['lines'] == [['7 - Rossi Marco', '10 - Neri Giorgio'], ['9 - Bianchi Luca']]
    assert data['goalies'] == ['1 - Verdi Paolo']


def test_last_game_lineup_wrong_season(client):
    """Does not return games from a different season."""
    from services.game_service import save_game

    save_game({
        'id': 1003,
        'date': '2026-01-10',
        'season': '2024-25',
        'team': 'U21',
        'home_team': 'A',
        'away_team': 'B',
        'lines': [['7 - Rossi Marco']],
        'goalies': [],
    })

    rv = client.get('/api/last_game_lineup?season=2025-26&category=U21')
    assert rv.status_code == 200
    assert rv.get_json() == {'found': False}


def test_last_game_lineup_wrong_category(client):
    """Does not return games from a different category."""
    from services.game_service import save_game

    save_game({
        'id': 1004,
        'date': '2026-01-10',
        'season': '2025-26',
        'team': 'U18',
        'home_team': 'A',
        'away_team': 'B',
        'lines': [['7 - Rossi Marco']],
        'goalies': [],
    })

    rv = client.get('/api/last_game_lineup?season=2025-26&category=U21')
    assert rv.status_code == 200
    assert rv.get_json() == {'found': False}


def test_last_game_lineup_requires_auth():
    """Unauthenticated request is denied (redirect to login or 401)."""
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False
    with flask_app.test_client() as unauthed:
        with flask_app.app_context():
            rv = unauthed.get(
                '/api/last_game_lineup?season=2025-26&category=U21',
                follow_redirects=False,
            )
            # The app's global before_request hook redirects unauthenticated
            # requests (302). The route-level check would return 401 if reached.
            assert rv.status_code in (401, 302)
