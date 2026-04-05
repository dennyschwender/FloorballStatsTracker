"""
Tests for /api/chart-data endpoint
"""
import pytest
from models.database import db
from models.game_model import GameRecord


@pytest.fixture
def sample_games(clean_db):
    """Create sample games with stats for testing across teams and seasons."""
    # game1: 2025-26 season, U21 team
    game1 = GameRecord(id=1)
    game1.update_from_dict({
        'id': 1,
        'season': '2025-26',
        'team': 'U21',
        'date': '2025-11-14',
        'home_team': 'Team A',
        'away_team': 'Team B',
        'lines': [['7 - Player Seven', '12 - Player Twelve']],
        'goalies': [],
        'goals': {'7 - Player Seven': 2, '12 - Player Twelve': 1},
        'assists': {'7 - Player Seven': 1, '12 - Player Twelve': 0},
        'plusminus': {'7 - Player Seven': 1, '12 - Player Twelve': -1},
        'unforced_errors': {'7 - Player Seven': 0, '12 - Player Twelve': 1},
        'sog': {'7 - Player Seven': 3, '12 - Player Twelve': 2},
        'penalties_taken': {'7 - Player Seven': 0, '12 - Player Twelve': 1},
        'penalties_drawn': {'7 - Player Seven': 1, '12 - Player Twelve': 0},
        'block_shots': {},
        'stolen_balls': {},
        'saves': {},
        'goals_conceded': {},
        'result': {'1': {'home': 2, 'away': 1}, '2': {'home': 0, 'away': 0}, '3': {'home': 0, 'away': 0}},
        'current_period': '3'
    })
    db.session.add(game1)

    # game2: 2025-26 season, U21 team
    game2 = GameRecord(id=2)
    game2.update_from_dict({
        'id': 2,
        'season': '2025-26',
        'team': 'U21',
        'date': '2025-11-21',
        'home_team': 'Team B',
        'away_team': 'Team A',
        'lines': [['7 - Player Seven', '12 - Player Twelve']],
        'goalies': [],
        'goals': {'7 - Player Seven': 1, '12 - Player Twelve': 2},
        'assists': {'7 - Player Seven': 2, '12 - Player Twelve': 1},
        'plusminus': {'7 - Player Seven': 0, '12 - Player Twelve': 2},
        'unforced_errors': {'7 - Player Seven': 1, '12 - Player Twelve': 0},
        'sog': {'7 - Player Seven': 2, '12 - Player Twelve': 4},
        'penalties_taken': {'7 - Player Seven': 1, '12 - Player Twelve': 0},
        'penalties_drawn': {'7 - Player Seven': 0, '12 - Player Twelve': 1},
        'block_shots': {},
        'stolen_balls': {},
        'saves': {},
        'goals_conceded': {},
        'result': {'1': {'home': 1, 'away': 0}, '2': {'home': 1, 'away': 1}, '3': {'home': 0, 'away': 1}},
        'current_period': '3'
    })
    db.session.add(game2)

    # game3: 2024-25 season, U21 team (for season filtering test)
    game3 = GameRecord(id=3)
    game3.update_from_dict({
        'id': 3,
        'season': '2024-25',
        'team': 'U21',
        'date': '2024-11-14',
        'home_team': 'Team A',
        'away_team': 'Team B',
        'lines': [['7 - Player Seven', '12 - Player Twelve']],
        'goalies': [],
        'goals': {'7 - Player Seven': 2, '12 - Player Twelve': 1},
        'assists': {'7 - Player Seven': 1, '12 - Player Twelve': 0},
        'plusminus': {'7 - Player Seven': 1, '12 - Player Twelve': -1},
        'unforced_errors': {'7 - Player Seven': 0, '12 - Player Twelve': 1},
        'sog': {'7 - Player Seven': 3, '12 - Player Twelve': 2},
        'penalties_taken': {'7 - Player Seven': 0, '12 - Player Twelve': 1},
        'penalties_drawn': {'7 - Player Seven': 1, '12 - Player Twelve': 0},
        'block_shots': {},
        'stolen_balls': {},
        'saves': {},
        'goals_conceded': {},
        'result': {'1': {'home': 2, 'away': 1}, '2': {'home': 0, 'away': 0}, '3': {'home': 0, 'away': 0}},
        'current_period': '3'
    })
    db.session.add(game3)

    # game4: 2025-26 season, U18 team (for team filtering test)
    game4 = GameRecord(id=4)
    game4.update_from_dict({
        'id': 4,
        'season': '2025-26',
        'team': 'U18',
        'date': '2025-11-28',
        'home_team': 'Team C',
        'away_team': 'Team D',
        'lines': [['7 - Player Seven', '12 - Player Twelve']],
        'goalies': [],
        'goals': {'7 - Player Seven': 0, '12 - Player Twelve': 3},
        'assists': {'7 - Player Seven': 2, '12 - Player Twelve': 1},
        'plusminus': {'7 - Player Seven': -1, '12 - Player Twelve': 2},
        'unforced_errors': {'7 - Player Seven': 1, '12 - Player Twelve': 0},
        'sog': {'7 - Player Seven': 1, '12 - Player Twelve': 5},
        'penalties_taken': {'7 - Player Seven': 2, '12 - Player Twelve': 0},
        'penalties_drawn': {'7 - Player Seven': 0, '12 - Player Twelve': 1},
        'block_shots': {},
        'stolen_balls': {},
        'saves': {},
        'goals_conceded': {},
        'result': {'1': {'home': 1, 'away': 1}, '2': {'home': 1, 'away': 2}, '3': {'home': 0, 'away': 0}},
        'current_period': '3'
    })
    db.session.add(game4)

    db.session.commit()
    return [game1, game2, game3, game4]


class TestChartDataEndpoint:
    """Test /api/chart-data endpoint."""

    def test_valid_request_returns_data(self, client, sample_games):
        """Valid request with season, team, players returns correct data."""
        response = client.get('/api/chart-data?season=2025-26&team=U21&players=7%20-%20Player%20Seven&players=12%20-%20Player%20Twelve')
        assert response.status_code == 200
        data = response.get_json()

        assert 'players' in data
        assert 'games' in data
        assert data['players'] == ['7 - Player Seven', '12 - Player Twelve']
        # Should only return U21 games in 2025-26 (game1 and game2, not game3 or game4)
        assert len(data['games']) == 2

        # Check first game
        game1 = data['games'][0]
        assert game1['date'] == '2025-11-14'
        assert game1['game_id'] == 1
        assert '7 - Player Seven' in game1
        assert '12 - Player Twelve' in game1
        assert game1['7 - Player Seven']['goals'] == 2
        assert game1['7 - Player Seven']['assists'] == 1

    def test_missing_season_returns_400(self, client, sample_games):
        """Request without season returns 400."""
        response = client.get('/api/chart-data?team=U21&players=7')
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_missing_team_returns_400(self, client, sample_games):
        """Request without team returns 400."""
        response = client.get('/api/chart-data?season=2025-26&players=7')
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_missing_players_returns_400(self, client, sample_games):
        """Request without players returns 400."""
        response = client.get('/api/chart-data?season=2025-26&team=U21')
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data and 'player' in data['error'].lower()

    def test_last_n_games_filtering(self, client, sample_games):
        """last_n_games parameter limits results."""
        response = client.get('/api/chart-data?season=2025-26&team=U21&players=7%20-%20Player%20Seven&last_n_games=1')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['games']) == 1
        assert data['games'][0]['game_id'] == 2  # Most recent game

    def test_nonexistent_season_returns_empty(self, client, sample_games):
        """Request for nonexistent season returns empty games array."""
        response = client.get('/api/chart-data?season=1999-00&team=U21&players=7')
        assert response.status_code == 200
        data = response.get_json()
        assert data['games'] == []

    def test_player_not_in_dataset_omitted_from_game(self, client, sample_games):
        """Player not in a specific game is omitted from response for that game."""
        response = client.get('/api/chart-data?season=2025-26&team=U21&players=999&players=7%20-%20Player%20Seven')
        assert response.status_code == 200
        data = response.get_json()

        # Player 999 is in the request, so should be in the players list
        assert '999' in data['players']
        assert '7 - Player Seven' in data['players']

        # But in the actual games, 999 should NOT appear (because it's not in those games)
        # Only 7 - Player Seven should have stats in each game
        for game in data['games']:
            assert '7 - Player Seven' in game  # This player is in all our sample games
            assert '999' not in game  # This player is not in any game

    def test_game_score_calculated_correctly(self, client, sample_games):
        """Response includes calculated game_score for each player."""
        response = client.get('/api/chart-data?season=2025-26&team=U21&players=7%20-%20Player%20Seven')
        assert response.status_code == 200
        data = response.get_json()

        for game in data['games']:
            assert 'game_score' in game['7 - Player Seven']
            # Game score should be a positive number (or zero)
            assert isinstance(game['7 - Player Seven']['game_score'], (int, float))
            assert game['7 - Player Seven']['game_score'] >= 0

    def test_game_score_formula(self, client, sample_games):
        """Verify game_score formula: goals*3 + assists*2 + sog*0.75 + plusminus*0.5 + penalties_drawn*0.5 - penalties_taken - errors."""
        response = client.get('/api/chart-data?season=2025-26&team=U21&players=7%20-%20Player%20Seven')
        assert response.status_code == 200
        data = response.get_json()

        # game1 (id=1) player "7 - Player Seven" stats:
        # goals: 2, assists: 1, sog: 3, plusminus: 1, penalties_drawn: 1, penalties_taken: 0, errors: 0
        # Expected: 2*3.0 + 1*2.0 + 3*0.75 + 1*0.5 + 1*0.5 - 0*1.0 - 0*1.0
        #         = 6 + 2 + 2.25 + 0.5 + 0.5 - 0 - 0 = 11.25
        game1 = data['games'][0]
        assert game1['game_id'] == 1
        assert game1['7 - Player Seven']['game_score'] == 11.25

    def test_filtering_by_team(self, client, sample_games):
        """Request for specific team returns only games from that team."""
        # Request U21 team in 2025-26 season
        response = client.get('/api/chart-data?season=2025-26&team=U21&players=7%20-%20Player%20Seven')
        assert response.status_code == 200
        data = response.get_json()

        # Should only have 2 U21 games (game1 and game2), not game4 (U18)
        assert len(data['games']) == 2
        for game in data['games']:
            assert game['game_id'] in [1, 2]  # Only U21 games

        # Request U18 team in 2025-26 season
        response = client.get('/api/chart-data?season=2025-26&team=U18&players=7%20-%20Player%20Seven')
        assert response.status_code == 200
        data = response.get_json()

        # Should only have 1 U18 game (game4)
        assert len(data['games']) == 1
        assert data['games'][0]['game_id'] == 4

    def test_filtering_by_season(self, client, sample_games):
        """Request for specific season returns only games from that season."""
        # Request 2025-26 season, U21 team
        response = client.get('/api/chart-data?season=2025-26&team=U21&players=7%20-%20Player%20Seven')
        assert response.status_code == 200
        data = response.get_json()

        # Should only have 2 games from 2025-26 season (game1 and game2), not game3 (2024-25)
        assert len(data['games']) == 2
        for game in data['games']:
            assert game['game_id'] in [1, 2]

        # Request 2024-25 season, U21 team
        response = client.get('/api/chart-data?season=2024-25&team=U21&players=7%20-%20Player%20Seven')
        assert response.status_code == 200
        data = response.get_json()

        # Should only have 1 game from 2024-25 season (game3)
        assert len(data['games']) == 1
        assert data['games'][0]['game_id'] == 3


class TestChartIntegration:
    """Integration tests for the chart feature."""

    def test_stats_page_includes_charts_section(self, client):
        """Stats page includes the charts HTML section."""
        response = client.get('/stats')
        assert response.status_code == 200
        assert b'charts-section' in response.data
        assert b'player-search' in response.data
        assert b'show-chart-btn' in response.data
        assert b'StatsChartUI' in response.data  # JavaScript initialization
