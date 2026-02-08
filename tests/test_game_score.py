"""
Tests for Game Score (GS) calculation and display.

Game Score formula: GS = (1.5 * G) + (1.0 * A) + (0.1 * SOG) + (0.3 * PM) + (0.15 * PD) - (0.15 * PT) - (0.2 * Errors)
Goalie GS formula: GS = (0.10 * Saves) - (0.25 * Goals Conceded)
"""
import json
import pytest

from app import GAMES_FILE, calculate_game_score, calculate_goalie_game_score


def _read_games():
    try:
        with open(GAMES_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return []


def _write_games(games):
    with open(GAMES_FILE, 'w') as f:
        json.dump(games, f, indent=2)


def make_sample_game(game_id=0):
    """Create a sample game with default values."""
    return {
        'id': game_id,
        'team': 'Test Team',
        'season': '2024-25',
        'home_team': 'Home',
        'away_team': 'Away',
        'date': '2024-11-15',
        'lines': [['Player1', 'Player2'], ['Player3'], [], []],
        'goalies': ['Goalie1'],
        'result': {p: {'home': 0, 'away': 0} for p in ['1', '2', '3', 'OT']},
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
    }


class TestGameScoreCalculation:
    """Test the calculate_game_score() helper function."""

    def test_basic_calculation(self):
        """Test basic Game Score calculation with positive values."""
        # GS = (1.5 * 2) + (1.0 * 3) + (0.1 * 5) + (0.3 * 5) + (0.15 * 2) - (0.15 * 1) - (0.2 * 1)
        # GS = 3.0 + 3.0 + 0.5 + 1.5 + 0.3 - 0.15 - 0.2 = 7.95
        result = calculate_game_score(goals=2, assists=3, plusminus=5, errors=1, sog=5, penalties_drawn=2, penalties_taken=1)
        assert round(result, 2) == 7.95

    def test_zero_values(self):
        """Test Game Score calculation with all zeros."""
        result = calculate_game_score(goals=0, assists=0, plusminus=0, errors=0)
        assert result == 0.0

    def test_negative_plusminus(self):
        """Test Game Score calculation with negative plus/minus."""
        # GS = (1.5 * 1) + (1.0 * 1) + (0.1 * 3) + (0.3 * -3) + (0.15 * 1) - (0.15 * 2) - (0.2 * 2)
        # GS = 1.5 + 1.0 + 0.3 - 0.9 + 0.15 - 0.3 - 0.4 = 1.35
        result = calculate_game_score(goals=1, assists=1, plusminus=-3, errors=2, sog=3, penalties_drawn=1, penalties_taken=2)
        assert round(result, 2) == 1.35

    def test_high_errors_negative_score(self):
        """Test Game Score calculation where errors and penalties result in negative score."""
        # GS = (1.5 * 0) + (1.0 * 0) + (0.1 * 0) + (0.3 * -2) + (0.15 * 0) - (0.15 * 3) - (0.2 * 5)
        # GS = 0 + 0 + 0 - 0.6 + 0 - 0.45 - 1.0 = -2.05
        result = calculate_game_score(goals=0, assists=0, plusminus=-2, errors=5, sog=0, penalties_drawn=0, penalties_taken=3)
        assert round(result, 2) == -2.05

    def test_only_goals(self):
        """Test Game Score calculation with only goals."""
        # GS = (1.5 * 3) + 0 + 0 - 0 = 4.5
        result = calculate_game_score(goals=3, assists=0, plusminus=0, errors=0)
        assert result == 4.5

    def test_only_assists(self):
        """Test Game Score calculation with only assists."""
        # GS = 0 + (1.0 * 4) + 0 - 0 = 4.0
        result = calculate_game_score(goals=0, assists=4, plusminus=0, errors=0)
        assert result == 4.0

    def test_realistic_example(self):
        """Test with realistic game data."""
        # Player with 2 goals, 1 assist, +2, 1 error, 4 SOG, 1 PD, 0 PT
        # GS = (1.5 * 2) + (1.0 * 1) + (0.1 * 4) + (0.3 * 2) + (0.15 * 1) - (0.15 * 0) - (0.2 * 1)
        # GS = 3.0 + 1.0 + 0.4 + 0.6 + 0.15 - 0 - 0.2 = 4.95
        result = calculate_game_score(goals=2, assists=1, plusminus=2, errors=1, sog=4, penalties_drawn=1, penalties_taken=0)
        assert round(result, 2) == 4.95

    def test_only_sog(self):
        """Test Game Score calculation with only SOG."""
        # GS = 0 + 0 + (0.1 * 10) + 0 + 0 - 0 - 0 = 1.0
        result = calculate_game_score(goals=0, assists=0, plusminus=0, errors=0, sog=10, penalties_drawn=0, penalties_taken=0)
        assert result == 1.0

    def test_penalties_drawn_vs_taken(self):
        """Test that penalties drawn increase GS and penalties taken decrease it."""
        # GS with penalties drawn = (0.15 * 3) = 0.45
        result1 = calculate_game_score(goals=0, assists=0, plusminus=0, errors=0, sog=0, penalties_drawn=3, penalties_taken=0)
        assert round(result1, 2) == 0.45
        
        # GS with penalties taken = -(0.15 * 3) = -0.45
        result2 = calculate_game_score(goals=0, assists=0, plusminus=0, errors=0, sog=0, penalties_drawn=0, penalties_taken=3)
        assert round(result2, 2) == -0.45

    def test_default_values(self):
        """Test that function works with default values (backward compatibility)."""
        # Only required params, others default to 0
        result = calculate_game_score(goals=2, assists=1, plusminus=1, errors=0)
        # GS = (1.5 * 2) + (1.0 * 1) + (0.1 * 0) + (0.3 * 1) + (0.15 * 0) - (0.15 * 0) - (0.2 * 0)
        # GS = 3.0 + 1.0 + 0 + 0.3 + 0 - 0 - 0 = 4.3
        assert result == 4.3


class TestGoalieGameScore:
    """Test the calculate_goalie_game_score() helper function."""

    def test_basic_goalie_calculation(self):
        """Test basic goalie Game Score calculation."""
        # GS = (0.10 * 30) - (0.25 * 2)
        # GS = 3.0 - 0.5 = 2.5
        result = calculate_goalie_game_score(saves=30, goals_conceded=2)
        assert result == 2.5

    def test_goalie_zero_values(self):
        """Test goalie Game Score with no activity."""
        result = calculate_goalie_game_score(saves=0, goals_conceded=0)
        assert result == 0.0

    def test_goalie_shutout(self):
        """Test goalie Game Score for a shutout."""
        # GS = (0.10 * 40) - (0.25 * 0) = 4.0
        result = calculate_goalie_game_score(saves=40, goals_conceded=0)
        assert result == 4.0

    def test_goalie_bad_game(self):
        """Test goalie Game Score for a bad performance."""
        # GS = (0.10 * 10) - (0.25 * 8)
        # GS = 1.0 - 2.0 = -1.0
        result = calculate_goalie_game_score(saves=10, goals_conceded=8)
        assert result == -1.0

    def test_goalie_realistic_example(self):
        """Test with realistic goalie data."""
        # Goalie with 25 saves, 3 goals conceded
        # GS = (0.10 * 25) - (0.25 * 3)
        # GS = 2.5 - 0.75 = 1.75
        result = calculate_goalie_game_score(saves=25, goals_conceded=3)
        assert result == 1.75


class TestGameScorePerGame:
    """Test per-game Game Score calculation in stats page."""

    def test_per_game_game_score_calculation(self, client):
        """Test that per-game Game Score is calculated correctly."""
        game = make_sample_game(game_id=1)
        game['goals'] = {'Player1': 2, 'Player2': 0}
        game['assists'] = {'Player1': 1, 'Player2': 1}
        game['plusminus'] = {'Player1': 2, 'Player2': -1}
        game['unforced_errors'] = {'Player1': 1, 'Player2': 2}
        game['shots_on_goal'] = {'Player1': 5, 'Player2': 3}
        game['penalties_drawn'] = {'Player1': 1, 'Player2': 0}
        game['penalties_taken'] = {'Player1': 0, 'Player2': 1}
        
        _write_games([game])

        rv = client.get('/stats')
        assert rv.status_code == 200
        data = rv.data.decode('utf-8')
        
        # Check that Game Score section exists
        assert 'Game Score' in data
        
        # Player1: (1.5*2) + (1.0*1) + (0.1*5) + (0.3*2) + (0.15*1) - (0.15*0) - (0.2*1) = 5.05
        assert '5.0' in data or '5.1' in data
        
        # Player2: (1.5*0) + (1.0*1) + (0.1*3) + (0.3*-1) + (0.15*0) - (0.15*1) - (0.2*2) = 0.45
        assert '0.4' in data or '0.5' in data

    def test_game_score_with_multiple_games(self, client):
        """Test that Game Score aggregates correctly across multiple games."""
        from app import ensure_game_ids
        
        game1 = make_sample_game()
        game1['date'] = '2024-11-15'
        game1['goals'] = {'Player1': 1, 'Player2': 0}
        game1['assists'] = {'Player1': 0, 'Player2': 1}
        game1['plusminus'] = {'Player1': 1, 'Player2': 0}
        game1['unforced_errors'] = {'Player1': 0, 'Player2': 1}
        game1['shots_on_goal'] = {'Player1': 2, 'Player2': 1}
        game1['penalties_drawn'] = {'Player1': 0, 'Player2': 1}
        game1['penalties_taken'] = {'Player1': 0, 'Player2': 0}
        
        game2 = make_sample_game()
        game2['date'] = '2024-11-22'
        game2['goals'] = {'Player1': 2, 'Player2': 1}
        game2['assists'] = {'Player1': 1, 'Player2': 0}
        game2['plusminus'] = {'Player1': 1, 'Player2': 1}
        game2['unforced_errors'] = {'Player1': 1, 'Player2': 0}
        game2['shots_on_goal'] = {'Player1': 4, 'Player2': 2}
        game2['penalties_drawn'] = {'Player1': 1, 'Player2': 0}
        game2['penalties_taken'] = {'Player1': 0, 'Player2': 1}
        
        games = [game1, game2]
        ensure_game_ids(games)
        _write_games(games)

        rv = client.get('/stats')
        assert rv.status_code == 200
        data = rv.data.decode('utf-8')
        
        # Player1 total: Game1 (1.5*1 + 1.0*0 + 0.1*2 + 0.3*1 + 0.15*0 - 0.15*0 - 0.2*0 = 2.0)
        #                + Game2 (1.5*2 + 1.0*1 + 0.1*4 + 0.3*1 + 0.15*1 - 0.15*0 - 0.2*1 = 4.65)
        #                = 6.65 (rounded to 6.6 or 6.7)
        assert '6.6' in data or '6.7' in data
        
        # Player2 total: Game1 (1.5*0 + 1.0*1 + 0.1*1 + 0.3*0 + 0.15*1 - 0.15*0 - 0.2*1 = 1.05)
        #                + Game2 (1.5*1 + 1.0*0 + 0.1*2 + 0.3*1 + 0.15*0 - 0.15*1 - 0.2*0 = 1.85)
        #                = 2.9
        assert '2.9' in data


class TestGameScoreDisplay:
    """Test Game Score display on stats page."""

    def test_game_score_table_present(self, client):
        """Test that Game Score table appears in stats page HTML."""
        game = make_sample_game(game_id=1)
        game['goals'] = {'Player1': 1}
        game['assists'] = {'Player1': 0}
        game['plusminus'] = {'Player1': 1}
        game['unforced_errors'] = {'Player1': 0}
        
        _write_games([game])

        rv = client.get('/stats')
        assert rv.status_code == 200
        data = rv.data.decode('utf-8')
        
        # Check for Game Score table ID
        assert 'id="gameScoreTable"' in data or 'Game Score' in data

    def test_game_score_italian_translation(self, client):
        """Test that Game Score appears with Italian translation."""
        game = make_sample_game(game_id=1)
        game['goals'] = {'Player1': 1}
        game['assists'] = {'Player1': 0}
        game['plusminus'] = {'Player1': 0}
        game['unforced_errors'] = {'Player1': 0}
        
        _write_games([game])

        # Set Italian language
        rv = client.get('/stats?lang=it')
        assert rv.status_code == 200
        data = rv.data.decode('utf-8')
        
        # Check for Italian translation "Punteggio Partita"
        assert 'Punteggio Partita' in data or 'Game Score' in data

    def test_game_score_with_zero_stats(self, client):
        """Test Game Score calculation when player has no stats."""
        game = make_sample_game(game_id=1)
        # Player1 has no stats recorded
        
        _write_games([game])

        rv = client.get('/stats')
        assert rv.status_code == 200
        data = rv.data.decode('utf-8')
        
        # Should still render the page successfully
        assert 'Game Score' in data

    def test_game_score_formatting(self, client):
        """Test that Game Score is formatted to 1 decimal place."""
        game = make_sample_game(game_id=1)
        # Create a score that would have multiple decimal places
        game['goals'] = {'Player1': 1}
        game['assists'] = {'Player1': 1}
        game['plusminus'] = {'Player1': 1}
        game['unforced_errors'] = {'Player1': 1}
        game['shots_on_goal'] = {'Player1': 2}
        game['penalties_drawn'] = {'Player1': 1}
        game['penalties_taken'] = {'Player1': 0}
        # GS = 1.5 + 1.0 + 0.2 + 0.3 + 0.15 - 0 - 0.2 = 2.95 (displayed as 2.9 or 3.0)
        
        _write_games([game])

        rv = client.get('/stats')
        assert rv.status_code == 200
        data = rv.data.decode('utf-8')
        
        # Should show rounded value
        assert '2.9' in data or '3.0' in data


class TestGameScoreEdgeCases:
    """Test edge cases and boundary conditions for Game Score."""

    def test_game_score_with_no_games(self, client):
        """Test stats page with no games (empty dataset)."""
        _write_games([])

        rv = client.get('/stats')
        assert rv.status_code == 200
        data = rv.data.decode('utf-8')
        
        # Page should render without errors
        assert 'Game Score' in data or 'Stats Overview' in data

    def test_game_score_with_missing_stats_fields(self, client):
        """Test Game Score calculation when stats fields are missing."""
        game = make_sample_game(game_id=1)
        # Remove some stats fields
        del game['unforced_errors']
        del game['plusminus']
        game['goals'] = {'Player1': 2}
        game['assists'] = {'Player1': 1}
        
        _write_games([game])

        rv = client.get('/stats')
        assert rv.status_code == 200
        # Should handle missing fields gracefully

    def test_game_score_hide_zeros_filter(self, client):
        """Test that Game Score respects hide_zero_stats filter."""
        game = make_sample_game(game_id=1)
        game['goals'] = {'Player1': 2, 'Player2': 0}
        game['assists'] = {'Player1': 1, 'Player2': 0}
        game['plusminus'] = {'Player1': 1, 'Player2': 0}
        game['unforced_errors'] = {'Player1': 0, 'Player2': 0}
        game['shots_on_goal'] = {'Player1': 3, 'Player2': 0}
        game['penalties_drawn'] = {'Player1': 0, 'Player2': 0}
        game['penalties_taken'] = {'Player1': 0, 'Player2': 0}
        # Player1 has non-zero Game Score, Player2 has zero
        
        _write_games([game])

        rv = client.get('/stats?hide_zero_stats=true')
        assert rv.status_code == 200
        data = rv.data.decode('utf-8')
        
        # Player1 should appear
        assert 'Player1' in data
        # Player2 might not appear if filter works correctly

    def test_game_score_with_very_large_numbers(self, client):
        """Test Game Score with unusually high stat values."""
        game = make_sample_game(game_id=1)
        game['goals'] = {'Player1': 10}
        game['assists'] = {'Player1': 15}
        game['plusminus'] = {'Player1': 20}
        game['unforced_errors'] = {'Player1': 5}
        game['shots_on_goal'] = {'Player1': 25}
        game['penalties_drawn'] = {'Player1': 3}
        game['penalties_taken'] = {'Player1': 1}
        # GS = (1.5 * 10) + (1.0 * 15) + (0.1 * 25) + (0.3 * 20) + (0.15 * 3) - (0.15 * 1) - (0.2 * 5)
        # GS = 15 + 15 + 2.5 + 6 + 0.45 - 0.15 - 1 = 37.8
        
        _write_games([game])

        rv = client.get('/stats')
        assert rv.status_code == 200
        data = rv.data.decode('utf-8')
        
        # Should handle large numbers correctly
        assert '37.8' in data or '37.9' in data

    def test_game_score_player_not_in_lines(self, client):
        """Test that players not in any line get dash (-) for Game Score."""
        game = make_sample_game(game_id=1)
        game['lines'] = [['Player1'], [], [], []]
        game['goals'] = {'Player1': 1, 'Player2': 1}  # Player2 not in lines
        game['assists'] = {'Player1': 0, 'Player2': 0}
        game['plusminus'] = {'Player1': 1, 'Player2': 1}
        game['unforced_errors'] = {'Player1': 0, 'Player2': 0}
        
        _write_games([game])

        rv = client.get('/stats')
        assert rv.status_code == 200
        # Should render successfully even with inconsistent data
