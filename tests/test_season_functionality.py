import pytest
from services.game_service import load_games, save_games
from models.roster import save_roster


def test_season_in_game_creation(client):
    """Test that games are created with season field"""
    roster_data = [
        {"id": "1", "number": "69", "surname": "Test", "name": "Player", "position": "A", "tesser": "U21", "nickname": "TP"}
    ]

    season = '2024-25'
    team = 'U21'
    save_roster(roster_data, team, season)

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
    games = load_games()
    game = next((g for g in games if g['home_team'] == 'Home Team'), None)
    assert game is not None
    assert game['season'] == season
    assert game['team'] == team


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

    save_roster(roster_data_2024, team, season_2024)
    save_roster(roster_data_2025, team, season_2025)

    # Test roster loads correctly for 2024 season (need to specify category)
    response = client.get(f'/roster/?category={team}&season={season_2024}')
    assert response.status_code == 200
    assert b'Player2024' in response.data

    # Test roster loads correctly for 2025 season
    response = client.get(f'/roster/?category={team}&season={season_2025}')
    assert response.status_code == 200
    assert b'Player2025' in response.data


def test_get_all_seasons(client):
    """Test that get_all_seasons returns unique seasons from rosters"""
    seasons = ['2022-23', '2023-24', '2024-25']

    for season in seasons:
        save_roster(
            [{"id": "1", "number": "1", "surname": "Test", "name": "Player", "position": "A"}],
            'TestTeam',
            season
        )

    # Access roster page which should show seasons
    response = client.get('/roster/')
    assert response.status_code == 200 or response.status_code == 302


def test_season_filtering_on_stats(client):
    """Test that stats page can filter by season"""
    roster_data = [
        {"id": "1", "number": "69", "surname": "Test", "name": "Player", "position": "A", "tesser": "U21", "nickname": "TP"}
    ]

    season_2024 = '2023-24'
    season_2025 = '2024-25'
    team = 'U21'

    for season in [season_2024, season_2025]:
        save_roster(roster_data, team, season)

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


def test_empty_season_handling(client):
    """Test that empty season strings are handled correctly"""
    roster_data = [
        {"id": "1", "number": "69", "surname": "Test", "name": "Player", "position": "A", "tesser": "U21", "nickname": "TP"}
    ]

    team = 'U21'
    save_roster(roster_data, team, '')

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
    games = load_games()
    game = next((g for g in games if g['home_team'] == 'Home Team'), None)
    assert game is not None
    assert game['season'] == ''  # Empty season is stored as empty string


def test_api_categories_by_season(client):
    """Test /api/categories endpoint filters by season"""
    season_2024 = '2023-24'
    season_2025 = '2024-25'

    # Season 2024: U21 and U18
    for team in ['U21', 'U18']:
        save_roster(
            [{"id": "1", "number": "1", "surname": "Test", "name": "Player", "position": "A"}],
            team, season_2024
        )

    # Season 2025: U21 only
    save_roster(
        [{"id": "1", "number": "1", "surname": "Test", "name": "Player", "position": "A"}],
        'U21', season_2025
    )

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


def test_modify_game_preserves_season(client):
    """Test that modifying a game preserves its season"""
    roster_data = [
        {"id": "1", "number": "69", "surname": "Test", "name": "Player", "position": "A", "tesser": "U21", "nickname": "TP"}
    ]

    season = '2024-25'
    team = 'U21'
    save_roster(roster_data, team, season)

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
    games = load_games()
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
    games = load_games()
    modified_game = next((g for g in games if g['id'] == game_id), None)
    assert modified_game is not None
    assert modified_game['season'] == season
    assert modified_game['home_team'] == 'Modified Home'


def test_backward_compatibility_no_season(client):
    """Test that games without season field still work (backward compatibility)"""
    roster_data = [
        {"id": "1", "number": "69", "surname": "Test", "name": "Player", "position": "A", "tesser": "U21", "nickname": "TP"}
    ]

    team = 'U21'
    save_roster(roster_data, team, '')

    # Manually insert a game without season field (simulating old data)
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

    save_games([old_game])

    # Test that stats page handles games without season
    response = client.get('/stats')
    assert response.status_code == 200

    # Test that home page handles games without season
    response = client.get('/')
    assert response.status_code == 200
