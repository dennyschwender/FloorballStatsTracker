# tests/test_event_endpoint.py
import json
import pytest
from tests.test_actions import _write_games, _read_games, make_sample_game

AJAX = {'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/json'}


def _post(client, game_id, payload):
    return client.post(
        f'/event/{game_id}',
        data=json.dumps(payload),
        headers=AJAX,
        content_type='application/json',
    )


# ── goal / our team ───────────────────────────────────────────────────────────

def test_event_goal_ours_increments_scorer(client):
    _write_games([make_sample_game()])
    rv = _post(client, 0, {'type': 'goal', 'team': 'ours', 'scorer': 'P1',
                            'plusminus_players': ['P1']})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['ok'] is True
    assert data['stats']['goals'].get('P1', 0) == 1


def test_event_goal_ours_increments_assist(client):
    _write_games([make_sample_game()])
    rv = _post(client, 0, {'type': 'goal', 'team': 'ours', 'scorer': 'P1',
                            'assist': 'P2', 'plusminus_players': []})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['stats']['assists'].get('P2', 0) == 1


def test_event_goal_ours_updates_plusminus(client):
    _write_games([make_sample_game()])
    rv = _post(client, 0, {'type': 'goal', 'team': 'ours', 'scorer': 'P1',
                            'plusminus_players': ['P1', 'P2', 'P3']})
    data = rv.get_json()
    assert data['stats']['plusminus'].get('P1', 0) == 1
    assert data['stats']['plusminus'].get('P2', 0) == 1
    assert data['stats']['plusminus'].get('P3', 0) == 1


def test_event_goal_ours_updates_home_result(client):
    _write_games([make_sample_game()])
    rv = _post(client, 0, {'type': 'goal', 'team': 'ours', 'scorer': 'P1',
                            'plusminus_players': []})
    data = rv.get_json()
    assert data['result']['1']['home'] == 1


def test_event_goal_ours_increments_opponent_goalie_conceded_when_enabled(client):
    _write_games([make_sample_game(opponent_goalie_enabled=True)])
    rv = _post(client, 0, {'type': 'goal', 'team': 'ours', 'scorer': 'P1',
                            'plusminus_players': []})
    data = rv.get_json()
    assert data['stats']['opponent_goalie_goals_conceded'].get('Opponent Goalie', 0) == 1


# ── goal / opponent ───────────────────────────────────────────────────────────

def test_event_goal_opponent_decrements_plusminus(client):
    _write_games([make_sample_game()])
    rv = _post(client, 0, {'type': 'goal', 'team': 'opponent',
                            'plusminus_players': ['P1', 'P2']})
    data = rv.get_json()
    assert data['stats']['plusminus'].get('P1', 0) == -1
    assert data['stats']['plusminus'].get('P2', 0) == -1


def test_event_goal_opponent_increments_goalie_conceded(client):
    _write_games([make_sample_game()])
    rv = _post(client, 0, {'type': 'goal', 'team': 'opponent',
                            'plusminus_players': [], 'goalie': 'G1'})
    data = rv.get_json()
    assert data['stats']['goals_conceded'].get('G1', 0) == 1
    assert data['result']['1']['away'] == 1


def test_event_goal_opponent_no_goalie_still_ok(client):
    _write_games([make_sample_game()])
    rv = _post(client, 0, {'type': 'goal', 'team': 'opponent',
                            'plusminus_players': []})
    assert rv.status_code == 200


# ── penalty ───────────────────────────────────────────────────────────────────

def test_event_penalty_taken(client):
    _write_games([make_sample_game()])
    rv = _post(client, 0, {'type': 'penalty', 'subtype': 'taken', 'player': 'P1'})
    data = rv.get_json()
    assert data['stats']['penalties_taken'].get('P1', 0) == 1


def test_event_penalty_drawn(client):
    _write_games([make_sample_game()])
    rv = _post(client, 0, {'type': 'penalty', 'subtype': 'drawn', 'player': 'P2'})
    data = rv.get_json()
    assert data['stats']['penalties_drawn'].get('P2', 0) == 1


def test_event_penalty_missing_player_returns_400(client):
    _write_games([make_sample_game()])
    rv = _post(client, 0, {'type': 'penalty', 'subtype': 'taken'})
    assert rv.status_code == 400


# ── save ─────────────────────────────────────────────────────────────────────

def test_event_save_our_goalie(client):
    _write_games([make_sample_game()])
    rv = _post(client, 0, {'type': 'save', 'player': 'G1'})
    data = rv.get_json()
    assert data['stats']['saves'].get('G1', 0) == 1


def test_event_save_opponent_goalie(client):
    _write_games([make_sample_game(opponent_goalie_enabled=True)])
    rv = _post(client, 0, {'type': 'save', 'player': 'Opponent Goalie'})
    data = rv.get_json()
    assert data['stats']['opponent_goalie_saves'].get('Opponent Goalie', 0) == 1


# ── shot on goal ─────────────────────────────────────────────────────────────

def test_event_shot_on_goal(client):
    _write_games([make_sample_game()])
    rv = _post(client, 0, {'type': 'shot_on_goal', 'player': 'P3'})
    data = rv.get_json()
    assert data['stats']['shots_on_goal'].get('P3', 0) == 1


# ── period change ─────────────────────────────────────────────────────────────

def test_event_period_change_advances_period(client):
    _write_games([make_sample_game()])  # current_period = '1'
    rv = _post(client, 0, {'type': 'period_change'})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['current_period'] == '2'
    g = _read_games()[0]
    assert g['current_period'] == '2'


def test_event_period_change_does_not_exceed_OT(client):
    game = make_sample_game()
    game['current_period'] = 'OT'
    _write_games([game])
    rv = _post(client, 0, {'type': 'period_change'})
    data = rv.get_json()
    assert data['current_period'] == 'OT'


# ── error cases ───────────────────────────────────────────────────────────────

def test_event_unknown_type_returns_400(client):
    _write_games([make_sample_game()])
    rv = _post(client, 0, {'type': 'flying_saucer'})
    assert rv.status_code == 400


def test_event_game_not_found_returns_404(client):
    _write_games([])
    rv = _post(client, 999, {'type': 'period_change'})
    assert rv.status_code == 404


def test_event_response_contains_stats_and_result(client):
    _write_games([make_sample_game()])
    rv = _post(client, 0, {'type': 'shot_on_goal', 'player': 'P1'})
    data = rv.get_json()
    assert 'stats' in data
    assert 'result' in data
    assert 'ok' in data
