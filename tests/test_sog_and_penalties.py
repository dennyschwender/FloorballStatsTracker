import json
import pytest

from config import GAMES_FILE


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
        'id': 0,
        'team': 'T1',
        'home_team': 'Home',
        'away_team': 'Away',
        'date': '2025-09-01',
        'lines': [['P1', 'P2', 'P3'], ['P4', 'P5'], [], []],
        'goalies': ['G1'],
        'result': {p: {'home': 0, 'away': 0} for p in ['1', '2', '3', 'OT']},
        'current_period': '1',
    }


def test_shot_on_goal_actions(client):
    """Test that shot on goal actions increment and decrement correctly."""
    games = [make_sample_game()]
    _write_games(games)

    # Add a shot on goal
    rv = client.get('/action/0/P1?action=shot_on_goal', follow_redirects=True)
    assert rv.status_code == 200
    g = _read_games()[0]
    assert g['shots_on_goal']['P1'] == 1

    # Add another shot on goal
    rv = client.get('/action/0/P1?action=shot_on_goal', follow_redirects=True)
    assert rv.status_code == 200
    g = _read_games()[0]
    assert g['shots_on_goal']['P1'] == 2

    # Decrement shot on goal
    rv = client.get('/action/0/P1?action=shot_on_goal_minus', follow_redirects=True)
    assert rv.status_code == 200
    g = _read_games()[0]
    assert g['shots_on_goal']['P1'] == 1

    # Should not go below 0
    rv = client.get('/action/0/P1?action=shot_on_goal_minus', follow_redirects=True)
    rv = client.get('/action/0/P1?action=shot_on_goal_minus', follow_redirects=True)
    assert rv.status_code == 200
    g = _read_games()[0]
    assert g['shots_on_goal']['P1'] == 0


def test_penalty_taken_actions(client):
    """Test that penalty taken actions increment and decrement correctly."""
    games = [make_sample_game()]
    _write_games(games)

    # Add a penalty taken
    rv = client.get('/action/0/P2?action=penalty_taken', follow_redirects=True)
    assert rv.status_code == 200
    g = _read_games()[0]
    assert g['penalties_taken']['P2'] == 1

    # Add another penalty taken
    rv = client.get('/action/0/P2?action=penalty_taken', follow_redirects=True)
    assert rv.status_code == 200
    g = _read_games()[0]
    assert g['penalties_taken']['P2'] == 2

    # Decrement penalty taken
    rv = client.get('/action/0/P2?action=penalty_taken_minus', follow_redirects=True)
    assert rv.status_code == 200
    g = _read_games()[0]
    assert g['penalties_taken']['P2'] == 1

    # Should not go below 0
    rv = client.get('/action/0/P2?action=penalty_taken_minus', follow_redirects=True)
    rv = client.get('/action/0/P2?action=penalty_taken_minus', follow_redirects=True)
    assert rv.status_code == 200
    g = _read_games()[0]
    assert g['penalties_taken']['P2'] == 0


def test_penalty_drawn_actions(client):
    """Test that penalty drawn actions increment and decrement correctly."""
    games = [make_sample_game()]
    _write_games(games)

    # Add a penalty drawn
    rv = client.get('/action/0/P3?action=penalty_drawn', follow_redirects=True)
    assert rv.status_code == 200
    g = _read_games()[0]
    assert g['penalties_drawn']['P3'] == 1

    # Add another penalty drawn
    rv = client.get('/action/0/P3?action=penalty_drawn', follow_redirects=True)
    assert rv.status_code == 200
    g = _read_games()[0]
    assert g['penalties_drawn']['P3'] == 2

    # Decrement penalty drawn
    rv = client.get('/action/0/P3?action=penalty_drawn_minus', follow_redirects=True)
    assert rv.status_code == 200
    g = _read_games()[0]
    assert g['penalties_drawn']['P3'] == 1

    # Should not go below 0
    rv = client.get('/action/0/P3?action=penalty_drawn_minus', follow_redirects=True)
    rv = client.get('/action/0/P3?action=penalty_drawn_minus', follow_redirects=True)
    assert rv.status_code == 200
    g = _read_games()[0]
    assert g['penalties_drawn']['P3'] == 0


def test_multiple_stats_for_same_player(client):
    """Test that multiple new stats can be tracked for the same player."""
    games = [make_sample_game()]
    _write_games(games)

    # Add various stats for P1
    client.get('/action/0/P1?action=shot_on_goal', follow_redirects=True)
    client.get('/action/0/P1?action=shot_on_goal', follow_redirects=True)
    client.get('/action/0/P1?action=shot_on_goal', follow_redirects=True)
    client.get('/action/0/P1?action=penalty_taken', follow_redirects=True)
    client.get('/action/0/P1?action=penalty_drawn', follow_redirects=True)
    client.get('/action/0/P1?action=penalty_drawn', follow_redirects=True)

    g = _read_games()[0]
    assert g['shots_on_goal']['P1'] == 3
    assert g['penalties_taken']['P1'] == 1
    assert g['penalties_drawn']['P1'] == 2


def test_reset_game_includes_new_stats(client):
    """Test that reset_game clears the new stats."""
    games = [make_sample_game()]
    _write_games(games)

    # Add various stats
    client.get('/action/0/P1?action=shot_on_goal', follow_redirects=True)
    client.get('/action/0/P1?action=shot_on_goal', follow_redirects=True)
    client.get('/action/0/P2?action=penalty_taken', follow_redirects=True)
    client.get('/action/0/P3?action=penalty_drawn', follow_redirects=True)

    # Verify stats exist
    g = _read_games()[0]
    assert g['shots_on_goal']['P1'] == 2
    assert g['penalties_taken']['P2'] == 1
    assert g['penalties_drawn']['P3'] == 1

    # Reset game
    rv = client.get('/reset_game/0', follow_redirects=True)
    assert rv.status_code == 200

    # Verify all stats are reset
    g = _read_games()[0]
    assert g['shots_on_goal']['P1'] == 0
    assert g['penalties_taken']['P2'] == 0
    assert g['penalties_drawn']['P3'] == 0


def test_stats_page_includes_new_stats(client):
    """Test that the stats page displays new stats correctly."""
    games = [make_sample_game()]
    games[0]['shots_on_goal'] = {'P1': 5}
    games[0]['penalties_taken'] = {'P2': 2}
    games[0]['penalties_drawn'] = {'P3': 3}
    _write_games(games)

    rv = client.get('/stats')
    assert rv.status_code == 200
    data = rv.data.decode('utf-8')
    
    # Check that player names are in the page
    assert 'P1' in data
    assert 'P2' in data
    assert 'P3' in data


def test_game_details_page_displays_new_stats(client):
    """Test that the game details page shows the new stat columns."""
    games = [make_sample_game()]
    games[0]['shots_on_goal'] = {'P1': 3}
    games[0]['penalties_taken'] = {'P2': 1}
    games[0]['penalties_drawn'] = {'P3': 2}
    _write_games(games)

    rv = client.get('/game/0')
    assert rv.status_code == 200
    data = rv.data.decode('utf-8')
    
    # Check that the new stat columns are present
    # SOG column should be there
    assert 'SOG' in data or 'TIG' in data  # English or Italian
    
    # Check for the penalty columns
    assert 'Penalty' in data or 'Penalità' in data


def test_edit_mode_preserves_new_stats_actions(client):
    """Test that edit mode URL parameter is preserved for new stat actions."""
    games = [make_sample_game()]
    _write_games(games)

    # Test shot_on_goal in edit mode
    rv = client.get('/action/0/P1?action=shot_on_goal&edit=1', follow_redirects=False)
    assert rv.status_code in (302, 301)
    assert 'edit=1' in rv.location

    # Test penalty_taken in edit mode
    rv = client.get('/action/0/P2?action=penalty_taken&edit=1', follow_redirects=False)
    assert rv.status_code in (302, 301)
    assert 'edit=1' in rv.location

    # Test penalty_drawn in edit mode
    rv = client.get('/action/0/P3?action=penalty_drawn&edit=1', follow_redirects=False)
    assert rv.status_code in (302, 301)
    assert 'edit=1' in rv.location


def test_stats_totals_aggregation(client):
    """Test that stats page correctly aggregates new stats across multiple games."""
    games = [
        make_sample_game(),
        make_sample_game(),
    ]
    # Ensure unique IDs
    from services.game_service import ensure_game_ids
    ensure_game_ids(games)
    
    # Set different stats for each game
    games[0]['shots_on_goal'] = {'P1': 3, 'P2': 2}
    games[0]['penalties_taken'] = {'P1': 1}
    games[0]['penalties_drawn'] = {'P2': 2}
    
    games[1]['shots_on_goal'] = {'P1': 2, 'P2': 1}
    games[1]['penalties_taken'] = {'P1': 1, 'P2': 1}
    games[1]['penalties_drawn'] = {'P1': 1, 'P2': 1}
    
    _write_games(games)

    rv = client.get('/stats')
    assert rv.status_code == 200
    data = rv.data.decode('utf-8')
    
    # Basic check - page should contain player names
    assert 'P1' in data
    assert 'P2' in data
