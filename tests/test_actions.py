import json
import copy
import os

import pytest

from app import GAMES_FILE


def _read_games():
    try:
        with open(GAMES_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return []


def _write_games(games):
    with open(GAMES_FILE, 'w') as f:
        json.dump(games, f, indent=2)


# games file preservation handled in tests/conftest.py


def make_sample_game(opponent_goalie_enabled=False):
    return {
        'id': 0,
        'team': 'T1',
        'home_team': 'Home',
        'away_team': 'Away',
        'date': '2025-09-01',
        'lines': [['P1', 'P2', 'P3'], ['P4', 'P5'], [], []],
        'goalies': ['G1'],
        'opponent_goalie_enabled': opponent_goalie_enabled,
        'result': {p: {'home': 0, 'away': 0} for p in ['1', '2', '3', 'OT']},
        'current_period': '1',
    }


def test_player_actions_and_goal_update(client):
    games = [make_sample_game(opponent_goalie_enabled=True)]
    _write_games(games)

    # plus
    rv = client.get('/action/0/P1?action=plus', follow_redirects=True)
    assert rv.status_code == 200
    g = _read_games()[0]
    assert g['plusminus']['P1'] == 1

    # goal increments player's goals and period home score and opponent goalie conceded
    rv = client.get('/action/0/P1?action=goal', follow_redirects=True)
    assert rv.status_code == 200
    g = _read_games()[0]
    assert g['goals']['P1'] == 1
    assert g['result'][g['current_period']]['home'] == 1
    # opponent goalie tally
    assert g['opponent_goalie_goals_conceded']['Opponent Goalie'] == 1

    # goal_minus decrements when >0
    rv = client.get('/action/0/P1?action=goal_minus', follow_redirects=True)
    assert rv.status_code == 200
    g = _read_games()[0]
    assert g['goals']['P1'] == 0

    # assist
    rv = client.get('/action/0/P1?action=assist', follow_redirects=True)
    assert rv.status_code == 200
    g = _read_games()[0]
    assert g['assists']['P1'] == 1


def test_line_action_goal_and_plus(client):
    games = [make_sample_game(opponent_goalie_enabled=True)]
    _write_games(games)

    # line goal should increment each player goals and period home once
    rv = client.get('/action_line/0/0?action=goal', follow_redirects=True)
    assert rv.status_code == 200
    g = _read_games()[0]
    # each player in line 0 should have 1 goal
    for p in g['lines'][0]:
        assert g['goals'][p] == 1
    assert g['result'][g['current_period']]['home'] == 1
    # opponent goalie conceded incremented once
    assert g['opponent_goalie_goals_conceded']['Opponent Goalie'] == 1

    # line plus should increment plusminus for each player
    rv = client.get('/action_line/0/0?action=plus', follow_redirects=True)
    assert rv.status_code == 200
    g = _read_games()[0]
    for p in g['lines'][0]:
        assert g['plusminus'][p] == 1


def test_goalie_and_opponent_goalie_actions(client):
    games = [make_sample_game(opponent_goalie_enabled=False)]
    _write_games(games)

    # goalie save
    rv = client.get('/action_goalie/0/G1?action=save', follow_redirects=True)
    assert rv.status_code == 200
    g = _read_games()[0]
    assert g['saves']['G1'] == 1

    # goalie goal conceded increments away team score
    rv = client.get('/action_goalie/0/G1?action=goal_conceded', follow_redirects=True)
    assert rv.status_code == 200
    g = _read_games()[0]
    assert g['goals_conceded']['G1'] == 1
    assert g['result'][g['current_period']]['away'] == 1

    # opponent goalie actions (home team goals)
    rv = client.get('/action_opponent_goalie/0?action=save', follow_redirects=True)
    assert rv.status_code == 200
    g = _read_games()[0]
    assert g['opponent_goalie_saves']['Opponent Goalie'] == 1

    rv = client.get('/action_opponent_goalie/0?action=goal_conceded', follow_redirects=True)
    assert rv.status_code == 200
    g = _read_games()[0]
    assert g['opponent_goalie_goals_conceded']['Opponent Goalie'] == 1
    # home score incremented
    assert g['result'][g['current_period']]['home'] == 1


def test_reset_and_delete_game(client):
    games = [make_sample_game(opponent_goalie_enabled=True), make_sample_game()]
    # Ensure unique IDs
    from app import ensure_game_ids, save_games
    ensure_game_ids(games)
    _write_games(games)

    # Get actual game IDs
    saved_games = _read_games()
    game_id_1 = saved_games[0]['id']
    game_id_2 = saved_games[1]['id']

    # set some stats
    g = saved_games[0]
    g.setdefault('goals', {})['P1'] = 2
    g.setdefault('saves', {})['G1'] = 3
    saved_games[0] = g
    _write_games(saved_games)

    rv = client.get(f'/reset_game/{game_id_1}', follow_redirects=True)
    assert rv.status_code == 200
    g = _read_games()[0]
    assert g['goals']['P1'] == 0
    assert g['saves']['G1'] == 0

    # delete second game using its ID
    rv = client.post(f'/delete_game/{game_id_2}', follow_redirects=True)
    assert rv.status_code == 200
    gs = _read_games()
    assert len(gs) == 1


def test_set_period_and_modify_game(client):
    # Create a roster for the teams
    import os
    roster_data = [
        {"id": "1", "number": "10", "surname": "Player", "name": "One", "position": "A", "tesser": "U21", "nickname": "P1"},
        {"id": "2", "number": "20", "surname": "Player", "name": "Two", "position": "A", "tesser": "U21", "nickname": "P2"},
        {"id": "3", "number": "1", "surname": "Goalie", "name": "Two", "position": "P", "tesser": "U21", "nickname": "G2"}
    ]
    from app import ROSTERS_DIR
    roster_path = os.path.join(ROSTERS_DIR, 'roster_NewTeam.json')
    with open(roster_path, 'w') as f:
        json.dump(roster_data, f)
    
    games = [make_sample_game()]
    _write_games(games)

    rv = client.get('/set_period/0/2', follow_redirects=True)
    assert rv.status_code == 200
    g = _read_games()[0]
    assert g['current_period'] == '2'

    # modify game POST using roster-based format
    data = {
        'team': 'NewTeam',
        'home_team': 'H2',
        'away_team': 'A2',
        'date': '2025-09-10',
        'l1_1': '1',  # Player One at position 1
        'l1_2': '2',  # Player Two at position 2
        'goalie1': '3',  # Goalie Two
        'goalie2': '',
        'enable_opponent_goalie': 'on'
    }
    rv = client.post('/modify_game/0', data=data, follow_redirects=True)
    assert rv.status_code == 200
    g = _read_games()[0]
    assert g['team'] == 'NewTeam'
    assert g['home_team'] == 'H2'
    assert len(g['goalies']) == 1
    assert '1 - Goalie Two' in g['goalies'][0]
    assert g['opponent_goalie_enabled'] is True
    
    # Cleanup
    if os.path.exists(roster_path):
        os.remove(roster_path)


def test_stats_page_contains_players_and_goalies(client):
    games = [make_sample_game(opponent_goalie_enabled=True)]
    # populate some stats
    games[0]['goals'] = {'P1': 2}
    games[0]['saves'] = {'G1': 3}
    _write_games(games)

    rv = client.get('/stats')
    assert rv.status_code == 200
    data = rv.data.decode('utf-8')
    assert 'P1' in data
    assert 'G1' in data


def test_invalid_game_and_period(client):
    # no games -> invalid game id
    with open(GAMES_FILE, 'w') as f:
        f.write('[]')
    rv = client.get('/game/99')
    assert rv.status_code == 404

    rv = client.get('/action/99/P1?action=plus')
    assert rv.status_code == 404

    # create a game and request invalid period
    games = [make_sample_game()]
    _write_games(games)
    rv = client.get('/set_period/0/FOO')
    assert rv.status_code == 400


def test_unauthenticated_redirect(client):
    # Clear authentication from session via a fresh test client
    from app import app as _app
    _app.config['TESTING'] = True
    with _app.test_client() as anon:
        # no authenticated session -> index shows pin page
        rv = anon.get('/')
        assert rv.status_code == 200
        assert b'PIN' in rv.data or b'Enter Access PIN' in rv.data
        # protected route should redirect to index
        rv2 = anon.get('/stats', follow_redirects=False)
        assert rv2.status_code in (302, 301)