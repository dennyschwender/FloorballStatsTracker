"""Tests for /undo/<game_id> endpoint."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from test_actions import _write_games, _read_games, make_sample_game  # noqa: E402
from services import undo_store

AJAX = {'X-Requested-With': 'XMLHttpRequest'}


def test_undo_reverses_last_goal(client):
    _write_games([make_sample_game()])
    undo_store.clear(0)

    client.get('/action/0/P1?action=goal', headers=AJAX)
    assert _read_games()[0]['goals'].get('P1', 0) == 1

    rv = client.get('/undo/0', headers=AJAX)
    assert rv.status_code == 200
    assert rv.get_json()['ok'] is True
    assert _read_games()[0]['goals'].get('P1', 0) == 0


def test_undo_returns_full_stats(client):
    _write_games([make_sample_game()])
    undo_store.clear(0)

    client.get('/action/0/P1?action=assist', headers=AJAX)
    rv = client.get('/undo/0', headers=AJAX)
    data = rv.get_json()

    assert 'stats' in data
    assert 'result' in data
    assert 'goals' in data['stats']


def test_undo_nothing_returns_error(client):
    _write_games([make_sample_game()])
    undo_store.clear(0)

    rv = client.get('/undo/0', headers=AJAX)
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['ok'] is False
    assert data['error'] == 'nothing_to_undo'


def test_undo_only_one_level(client):
    _write_games([make_sample_game()])
    undo_store.clear(0)

    client.get('/action/0/P1?action=goal', headers=AJAX)
    client.get('/action/0/P1?action=goal', headers=AJAX)  # second replaces first snapshot

    # First undo: back to 1 goal
    client.get('/undo/0', headers=AJAX)
    assert _read_games()[0]['goals'].get('P1', 0) == 1

    # Second undo: nothing stored
    rv = client.get('/undo/0', headers=AJAX)
    assert rv.get_json()['error'] == 'nothing_to_undo'
