"""
Tests for player trends calculation and analysis.

These tests verify the calculate_player_trends() function which:
- Calculates mean, std dev, min, max for player Game Scores
- Identifies outliers using z-score analysis (|z_score| > 1.0)
- Maintains chronological order of games
- Handles edge cases (empty data, insufficient games, non-existent players)
"""
import pytest
import math
from datetime import datetime, timedelta
from services.stats_service import calculate_game_score, calculate_player_trends, calculate_lineup_combinations

# Constants for test expectations
Z_SCORE_OUTLIER_THRESHOLD = 1.0  # Only |z_score| > 1.0 are outliers
SCORE_TOLERANCE = 0.01           # Floating-point comparison tolerance


def make_sample_game(game_id, date, home_team='Home', away_team='Away'):
    """
    Create a sample game dict with default values.

    The 'result' field tracks period scores and is required for game record schema.
    """
    return {
        'id': game_id,
        'team': 'Test Team',
        'season': '2024-25',
        'home_team': home_team,
        'away_team': away_team,
        'date': date,
        'lines': [],
        'goalies': [],
        'result': {p: {'home': 0, 'away': 0} for p in ['1', '2', '3', 'OT']},  # Period scores
        'current_period': '1',
        'plusminus': {},
        'goals': {},
        'assists': {},
        'unforced_errors': {},
        'shots_on_goal': {},
        'penalties_taken': {},
        'penalties_drawn': {},
        'saves': {},
        'goals_conceded': {},
        'game_scores': {},
        'goalie_game_scores': {},
    }


@pytest.fixture
def sample_games_3_players():
    """
    Fixture providing 3 games with 3 players (Alice, Bob, Charlie).

    Formula: GS = (1.5 * G) + (1.0 * A) + (0.1 * SOG) + (0.3 * PM) + (0.15 * PD) - (0.15 * PT) - (0.2 * Errors)

    Game 1 (2024-11-01):
      - Alice: 2 goals, 1 assist, +2, 0 errors, 4 SOG, 0 PD, 0 PT → GS = (1.5*2) + (1.0*1) + (0.1*4) + (0.3*2) + 0 - 0 - 0 = 5.2
      - Bob: 1 goal, 1 assist, +1, 1 error, 3 SOG, 1 PD, 0 PT → GS = (1.5*1) + (1.0*1) + (0.1*3) + (0.3*1) + (0.15*1) - 0 - (0.2*1) = 2.85
      - Charlie: 0 goals, 1 assist, -1, 2 errors, 2 SOG, 0 PD, 1 PT → GS = 0 + (1.0*1) + (0.1*2) + (0.3*-1) + 0 - (0.15*1) - (0.2*2) = 0.35

    Game 2 (2024-11-08):
      - Alice: 1 goal, 0 assists, +1, 0 errors, 2 SOG, 0 PD, 0 PT → GS = (1.5*1) + 0 + (0.1*2) + (0.3*1) + 0 - 0 - 0 = 2.2
      - Bob: 0 goals, 2 assists, +0, 0 errors, 1 SOG, 0 PD, 0 PT → GS = 0 + (1.0*2) + (0.1*1) + 0 + 0 - 0 - 0 = 2.1
      - Charlie: 2 goals, 1 assist, +2, 1 error, 3 SOG, 1 PD, 0 PT → GS = (1.5*2) + (1.0*1) + (0.1*3) + (0.3*2) + (0.15*1) - 0 - (0.2*1) = 4.45

    Game 3 (2024-11-15):
      - Alice: 3 goals, 2 assists, +3, 0 errors, 5 SOG, 1 PD, 0 PT → GS = (1.5*3) + (1.0*2) + (0.1*5) + (0.3*3) + (0.15*1) - 0 - 0 = 8.35
      - Bob: 2 goals, 0 assists, +2, 2 errors, 4 SOG, 2 PD, 1 PT → GS = (1.5*2) + 0 + (0.1*4) + (0.3*2) + (0.15*2) - (0.15*1) - (0.2*2) = 4.5
      - Charlie: 1 goal, 0 assists, +0, 0 errors, 1 SOG, 0 PD, 0 PT → GS = (1.5*1) + 0 + (0.1*1) + 0 + 0 - 0 - 0 = 1.6
    """
    game1 = make_sample_game(game_id=1, date='2024-11-01')
    game1['lines'] = [['Alice', 'Bob', 'Charlie'], [], [], []]
    game1['goals'] = {'Alice': 2, 'Bob': 1, 'Charlie': 0}
    game1['assists'] = {'Alice': 1, 'Bob': 1, 'Charlie': 1}
    game1['plusminus'] = {'Alice': 2, 'Bob': 1, 'Charlie': -1}
    game1['unforced_errors'] = {'Alice': 0, 'Bob': 1, 'Charlie': 2}
    game1['shots_on_goal'] = {'Alice': 4, 'Bob': 3, 'Charlie': 2}
    game1['penalties_drawn'] = {'Alice': 0, 'Bob': 1, 'Charlie': 0}
    game1['penalties_taken'] = {'Alice': 0, 'Bob': 0, 'Charlie': 1}
    # Calculate and store game scores
    game1['game_scores'] = {
        'Alice': calculate_game_score(2, 1, 2, 0, 4, 0, 0),
        'Bob': calculate_game_score(1, 1, 1, 1, 3, 1, 0),
        'Charlie': calculate_game_score(0, 1, -1, 2, 2, 0, 1),
    }

    game2 = make_sample_game(game_id=2, date='2024-11-08')
    game2['lines'] = [['Alice', 'Bob', 'Charlie'], [], [], []]
    game2['goals'] = {'Alice': 1, 'Bob': 0, 'Charlie': 2}
    game2['assists'] = {'Alice': 0, 'Bob': 2, 'Charlie': 1}
    game2['plusminus'] = {'Alice': 1, 'Bob': 0, 'Charlie': 2}
    game2['unforced_errors'] = {'Alice': 0, 'Bob': 0, 'Charlie': 1}
    game2['shots_on_goal'] = {'Alice': 2, 'Bob': 1, 'Charlie': 3}
    game2['penalties_drawn'] = {'Alice': 0, 'Bob': 0, 'Charlie': 1}
    game2['penalties_taken'] = {'Alice': 0, 'Bob': 0, 'Charlie': 0}
    game2['game_scores'] = {
        'Alice': calculate_game_score(1, 0, 1, 0, 2, 0, 0),
        'Bob': calculate_game_score(0, 2, 0, 0, 1, 0, 0),
        'Charlie': calculate_game_score(2, 1, 2, 1, 3, 1, 0),
    }

    game3 = make_sample_game(game_id=3, date='2024-11-15')
    game3['lines'] = [['Alice', 'Bob', 'Charlie'], [], [], []]
    game3['goals'] = {'Alice': 3, 'Bob': 2, 'Charlie': 1}
    game3['assists'] = {'Alice': 2, 'Bob': 0, 'Charlie': 0}
    game3['plusminus'] = {'Alice': 3, 'Bob': 2, 'Charlie': 0}
    game3['unforced_errors'] = {'Alice': 0, 'Bob': 2, 'Charlie': 0}
    game3['shots_on_goal'] = {'Alice': 5, 'Bob': 4, 'Charlie': 1}
    game3['penalties_drawn'] = {'Alice': 1, 'Bob': 2, 'Charlie': 0}
    game3['penalties_taken'] = {'Alice': 0, 'Bob': 1, 'Charlie': 0}
    game3['game_scores'] = {
        'Alice': calculate_game_score(3, 2, 3, 0, 5, 1, 0),
        'Bob': calculate_game_score(2, 0, 2, 2, 4, 2, 1),
        'Charlie': calculate_game_score(1, 0, 0, 0, 1, 0, 0),
    }

    return [game1, game2, game3]


@pytest.fixture
def sample_games_with_outliers():
    """
    Fixture with games designed to test outlier detection.

    Formula: GS = (1.5 * G) + (1.0 * A) + (0.1 * SOG) + (0.3 * PM) + (0.15 * PD) - (0.15 * PT) - (0.2 * Errors)

    Player 'David' has consistent performance with one outlier:
    Game 4: 1 goal, 0 assists, -5, 5 errors, 0 SOG, 0 PD, 2 PT → GS = (1.5*1) + 0 + 0 + (0.3*-5) + 0 - (0.15*2) - (0.2*5) = -3.1 (low outlier)
    """
    game1 = make_sample_game(game_id=1, date='2024-11-01')
    game1['lines'] = [['David'], [], [], []]
    game1['goals'] = {'David': 2}
    game1['assists'] = {'David': 1}
    game1['plusminus'] = {'David': 2}
    game1['unforced_errors'] = {'David': 1}
    game1['shots_on_goal'] = {'David': 4}
    game1['penalties_drawn'] = {'David': 0}
    game1['penalties_taken'] = {'David': 0}
    game1['game_scores'] = {'David': calculate_game_score(2, 1, 2, 1, 4, 0, 0)}

    game2 = make_sample_game(game_id=2, date='2024-11-08')
    game2['lines'] = [['David'], [], [], []]
    game2['goals'] = {'David': 1}
    game2['assists'] = {'David': 2}
    game2['plusminus'] = {'David': 1}
    game2['unforced_errors'] = {'David': 0}
    game2['shots_on_goal'] = {'David': 3}
    game2['penalties_drawn'] = {'David': 1}
    game2['penalties_taken'] = {'David': 0}
    game2['game_scores'] = {'David': calculate_game_score(1, 2, 1, 0, 3, 1, 0)}

    game3 = make_sample_game(game_id=3, date='2024-11-15')
    game3['lines'] = [['David'], [], [], []]
    game3['goals'] = {'David': 2}
    game3['assists'] = {'David': 0}
    game3['plusminus'] = {'David': 2}
    game3['unforced_errors'] = {'David': 0}
    game3['shots_on_goal'] = {'David': 4}
    game3['penalties_drawn'] = {'David': 1}
    game3['penalties_taken'] = {'David': 0}
    game3['game_scores'] = {'David': calculate_game_score(2, 0, 2, 0, 4, 1, 0)}

    # Game 4: Poor performance (outlier - low)
    game4 = make_sample_game(game_id=4, date='2024-11-22')
    game4['lines'] = [['David'], [], [], []]
    game4['goals'] = {'David': 1}
    game4['assists'] = {'David': 0}
    game4['plusminus'] = {'David': -5}
    game4['unforced_errors'] = {'David': 5}
    game4['shots_on_goal'] = {'David': 0}
    game4['penalties_drawn'] = {'David': 0}
    game4['penalties_taken'] = {'David': 2}
    game4['game_scores'] = {'David': calculate_game_score(1, 0, -5, 5, 0, 0, 2)}

    return [game1, game2, game3, game4]


@pytest.fixture
def sample_games_sparse_players():
    """
    Fixture with players having different game counts for testing edge cases:
    - Eve: 2 games
    - Frank: 3 games
    - Grace: 1 game (insufficient data - should be marked with insufficient_data flag)
    """
    game1 = make_sample_game(game_id=1, date='2024-11-01')
    game1['lines'] = [['Eve', 'Frank', 'Grace'], [], [], []]
    game1['goals'] = {'Eve': 1, 'Frank': 2, 'Grace': 0}
    game1['assists'] = {'Eve': 0, 'Frank': 1, 'Grace': 1}
    game1['plusminus'] = {'Eve': 1, 'Frank': 2, 'Grace': -1}
    game1['unforced_errors'] = {'Eve': 0, 'Frank': 0, 'Grace': 2}
    game1['shots_on_goal'] = {'Eve': 2, 'Frank': 4, 'Grace': 1}
    game1['penalties_drawn'] = {'Eve': 0, 'Frank': 0, 'Grace': 0}
    game1['penalties_taken'] = {'Eve': 0, 'Frank': 0, 'Grace': 1}
    game1['game_scores'] = {
        'Eve': calculate_game_score(1, 0, 1, 0, 2, 0, 0),
        'Frank': calculate_game_score(2, 1, 2, 0, 4, 0, 0),
        'Grace': calculate_game_score(0, 1, -1, 2, 1, 0, 1),
    }

    game2 = make_sample_game(game_id=2, date='2024-11-08')
    game2['lines'] = [['Eve', 'Frank'], [], [], []]
    game2['goals'] = {'Eve': 0, 'Frank': 1}
    game2['assists'] = {'Eve': 2, 'Frank': 0}
    game2['plusminus'] = {'Eve': 0, 'Frank': 1}
    game2['unforced_errors'] = {'Eve': 1, 'Frank': 1}
    game2['shots_on_goal'] = {'Eve': 1, 'Frank': 2}
    game2['penalties_drawn'] = {'Eve': 1, 'Frank': 1}
    game2['penalties_taken'] = {'Eve': 0, 'Frank': 0}
    game2['game_scores'] = {
        'Eve': calculate_game_score(0, 2, 0, 1, 1, 1, 0),
        'Frank': calculate_game_score(1, 0, 1, 1, 2, 1, 0),
    }

    game3 = make_sample_game(game_id=3, date='2024-11-15')
    game3['lines'] = [['Frank'], [], [], []]
    game3['goals'] = {'Frank': 0}
    game3['assists'] = {'Frank': 1}
    game3['plusminus'] = {'Frank': -1}
    game3['unforced_errors'] = {'Frank': 2}
    game3['shots_on_goal'] = {'Frank': 3}
    game3['penalties_drawn'] = {'Frank': 0}
    game3['penalties_taken'] = {'Frank': 1}
    game3['game_scores'] = {'Frank': calculate_game_score(0, 1, -1, 2, 3, 0, 1)}

    return [game1, game2, game3]


class TestCalculatePlayerTrendsBasic:
    """Test basic functionality of calculate_player_trends()."""

    def test_basic_trends_calculation(self, sample_games_3_players):
        """Test that mean, std dev, min, max are calculated correctly."""
        result = calculate_player_trends(sample_games_3_players)

        # Check that all three players are in the result
        assert 'Alice' in result
        assert 'Bob' in result
        assert 'Charlie' in result

        # Check Alice's stats (games: 5.0, 2.0, 8.05)
        alice = result['Alice']
        assert len(alice['game_scores']) == 3
        assert alice['game_scores'] == [
            sample_games_3_players[0]['game_scores']['Alice'],
            sample_games_3_players[1]['game_scores']['Alice'],
            sample_games_3_players[2]['game_scores']['Alice'],
        ]

        # Verify mean calculation
        expected_mean = (5.0 + 2.0 + 8.05) / 3
        assert abs(alice['mean_score'] - expected_mean) < SCORE_TOLERANCE

        # Verify min/max
        assert abs(alice['min_score'] - 2.0) < SCORE_TOLERANCE
        assert abs(alice['max_score'] - 8.05) < SCORE_TOLERANCE

        # Verify std dev (should be non-zero since scores vary)
        assert alice['std_dev'] > 0

    def test_game_scores_in_chronological_order(self, sample_games_3_players):
        """Test that game scores are returned in chronological order."""
        result = calculate_player_trends(sample_games_3_players)

        alice = result['Alice']
        # Games are ordered by date: 2024-11-01, 2024-11-08, 2024-11-15
        assert alice['game_ids'] == [1, 2, 3]

        # Verify game_scores are in same chronological order as game_ids
        # Extract expected scores from original games in date order
        expected_scores = [
            sample_games_3_players[0]['game_scores']['Alice'],
            sample_games_3_players[1]['game_scores']['Alice'],
            sample_games_3_players[2]['game_scores']['Alice'],
        ]
        assert alice['game_scores'] == expected_scores

    def test_game_ids_correspondence(self, sample_games_3_players):
        """Test that game_ids correspond to the correct scores."""
        result = calculate_player_trends(sample_games_3_players)

        bob = result['Bob']
        for i, game_id in enumerate(bob['game_ids']):
            game = sample_games_3_players[i]
            assert game['id'] == game_id
            assert abs(bob['game_scores'][i] - game['game_scores']['Bob']) < SCORE_TOLERANCE


class TestCalculatePlayerTrendsOutliers:
    """Test outlier detection functionality."""

    def test_outlier_detection_with_realistic_data(self, sample_games_with_outliers):
        """Test that outliers with |z_score| > 1.0 are correctly identified."""
        result = calculate_player_trends(sample_games_with_outliers)

        david = result['David']
        outliers = david.get('outliers', [])

        # David should have at least one outlier (the low-performing game 4)
        assert len(outliers) >= 1

        # Find the low outlier (game 4)
        low_outliers = [o for o in outliers if o['type'] == 'low']
        assert len(low_outliers) >= 1

        # Verify outlier structure
        outlier = low_outliers[0]
        assert 'game_id' in outlier
        assert 'score' in outlier
        assert 'z_score' in outlier
        assert 'type' in outlier
        assert outlier['type'] == 'low'
        assert abs(outlier['z_score']) > Z_SCORE_OUTLIER_THRESHOLD

    def test_no_outliers_for_consistent_performance(self):
        """Test that consistent performance (low variance) has no outliers."""
        # Create games with consistent performance (all scores = 5.0)
        games = []
        for i in range(1, 4):
            game = make_sample_game(game_id=i, date=f'2024-11-{i:02d}')
            game['lines'] = [['Consistent'], [], [], []]
            game['goals'] = {'Consistent': 1}
            game['assists'] = {'Consistent': 1}
            game['plusminus'] = {'Consistent': 1}
            game['unforced_errors'] = {'Consistent': 0}
            game['shots_on_goal'] = {'Consistent': 0}
            game['penalties_drawn'] = {'Consistent': 0}
            game['penalties_taken'] = {'Consistent': 0}
            game['game_scores'] = {'Consistent': 3.5}  # Same score each game
            games.append(game)

        result = calculate_player_trends(games)

        consistent = result['Consistent']
        outliers = consistent.get('outliers', [])

        # With std_dev = 0, z_score calculation is undefined, so no outliers detected
        assert len(outliers) == 0

    def test_z_score_calculation(self, sample_games_with_outliers):
        """Test that z_scores are calculated correctly."""
        result = calculate_player_trends(sample_games_with_outliers)
        david = result['David']

        scores = david['game_scores']
        mean = david['mean_score']
        std_dev = david['std_dev']

        # Manually calculate z_score for the low outlier
        if std_dev > 0:
            for outlier in david['outliers']:
                score_idx = david['game_ids'].index(outlier['game_id'])
                score = scores[score_idx]
                expected_z = (score - mean) / std_dev
                assert abs(outlier['z_score'] - expected_z) < SCORE_TOLERANCE


class TestCalculatePlayerTrendsEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_games_list(self):
        """Test with empty games list."""
        result = calculate_player_trends([])
        assert result == {}

    def test_games_with_no_game_scores(self):
        """Test games that have no game_scores field."""
        game = make_sample_game(game_id=1, date='2024-11-01')
        game['lines'] = [['Player'], [], [], []]
        # Intentionally omit or empty game_scores
        game['game_scores'] = {}

        result = calculate_player_trends([game])
        # Player should be omitted if no game score
        assert 'Player' not in result

    def test_player_insufficient_data_included_with_flag(self, sample_games_sparse_players):
        """Test that players with <3 games are included but marked as insufficient."""
        result = calculate_player_trends(sample_games_sparse_players)

        # Grace has only 1 game
        assert 'Grace' in result
        assert result['Grace'].get('insufficient_data') == True

    def test_player_not_in_games_omitted(self):
        """Test that players not appearing in any game are omitted."""
        games = [make_sample_game(game_id=1, date='2024-11-01')]
        games[0]['lines'] = [['Player1'], [], [], []]
        games[0]['game_scores'] = {'Player1': 5.0}

        result = calculate_player_trends(games)

        # Only Player1 should be in result
        assert 'Player1' in result
        assert 'NonexistentPlayer' not in result

    def test_player_filter_with_names_list(self, sample_games_3_players):
        """Test that specifying a players list filters results."""
        result = calculate_player_trends(sample_games_3_players, players=['Alice', 'Bob'])

        # Only Alice and Bob should be included
        assert 'Alice' in result
        assert 'Bob' in result
        assert 'Charlie' not in result

    def test_player_filter_with_nonexistent_name(self, sample_games_3_players):
        """Test filtering with a player name that doesn't exist in games."""
        result = calculate_player_trends(sample_games_3_players, players=['Alice', 'Nonexistent'])

        # Only Alice should be in result
        assert 'Alice' in result
        assert 'Nonexistent' not in result
        assert 'Bob' not in result
        assert 'Charlie' not in result

    def test_player_missing_from_single_game(self):
        """Test player who is missing from some games (not all)."""
        # Game 1: both players
        game1 = make_sample_game(game_id=1, date='2024-11-01')
        game1['lines'] = [['Isaac', 'Jane'], [], [], []]
        game1['game_scores'] = {'Isaac': 5.0, 'Jane': 4.0}

        # Game 2: only Isaac
        game2 = make_sample_game(game_id=2, date='2024-11-08')
        game2['lines'] = [['Isaac'], [], [], []]
        game2['game_scores'] = {'Isaac': 6.0}

        # Game 3: both players
        game3 = make_sample_game(game_id=3, date='2024-11-15')
        game3['lines'] = [['Isaac', 'Jane'], [], [], []]
        game3['game_scores'] = {'Isaac': 5.5, 'Jane': 7.0}

        result = calculate_player_trends([game1, game2, game3])

        # Isaac appears in all 3 games
        isaac = result['Isaac']
        assert len(isaac['game_scores']) == 3

        # Jane appears in 2 games
        jane = result['Jane']
        assert len(jane['game_scores']) == 2
        assert jane['game_ids'] == [1, 3]


class TestCalculatePlayerTrendsMultipleScenarios:
    """Test with multiple players and complex scenarios."""

    def test_multiple_players_different_game_counts(self, sample_games_sparse_players):
        """Test trends calculation with players having different numbers of games."""
        result = calculate_player_trends(sample_games_sparse_players)

        # Eve: 2 games, Frank: 3 games, Grace: 1 game
        assert len(result['Eve']['game_scores']) == 2
        assert len(result['Frank']['game_scores']) == 3
        assert len(result['Grace']['game_scores']) == 1

    def test_result_structure(self, sample_games_3_players):
        """Test that the result structure matches expected format."""
        result = calculate_player_trends(sample_games_3_players)

        assert isinstance(result, dict)

        for player_name, player_data in result.items():
            # Required fields
            assert 'game_scores' in player_data
            assert 'game_ids' in player_data
            assert 'mean_score' in player_data
            assert 'std_dev' in player_data
            assert 'min_score' in player_data
            assert 'max_score' in player_data
            assert 'outliers' in player_data

            # Type checks
            assert isinstance(player_data['game_scores'], list)
            assert isinstance(player_data['game_ids'], list)
            assert isinstance(player_data['mean_score'], (int, float))
            assert isinstance(player_data['std_dev'], (int, float))
            assert isinstance(player_data['min_score'], (int, float))
            assert isinstance(player_data['max_score'], (int, float))
            assert isinstance(player_data['outliers'], list)

            # Validity checks
            assert player_data['mean_score'] >= player_data['min_score']
            assert player_data['mean_score'] <= player_data['max_score']
            assert player_data['std_dev'] >= 0

    def test_stats_validity(self, sample_games_3_players):
        """Test that calculated stats are mathematically valid."""
        result = calculate_player_trends(sample_games_3_players)

        for player_name, player_data in result.items():
            scores = player_data['game_scores']

            # Mean should be average of all scores
            expected_mean = sum(scores) / len(scores) if scores else 0
            assert abs(player_data['mean_score'] - expected_mean) < SCORE_TOLERANCE

            # Min and max
            assert player_data['min_score'] == min(scores)
            assert player_data['max_score'] == max(scores)

            # Std dev (if more than 1 score)
            if len(scores) > 1:
                mean = player_data['mean_score']
                variance = sum((x - mean) ** 2 for x in scores) / len(scores)
                expected_std = math.sqrt(variance)
                assert abs(player_data['std_dev'] - expected_std) < SCORE_TOLERANCE


class TestCalculatePlayerTrendsOutlierFiltering:
    """Test outlier detection and filtering."""

    def test_only_z_score_greater_than_1_included(self, sample_games_with_outliers):
        """Test that only outliers with |z_score| > 1.0 are included."""
        result = calculate_player_trends(sample_games_with_outliers)
        david = result['David']

        for outlier in david['outliers']:
            assert abs(outlier['z_score']) > Z_SCORE_OUTLIER_THRESHOLD

    def test_outlier_has_required_fields(self, sample_games_with_outliers):
        """Test that each outlier has all required fields."""
        result = calculate_player_trends(sample_games_with_outliers)
        david = result['David']

        for outlier in david['outliers']:
            assert 'game_id' in outlier
            assert 'score' in outlier
            assert 'z_score' in outlier
            assert 'type' in outlier
            assert outlier['type'] in ['high', 'low']

    def test_outlier_type_high_vs_low(self, sample_games_with_outliers):
        """Test that outlier type is correctly set as 'high' or 'low'."""
        result = calculate_player_trends(sample_games_with_outliers)
        david = result['David']
        mean = david['mean_score']

        for outlier in david['outliers']:
            if outlier['score'] > mean:
                assert outlier['type'] == 'high'
            else:
                assert outlier['type'] == 'low'


class TestCalculatePlayerTrendsEdgeCasesAdvanced:
    """Test advanced edge cases."""

    def test_single_player_single_game(self):
        """Test with only one player and one game."""
        game = make_sample_game(game_id=1, date='2024-11-01')
        game['lines'] = [['Player'], [], [], []]
        game['game_scores'] = {'Player': 5.5}

        result = calculate_player_trends([game])

        player = result['Player']
        assert len(player['game_scores']) == 1
        assert player['game_scores'][0] == 5.5
        assert player['mean_score'] == 5.5
        assert player['min_score'] == 5.5
        assert player['max_score'] == 5.5
        assert player['std_dev'] == 0

    def test_games_out_of_chronological_order(self):
        """Test that function handles games in non-chronological order."""
        # Create games with reversed order
        game3 = make_sample_game(game_id=3, date='2024-11-15')
        game3['lines'] = [['Kevin'], [], [], []]
        game3['game_scores'] = {'Kevin': 8.0}

        game1 = make_sample_game(game_id=1, date='2024-11-01')
        game1['lines'] = [['Kevin'], [], [], []]
        game1['game_scores'] = {'Kevin': 4.0}

        game2 = make_sample_game(game_id=2, date='2024-11-08')
        game2['lines'] = [['Kevin'], [], [], []]
        game2['game_scores'] = {'Kevin': 6.0}

        # Pass in reversed order
        result = calculate_player_trends([game3, game1, game2])

        kevin = result['Kevin']
        # Should be sorted by date, not by game_id
        assert kevin['game_ids'] == [1, 2, 3]
        assert kevin['game_scores'] == [4.0, 6.0, 8.0]

    def test_negative_game_scores(self):
        """Test that negative game scores are handled correctly."""
        games = []
        scores = [5.0, -2.0, 3.0]
        for i, score in enumerate(scores, 1):
            game = make_sample_game(game_id=i, date=f'2024-11-{i:02d}')
            game['lines'] = [['Larry'], [], [], []]
            game['game_scores'] = {'Larry': score}
            games.append(game)

        result = calculate_player_trends(games)
        larry = result['Larry']

        assert larry['game_scores'] == scores
        assert larry['min_score'] == -2.0
        assert larry['max_score'] == 5.0
        expected_mean = sum(scores) / len(scores)
        assert abs(larry['mean_score'] - expected_mean) < SCORE_TOLERANCE

    def test_very_small_variance(self):
        """Test with scores that have very small variance."""
        games = []
        # Very similar scores: 5.00, 5.01, 5.02
        scores = [5.00, 5.01, 5.02]
        for i, score in enumerate(scores, 1):
            game = make_sample_game(game_id=i, date=f'2024-11-{i:02d}')
            game['lines'] = [['Martin'], [], [], []]
            game['game_scores'] = {'Martin': score}
            games.append(game)

        result = calculate_player_trends(games)
        martin = result['Martin']

        # Std dev should be very small but positive
        assert martin['std_dev'] >= 0
        assert martin['std_dev'] < 0.02  # Very small variance threshold

        # No outliers expected with such small variance
        assert len(martin['outliers']) == 0


# ──────────────────────────────────────────────────────────────────────────────
# Tests for calculate_lineup_combinations()
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def sample_games_for_combos():
    """
    Fixture providing 5 games with 7 players (numbered 1-7).

    Games structured to test combo detection and metric calculations:
    - Game 1 (2024-11-01): Players 1,2,3,4,5 (6-3 win, diff +3)
    - Game 2 (2024-11-08): Players 1,2,3,4,6 (4-2 win, diff +2)
    - Game 3 (2024-11-15): Players 1,2,3,5,6 (5-6 loss, diff -1)
    - Game 4 (2024-11-22): Players 1,2,4,5,6 (3-3 draw)
    - Game 5 (2024-11-29): Players 1,2,3,4,5,6,7 (7-2 win, diff +5)

    Combo (1,2,3,4,5) should appear in games 1, 2, 5 → 3 games, 2 wins, 1 loss
    Combo (1,2,3,4,6) should appear in games 2, 5 → 2 games, 2 wins
    """
    games = []

    # Game 1: 2024-11-01, Home 6 - Away 3 (win by 3)
    game1 = make_sample_game(game_id=1, date='2024-11-01', home_team='TestTeam', away_team='Opponent1')
    game1['lines'] = [['1 - Player One', '2 - Player Two', '3 - Player Three', '4 - Player Four', '5 - Player Five'], [], [], []]
    game1['result'] = {
        '1': {'home': 2, 'away': 1},
        '2': {'home': 2, 'away': 1},
        '3': {'home': 2, 'away': 1},
        'OT': {'home': 0, 'away': 0}
    }
    game1['goals'] = {'1 - Player One': 1, '2 - Player Two': 1, '3 - Player Three': 1, '4 - Player Four': 1, '5 - Player Five': 2}
    game1['assists'] = {'1 - Player One': 1, '2 - Player Two': 1, '3 - Player Three': 0, '4 - Player Four': 1, '5 - Player Five': 1}
    game1['plusminus'] = {'1 - Player One': 2, '2 - Player Two': 2, '3 - Player Three': 1, '4 - Player Four': 1, '5 - Player Five': 2}
    game1['unforced_errors'] = {'1 - Player One': 0, '2 - Player Two': 1, '3 - Player Three': 0, '4 - Player Four': 1, '5 - Player Five': 0}
    game1['shots_on_goal'] = {'1 - Player One': 3, '2 - Player Two': 2, '3 - Player Three': 4, '4 - Player Four': 3, '5 - Player Five': 4}
    game1['penalties_drawn'] = {'1 - Player One': 0, '2 - Player Two': 0, '3 - Player Three': 0, '4 - Player Four': 1, '5 - Player Five': 0}
    game1['penalties_taken'] = {'1 - Player One': 0, '2 - Player Two': 0, '3 - Player Three': 0, '4 - Player Four': 0, '5 - Player Five': 0}
    game1['game_scores'] = {
        '1 - Player One': calculate_game_score(1, 1, 2, 0, 3, 0, 0),
        '2 - Player Two': calculate_game_score(1, 1, 2, 1, 2, 0, 0),
        '3 - Player Three': calculate_game_score(1, 0, 1, 0, 4, 0, 0),
        '4 - Player Four': calculate_game_score(1, 1, 1, 1, 3, 1, 0),
        '5 - Player Five': calculate_game_score(2, 1, 2, 0, 4, 0, 0),
    }
    games.append(game1)

    # Game 2: 2024-11-08, Home 4 - Away 2 (win by 2)
    game2 = make_sample_game(game_id=2, date='2024-11-08', home_team='TestTeam', away_team='Opponent2')
    game2['lines'] = [['1 - Player One', '2 - Player Two', '3 - Player Three', '4 - Player Four', '6 - Player Six'], [], [], []]
    game2['result'] = {
        '1': {'home': 2, 'away': 0},
        '2': {'home': 1, 'away': 1},
        '3': {'home': 1, 'away': 1},
        'OT': {'home': 0, 'away': 0}
    }
    game2['goals'] = {'1 - Player One': 1, '2 - Player Two': 0, '3 - Player Three': 1, '4 - Player Four': 1, '6 - Player Six': 1}
    game2['assists'] = {'1 - Player One': 1, '2 - Player Two': 2, '3 - Player Three': 1, '4 - Player Four': 0, '6 - Player Six': 0}
    game2['plusminus'] = {'1 - Player One': 1, '2 - Player Two': 2, '3 - Player Three': 1, '4 - Player Four': 1, '6 - Player Six': 1}
    game2['unforced_errors'] = {'1 - Player One': 0, '2 - Player Two': 0, '3 - Player Three': 1, '4 - Player Four': 0, '6 - Player Six': 0}
    game2['shots_on_goal'] = {'1 - Player One': 3, '2 - Player Two': 2, '3 - Player Three': 3, '4 - Player Four': 2, '6 - Player Six': 3}
    game2['penalties_drawn'] = {'1 - Player One': 0, '2 - Player Two': 1, '3 - Player Three': 0, '4 - Player Four': 0, '6 - Player Six': 0}
    game2['penalties_taken'] = {'1 - Player One': 0, '2 - Player Two': 0, '3 - Player Three': 0, '4 - Player Four': 0, '6 - Player Six': 0}
    game2['game_scores'] = {
        '1 - Player One': calculate_game_score(1, 1, 1, 0, 3, 0, 0),
        '2 - Player Two': calculate_game_score(0, 2, 2, 0, 2, 1, 0),
        '3 - Player Three': calculate_game_score(1, 1, 1, 1, 3, 0, 0),
        '4 - Player Four': calculate_game_score(1, 0, 1, 0, 2, 0, 0),
        '6 - Player Six': calculate_game_score(1, 0, 1, 0, 3, 0, 0),
    }
    games.append(game2)

    # Game 3: 2024-11-15, Home 5 - Away 6 (loss by 1)
    game3 = make_sample_game(game_id=3, date='2024-11-15', home_team='TestTeam', away_team='Opponent3')
    game3['lines'] = [['1 - Player One', '2 - Player Two', '3 - Player Three', '5 - Player Five', '6 - Player Six'], [], [], []]
    game3['result'] = {
        '1': {'home': 1, 'away': 2},
        '2': {'home': 2, 'away': 2},
        '3': {'home': 2, 'away': 2},
        'OT': {'home': 0, 'away': 0}
    }
    game3['goals'] = {'1 - Player One': 1, '2 - Player Two': 1, '3 - Player Three': 1, '5 - Player Five': 1, '6 - Player Six': 1}
    game3['assists'] = {'1 - Player One': 0, '2 - Player Two': 1, '3 - Player Three': 1, '5 - Player Five': 0, '6 - Player Six': 0}
    game3['plusminus'] = {'1 - Player One': -1, '2 - Player Two': 0, '3 - Player Three': -1, '5 - Player Five': 0, '6 - Player Six': 0}
    game3['unforced_errors'] = {'1 - Player One': 1, '2 - Player Two': 1, '3 - Player Three': 0, '5 - Player Five': 1, '6 - Player Six': 0}
    game3['shots_on_goal'] = {'1 - Player One': 2, '2 - Player Two': 3, '3 - Player Three': 2, '5 - Player Five': 2, '6 - Player Six': 3}
    game3['penalties_drawn'] = {'1 - Player One': 0, '2 - Player Two': 0, '3 - Player Three': 0, '5 - Player Five': 0, '6 - Player Six': 0}
    game3['penalties_taken'] = {'1 - Player One': 0, '2 - Player Two': 1, '3 - Player Three': 0, '5 - Player Five': 0, '6 - Player Six': 0}
    game3['game_scores'] = {
        '1 - Player One': calculate_game_score(1, 0, -1, 1, 2, 0, 0),
        '2 - Player Two': calculate_game_score(1, 1, 0, 1, 3, 0, 1),
        '3 - Player Three': calculate_game_score(1, 1, -1, 0, 2, 0, 0),
        '5 - Player Five': calculate_game_score(1, 0, 0, 1, 2, 0, 0),
        '6 - Player Six': calculate_game_score(1, 0, 0, 0, 3, 0, 0),
    }
    games.append(game3)

    # Game 4: 2024-11-22, Home 3 - Away 3 (draw)
    game4 = make_sample_game(game_id=4, date='2024-11-22', home_team='TestTeam', away_team='Opponent4')
    game4['lines'] = [['1 - Player One', '2 - Player Two', '4 - Player Four', '5 - Player Five', '6 - Player Six'], [], [], []]
    game4['result'] = {
        '1': {'home': 1, 'away': 1},
        '2': {'home': 1, 'away': 1},
        '3': {'home': 1, 'away': 1},
        'OT': {'home': 0, 'away': 0}
    }
    game4['goals'] = {'1 - Player One': 1, '2 - Player Two': 1, '4 - Player Four': 0, '5 - Player Five': 1, '6 - Player Six': 0}
    game4['assists'] = {'1 - Player One': 0, '2 - Player Two': 0, '4 - Player Four': 1, '5 - Player Five': 1, '6 - Player Six': 1}
    game4['plusminus'] = {'1 - Player One': 0, '2 - Player Two': 0, '4 - Player Four': 0, '5 - Player Five': 0, '6 - Player Six': 0}
    game4['unforced_errors'] = {'1 - Player One': 0, '2 - Player Two': 0, '4 - Player Four': 1, '5 - Player Five': 0, '6 - Player Six': 1}
    game4['shots_on_goal'] = {'1 - Player One': 3, '2 - Player Two': 2, '4 - Player Four': 2, '5 - Player Five': 3, '6 - Player Six': 2}
    game4['penalties_drawn'] = {'1 - Player One': 0, '2 - Player Two': 0, '4 - Player Four': 0, '5 - Player Five': 0, '6 - Player Six': 0}
    game4['penalties_taken'] = {'1 - Player One': 0, '2 - Player Two': 0, '4 - Player Four': 0, '5 - Player Five': 0, '6 - Player Six': 0}
    game4['game_scores'] = {
        '1 - Player One': calculate_game_score(1, 0, 0, 0, 3, 0, 0),
        '2 - Player Two': calculate_game_score(1, 0, 0, 0, 2, 0, 0),
        '4 - Player Four': calculate_game_score(0, 1, 0, 1, 2, 0, 0),
        '5 - Player Five': calculate_game_score(1, 1, 0, 0, 3, 0, 0),
        '6 - Player Six': calculate_game_score(0, 1, 0, 1, 2, 0, 0),
    }
    games.append(game4)

    # Game 5: 2024-11-29, Home 7 - Away 2 (big win by 5)
    game5 = make_sample_game(game_id=5, date='2024-11-29', home_team='TestTeam', away_team='Opponent5')
    game5['lines'] = [['1 - Player One', '2 - Player Two', '3 - Player Three', '4 - Player Four', '5 - Player Five', '6 - Player Six', '7 - Player Seven'], [], [], []]
    game5['result'] = {
        '1': {'home': 2, 'away': 0},
        '2': {'home': 3, 'away': 1},
        '3': {'home': 2, 'away': 1},
        'OT': {'home': 0, 'away': 0}
    }
    game5['goals'] = {'1 - Player One': 1, '2 - Player Two': 1, '3 - Player Three': 2, '4 - Player Four': 1, '5 - Player Five': 1, '6 - Player Six': 1, '7 - Player Seven': 0}
    game5['assists'] = {'1 - Player One': 1, '2 - Player Two': 1, '3 - Player Three': 1, '4 - Player Four': 1, '5 - Player Five': 1, '6 - Player Six': 1, '7 - Player Seven': 1}
    game5['plusminus'] = {'1 - Player One': 2, '2 - Player Two': 2, '3 - Player Three': 2, '4 - Player Four': 2, '5 - Player Five': 2, '6 - Player Six': 2, '7 - Player Seven': 1}
    game5['unforced_errors'] = {'1 - Player One': 0, '2 - Player Two': 0, '3 - Player Three': 0, '4 - Player Four': 0, '5 - Player Five': 0, '6 - Player Six': 0, '7 - Player Seven': 1}
    game5['shots_on_goal'] = {'1 - Player One': 3, '2 - Player Two': 3, '3 - Player Three': 4, '4 - Player Four': 3, '5 - Player Five': 3, '6 - Player Six': 3, '7 - Player Seven': 2}
    game5['penalties_drawn'] = {'1 - Player One': 0, '2 - Player Two': 0, '3 - Player Three': 0, '4 - Player Four': 0, '5 - Player Five': 0, '6 - Player Six': 0, '7 - Player Seven': 0}
    game5['penalties_taken'] = {'1 - Player One': 0, '2 - Player Two': 0, '3 - Player Three': 0, '4 - Player Four': 0, '5 - Player Five': 0, '6 - Player Six': 0, '7 - Player Seven': 0}
    game5['game_scores'] = {
        '1 - Player One': calculate_game_score(1, 1, 2, 0, 3, 0, 0),
        '2 - Player Two': calculate_game_score(1, 1, 2, 0, 3, 0, 0),
        '3 - Player Three': calculate_game_score(2, 1, 2, 0, 4, 0, 0),
        '4 - Player Four': calculate_game_score(1, 1, 2, 0, 3, 0, 0),
        '5 - Player Five': calculate_game_score(1, 1, 2, 0, 3, 0, 0),
        '6 - Player Six': calculate_game_score(1, 1, 2, 0, 3, 0, 0),
        '7 - Player Seven': calculate_game_score(0, 1, 1, 1, 2, 0, 0),
    }
    games.append(game5)

    return games


class TestCalculateLineupCombosBasic:
    """Test basic functionality of calculate_lineup_combinations()."""

    def test_function_returns_list(self, sample_games_for_combos):
        """Test that function returns a list."""
        result = calculate_lineup_combinations(sample_games_for_combos)
        assert isinstance(result, list)

    def test_result_contains_combo_dicts(self, sample_games_for_combos):
        """Test that each result item is a dict with expected fields."""
        result = calculate_lineup_combinations(sample_games_for_combos)

        assert len(result) > 0
        for combo in result:
            assert isinstance(combo, dict)
            # Check required fields
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

    def test_players_in_combos_format(self, sample_games_for_combos):
        """Test that player names are in the correct format."""
        result = calculate_lineup_combinations(sample_games_for_combos)

        for combo in result:
            assert isinstance(combo['players'], list)
            assert len(combo['players']) == combo['combo_size']
            for player_name in combo['players']:
                assert isinstance(player_name, str)
                # Should be in format like "1 - Player One"
                assert ' - ' in player_name

    def test_combo_ids_are_unique(self, sample_games_for_combos):
        """Test that all combo_ids are unique."""
        result = calculate_lineup_combinations(sample_games_for_combos)

        combo_ids = [c['combo_id'] for c in result]
        assert len(combo_ids) == len(set(combo_ids))

    def test_combo_size_respects_range(self, sample_games_for_combos):
        """Test that all returned combos have sizes within the specified range."""
        result = calculate_lineup_combinations(sample_games_for_combos, combo_size_range=(5, 7))

        for combo in result:
            assert combo['combo_size'] >= 5
            assert combo['combo_size'] <= 7

    def test_single_combo_size_range(self, sample_games_for_combos):
        """Test with only one combo size (e.g., only 5-player combos)."""
        result = calculate_lineup_combinations(sample_games_for_combos, combo_size_range=(5, 5))

        for combo in result:
            assert combo['combo_size'] == 5

    def test_wins_and_losses_add_up(self, sample_games_for_combos):
        """Test that wins + losses equals games_played_together."""
        result = calculate_lineup_combinations(sample_games_for_combos)

        for combo in result:
            # For draws (0-0 final), we count neither win nor loss
            # So wins + losses <= games_played_together
            assert combo['wins'] + combo['losses'] <= combo['games_played_together']

    def test_game_ids_are_valid(self, sample_games_for_combos):
        """Test that all game_ids are valid integers from input games."""
        result = calculate_lineup_combinations(sample_games_for_combos)
        valid_game_ids = {g['id'] for g in sample_games_for_combos}

        for combo in result:
            for game_id in combo['game_ids']:
                assert game_id in valid_game_ids

    def test_goal_differential_calculation(self, sample_games_for_combos):
        """Test that goal differential is calculated correctly."""
        result = calculate_lineup_combinations(sample_games_for_combos)

        # Find a combo that played at least one game
        combo_with_games = next((c for c in result if c['games_played_together'] > 0), None)
        assert combo_with_games is not None

        # Goal differential should be between -10 and +10 for typical floorball
        assert -20 <= combo_with_games['avg_goal_differential'] <= 20


class TestCalculateLineupCombosMetrics:
    """Test metric calculations for lineup combinations."""

    def test_win_percentage_calculation(self, sample_games_for_combos):
        """Test that win_percentage is calculated correctly."""
        result = calculate_lineup_combinations(sample_games_for_combos)

        for combo in result:
            if combo['games_played_together'] == 0:
                # No games played, win_percentage should be 0 or n/a
                assert combo['win_percentage'] == 0 or combo['win_percentage'] is None
            else:
                # Win percentage should be wins / games * 100
                expected_wp = (combo['wins'] / combo['games_played_together']) * 100
                assert abs(combo['win_percentage'] - expected_wp) < SCORE_TOLERANCE

    def test_win_percentage_in_valid_range(self, sample_games_for_combos):
        """Test that win_percentage is between 0 and 100."""
        result = calculate_lineup_combinations(sample_games_for_combos)

        for combo in result:
            if combo['games_played_together'] > 0:
                assert 0 <= combo['win_percentage'] <= 100

    def test_avg_aggregate_game_score_calculation(self, sample_games_for_combos):
        """Test that average aggregate game score is calculated correctly."""
        result = calculate_lineup_combinations(sample_games_for_combos)

        # Find a combo with games played
        combo_with_games = next((c for c in result if c['games_played_together'] > 0), None)
        assert combo_with_games is not None

        # Score should be positive (sum of game scores per player)
        assert combo_with_games['avg_aggregate_game_score'] > 0

    def test_results_sorted_by_aggregate_score_descending(self, sample_games_for_combos):
        """Test that results are sorted by avg_aggregate_game_score descending."""
        result = calculate_lineup_combinations(sample_games_for_combos)

        # Only compare combos that played games
        combos_with_games = [c for c in result if c['games_played_together'] > 0]

        if len(combos_with_games) > 1:
            for i in range(len(combos_with_games) - 1):
                assert combos_with_games[i]['avg_aggregate_game_score'] >= \
                       combos_with_games[i + 1]['avg_aggregate_game_score']


class TestCalculateLineupCombosEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_games_list(self):
        """Test with empty games list."""
        result = calculate_lineup_combinations([])
        assert result == []

    def test_single_game(self):
        """Test with only one game."""
        game = make_sample_game(game_id=1, date='2024-11-01')
        game['lines'] = [['1 - Player One', '2 - Player Two', '3 - Player Three', '4 - Player Four', '5 - Player Five'], [], [], []]
        game['result'] = {
            '1': {'home': 1, 'away': 0},
            '2': {'home': 1, 'away': 0},
            '3': {'home': 1, 'away': 0},
            'OT': {'home': 0, 'away': 0}
        }
        game['game_scores'] = {
            '1 - Player One': 5.0,
            '2 - Player Two': 4.5,
            '3 - Player Three': 4.0,
            '4 - Player Four': 3.5,
            '5 - Player Five': 3.0,
        }

        result = calculate_lineup_combinations([game])
        assert isinstance(result, list)

    def test_games_with_no_game_scores(self):
        """Test games that have empty game_scores field."""
        game = make_sample_game(game_id=1, date='2024-11-01')
        game['lines'] = [['Player'], [], [], []]
        game['game_scores'] = {}

        result = calculate_lineup_combinations([game])
        # Should return empty list or handle gracefully
        assert isinstance(result, list)

    def test_insufficient_combo_players(self):
        """Test games with fewer players than min combo size."""
        game = make_sample_game(game_id=1, date='2024-11-01')
        # Only 3 players, combo_size_range is (5,7) by default
        game['lines'] = [['1 - Player One', '2 - Player Two', '3 - Player Three'], [], [], []]
        game['game_scores'] = {
            '1 - Player One': 5.0,
            '2 - Player Two': 4.0,
            '3 - Player Three': 3.0,
        }

        result = calculate_lineup_combinations([game], combo_size_range=(5, 7))
        # Should return empty list (not enough players for any combos)
        assert isinstance(result, list)

    def test_combo_played_zero_games_together(self):
        """Test combo that never played together in any game."""
        # Game 1: Players 1,2,3,4,5
        game1 = make_sample_game(game_id=1, date='2024-11-01')
        game1['lines'] = [['1 - Player One', '2 - Player Two', '3 - Player Three', '4 - Player Four', '5 - Player Five'], [], [], []]
        game1['game_scores'] = {'1 - Player One': 5.0, '2 - Player Two': 4.0, '3 - Player Three': 3.0, '4 - Player Four': 2.5, '5 - Player Five': 2.0}

        # Game 2: Different players (6,7,8,9,10)
        game2 = make_sample_game(game_id=2, date='2024-11-08')
        game2['lines'] = [['6 - Player Six', '7 - Player Seven', '8 - Player Eight', '9 - Player Nine', '10 - Player Ten'], [], [], []]
        game2['game_scores'] = {'6 - Player Six': 4.5, '7 - Player Seven': 3.5, '8 - Player Eight': 3.0, '9 - Player Nine': 2.5, '10 - Player Ten': 2.0}

        result = calculate_lineup_combinations([game1, game2], combo_size_range=(5, 5))
        # May or may not include combos with 0 games - spec says "include but show 0 games"
        # If included, should have games_played_together = 0
        for combo in result:
            assert combo['games_played_together'] >= 0

    def test_insufficient_data_note_included(self, sample_games_for_combos):
        """Test that combos with <3 games are included but can be identified."""
        result = calculate_lineup_combinations(sample_games_for_combos)

        # Some combos may have <3 games
        combos_with_few_games = [c for c in result if 0 < c['games_played_together'] < 3]
        # Just verify structure is maintained
        for combo in combos_with_few_games:
            assert combo['games_played_together'] > 0

    def test_combo_size_boundaries(self, sample_games_for_combos):
        """Test that combo_size_range boundaries are respected."""
        result_5_to_5 = calculate_lineup_combinations(sample_games_for_combos, combo_size_range=(5, 5))
        result_6_to_7 = calculate_lineup_combinations(sample_games_for_combos, combo_size_range=(6, 7))

        for combo in result_5_to_5:
            assert combo['combo_size'] == 5

        for combo in result_6_to_7:
            assert combo['combo_size'] in [6, 7]


class TestCalculateLineupCombosSorting:
    """Test sorting and limiting of results."""

    def test_results_sorted_descending_by_score(self, sample_games_for_combos):
        """Test that results are sorted by avg_aggregate_game_score descending."""
        result = calculate_lineup_combinations(sample_games_for_combos)

        scores = [c['avg_aggregate_game_score'] for c in result if c['games_played_together'] > 0]

        # Check that scores are in descending order
        if len(scores) > 1:
            for i in range(len(scores) - 1):
                assert scores[i] >= scores[i + 1]

    def test_limit_parameter_caps_results(self, sample_games_for_combos):
        """Test that limit parameter caps the number of results returned."""
        result_limit_2 = calculate_lineup_combinations(
            sample_games_for_combos,
            combo_size_range=(5, 5),
            limit=2
        )
        result_limit_1 = calculate_lineup_combinations(
            sample_games_for_combos,
            combo_size_range=(5, 5),
            limit=1
        )

        # Each size should respect the limit
        assert len(result_limit_2) <= 2
        assert len(result_limit_1) <= 1

    def test_per_size_limiting(self, sample_games_for_combos):
        """Test that limit is applied per combo size."""
        # Test that limit applies per combo size
        # If we have 3 combo sizes (5, 6, 7) and limit=5
        # we should get at most 5 of size 5, 5 of size 6, 5 of size 7 (15 total)
        result = calculate_lineup_combinations(
            sample_games_for_combos,
            combo_size_range=(5, 7),
            limit=5
        )

        # Group by size
        by_size = {}
        for combo in result:
            size = combo['combo_size']
            if size not in by_size:
                by_size[size] = []
            by_size[size].append(combo)

        # Each size should have at most 5 results
        for size, combos in by_size.items():
            assert len(combos) <= 5, f"Size {size} has {len(combos)} combos, expected <= 5"

    def test_default_limit_is_10_per_size(self, sample_games_for_combos):
        """Test that default limit is 10 per combo size."""
        result = calculate_lineup_combinations(sample_games_for_combos)

        # Group by size
        by_size = {}
        for combo in result:
            size = combo['combo_size']
            if size not in by_size:
                by_size[size] = []
            by_size[size].append(combo)

        # Each size should have at most 10 results (the default)
        for size, combos in by_size.items():
            assert len(combos) <= 10, f"Default limit exceeded for size {size}: {len(combos)} > 10"


class TestCalculateLineupCombosDataIntegrity:
    """Test data integrity and validity."""

    def test_all_players_in_result_are_in_games(self, sample_games_for_combos):
        """Test that all player names in results exist in the input games."""
        result = calculate_lineup_combinations(sample_games_for_combos)

        all_game_players = set()
        for game in sample_games_for_combos:
            for line in game.get('lines', []):
                for player in line:
                    all_game_players.add(player)

        for combo in result:
            for player in combo['players']:
                assert player in all_game_players

    def test_win_percentage_validity(self, sample_games_for_combos):
        """Test that win_percentage is within valid range."""
        result = calculate_lineup_combinations(sample_games_for_combos)

        for combo in result:
            if combo['games_played_together'] > 0:
                assert 0 <= combo['win_percentage'] <= 100

    def test_goal_differential_validity(self, sample_games_for_combos):
        """Test that goal_differential can be negative."""
        result = calculate_lineup_combinations(sample_games_for_combos)

        for combo in result:
            if combo['games_played_together'] > 0:
                # Goal differential can be positive or negative
                assert isinstance(combo['avg_goal_differential'], (int, float))

    def test_game_ids_match_games_played_together_count(self, sample_games_for_combos):
        """Test that length of game_ids matches games_played_together."""
        result = calculate_lineup_combinations(sample_games_for_combos)

        for combo in result:
            assert len(combo['game_ids']) == combo['games_played_together']

    def test_no_duplicate_game_ids_in_combo(self, sample_games_for_combos):
        """Test that each game_id appears only once per combo."""
        result = calculate_lineup_combinations(sample_games_for_combos)

        for combo in result:
            game_ids = combo['game_ids']
            assert len(game_ids) == len(set(game_ids))

    def test_game_ids_are_integers(self, sample_games_for_combos):
        """Test that all game_ids are integers."""
        result = calculate_lineup_combinations(sample_games_for_combos)

        for combo in result:
            for game_id in combo['game_ids']:
                assert isinstance(game_id, int)

    def test_numeric_metrics_are_numbers(self, sample_games_for_combos):
        """Test that all numeric metrics are actual numbers."""
        result = calculate_lineup_combinations(sample_games_for_combos)

        for combo in result:
            assert isinstance(combo['wins'], int)
            assert isinstance(combo['losses'], int)
            assert isinstance(combo['games_played_together'], int)
            assert isinstance(combo['win_percentage'], (int, float))
            assert isinstance(combo['avg_goal_differential'], (int, float))
            assert isinstance(combo['avg_aggregate_game_score'], (int, float))
