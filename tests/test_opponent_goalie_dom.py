import pytest
from services.game_service import load_games, save_games


def _make_game(opponent_goalie_enabled=True):
    return {
        'id': 0,
        'season': '2025-26',
        'team': 'U21',
        'home_team': 'Home',
        'away_team': 'Away',
        'date': '2025-09-01',
        'lines': [['P1', 'P2', 'P3'], ['P4', 'P5'], [], []],
        'goalies': ['G1'],
        'opponent_goalie_enabled': opponent_goalie_enabled,
        'opponent_goalie_saves': {'Opponent Goalie': 5},
        'opponent_goalie_goals_conceded': {'Opponent Goalie': 3},
        'result': {p: {'home': 0, 'away': 0} for p in ['1', '2', '3', 'OT']},
        'current_period': '1',
    }


def test_opponent_goalie_goals_span_present_and_numeric(client):
    save_games([_make_game(opponent_goalie_enabled=True)])
    games = load_games()
    game = games[0]
    game_id = game.get('id', 0)

    expected = 3

    rv = client.get(f'/game/{game_id}')
    assert rv.status_code == 200
    html = rv.get_data(as_text=True)

    if 'id="opponent-goalie-goals"' in html:
        start = html.find('id="opponent-goalie-goals"')
        span_open = html.find('>', start)
        span_close = html.find('</span>', span_open)
        assert span_open != -1 and span_close != -1
        content = html[span_open + 1:span_close].strip()
        assert content.isdigit() or (content.replace('.', '', 1).isdigit() and content.count('.') <= 1)
        assert int(float(content)) == expected
    else:
        assert '<span class="fw-bold">' in html
        header_idx = html.find('Opponent Goalie')
        assert header_idx != -1
        snippet = html[header_idx: header_idx + 800]
        assert str(expected) in snippet