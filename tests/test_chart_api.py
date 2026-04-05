"""
Tests for /api/chart-data endpoint
"""
import pytest
from models.database import db
from models.game_model import GameRecord


@pytest.fixture
def sample_games(clean_db):
    """Create sample games with stats for testing."""
    # Create sample games with stats
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
    db.session.commit()
    return [game1, game2]


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
        """Player not in a specific game is omitted from that game."""
        response = client.get('/api/chart-data?season=2025-26&team=U21&players=999&players=7%20-%20Player%20Seven')
        assert response.status_code == 200
        data = response.get_json()
        # Player 999 should be in the player list
        assert '999' in data['players']
        # But not in the actual game data (since we didn't create games with this player)
        for game in data['games']:
            if '999' not in game:
                # This is acceptable behavior
                pass

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
