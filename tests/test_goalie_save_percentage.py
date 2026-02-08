"""Test to verify goalie save percentage calculation"""
import json
import os
from config import GAMES_FILE, ROSTERS_DIR


def test_goalie_save_percentage_with_fallback(client):
    """Test that goalie save percentage correctly calculates when goals_conceded is not tracked"""
    roster_data = [
        {"id": "1", "number": "57", "surname": "Peverelli", "name": "Matteo", "position": "P", "tesser": "U21", "nickname": "MP"}
    ]
    
    season = '2024-25'
    team = 'U21'
    roster_path = os.path.join(ROSTERS_DIR, f'roster_{season}_{team}.json')
    
    with open(roster_path, 'w') as f:
        json.dump(roster_data, f)
    
    # Create a game
    game_data = {
        'season': season,
        'team': team,
        'home_team': 'Test Team',
        'away_team': 'Opponent Team',
        'date': '2025-01-15',
        'goalie1': '1',  # Assign goalie
        'goalie2': '',
        'l1_1': '',
    }
    
    client.post('/create_game', data=game_data, follow_redirects=True)
    
    # Get the game
    with open(GAMES_FILE) as f:
        games = json.load(f)
    game = next((g for g in games if g['home_team'] == 'Test Team'), None)
    assert game is not None, "Game should be created"
    game_id = game['id']
    goalie_name = '57 - Peverelli Matteo'
    
    # Record 28 saves for the goalie (like in the screenshot)
    for _ in range(28):
        client.get(f'/action_goalie/{game_id}/{goalie_name}?action=save')
    
    # Manually set the game result to show 7-4 (home-away) without tracking goals_conceded
    with open(GAMES_FILE) as f:
        games = json.load(f)
    
    for g in games:
        if g['id'] == game_id:
            # Set result to 7-4 (Period 1: 1-2, Period 2: 3-0, Period 3: 3-2)
            g['result'] = {
                '1': {'home': 1, 'away': 2},
                '2': {'home': 3, 'away': 0},
                '3': {'home': 3, 'away': 2},
                'OT': {'home': 0, 'away': 0}
            }
            # Intentionally NOT setting goals_conceded (simulating the bug)
            # goals_conceded should be 0 or not set
            if 'goals_conceded' not in g:
                g['goals_conceded'] = {}
            g['goals_conceded'][goalie_name] = 0  # Bug: not tracked
            break
    
    with open(GAMES_FILE, 'w') as f:
        json.dump(games, f, indent=2)
    
    # Now check the game details page
    response = client.get(f'/game/{game_id}')
    assert response.status_code == 200
    
    # The page should show:
    # - 28 saves
    # - 4 goals conceded (calculated from away score: 2+0+2 = 4)
    # - Save %: 28/(28+4) = 87.5%
    page_content = response.data.decode('utf-8')
    
    # Check that goals conceded is displayed as 4 (not 0)
    # Look for the table structure with 28 saves and goals conceded
    assert '28' in page_content  # Saves
    
    # The save percentage should be 87.5% (28 out of 32 total shots)
    # 28 / (28 + 4) = 28 / 32 = 0.875 = 87.5%
    assert '87.5%' in page_content or '87.5' in page_content
    
    # Also check stats page
    response = client.get(f'/stats?season={season}')
    assert response.status_code == 200
    stats_content = response.data.decode('utf-8')
    
    # Should show correct save percentage on stats page too
    assert '87.5' in stats_content or '87' in stats_content  # Allow for rounding
    
    # Cleanup
    if os.path.exists(roster_path):
        os.remove(roster_path)


def test_goalie_save_percentage_calculation(client):
    """Test that goalie save percentages include goals conceded in calculation"""
    roster_data = [
        {"id": "1", "number": "30", "surname": "Goalie", "name": "Test", "position": "P", "tesser": "U21", "nickname": "TG"},
        {"id": "2", "number": "10", "surname": "Player", "name": "Test", "position": "A", "tesser": "U21", "nickname": "TP"}
    ]
    
    season = '2024-25'
    team = 'U21'
    roster_path = os.path.join(ROSTERS_DIR, f'roster_{season}_{team}.json')
    
    with open(roster_path, 'w') as f:
        json.dump(roster_data, f)
    
    # Create game
    game_data = {
        'season': season,
        'team': team,
        'home_team': 'Save % Test',
        'away_team': 'Away',
        'date': '2025-01-15',
        'l1_2': '1',
        'goalie1': '1',
        'goalie2': ''
    }
    
    client.post('/create_game', data=game_data, follow_redirects=True)
    
    # Get game ID
    with open(GAMES_FILE) as f:
        games = json.load(f)
    game = next((g for g in games if g['home_team'] == 'Save % Test'), None)
    assert game is not None, "Game should be created"
    game_id = game['id']
    
    goalie = '30 - Goalie Test'
    
    # Record 7 saves
    for _ in range(7):
        client.get(f'/action_goalie/{game_id}/{goalie}?action=save')
    
    # Record 3 goals conceded
    for _ in range(3):
        client.get(f'/action_goalie/{game_id}/{goalie}?action=goal_conceded')
    
    # Verify in game data
    with open(GAMES_FILE) as f:
        games = json.load(f)
    game = next((g for g in games if g['id'] == game_id), None)
    
    assert game is not None
    assert game['saves'].get(goalie, 0) == 7
    assert game['goals_conceded'].get(goalie, 0) == 3
    
    # Check stats page calculation
    response = client.get(f'/stats?season={season}')
    assert response.status_code == 200
    
    # Expected save percentage: 7 / (7 + 3) = 70%
    # Check if 70% appears in the page (should be formatted as "70.0%")
    assert b'70.0%' in response.data or b'70%' in response.data, \
        "Save percentage should be 70% (7 saves / 10 total shots)"
    
    # Verify it's NOT 100%
    # Count occurrences - there should be some, but not for our goalie's average
    assert response.data.count(b'100.0%') == 0 or b'Goalie Test' not in response.data, \
        "Goalie should NOT have 100% save rate when they conceded goals"
    
    # Cleanup
    if os.path.exists(roster_path):
        os.remove(roster_path)


def test_goalie_with_only_saves_no_goals(client):
    """Test goalie with saves but no goals conceded (legitimate 100% save rate)"""
    roster_data = [
        {"id": "1", "number": "30", "surname": "Perfect", "name": "Goalie", "position": "P", "tesser": "U21", "nickname": "PG"},
        {"id": "2", "number": "10", "surname": "Player", "name": "Test", "position": "A", "tesser": "U21", "nickname": "TP"}
    ]
    
    season = '2024-25'
    team = 'U21'
    roster_path = os.path.join(ROSTERS_DIR, f'roster_{season}_{team}.json')
    
    with open(roster_path, 'w') as f:
        json.dump(roster_data, f)
    
    # Create game
    game_data = {
        'season': season,
        'team': team,
        'home_team': 'Perfect Save Test',
        'away_team': 'Away',
        'date': '2025-01-15',
        'l1_2': '1',
        'goalie1': '1',
        'goalie2': ''
    }
    
    client.post('/create_game', data=game_data, follow_redirects=True)
    
    # Get game ID
    with open(GAMES_FILE) as f:
        games = json.load(f)
    game = next((g for g in games if g['home_team'] == 'Perfect Save Test'), None)
    assert game is not None, "Game should be created"
    game_id = game['id']
    
    goalie = '30 - Perfect Goalie'
    
    # Record 10 saves, 0 goals conceded
    for _ in range(10):
        client.get(f'/action_goalie/{game_id}/{goalie}?action=save')
    
    # Verify in game data
    with open(GAMES_FILE) as f:
        games = json.load(f)
    game = next((g for g in games if g['id'] == game_id), None)
    
    assert game is not None
    assert game['saves'].get(goalie, 0) == 10
    assert game['goals_conceded'].get(goalie, 0) == 0
    
    # Check stats page - this SHOULD be 100%
    response = client.get(f'/stats?season={season}')
    assert response.status_code == 200
    assert b'100.0%' in response.data or b'100%' in response.data
    
    # Cleanup
    if os.path.exists(roster_path):
        os.remove(roster_path)


def test_goalie_goals_conceded_tracked_correctly(client):
    """Test that goals conceded are properly tracked and displayed"""
    roster_data = [
        {"id": "1", "number": "30", "surname": "Busy", "name": "Goalie", "position": "P", "tesser": "U21", "nickname": "BG"}
    ]
    
    season = '2024-25'
    team = 'U21'
    roster_path = os.path.join(ROSTERS_DIR, f'roster_{season}_{team}.json')
    
    with open(roster_path, 'w') as f:
        json.dump(roster_data, f)
    
    # Create game
    game_data = {
        'season': season,
        'team': team,
        'home_team': 'Goals Conceded Test',
        'away_team': 'Away',
        'date': '2025-01-15',
        'goalie1': '1',
        'goalie2': ''
    }
    
    client.post('/create_game', data=game_data, follow_redirects=True)
    
    # Get game ID
    with open(GAMES_FILE) as f:
        games = json.load(f)
    game = next((g for g in games if g['home_team'] == 'Goals Conceded Test'), None)
    game_id = game['id']
    
    goalie = '30 - Busy Goalie'
    
    # Record 3 saves and 7 goals conceded (30% save rate)
    for _ in range(3):
        client.get(f'/action_goalie/{game_id}/{goalie}?action=save')
    
    for _ in range(7):
        client.get(f'/action_goalie/{game_id}/{goalie}?action=goal_conceded')
    
    # Verify data
    with open(GAMES_FILE) as f:
        games = json.load(f)
    game = next((g for g in games if g['id'] == game_id), None)
    
    # Debug: print the game data
    print(f"\nGame data for goalie '{goalie}':")
    print(f"  Saves: {game.get('saves', {})}")
    print(f"  Goals Conceded: {game.get('goals_conceded', {})}")
    
    assert game['saves'].get(goalie, 0) == 3, "Should have 3 saves"
    assert game['goals_conceded'].get(goalie, 0) == 7, "Should have 7 goals conceded"
    
    # Expected: 3 / (3 + 7) = 30%
    response = client.get(f'/stats?season={season}')
    assert response.status_code == 200
    
    # Check for 30% save rate
    assert b'30.0%' in response.data or b'30%' in response.data, \
        f"Save percentage should be 30% (3 saves / 10 total shots), not 100%"
    
    # Cleanup
    if os.path.exists(roster_path):
        os.remove(roster_path)
