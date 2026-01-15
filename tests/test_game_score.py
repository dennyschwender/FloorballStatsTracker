"""Tests for Game Score calculations and new stat tracking (SOG, PT, PD)"""
import json
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


def make_sample_game():
    return {
        'id': 1,
        'season': '2024-25',
        'team': 'Test Team',
        'home_team': 'Home',
        'away_team': 'Away',
        'date': '2024-01-15',
        'lines': [['Player1', 'Player2'], ['Player3']],
        'goalies': ['Goalie1'],
        'result': {p: {'home': 0, 'away': 0} for p in ['1', '2', '3', 'OT']},
        'current_period': '1',
    }


def test_shot_on_goal_action(client):
    """Test SOG tracking increment/decrement"""
    games = [make_sample_game()]
    _write_games(games)
    
    # Add SOG
    rv = client.get('/action/1/Player1?action=shot_on_goal', follow_redirects=True)
    assert rv.status_code == 200
    g = _read_games()[0]
    assert g['shots_on_goal']['Player1'] == 1
    
    # Add more SOG
    client.get('/action/1/Player1?action=shot_on_goal')
    g = _read_games()[0]
    assert g['shots_on_goal']['Player1'] == 2
    
    # Decrement SOG
    rv = client.get('/action/1/Player1?action=shot_on_goal_minus', follow_redirects=True)
    assert rv.status_code == 200
    g = _read_games()[0]
    assert g['shots_on_goal']['Player1'] == 1
    
    # Should not go below zero
    client.get('/action/1/Player1?action=shot_on_goal_minus')
    client.get('/action/1/Player1?action=shot_on_goal_minus')
    g = _read_games()[0]
    assert g['shots_on_goal']['Player1'] == 0


def test_penalty_taken_action(client):
    """Test PT tracking increment/decrement"""
    games = [make_sample_game()]
    _write_games(games)
    
    # Add PT
    rv = client.get('/action/1/Player2?action=penalty_taken', follow_redirects=True)
    assert rv.status_code == 200
    g = _read_games()[0]
    assert g['penalties_taken']['Player2'] == 1
    
    # Add more PT
    client.get('/action/1/Player2?action=penalty_taken')
    g = _read_games()[0]
    assert g['penalties_taken']['Player2'] == 2
    
    # Decrement PT
    rv = client.get('/action/1/Player2?action=penalty_taken_minus', follow_redirects=True)
    assert rv.status_code == 200
    g = _read_games()[0]
    assert g['penalties_taken']['Player2'] == 1
    
    # Should not go below zero
    client.get('/action/1/Player2?action=penalty_taken_minus')
    client.get('/action/1/Player2?action=penalty_taken_minus')
    g = _read_games()[0]
    assert g['penalties_taken']['Player2'] == 0


def test_penalty_drawn_action(client):
    """Test PD tracking increment/decrement"""
    games = [make_sample_game()]
    _write_games(games)
    
    # Add PD
    rv = client.get('/action/1/Player3?action=penalty_drawn', follow_redirects=True)
    assert rv.status_code == 200
    g = _read_games()[0]
    assert g['penalties_drawn']['Player3'] == 1
    
    # Add more PD
    client.get('/action/1/Player3?action=penalty_drawn')
    client.get('/action/1/Player3?action=penalty_drawn')
    g = _read_games()[0]
    assert g['penalties_drawn']['Player3'] == 3
    
    # Decrement PD
    rv = client.get('/action/1/Player3?action=penalty_drawn_minus', follow_redirects=True)
    assert rv.status_code == 200
    g = _read_games()[0]
    assert g['penalties_drawn']['Player3'] == 2
    
    # Should not go below zero
    client.get('/action/1/Player3?action=penalty_drawn_minus')
    client.get('/action/1/Player3?action=penalty_drawn_minus')
    client.get('/action/1/Player3?action=penalty_drawn_minus')
    g = _read_games()[0]
    assert g['penalties_drawn']['Player3'] == 0


def test_player_game_score_calculation(client):
    """Test Game Score calculation for players with all stats"""
    # Create game with complete stats
    game = make_sample_game()
    game['plusminus'] = {'Player1': 2, 'Player2': -1}
    game['goals'] = {'Player1': 3, 'Player2': 1}
    game['assists'] = {'Player1': 2, 'Player2': 1}
    game['unforced_errors'] = {'Player1': 1, 'Player2': 2}
    game['shots_on_goal'] = {'Player1': 10, 'Player2': 5}
    game['penalties_taken'] = {'Player1': 1, 'Player2': 0}
    game['penalties_drawn'] = {'Player1': 2, 'Player2': 1}
    
    _write_games([game])
    
    # Get stats page
    rv = client.get('/stats')
    assert rv.status_code == 200
    
    # Check Game Score is present
    assert b'Game Score' in rv.data
    
    # Verify Player1 Game Score calculation
    # GS = (1.5 * 3) + (1.0 * 2) + (0.1 * 10) + (0.3 * 2) + (0.15 * 2) - (0.15 * 1) - (0.2 * 1)
    # GS = 4.5 + 2.0 + 1.0 + 0.6 + 0.3 - 0.15 - 0.2 = 8.05
    assert b'8.05' in rv.data
    
    # Verify Player2 Game Score calculation
    # GS = (1.5 * 1) + (1.0 * 1) + (0.1 * 5) + (0.3 * -1) + (0.15 * 1) - (0.15 * 0) - (0.2 * 2)
    # GS = 1.5 + 1.0 + 0.5 - 0.3 + 0.15 - 0 - 0.4 = 2.45
    assert b'2.45' in rv.data


def test_player_game_score_with_zeros(client):
    """Test Game Score calculation when all stats are zero"""
    game = make_sample_game()
    game['plusminus'] = {'Player1': 0}
    game['goals'] = {'Player1': 0}
    game['assists'] = {'Player1': 0}
    game['unforced_errors'] = {'Player1': 0}
    game['shots_on_goal'] = {'Player1': 0}
    game['penalties_taken'] = {'Player1': 0}
    game['penalties_drawn'] = {'Player1': 0}
    
    _write_games([game])
    
    rv = client.get('/stats')
    assert rv.status_code == 200
    
    # Game Score should be 0.0
    assert b'Player1' in rv.data
    # The table should show 0 for the game score


def test_player_game_score_negative(client):
    """Test Game Score can be negative with many errors and penalties"""
    game = make_sample_game()
    game['plusminus'] = {'Player1': -3}
    game['goals'] = {'Player1': 0}
    game['assists'] = {'Player1': 0}
    game['unforced_errors'] = {'Player1': 5}
    game['shots_on_goal'] = {'Player1': 0}
    game['penalties_taken'] = {'Player1': 3}
    game['penalties_drawn'] = {'Player1': 0}
    
    _write_games([game])
    
    rv = client.get('/stats')
    assert rv.status_code == 200
    
    # GS = 0 + 0 + 0 + (0.3 * -3) + 0 - (0.15 * 3) - (0.2 * 5)
    # GS = -0.9 - 0.45 - 1.0 = -2.35
    assert b'-2.35' in rv.data


def test_goalie_game_score_calculation(client):
    """Test Game Score calculation for goalies"""
    game = make_sample_game()
    game['saves'] = {'Goalie1': 20}
    game['goals_conceded'] = {'Goalie1': 2}
    
    _write_games([game])
    
    rv = client.get('/stats')
    assert rv.status_code == 200
    
    # Check Goalie Game Score is present
    assert b'Game Score - Goalies' in rv.data or b'Game Score - Portieri' in rv.data
    
    # Verify Goalie1 Game Score calculation
    # GS = (0.10 * 20) - (0.25 * 2) = 2.0 - 0.5 = 1.5
    assert b'1.5' in rv.data or b'1.50' in rv.data


def test_goalie_game_score_negative(client):
    """Test goalie Game Score can be negative with many goals conceded"""
    game = make_sample_game()
    game['saves'] = {'Goalie1': 10}
    game['goals_conceded'] = {'Goalie1': 8}
    
    _write_games([game])
    
    rv = client.get('/stats')
    assert rv.status_code == 200
    
    # GS = (0.10 * 10) - (0.25 * 8) = 1.0 - 2.0 = -1.0
    assert b'-1.0' in rv.data or b'-1' in rv.data


def test_goalie_game_score_shutout(client):
    """Test goalie Game Score with shutout (no goals conceded)"""
    game = make_sample_game()
    game['saves'] = {'Goalie1': 25}
    game['goals_conceded'] = {'Goalie1': 0}
    
    _write_games([game])
    
    rv = client.get('/stats')
    assert rv.status_code == 200
    
    # GS = (0.10 * 25) - (0.25 * 0) = 2.5
    assert b'2.5' in rv.data or b'2.50' in rv.data


def test_multiple_players_game_score(client):
    """Test Game Score calculation with multiple players"""
    game = make_sample_game()
    game['plusminus'] = {'Player1': 1, 'Player2': 0, 'Player3': -1}
    game['goals'] = {'Player1': 2, 'Player2': 1, 'Player3': 0}
    game['assists'] = {'Player1': 1, 'Player2': 0, 'Player3': 1}
    game['unforced_errors'] = {'Player1': 0, 'Player2': 1, 'Player3': 0}
    game['shots_on_goal'] = {'Player1': 5, 'Player2': 3, 'Player3': 2}
    game['penalties_taken'] = {'Player1': 0, 'Player2': 1, 'Player3': 0}
    game['penalties_drawn'] = {'Player1': 1, 'Player2': 0, 'Player3': 0}
    
    _write_games([game])
    
    rv = client.get('/stats')
    assert rv.status_code == 200
    
    # All three players should have their Game Scores calculated
    assert b'Player1' in rv.data
    assert b'Player2' in rv.data
    assert b'Player3' in rv.data
    
    # Player1: (1.5*2) + (1.0*1) + (0.1*5) + (0.3*1) + (0.15*1) - 0 - 0
    #        = 3.0 + 1.0 + 0.5 + 0.3 + 0.15 = 4.95
    assert b'4.95' in rv.data
