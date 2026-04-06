"""
Tests for the analytics API endpoints (/api/player-trends and /api/lineup-combos)
"""
import pytest


class TestPlayerTrendsEndpoint:
    """Test the /api/player-trends endpoint."""

    def test_player_trends_missing_season(self, client):
        """Test that missing season parameter returns 400."""
        response = client.get('/api/player-trends?team=U21&players=Alice')
        assert response.status_code == 400
        assert 'season parameter is required' in response.get_json()['error']

    def test_player_trends_missing_team(self, client):
        """Test that missing team parameter returns 400."""
        response = client.get('/api/player-trends?season=2025-26&players=Alice')
        assert response.status_code == 400
        assert 'team parameter is required' in response.get_json()['error']

    def test_player_trends_missing_players(self, client):
        """Test that missing players parameter returns 400."""
        response = client.get('/api/player-trends?season=2025-26&team=U21')
        assert response.status_code == 400
        assert 'players parameter is required' in response.get_json()['error']

    def test_player_trends_empty_players(self, client):
        """Test that empty players parameter returns 400."""
        response = client.get('/api/player-trends?season=2025-26&team=U21&players=')
        assert response.status_code == 400
        # When players param is empty string, it's treated as missing
        assert 'players parameter' in response.get_json()['error']

    def test_player_trends_no_games_found(self, client):
        """Test that nonexistent season/team returns 200 with empty data."""
        response = client.get('/api/player-trends?season=9999-00&team=NONEXISTENT&players=Alice')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data'] == {}

    def test_player_trends_success(self, client, clean_db):
        """Test successful player trends response with mock data."""
        # Add a test game
        test_game = {
            'id': 1,
            'date': '2025-01-15',
            'season': '2025-26',
            'team': 'U21',
            'home_team': 'Home',
            'away_team': 'Away',
            'lines': [['Alice', 'Bob'], ['Charlie']],
            'goals': {'Alice': 2, 'Bob': 1, 'Charlie': 0},
            'assists': {'Alice': 1, 'Bob': 0, 'Charlie': 1},
            'plusminus': {'Alice': 3, 'Bob': 1, 'Charlie': -2},
            'unforced_errors': {'Alice': 0, 'Bob': 1, 'Charlie': 0},
            'shots_on_goal': {'Alice': 4, 'Bob': 2, 'Charlie': 1},
            'penalties_drawn': {'Alice': 0, 'Bob': 1, 'Charlie': 0},
            'penalties_taken': {'Alice': 0, 'Bob': 0, 'Charlie': 1},
            'game_scores': {'Alice': 5.35, 'Bob': 2.05, 'Charlie': -0.15},
            'result': {'1': {'home': 3, 'away': 1}, '2': {'home': 0, 'away': 0}, '3': {'home': 0, 'away': 0}}
        }
        from services.game_service import save_game
        save_game(test_game)

        # Request trends for Alice and Bob (who have data)
        response = client.get('/api/player-trends?season=2025-26&team=U21&players=Alice,Bob')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'Alice' in data['data']
        assert 'Bob' in data['data']
        # Verify structure of returned data
        assert 'game_scores' in data['data']['Alice']
        assert 'game_ids' in data['data']['Alice']
        assert 'mean_score' in data['data']['Alice']
        assert 'std_dev' in data['data']['Alice']
        assert 'min_score' in data['data']['Alice']
        assert 'max_score' in data['data']['Alice']
        assert 'outliers' in data['data']['Alice']
        assert 'insufficient_data' in data['data']['Alice']

    def test_player_trends_comma_separated_players(self, client, clean_db):
        """Test that comma-separated players are correctly parsed."""
        # Add test games
        test_game = {
            'id': 1,
            'date': '2025-01-15',
            'season': '2025-26',
            'team': 'U21',
            'home_team': 'Home',
            'away_team': 'Away',
            'lines': [['Player One', 'Player Two', 'Player Three']],
            'goals': {'Player One': 1, 'Player Two': 2, 'Player Three': 0},
            'assists': {'Player One': 0, 'Player Two': 1, 'Player Three': 0},
            'plusminus': {'Player One': 1, 'Player Two': 2, 'Player Three': -1},
            'unforced_errors': {'Player One': 0, 'Player Two': 0, 'Player Three': 1},
            'shots_on_goal': {'Player One': 2, 'Player Two': 3, 'Player Three': 1},
            'penalties_drawn': {'Player One': 0, 'Player Two': 0, 'Player Three': 1},
            'penalties_taken': {'Player One': 0, 'Player Two': 1, 'Player Three': 0},
            'game_scores': {'Player One': 1.5, 'Player Two': 3.25, 'Player Three': -0.25},
            'result': {'1': {'home': 2, 'away': 1}, '2': {'home': 1, 'away': 0}, '3': {'home': 0, 'away': 0}}
        }
        from services.game_service import save_game
        save_game(test_game)

        response = client.get('/api/player-trends?season=2025-26&team=U21&players=Player%20One,Player%20Two,Player%20Three')
        assert response.status_code == 200
        data = response.get_json()
        assert 'Player One' in data['data']
        assert 'Player Two' in data['data']
        assert 'Player Three' in data['data']


class TestLineupCombosEndpoint:
    """Test the /api/lineup-combos endpoint."""

    def test_lineup_combos_missing_season(self, client):
        """Test that missing season parameter returns 400."""
        response = client.get('/api/lineup-combos?team=U21')
        assert response.status_code == 400
        assert 'season parameter is required' in response.get_json()['error']

    def test_lineup_combos_missing_team(self, client):
        """Test that missing team parameter returns 400."""
        response = client.get('/api/lineup-combos?season=2025-26')
        assert response.status_code == 400
        assert 'team parameter is required' in response.get_json()['error']

    def test_lineup_combos_invalid_combo_size_range_format(self, client):
        """Test that invalid combo_size_range format returns 400."""
        response = client.get('/api/lineup-combos?season=2025-26&team=U21&combo_size_range=invalid')
        assert response.status_code == 400
        assert 'must be format' in response.get_json()['error']

    def test_lineup_combos_invalid_combo_size_range_values(self, client):
        """Test that non-integer combo_size_range values return 400."""
        response = client.get('/api/lineup-combos?season=2025-26&team=U21&combo_size_range=abc,def')
        assert response.status_code == 400
        assert 'must be integers' in response.get_json()['error']

    def test_lineup_combos_invalid_limit(self, client):
        """Test that non-integer limit returns 400."""
        response = client.get('/api/lineup-combos?season=2025-26&team=U21&limit=abc')
        assert response.status_code == 400
        assert 'must be an integer' in response.get_json()['error']

    def test_lineup_combos_limit_zero(self, client):
        """Test that limit < 1 returns 400."""
        response = client.get('/api/lineup-combos?season=2025-26&team=U21&limit=0')
        assert response.status_code == 400
        assert 'must be at least 1' in response.get_json()['error']

    def test_lineup_combos_no_games_found(self, client):
        """Test that nonexistent season/team returns 200 with empty data."""
        response = client.get('/api/lineup-combos?season=9999-00&team=NONEXISTENT')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data'] == []

    def test_lineup_combos_success(self, client, clean_db):
        """Test successful lineup combos response with mock data."""
        # Add test games
        test_game = {
            'id': 1,
            'date': '2025-01-15',
            'season': '2025-26',
            'team': 'U21',
            'home_team': 'Home',
            'away_team': 'Away',
            'lines': [['Alice', 'Bob', 'Charlie', 'Dave', 'Eve']],
            'goals': {'Alice': 1, 'Bob': 1, 'Charlie': 0, 'Dave': 0, 'Eve': 1},
            'assists': {'Alice': 0, 'Bob': 1, 'Charlie': 1, 'Dave': 0, 'Eve': 0},
            'plusminus': {'Alice': 1, 'Bob': 2, 'Charlie': 0, 'Dave': -1, 'Eve': 1},
            'unforced_errors': {'Alice': 0, 'Bob': 0, 'Charlie': 1, 'Dave': 0, 'Eve': 0},
            'shots_on_goal': {'Alice': 2, 'Bob': 3, 'Charlie': 1, 'Dave': 1, 'Eve': 2},
            'penalties_drawn': {'Alice': 0, 'Bob': 0, 'Charlie': 0, 'Dave': 1, 'Eve': 0},
            'penalties_taken': {'Alice': 0, 'Bob': 0, 'Charlie': 0, 'Dave': 0, 'Eve': 1},
            'game_scores': {'Alice': 2.0, 'Bob': 3.5, 'Charlie': 0.75, 'Dave': -0.25, 'Eve': 2.25},
            'result': {'1': {'home': 3, 'away': 1}, '2': {'home': 0, 'away': 0}, '3': {'home': 0, 'away': 0}}
        }
        from services.game_service import save_game
        save_game(test_game)

        response = client.get('/api/lineup-combos?season=2025-26&team=U21')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        # Response should be a list
        assert isinstance(data['data'], list)
        # Each combo should have required fields
        for combo in data['data']:
            assert 'combo_id' in combo
            assert 'players' in combo
            assert 'combo_size' in combo
            assert 'games_played_together' in combo
            assert 'wins' in combo
            assert 'losses' in combo
            assert 'win_percentage' in combo
            assert 'avg_goal_differential' in combo
            assert 'avg_aggregate_game_score' in combo
            assert 'game_ids' in combo

    def test_lineup_combos_custom_range(self, client, clean_db):
        """Test lineup combos with custom combo_size_range."""
        # Add test games
        test_game = {
            'id': 1,
            'date': '2025-01-15',
            'season': '2025-26',
            'team': 'U21',
            'home_team': 'Home',
            'away_team': 'Away',
            'lines': [['A', 'B', 'C', 'D']],
            'goals': {'A': 1, 'B': 0, 'C': 1, 'D': 0},
            'assists': {'A': 0, 'B': 1, 'C': 0, 'D': 1},
            'plusminus': {'A': 1, 'B': 1, 'C': 1, 'D': 1},
            'unforced_errors': {'A': 0, 'B': 0, 'C': 0, 'D': 0},
            'shots_on_goal': {'A': 2, 'B': 1, 'C': 2, 'D': 1},
            'penalties_drawn': {'A': 0, 'B': 0, 'C': 0, 'D': 0},
            'penalties_taken': {'A': 0, 'B': 0, 'C': 0, 'D': 0},
            'game_scores': {'A': 1.75, 'B': 1.5, 'C': 1.75, 'D': 1.5},
            'result': {'1': {'home': 2, 'away': 0}, '2': {'home': 0, 'away': 0}, '3': {'home': 0, 'away': 0}}
        }
        from services.game_service import save_game
        save_game(test_game)

        # Request with custom range (only size 3)
        response = client.get('/api/lineup-combos?season=2025-26&team=U21&combo_size_range=3,3&limit=5')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        # All returned combos should have size 3
        for combo in data['data']:
            assert combo['combo_size'] == 3

    def test_lineup_combos_custom_limit(self, client, clean_db):
        """Test lineup combos with custom limit."""
        # Add test games
        test_game = {
            'id': 1,
            'date': '2025-01-15',
            'season': '2025-26',
            'team': 'U21',
            'home_team': 'Home',
            'away_team': 'Away',
            'lines': [['A', 'B', 'C', 'D', 'E', 'F']],
            'goals': {'A': 1, 'B': 1, 'C': 1, 'D': 1, 'E': 1, 'F': 0},
            'assists': {'A': 0, 'B': 1, 'C': 0, 'D': 1, 'E': 0, 'F': 1},
            'plusminus': {'A': 1, 'B': 1, 'C': 1, 'D': 1, 'E': 1, 'F': 1},
            'unforced_errors': {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'E': 0, 'F': 0},
            'shots_on_goal': {'A': 2, 'B': 2, 'C': 2, 'D': 2, 'E': 2, 'F': 1},
            'penalties_drawn': {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'E': 0, 'F': 0},
            'penalties_taken': {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'E': 0, 'F': 0},
            'game_scores': {'A': 1.75, 'B': 2.0, 'C': 1.75, 'D': 2.0, 'E': 1.75, 'F': 1.5},
            'result': {'1': {'home': 4, 'away': 1}, '2': {'home': 1, 'away': 0}, '3': {'home': 0, 'away': 0}}
        }
        from services.game_service import save_game
        save_game(test_game)

        # Request with limit of 2
        response = client.get('/api/lineup-combos?season=2025-26&team=U21&combo_size_range=5,6&limit=2')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        # The number of combos should not exceed 2 per size
        # Check that we have at most limit * number_of_sizes combos
        size_5_count = sum(1 for c in data['data'] if c['combo_size'] == 5)
        size_6_count = sum(1 for c in data['data'] if c['combo_size'] == 6)
        assert size_5_count <= 2
        assert size_6_count <= 2
