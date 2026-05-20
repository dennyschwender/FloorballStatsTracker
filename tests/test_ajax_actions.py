"""Tests for AJAX (JSON) responses from action routes."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from test_actions import _write_games, _read_games, make_sample_game  # noqa: E402

AJAX = {'X-Requested-With': 'XMLHttpRequest'}


def test_player_action_returns_json_on_ajax(client):
    _write_games([make_sample_game()])

    rv = client.get('/action/0/P1?action=goal', headers=AJAX)

    assert rv.status_code == 200
    assert rv.is_json
    data = rv.get_json()
    assert data['ok'] is True
    assert 'stats' in data
    assert 'result' in data
    assert data['stats']['goals'].get('P1', 0) == 1


def test_player_action_no_ajax_still_redirects(client):
    _write_games([make_sample_game()])

    rv = client.get('/action/0/P1?action=goal')

    assert rv.status_code == 302


def test_ajax_response_contains_required_stat_fields(client):
    _write_games([make_sample_game()])

    rv = client.get('/action/0/P1?action=assist', headers=AJAX)
    data = rv.get_json()

    for field in ('goals', 'assists', 'plusminus', 'shots_on_goal', 'game_scores'):
        assert field in data['stats'], f"Missing stat field: {field}"
    assert 'result' in data


def test_goalie_action_returns_json_on_ajax(client):
    _write_games([make_sample_game()])

    rv = client.get('/action_goalie/0/G1?action=save', headers=AJAX)

    assert rv.status_code == 200
    data = rv.get_json()
    assert data['ok'] is True
    assert data['stats']['saves'].get('G1', 0) == 1


def test_line_action_returns_json_on_ajax(client):
    _write_games([make_sample_game()])

    rv = client.get('/action_line/0/0?action=plus', headers=AJAX)

    assert rv.status_code == 200
    data = rv.get_json()
    assert data['ok'] is True
