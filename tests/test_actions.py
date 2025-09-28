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


@pytest.fixture(autouse=True)
def preserve_games_file(tmp_path):
    """Backup the games file before each test and restore it after."""
    orig = None
    if os.path.exists(GAMES_FILE):
        with open(GAMES_FILE, 'r') as f:
            orig = f.read()
    yield
    # restore
    if orig is None:
        try:
            os.remove(GAMES_FILE)
        except OSError:
            pass
    else:
        with open(GAMES_FILE, 'w') as f:
            f.write(orig)


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
    _write_games(games)

    # set some stats
    g = _read_games()[0]
    g.setdefault('goals', {})['P1'] = 2
    g.setdefault('saves', {})['G1'] = 3
    games[0] = g
    _write_games(games)

    rv = client.get('/reset_game/0', follow_redirects=True)
    assert rv.status_code == 200
    g = _read_games()[0]
    assert g['goals']['P1'] == 0
    assert g['saves']['G1'] == 0

    # delete second game (index 1)
    rv = client.post('/delete_game/1', follow_redirects=True)
    assert rv.status_code == 200
    gs = _read_games()
    assert len(gs) == 1


def test_set_period_and_modify_game(client):
    games = [make_sample_game()]
    _write_games(games)

    rv = client.get('/set_period/0/2', follow_redirects=True)
    assert rv.status_code == 200
    g = _read_games()[0]
    assert g['current_period'] == '2'

    # modify game POST
    data = {
        'team': 'NewTeam',
        'home_team': 'H2',
        'away_team': 'A2',
        'date': '2025-09-10',
        'line1': 'X1,X2',
        'line2': '',
        'line3': '',
        'line4': '',
        'goalie1': 'G2',
        'goalie2': '',
        'enable_opponent_goalie': 'on'
    }
    rv = client.post('/modify_game/0', data=data, follow_redirects=True)
    assert rv.status_code == 200
    g = _read_games()[0]
    assert g['team'] == 'NewTeam'
    assert g['home_team'] == 'H2'
    assert g['goalies'] == ['G2']
    assert g['opponent_goalie_enabled'] is True


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