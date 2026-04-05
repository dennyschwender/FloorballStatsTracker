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
from services.stats_service import calculate_game_score, calculate_player_trends

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

        # Check Alice's stats (games: 5.2, 2.2, 8.35)
        alice = result['Alice']
        assert len(alice['game_scores']) == 3
        assert alice['game_scores'] == [
            sample_games_3_players[0]['game_scores']['Alice'],
            sample_games_3_players[1]['game_scores']['Alice'],
            sample_games_3_players[2]['game_scores']['Alice'],
        ]

        # Verify mean calculation
        expected_mean = (5.2 + 2.2 + 8.35) / 3
        assert abs(alice['mean_score'] - expected_mean) < SCORE_TOLERANCE

        # Verify min/max
        assert abs(alice['min_score'] - 2.2) < SCORE_TOLERANCE
        assert abs(alice['max_score'] - 8.35) < SCORE_TOLERANCE

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
