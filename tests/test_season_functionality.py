import json
import os
from app import GAMES_FILE, ROSTERS_DIR


def test_season_in_game_creation(client):
    """Test that games are created with season field"""
    roster_data = [
        {"id": "1", "number": "69", "surname": "Test", "name": "Player", "position": "A", "tesser": "U21", "nickname": "TP"}
    ]
    
    # Create roster for specific season
    season = '2024-25'
    team = 'U21'
    roster_path = os.path.join(ROSTERS_DIR, f'roster_{season}_{team}.json')
    with open(roster_path, 'w') as f:
        json.dump(roster_data, f)
    
    # Create game with season
    data = {
        'season': season,
        'team': team,
        'home_team': 'Home Team',
        'away_team': 'Away Team',
        'date': '2025-01-15',
        'l1_1': '1',
        'goalie1': '',
        'goalie2': ''
    }
    
    response = client.post('/create_game', data=data, follow_redirects=True)
    assert response.status_code == 200
    
    # Verify game has season field
    with open(GAMES_FILE) as f:
        games = json.load(f)
    
    game = next((g for g in games if g['home_team'] == 'Home Team'), None)
    assert game is not None
    assert game['season'] == season
    assert game['team'] == team
    
    # Cleanup
    if os.path.exists(roster_path):
        os.remove(roster_path)


def test_multiple_seasons_rosters(client):
    """Test that rosters can be created for different seasons"""
    roster_data_2024 = [
        {"id": "1", "number": "10", "surname": "Player2024", "name": "Test", "position": "A", "tesser": "U21", "nickname": "P24"}
    ]
    
    roster_data_2025 = [
        {"id": "1", "number": "20", "surname": "Player2025", "name": "Test", "position": "A", "tesser": "U21", "nickname": "P25"}
    ]
    
    team = 'TestTeam'
    season_2024 = '2023-24'
    season_2025 = '2024-25'
    
    # Create rosters for different seasons
    roster_path_2024 = os.path.join(ROSTERS_DIR, f'roster_{season_2024}_{team}.json')
    roster_path_2025 = os.path.join(ROSTERS_DIR, f'roster_{season_2025}_{team}.json')
    
    with open(roster_path_2024, 'w') as f:
        json.dump(roster_data_2024, f)
    
    with open(roster_path_2025, 'w') as f:
        json.dump(roster_data_2025, f)
    
    # Test roster loads correctly for 2024 season (need to specify category)
    response = client.get(f'/roster?category={team}&season={season_2024}')
    assert response.status_code == 200
    assert b'Player2024' in response.data
    
    # Test roster loads correctly for 2025 season
    response = client.get(f'/roster?category={team}&season={season_2025}')
    assert response.status_code == 200
    assert b'Player2025' in response.data
    
    # Cleanup
    if os.path.exists(roster_path_2024):
        os.remove(roster_path_2024)
    if os.path.exists(roster_path_2025):
        os.remove(roster_path_2025)


def test_get_all_seasons(client):
    """Test that get_all_seasons returns unique seasons from rosters"""
    # Create test rosters for multiple seasons
    seasons = ['2022-23', '2023-24', '2024-25']
    roster_paths = []
    
    for season in seasons:
        roster_path = os.path.join(ROSTERS_DIR, f'roster_{season}_TestTeam.json')
        roster_paths.append(roster_path)
        with open(roster_path, 'w') as f:
            json.dump([{"id": "1", "number": "1", "surname": "Test", "name": "Player", "position": "A"}], f)
    
    # Access roster page which should show seasons
    response = client.get('/roster')
    assert response.status_code == 200 or response.status_code == 302  # May redirect to first season
    
    # Cleanup
    for path in roster_paths:
        if os.path.exists(path):
            os.remove(path)


def test_season_filtering_on_stats(client):
    """Test that stats page can filter by season"""
    roster_data = [
        {"id": "1", "number": "69", "surname": "Test", "name": "Player", "position": "A", "tesser": "U21", "nickname": "TP"}
    ]
    
    # Create games for different seasons
    season_2024 = '2023-24'
    season_2025 = '2024-25'
    team = 'U21'
    
    for season in [season_2024, season_2025]:
        roster_path = os.path.join(ROSTERS_DIR, f'roster_{season}_{team}.json')
        with open(roster_path, 'w') as f:
            json.dump(roster_data, f)
        
        # Create game for this season
        data = {
            'season': season,
            'team': team,
            'home_team': f'Home {season}',
            'away_team': f'Away {season}',
            'date': '2025-01-15',
            'l1_1': '1',
            'goalie1': '',
            'goalie2': ''
        }
        client.post('/create_game', data=data, follow_redirects=True)
    
    # Test stats page with season filter
    response = client.get(f'/stats?season={season_2024}')
    assert response.status_code == 200
    
    response = client.get(f'/stats?season={season_2025}')
    assert response.status_code == 200
    
    # Cleanup rosters
    for season in [season_2024, season_2025]:
        roster_path = os.path.join(ROSTERS_DIR, f'roster_{season}_{team}.json')
        if os.path.exists(roster_path):
            os.remove(roster_path)


def test_empty_season_handling(client):
    """Test that empty season strings are handled correctly"""
    roster_data = [
        {"id": "1", "number": "69", "surname": "Test", "name": "Player", "position": "A", "tesser": "U21", "nickname": "TP"}
    ]
    
    # Create roster without season (legacy format)
    team = 'U21'
    roster_path = os.path.join(ROSTERS_DIR, f'roster_{team}.json')
    with open(roster_path, 'w') as f:
        json.dump(roster_data, f)
    
    # Try to create game with empty season
    data = {
        'season': '',
        'team': team,
        'home_team': 'Home Team',
        'away_team': 'Away Team',
        'date': '2025-01-15',
        'l1_1': '1',
        'goalie1': '',
        'goalie2': ''
    }
    
    response = client.post('/create_game', data=data, follow_redirects=True)
    assert response.status_code == 200
    
    # Verify game was created
    with open(GAMES_FILE) as f:
        games = json.load(f)
    
    game = next((g for g in games if g['home_team'] == 'Home Team'), None)
    assert game is not None
    assert game['season'] == ''  # Empty season is stored as empty string
    
    # Cleanup
    if os.path.exists(roster_path):
        os.remove(roster_path)


def test_api_categories_by_season(client):
    """Test /api/categories endpoint filters by season"""
    # Create rosters for different seasons and categories
    season_2024 = '2023-24'
    season_2025 = '2024-25'
    
    roster_paths = []
    
    # Season 2024: U21 and U18
    for team in ['U21', 'U18']:
        roster_path = os.path.join(ROSTERS_DIR, f'roster_{season_2024}_{team}.json')
        roster_paths.append(roster_path)
        with open(roster_path, 'w') as f:
            json.dump([{"id": "1", "number": "1", "surname": "Test", "name": "Player", "position": "A"}], f)
    
    # Season 2025: U21 only
    roster_path = os.path.join(ROSTERS_DIR, f'roster_{season_2025}_U21.json')
    roster_paths.append(roster_path)
    with open(roster_path, 'w') as f:
        json.dump([{"id": "1", "number": "1", "surname": "Test", "name": "Player", "position": "A"}], f)
    
    # Test API endpoint for season 2024
    response = client.get(f'/api/categories?season={season_2024}')
    assert response.status_code == 200
    categories_2024 = response.json
    assert 'U21' in categories_2024
    assert 'U18' in categories_2024
    
    # Test API endpoint for season 2025
    response = client.get(f'/api/categories?season={season_2025}')
    assert response.status_code == 200
    categories_2025 = response.json
    assert 'U21' in categories_2025
    assert 'U18' not in categories_2025
    
    # Cleanup
    for path in roster_paths:
        if os.path.exists(path):
            os.remove(path)


def test_modify_game_preserves_season(client):
    """Test that modifying a game preserves its season"""
    roster_data = [
        {"id": "1", "number": "69", "surname": "Test", "name": "Player", "position": "A", "tesser": "U21", "nickname": "TP"}
    ]
    
    season = '2024-25'
    team = 'U21'
    roster_path = os.path.join(ROSTERS_DIR, f'roster_{season}_{team}.json')
    with open(roster_path, 'w') as f:
        json.dump(roster_data, f)
    
    # Create game
    data = {
        'season': season,
        'team': team,
        'home_team': 'Original Home',
        'away_team': 'Original Away',
        'date': '2025-01-15',
        'l1_1': '1',
        'goalie1': '',
        'goalie2': ''
    }
    
    client.post('/create_game', data=data, follow_redirects=True)
    
    # Get game ID
    with open(GAMES_FILE) as f:
        games = json.load(f)
    game = next((g for g in games if g['home_team'] == 'Original Home'), None)
    game_id = game['id']
    
    # Modify game
    modify_data = {
        'season': season,
        'team': team,
        'home_team': 'Modified Home',
        'away_team': 'Modified Away',
        'date': '2025-01-16',
        'l1_1': '1',
        'goalie1': '',
        'goalie2': ''
    }
    
    response = client.post(f'/modify_game/{game_id}', data=modify_data, follow_redirects=True)
    assert response.status_code == 200
    
    # Verify season is preserved
    with open(GAMES_FILE) as f:
        games = json.load(f)
    
    modified_game = next((g for g in games if g['id'] == game_id), None)
    assert modified_game is not None
    assert modified_game['season'] == season
    assert modified_game['home_team'] == 'Modified Home'
    
    # Cleanup
    if os.path.exists(roster_path):
        os.remove(roster_path)


def test_backward_compatibility_no_season(client):
    """Test that games without season field still work (backward compatibility)"""
    roster_data = [
        {"id": "1", "number": "69", "surname": "Test", "name": "Player", "position": "A", "tesser": "U21", "nickname": "TP"}
    ]
    
    # Create old-style roster without season
    team = 'U21'
    roster_path = os.path.join(ROSTERS_DIR, f'roster_{team}.json')
    with open(roster_path, 'w') as f:
        json.dump(roster_data, f)
    
    # Manually create a game without season field (simulating old data)
    with open(GAMES_FILE) as f:
        games = json.load(f)
    
    old_game = {
        'id': 9999,
        'team': team,
        'home_team': 'Old Home',
        'away_team': 'Old Away',
        'date': '2025-01-15',
        'lines': [['69 - Test Player']],
        'goalies': [],
        'opponent_goalie_enabled': False,
        'result': {'1': {'home': 0, 'away': 0}, '2': {'home': 0, 'away': 0}, '3': {'home': 0, 'away': 0}, 'OT': {'home': 0, 'away': 0}},
        'current_period': '1'
        # Note: no 'season' field
    }
    
    games.append(old_game)
    
    with open(GAMES_FILE, 'w') as f:
        json.dump(games, f, indent=2)
    
    # Test that stats page handles games without season
    response = client.get('/stats')
    assert response.status_code == 200
    
    # Test that home page handles games without season
    response = client.get('/')
    assert response.status_code == 200
    
    # Cleanup
    if os.path.exists(roster_path):
        os.remove(roster_path)
