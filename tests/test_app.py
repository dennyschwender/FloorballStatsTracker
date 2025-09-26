import json
from app import GAMES_FILE


def test_home_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Floorball Stats Tracker' in response.data


def test_create_game(client):
    data = {
        'team': 'Test',
        'home_team': 'A',
        'away_team': 'B',
        'date': '2025-09-26',
        'line1': 'P1,P2,P3',
        'line2': '',
        'line3': '',
        'line4': '',
        'goalie1': 'G1',
        'goalie2': ''
    }
    response = client.post('/create_game', data=data, follow_redirects=True)
    assert response.status_code == 200
    games = json.load(open(GAMES_FILE))
    assert any(g['home_team'] == 'A' and g['away_team'] == 'B' for g in games)

# client fixture is provided in tests/conftest.py
