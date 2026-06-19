import pytest
from services.game_service import load_games, save_games


def _make_game():
    return {
        'id': 0,
        'season': '2025-26',
        'team': 'U21',
        'home_team': 'Home',
        'away_team': 'Away',
        'date': '2025-09-01',
        'lines': [['P1', 'P2', 'P3'], ['P4', 'P5'], [], []],
        'goalies': ['G1'],
        'opponent_goalie_enabled': True,
        'opponent_goalie_saves': {'Opponent Goalie': 5},
        'opponent_goalie_goals_conceded': {'Opponent Goalie': 3},
        'result': {p: {'home': 0, 'away': 0} for p in ['1', '2', '3', 'OT']},
        'current_period': '1',
    }


def test_opponent_goalie_goals_conceded_render(client):
    import re
    save_games([_make_game()])
    games = load_games()
    game_id = games[0].get('id', 0)

    rv = client.get(f'/game/{game_id}')
    assert rv.status_code == 200
    html = rv.data.decode('utf-8')
    start = html.find('<h3 class="mb-3">Opponent Goalie')
    assert start != -1
    snippet = html[start:start + 800]
    assert re.search(r'Goals Conceded', snippet)
    assert re.search(r'\b\d+\b', snippet)


def test_opponent_goalie_render_in_edit_mode():
    import re
    from app import app
    save_games([_make_game()])
    games = load_games()
    game_id = games[0].get('id', 0)

    with app.test_client() as c:
        with c.session_transaction() as s:
            s['authenticated'] = True
        rv = c.get(f'/game/{game_id}?edit=1')
        assert rv.status_code == 200
        html = rv.data.decode('utf-8')
        start = html.find('<h3 class="mb-3">Opponent Goalie')
        assert start != -1
        snippet = html[start:start + 800]
        assert re.search(r'Goals Conceded', snippet)
        assert re.search(r'\b\d+\b', snippet)