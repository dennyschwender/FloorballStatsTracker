"""Tests for advanced features and edge cases"""
import json
import os
from config import GAMES_FILE, ROSTERS_DIR


def create_test_roster(team='TestTeam'):
    """Helper to create test roster"""
    roster_data = [
        {"id": "1", "number": "69", "surname": "Bazzuri", "name": "Andrea", "position": "A", "tesser": "U21", "nickname": "Andy"},
        {"id": "2", "number": "84", "surname": "Belvederi", "name": "Andrea", "position": "A", "tesser": "U21", "nickname": "Belve"},
        {"id": "3", "number": "79", "surname": "Biaggio", "name": "Filippo", "position": "A", "tesser": "U21", "nickname": "Pippo"},
        {"id": "4", "number": "77", "surname": "Schwender", "name": "Dennis", "position": "P", "tesser": "U21", "nickname": "Denny"}
    ]
    roster_path = os.path.join(ROSTERS_DIR, f'roster_{team}.json')
    with open(roster_path, 'w') as f:
        json.dump(roster_data, f)
    return roster_path


def test_line_action_plusminus(client):
    """Test applying plus/minus to entire line"""
    roster_path = create_test_roster('U21')
    
    # Create game with roster format
    data = {
        'team': 'U21',
        'home_team': 'Test Home',
        'away_team': 'Test Away',
        'date': '2025-11-14',
        'l1_1': '1',  # Bazzuri
        'l1_2': '2',  # Belvederi
        'l1_3': '3',  # Biaggio
        'goalie1': '4',
        'goalie2': ''
    }
    client.post('/create_game', data=data, follow_redirects=True)
    
    games = json.load(open(GAMES_FILE))
    game = next((g for g in games if g['home_team'] == 'Test Home'), None)
    assert game is not None
    game_id = game['id']
    
    # Apply plus to entire line 0
    response = client.get(f'/action_line/{game_id}/0?action=plus', follow_redirects=True)
    assert response.status_code == 200
    
    # Verify all players in line got +1
    games = json.load(open(GAMES_FILE))
    game = next((g for g in games if g['id'] == game_id), None)
    assert game is not None
    for player in game['lines'][0]:
        assert game['plusminus'].get(player, 0) == 1
    
    # Cleanup
    if os.path.exists(roster_path):
        os.remove(roster_path)


def test_unforced_errors(client):
    """Test tracking unforced errors"""
    roster_path = create_test_roster('U21')
    
    # Create game
    data = {
        'team': 'U21',
        'home_team': 'Test Home',
        'away_team': 'Test Away',
        'date': '2025-11-14',
        'l1_1': '1',
        'goalie1': '',
        'goalie2': ''
    }
    client.post('/create_game', data=data, follow_redirects=True)
    
    games = json.load(open(GAMES_FILE))
    game = next((g for g in games if g['home_team'] == 'Test Home'), None)
    assert game is not None
    game_id = game['id']
    player = '69 - Bazzuri Andrea'
    
    # Add unforced error
    response = client.get(f'/action/{game_id}/{player}?action=unforced_error', follow_redirects=True)
    assert response.status_code == 200
    
    # Verify error was recorded
    games = json.load(open(GAMES_FILE))
    game = next((g for g in games if g['id'] == game_id), None)
    assert game is not None
    assert game['unforced_errors'].get(player, 0) == 1
    
    # Remove unforced error
    response = client.get(f'/action/{game_id}/{player}?action=unforced_error_minus', follow_redirects=True)
    assert response.status_code == 200
    
    # Verify error was decremented
    games = json.load(open(GAMES_FILE))
    game = next((g for g in games if g['id'] == game_id), None)
    assert game is not None
    assert game['unforced_errors'].get(player, 0) == 0
    
    # Cleanup
    if os.path.exists(roster_path):
        os.remove(roster_path)


def test_special_formations(client):
    """Test creating game with special formations (PP, BP, etc)"""
    roster_path = create_test_roster('U21')
    
    # Create game with formations
    data = {
        'team': 'U21',
        'home_team': 'Test Home',
        'away_team': 'Test Away',
        'date': '2025-11-14',
        'l1_1': '1',
        'pp1_1': '1',  # Power play 1
        'pp1_2': '2',
        'bp1_1': '3',  # Box play 1
        'goalie1': '4',
        'goalie2': ''
    }
    client.post('/create_game', data=data, follow_redirects=True)
    
    games = json.load(open(GAMES_FILE))
    game = next((g for g in games if g['home_team'] == 'Test Home'), None)
    assert game is not None
    
    # Verify formations were created
    assert 'pp1' in game
    assert 'bp1' in game
    assert len(game['pp1']) == 2
    assert len(game['bp1']) == 1
    
    # Cleanup
    if os.path.exists(roster_path):
        os.remove(roster_path)


def test_game_lineup_page(client):
    """Test game lineup page loads"""
    roster_path = create_test_roster('U21')
    
    # Create game
    data = {
        'team': 'U21',
        'home_team': 'Test Home',
        'away_team': 'Test Away',
        'date': '2025-11-14',
        'l1_1': '1',
        'goalie1': '4',
        'goalie2': ''
    }
    client.post('/create_game', data=data, follow_redirects=True)
    
    games = json.load(open(GAMES_FILE))
    game = next((g for g in games if g['home_team'] == 'Test Home'), None)
    assert game is not None
    game_id = game['id']
    
    # Access lineup page
    response = client.get(f'/game/{game_id}/lineup')
    assert response.status_code == 200
    assert b'Test Home' in response.data
    
    # Cleanup
    if os.path.exists(roster_path):
        os.remove(roster_path)


def test_delete_game(client):
    """Test deleting a game"""
    roster_path = create_test_roster('U21')
    
    # Create game
    data = {
        'team': 'U21',
        'home_team': 'Test Home',
        'away_team': 'Test Away',
        'date': '2025-11-14',
        'l1_1': '1',
        'goalie1': '',
        'goalie2': ''
    }
    client.post('/create_game', data=data, follow_redirects=True)
    
    games = json.load(open(GAMES_FILE))
    initial_count = len(games)
    game = next((g for g in games if g['home_team'] == 'Test Home'), None)
    assert game is not None
    game_id = game['id']
    
    # Delete game
    response = client.post(f'/delete_game/{game_id}', follow_redirects=True)
    assert response.status_code == 200
    
    # Verify game was deleted
    games = json.load(open(GAMES_FILE))
    assert len(games) == initial_count - 1
    assert not any(g['id'] == game_id for g in games)
    
    # Cleanup
    if os.path.exists(roster_path):
        os.remove(roster_path)


def test_invalid_game_id(client):
    """Test accessing non-existent game ID"""
    response = client.get('/game/99999')
    assert response.status_code == 404


def test_invalid_period(client):
    """Test setting invalid period"""
    roster_path = create_test_roster('U21')
    
    # Create game
    data = {
        'team': 'U21',
        'home_team': 'Test Home',
        'away_team': 'Test Away',
        'date': '2025-11-14',
        'l1_1': '1',
        'goalie1': '',
        'goalie2': ''
    }
    client.post('/create_game', data=data, follow_redirects=True)
    
    games = json.load(open(GAMES_FILE))
    game = next((g for g in games if g['home_team'] == 'Test Home'), None)
    assert game is not None
    game_id = game['id']
    
    # Try to set invalid period
    response = client.get(f'/set_period/{game_id}/5')
    assert response.status_code == 400
    
    # Cleanup
    if os.path.exists(roster_path):
        os.remove(roster_path)


def test_empty_roster_handling(client):
    """Test handling of empty roster"""
    roster_path = os.path.join(ROSTERS_DIR, 'roster_EmptyTeam.json')
    with open(roster_path, 'w') as f:
        json.dump([], f)
    
    # Try to create game with empty roster
    response = client.get('/create_game')
    assert response.status_code == 200
    
    # Cleanup
    if os.path.exists(roster_path):
        os.remove(roster_path)


def test_goal_with_goalie_on_ice(client):
    """Test goal triggers opponent goalie goals conceded when enabled"""
    roster_path = create_test_roster('U21')
    
    # Create game with opponent goalie enabled
    data = {
        'team': 'U21',
        'home_team': 'Test Home',
        'away_team': 'Test Away',
        'date': '2025-11-14',
        'l1_1': '1',
        'goalie1': '4',
        'goalie2': '',
        'enable_opponent_goalie': 'on'
    }
    client.post('/create_game', data=data, follow_redirects=True)
    
    games = json.load(open(GAMES_FILE))
    game = next((g for g in games if g['home_team'] == 'Test Home'), None)
    assert game is not None
    game_id = game['id']
    player = '69 - Bazzuri Andrea'
    
    # Score a goal
    response = client.get(f'/action/{game_id}/{player}?action=goal', follow_redirects=True)
    assert response.status_code == 200
    
    # Verify opponent goalie goals conceded increased
    games = json.load(open(GAMES_FILE))
    game = next((g for g in games if g['id'] == game_id), None)
    assert game is not None
    assert game['opponent_goalie_goals_conceded'].get('Opponent Goalie', 0) == 1
    
    # Cleanup
    if os.path.exists(roster_path):
        os.remove(roster_path)


def test_goalie_assist(client):
    """Test tracking goalie assists"""
    roster_path = create_test_roster('U21')
    
    # Create game
    data = {
        'team': 'U21',
        'home_team': 'Test Home',
        'away_team': 'Test Away',
        'date': '2025-11-14',
        'l1_1': '1',
        'goalie1': '4',
        'goalie2': ''
    }
    client.post('/create_game', data=data, follow_redirects=True)
    
    games = json.load(open(GAMES_FILE))
    game = next((g for g in games if g['home_team'] == 'Test Home'), None)
    assert game is not None
    game_id = game['id']
    goalie = '77 - Schwender Dennis'
    
    # Record goalie assist
    response = client.get(f'/action_goalie/{game_id}/{goalie}?action=assist', follow_redirects=True)
    assert response.status_code == 200
    
    # Verify assist was recorded
    games = json.load(open(GAMES_FILE))
    game = next((g for g in games if g['id'] == game_id), None)
    assert game is not None
    assert game['assists'].get(goalie, 0) == 1
    
    # Cleanup
    if os.path.exists(roster_path):
        os.remove(roster_path)
