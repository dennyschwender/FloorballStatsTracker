import json
import os
from app import GAMES_FILE, ROSTERS_DIR


def create_test_game(client, roster_data, home_team, away_team, team='U21', season='2024-25', date='2025-11-14', 
                     line1_players=None, line2_players=None, goalies=None, opponent_goalie=False):
    """Helper function to create a test game with roster-based format
    
    Args:
        team: category/team name
        season: season identifier (e.g., '2024-25')
        line1_players: list of player IDs for line 1 (e.g., ['1', '2', '3'])
        line2_players: list of player IDs for line 2
        goalies: list of goalie player IDs (e.g., ['4'])
    """
    # Create roster with season
    roster_path = os.path.join(ROSTERS_DIR, f'roster_{season}_{team}.json')
    with open(roster_path, 'w') as f:
        json.dump(roster_data, f)
    
    # Build form data
    data = {
        'season': season,
        'team': team,
        'home_team': home_team,
        'away_team': away_team,
        'date': date,
    }
    
    # Add line 1 players with positions
    if line1_players:
        for pos, player_id in enumerate(line1_players, 1):
            data[f'l1_{player_id}'] = str(pos)
    
    # Add line 2 players with positions
    if line2_players:
        for pos, player_id in enumerate(line2_players, 1):
            data[f'l2_{player_id}'] = str(pos)
    
    # Add goalies
    if goalies:
        for i, goalie_id in enumerate(goalies[:2], 1):
            data[f'goalie{i}'] = goalie_id
    
    if not goalies or len(goalies) < 1:
        data['goalie1'] = ''
    if not goalies or len(goalies) < 2:
        data['goalie2'] = ''
    
    # Add opponent goalie if requested
    if opponent_goalie:
        data['enable_opponent_goalie'] = 'on'
    
    client.post('/create_game', data=data, follow_redirects=True)
    
    # Return the created game
    games = json.load(open(GAMES_FILE))
    game = next((g for g in games if g['home_team'] == home_team), None)
    return game, roster_path


def test_home_page(client):
    """Test that home page loads successfully"""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Floorball Stats Tracker' in response.data


def test_roster_management(client):
    """Test creating and loading a roster with realistic names"""
    roster_data = [
        {"id": "1", "number": "69", "surname": "Bazzuri", "name": "Andrea", "position": "A", "tesser": "U21", "nickname": "Andy"},
        {"id": "2", "number": "84", "surname": "Belvederi", "name": "Andrea", "position": "A", "tesser": "U21", "nickname": "Belve"},
        {"id": "3", "number": "79", "surname": "Biaggio", "name": "Filippo", "position": "A", "tesser": "U21", "nickname": "Pippo"},
        {"id": "4", "number": "98", "surname": "Bottoli", "name": "Enea", "position": "D", "tesser": "U21", "nickname": "Bottox"},
        {"id": "5", "number": "77", "surname": "Schwender", "name": "Dennis", "position": "P", "tesser": "U21", "nickname": "Denny"}
    ]
    
    # Create test roster with season
    test_season = '2024-25'
    roster_path = os.path.join(ROSTERS_DIR, f'roster_{test_season}_TestTeam.json')
    with open(roster_path, 'w') as f:
        json.dump(roster_data, f)
    
    # Test roster loads correctly with season parameter - just check it returns 200
    response = client.get(f'/roster?team=TestTeam&season={test_season}')
    assert response.status_code == 200
    
    # Cleanup
    if os.path.exists(roster_path):
        os.remove(roster_path)



def test_create_game_with_realistic_data(client):
    """Test creating a game with realistic team and player names"""
    # First create a test roster
    roster_data = [
        {"id": "1", "number": "69", "surname": "Bazzuri", "name": "Andrea", "position": "A", "tesser": "U21", "nickname": "Andy"},
        {"id": "2", "number": "84", "surname": "Belvederi", "name": "Andrea", "position": "A", "tesser": "U21", "nickname": "Belve"},
        {"id": "3", "number": "79", "surname": "Biaggio", "name": "Filippo", "position": "A", "tesser": "U21", "nickname": "Pippo"},
        {"id": "4", "number": "77", "surname": "Schwender", "name": "Dennis", "position": "P", "tesser": "U21", "nickname": "Denny"}
    ]
    
    roster_path = os.path.join(ROSTERS_DIR, 'roster_U21.json')
    with open(roster_path, 'w') as f:
        json.dump(roster_data, f)
    
    # Use the new roster-based form format
    data = {
        'team': 'U21',
        'home_team': 'Grasshoppers Zürich',
        'away_team': 'Red Lions Frauenfeld',
        'date': '2025-11-14',
        # Line 1 with position numbers for each player
        'l1_1': '1',  # Player ID 1 (Bazzuri) at position 1
        'l1_2': '2',  # Player ID 2 (Belvederi) at position 2
        'l1_3': '3',  # Player ID 3 (Biaggio) at position 3
        'goalie1': '4',  # Player ID 4 (Schwender) as goalie
        'goalie2': ''
    }
    
    response = client.post('/create_game', data=data, follow_redirects=True)
    assert response.status_code == 200
    
    games = json.load(open(GAMES_FILE))
    created_game = next((g for g in games if g['home_team'] == 'Grasshoppers Zürich'), None)
    assert created_game is not None
    assert created_game['away_team'] == 'Red Lions Frauenfeld'
    assert len(created_game['lines']) > 0
    # Check first line has players
    assert len(created_game['lines'][0]) == 3
    assert '69 - Bazzuri Andrea' in created_game['lines'][0]
    
    # Cleanup
    if os.path.exists(roster_path):
        os.remove(roster_path)


def test_game_details_by_id(client):
    """Test accessing game by ID (not array index)"""
    roster_data = [
        {"id": "1", "number": "69", "surname": "Bazzuri", "name": "Andrea", "position": "A", "tesser": "U21", "nickname": "Andy"}
    ]
    
    game, roster_path = create_test_game(
        client, roster_data, 'Home Team', 'Away Team',
        line1_players=['1']
    )
    
    assert game is not None
    game_id = game['id']
    
    # Access game by ID
    response = client.get(f'/game/{game_id}')
    assert response.status_code == 200
    assert b'Home Team' in response.data
    assert b'Away Team' in response.data
    
    # Cleanup
    if os.path.exists(roster_path):
        os.remove(roster_path)


def test_modify_game(client):
    """Test modifying game details"""
    roster_data = [
        {"id": "1", "number": "69", "surname": "Bazzuri", "name": "Andrea", "position": "A", "tesser": "U21", "nickname": "Andy"},
        {"id": "2", "number": "84", "surname": "Belvederi", "name": "Andrea", "position": "A", "tesser": "U21", "nickname": "Belve"}
    ]
    
    game, roster_path = create_test_game(
        client, roster_data, 'Original Home', 'Original Away',
        line1_players=['1']
    )
    game_id = game['id']
    
    # Modify the game using roster format
    modify_data = {
        'team': 'U21',
        'home_team': 'Modified Home',
        'away_team': 'Modified Away',
        'date': '2025-11-15',
        'l1_1': '1',  # Bazzuri at position 1
        'l1_2': '2',  # Belvederi at position 2
        'goalie1': '',
        'goalie2': ''
    }
    response = client.post(f'/modify_game/{game_id}', data=modify_data, follow_redirects=True)
    assert response.status_code == 200
    
    # Verify changes
    games = json.load(open(GAMES_FILE))
    modified_game = next((g for g in games if g['id'] == game_id), None)
    assert modified_game is not None
    assert modified_game['home_team'] == 'Modified Home'
    assert modified_game['away_team'] == 'Modified Away'
    
    # Cleanup
    if os.path.exists(roster_path):
        os.remove(roster_path)


def test_player_actions(client):
    """Test recording player actions (goals, assists, plusminus)"""
    roster_data = [
        {"id": "1", "number": "69", "surname": "Bazzuri", "name": "Andrea", "position": "A", "tesser": "U21", "nickname": "Andy"},
        {"id": "2", "number": "84", "surname": "Belvederi", "name": "Andrea", "position": "A", "tesser": "U21", "nickname": "Belve"}
    ]
    
    game, roster_path = create_test_game(
        client, roster_data, 'Test Home', 'Test Away',
        line1_players=['1', '2']
    )
    game_id = game['id']
    
    # Record a goal using the correct route
    response = client.get(f'/action/{game_id}/69 - Bazzuri Andrea?action=goal', follow_redirects=True)
    assert response.status_code == 200
    
    # Record an assist
    response = client.get(f'/action/{game_id}/84 - Belvederi Andrea?action=assist', follow_redirects=True)
    assert response.status_code == 200
    
    # Verify stats
    games = json.load(open(GAMES_FILE))
    game = next((g for g in games if g['id'] == game_id), None)
    assert game['goals'].get('69 - Bazzuri Andrea', 0) == 1
    assert game['assists'].get('84 - Belvederi Andrea', 0) == 1
    
    # Cleanup
    if os.path.exists(roster_path):
        os.remove(roster_path)


def test_goalie_actions(client):
    """Test recording goalie saves and goals conceded"""
    roster_data = [
        {"id": "1", "number": "77", "surname": "Schwender", "name": "Dennis", "position": "P", "tesser": "U21", "nickname": "Denny"},
        {"id": "2", "number": "69", "surname": "Bazzuri", "name": "Andrea", "position": "A", "tesser": "U21", "nickname": "Andy"}
    ]
    
    game, roster_path = create_test_game(
        client, roster_data, 'Test Home', 'Test Away',
        line1_players=['2'],
        goalies=['1']
    )
    game_id = game['id']
    
    # Record saves
    for _ in range(3):
        client.get(f'/action_goalie/{game_id}/77 - Schwender Dennis?action=save', follow_redirects=True)
    
    # Record a goal conceded
    client.get(f'/action_goalie/{game_id}/77 - Schwender Dennis?action=goal_conceded', follow_redirects=True)
    
    # Verify stats
    games = json.load(open(GAMES_FILE))
    game = next((g for g in games if g['id'] == game_id), None)
    assert game['saves'].get('77 - Schwender Dennis', 0) == 3
    assert game['goals_conceded'].get('77 - Schwender Dennis', 0) == 1
    
    # Cleanup
    if os.path.exists(roster_path):
        os.remove(roster_path)


def test_period_management(client):
    """Test setting and tracking game periods"""
    roster_data = [
        {"id": "1", "number": "69", "surname": "Bazzuri", "name": "Andrea", "position": "A", "tesser": "U21", "nickname": "Andy"}
    ]
    
    game, roster_path = create_test_game(
        client, roster_data, 'Test Home', 'Test Away',
        line1_players=['1']
    )
    game_id = game['id']
    
    # Set to period 2
    response = client.get(f'/set_period/{game_id}/2', follow_redirects=True)
    assert response.status_code == 200
    
    # Verify period
    games = json.load(open(GAMES_FILE))
    game = next((g for g in games if g['id'] == game_id), None)
    assert game['current_period'] == '2'
    
    # Set to period 3
    client.get(f'/set_period/{game_id}/3', follow_redirects=True)
    games = json.load(open(GAMES_FILE))
    game = next((g for g in games if g['id'] == game_id), None)
    assert game['current_period'] == '3'
    
    # Cleanup
    if os.path.exists(roster_path):
        os.remove(roster_path)


def test_stats_page(client):
    """Test stats page displays player statistics correctly"""
    roster_data = [
        {"id": "1", "number": "69", "surname": "Bazzuri", "name": "Andrea", "position": "A", "tesser": "U21", "nickname": "Andy"},
        {"id": "2", "number": "84", "surname": "Belvederi", "name": "Andrea", "position": "A", "tesser": "U21", "nickname": "Belve"}
    ]
    
    game, roster_path = create_test_game(
        client, roster_data, 'Test Home', 'Test Away',
        line1_players=['1', '2']
    )
    game_id = game['id']
    
    # Record some goals
    client.post(f'/delete_game/{game_id}/goal', data={
        'player': '69 - Bazzuri Andrea',
        'period': '1'
    }, follow_redirects=True)
    
    # Check stats page
    response = client.get('/stats')
    assert response.status_code == 200
    assert b'Bazzuri' in response.data
    
    # Test filters
    response = client.get('/stats?hide_no_number=1')
    assert response.status_code == 200
    
    response = client.get('/stats?hide_no_games=1')
    assert response.status_code == 200
    
    response = client.get('/stats?hide_zero_stats=1')
    assert response.status_code == 200
    
    # Cleanup
    if os.path.exists(roster_path):
        os.remove(roster_path)


def test_reset_stats(client):
    """Test resetting all game statistics"""
    roster_data = [
        {"id": "1", "number": "69", "surname": "Bazzuri", "name": "Andrea", "position": "A", "tesser": "U21", "nickname": "Andy"}
    ]
    
    game, roster_path = create_test_game(
        client, roster_data, 'Test Home', 'Test Away',
        line1_players=['1']
    )
    game_id = game['id']
    
    # Record some stats
    client.get(f'/action/{game_id}/69 - Bazzuri Andrea?action=goal', follow_redirects=True)
    
    # Verify stats exist
    games = json.load(open(GAMES_FILE))
    game = next((g for g in games if g['id'] == game_id), None)
    assert game['goals'].get('69 - Bazzuri Andrea', 0) > 0
    
    # Reset stats
    response = client.get(f'/reset_game/{game_id}', follow_redirects=True)
    assert response.status_code == 200
    
    # Verify stats are reset
    games = json.load(open(GAMES_FILE))
    game = next((g for g in games if g['id'] == game_id), None)
    assert game['goals'].get('69 - Bazzuri Andrea', 0) == 0
    
    # Cleanup
    if os.path.exists(roster_path):
        os.remove(roster_path)


def test_opponent_goalie_tracking(client):
    """Test tracking opponent goalie statistics"""
    roster_data = [
        {"id": "1", "number": "69", "surname": "Bazzuri", "name": "Andrea", "position": "A", "tesser": "U21", "nickname": "Andy"}
    ]
    
    game, roster_path = create_test_game(
        client, roster_data, 'Test Home', 'Test Away',
        line1_players=['1'],
        opponent_goalie=True
    )
    game_id = game['id']
    
    # Record opponent goalie saves
    for _ in range(5):
        client.get(f'/action_opponent_goalie/{game_id}?action=save', follow_redirects=True)
    
    # Record opponent goalie goals conceded
    client.get(f'/action_opponent_goalie/{game_id}?action=goal_conceded', follow_redirects=True)
    
    # Verify stats
    games = json.load(open(GAMES_FILE))
    game = next((g for g in games if g['id'] == game_id), None)
    assert game['opponent_goalie_saves'].get('Opponent Goalie', 0) == 5
    assert game['opponent_goalie_goals_conceded'].get('Opponent Goalie', 0) == 1
    
    # Cleanup
    if os.path.exists(roster_path):
        os.remove(roster_path)


def test_multiple_lines(client):
    """Test game with multiple player lines"""
    # Create a test roster
    roster_data = [
        {"id": "1", "number": "69", "surname": "Bazzuri", "name": "Andrea", "position": "A", "tesser": "U21", "nickname": "Andy"},
        {"id": "2", "number": "84", "surname": "Belvederi", "name": "Andrea", "position": "A", "tesser": "U21", "nickname": "Belve"},
        {"id": "3", "number": "79", "surname": "Biaggio", "name": "Filippo", "position": "A", "tesser": "U21", "nickname": "Pippo"},
        {"id": "4", "number": "98", "surname": "Bottoli", "name": "Enea", "position": "D", "tesser": "U21", "nickname": "Bottox"}
    ]
    roster_path = os.path.join(ROSTERS_DIR, 'roster_U21.json')
    with open(roster_path, 'w') as f:
        json.dump(roster_data, f)
    
    # Create a game with multiple lines using roster format
    data = {
        'team': 'U21',
        'home_team': 'Test Home',
        'away_team': 'Test Away',
        'date': '2025-11-14',
        'l1_1': '1',  # Line 1: Bazzuri at position 1
        'l1_2': '2',  # Line 1: Belvederi at position 2
        'l2_3': '1',  # Line 2: Biaggio at position 1
        'l2_4': '2',  # Line 2: Bottoli at position 2
        'goalie1': '',
        'goalie2': ''
    }
    response = client.post('/create_game', data=data, follow_redirects=True)
    assert response.status_code == 200
    
    # Verify lines
    games = json.load(open(GAMES_FILE))
    game = next((g for g in games if g['home_team'] == 'Test Home'), None)
    # Check that first two lines have players
    assert len(game['lines'][0]) == 2
    assert len(game['lines'][1]) == 2
    assert '69 - Bazzuri Andrea' in game['lines'][0]
    assert '79 - Biaggio Filippo' in game['lines'][1]
    
    # Cleanup
    if os.path.exists(roster_path):
        os.remove(roster_path)


# client fixture is provided in tests/conftest.py
