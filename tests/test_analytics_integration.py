"""
Integration tests for the analytics dashboard feature (end-to-end).

Tests cover:
1. Full stack integration (API + Backend + Frontend)
2. Complete user workflows (player trends, lineup combos)
3. HTML rendering and JavaScript integration
4. Error handling and edge cases
"""
import pytest
from services.stats_service import calculate_game_score
from services.game_service import save_game


def make_test_game(game_id, date, season='2025-26', team='U21',
                   home_team='Home', away_team='Away',
                   players=None, goals=None, assists=None, plusminus=None,
                   unforced_errors=None, shots_on_goal=None,
                   penalties_drawn=None, penalties_taken=None):
    """Create a test game with realistic data."""
    if players is None:
        players = ['Alice', 'Bob', 'Charlie']
    if goals is None:
        goals = {p: 0 for p in players}
    if assists is None:
        assists = {p: 0 for p in players}
    if plusminus is None:
        plusminus = {p: 0 for p in players}
    if unforced_errors is None:
        unforced_errors = {p: 0 for p in players}
    if shots_on_goal is None:
        shots_on_goal = {p: 2 for p in players}
    if penalties_drawn is None:
        penalties_drawn = {p: 0 for p in players}
    if penalties_taken is None:
        penalties_taken = {p: 0 for p in players}

    # Calculate game scores
    game_scores = {}
    for player in players:
        game_scores[player] = calculate_game_score(
            goals.get(player, 0),
            assists.get(player, 0),
            plusminus.get(player, 0),
            unforced_errors.get(player, 0),
            shots_on_goal.get(player, 0),
            penalties_drawn.get(player, 0),
            penalties_taken.get(player, 0)
        )

    game = {
        'id': game_id,
        'date': date,
        'season': season,
        'team': team,
        'home_team': home_team,
        'away_team': away_team,
        'lines': [players],
        'goals': goals,
        'assists': assists,
        'plusminus': plusminus,
        'unforced_errors': unforced_errors,
        'shots_on_goal': shots_on_goal,
        'penalties_drawn': penalties_drawn,
        'penalties_taken': penalties_taken,
        'game_scores': game_scores,
        'result': {'1': {'home': 2, 'away': 1}, '2': {'home': 0, 'away': 0}, '3': {'home': 0, 'away': 0}}
    }
    return game


class TestPlayerTrendsIntegration:
    """Integration tests for player trends feature."""

    def test_api_returns_valid_trends_structure(self, client, clean_db):
        """Test that API returns properly structured trends data."""
        # Create multiple games with realistic data
        players = ['Alice', 'Bob', 'Charlie']
        for i in range(3):
            game = make_test_game(
                game_id=i+1,
                date=f'2025-01-{10 + i*7}',
                players=players,
                goals={'Alice': 2, 'Bob': 1, 'Charlie': 0},
                assists={'Alice': 1, 'Bob': 0, 'Charlie': 1},
                plusminus={'Alice': 2, 'Bob': 1, 'Charlie': -1}
            )
            save_game(game)

        # Request trends
        response = client.get('/api/player-trends?season=2025-26&team=U21&players=Alice,Bob')
        assert response.status_code == 200
        data = response.get_json()

        # Validate structure
        assert data['success'] is True
        assert isinstance(data['data'], dict)
        assert 'Alice' in data['data']
        assert 'Bob' in data['data']

        # Validate each player's data structure
        for player in ['Alice', 'Bob']:
            player_data = data['data'][player]
            assert 'game_scores' in player_data
            assert isinstance(player_data['game_scores'], list)
            assert len(player_data['game_scores']) == 3  # Three games

            # Check statistical fields
            assert 'mean_score' in player_data
            assert 'std_dev' in player_data
            assert 'min_score' in player_data
            assert 'max_score' in player_data
            assert 'outliers' in player_data
            assert 'insufficient_data' in player_data
            assert 'game_ids' in player_data

            # Validate numeric types
            assert isinstance(player_data['mean_score'], (int, float))
            assert isinstance(player_data['std_dev'], (int, float))

    def test_api_handles_no_games_gracefully(self, client, clean_db):
        """Test that API returns empty data when no games exist."""
        response = client.get('/api/player-trends?season=9999-00&team=NONEXISTENT&players=Player1')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data'] == {}

    def test_api_filters_by_season_and_team(self, client, clean_db):
        """Test that API correctly filters by season and team."""
        # Create games in different seasons/teams
        game1 = make_test_game(1, '2025-01-15', season='2025-26', team='U21')
        game2 = make_test_game(2, '2025-01-22', season='2024-25', team='U21')
        game3 = make_test_game(3, '2025-01-29', season='2025-26', team='U18')
        save_game(game1)
        save_game(game2)
        save_game(game3)

        # Query specific season/team combination
        response = client.get('/api/player-trends?season=2025-26&team=U21&players=Alice')
        data = response.get_json()

        # Should only get data from game1
        assert data['data']['Alice']['game_ids'] == [1]

    def test_api_handles_multiple_players_with_varied_stats(self, client, clean_db):
        """Test trends API with players having different statistics."""
        players = ['Alice', 'Bob', 'Charlie', 'Dave']
        game1 = make_test_game(
            1, '2025-01-15',
            players=players,
            goals={'Alice': 3, 'Bob': 1, 'Charlie': 0, 'Dave': 2},
            assists={'Alice': 1, 'Bob': 2, 'Charlie': 0, 'Dave': 1},
            plusminus={'Alice': 3, 'Bob': 1, 'Charlie': -2, 'Dave': 2}
        )
        save_game(game1)

        response = client.get('/api/player-trends?season=2025-26&team=U21&players=Alice,Bob,Charlie,Dave')
        data = response.get_json()

        # All players should be in results
        for player in players:
            assert player in data['data']

        # Verify Alice has higher scores than Charlie (more goals/assists)
        alice_score = data['data']['Alice']['mean_score']
        charlie_score = data['data']['Charlie']['mean_score']
        assert alice_score > charlie_score

    def test_api_identifies_outliers_correctly(self, client, clean_db):
        """Test that API identifies outliers using z-score analysis."""
        # Create games where one has very different performance
        players = ['Alice']
        game1 = make_test_game(1, '2025-01-15', players=players, goals={'Alice': 1}, assists={'Alice': 0})
        game2 = make_test_game(2, '2025-01-22', players=players, goals={'Alice': 1}, assists={'Alice': 0})
        game3 = make_test_game(3, '2025-01-29', players=players, goals={'Alice': 10}, assists={'Alice': 5})
        save_game(game1)
        save_game(game2)
        save_game(game3)

        response = client.get('/api/player-trends?season=2025-26&team=U21&players=Alice')
        data = response.get_json()
        alice_data = data['data']['Alice']

        # Game 3 should be identified as an outlier
        assert len(alice_data['outliers']) > 0
        # Outlier should reference game 3
        outlier_games = [o['game_id'] for o in alice_data['outliers']]
        assert 3 in outlier_games


class TestLineupCombosIntegration:
    """Integration tests for lineup combos feature."""

    def test_api_returns_valid_combos_structure(self, client, clean_db):
        """Test that API returns properly structured combo data."""
        # Create game with 6 players to get varied combos
        players = ['A', 'B', 'C', 'D', 'E', 'F']
        game = make_test_game(
            1, '2025-01-15',
            players=players,
            goals={'A': 2, 'B': 1, 'C': 1, 'D': 0, 'E': 1, 'F': 0},
            assists={'A': 1, 'B': 1, 'C': 0, 'D': 2, 'E': 0, 'F': 1},
            plusminus={'A': 2, 'B': 1, 'C': 1, 'D': 1, 'E': 1, 'F': 0}
        )
        save_game(game)

        response = client.get('/api/lineup-combos?season=2025-26&team=U21')
        assert response.status_code == 200
        data = response.get_json()

        # Validate structure
        assert data['success'] is True
        assert isinstance(data['data'], list)

        if len(data['data']) > 0:
            combo = data['data'][0]
            # Required fields
            assert 'combo_id' in combo
            assert 'players' in combo
            assert isinstance(combo['players'], list)
            assert 'combo_size' in combo
            assert 'games_played_together' in combo
            assert 'wins' in combo
            assert 'losses' in combo
            assert 'win_percentage' in combo
            assert 'avg_goal_differential' in combo
            assert 'avg_aggregate_game_score' in combo
            assert 'game_ids' in combo

    def test_api_sorts_combos_by_score_descending(self, client, clean_db):
        """Test that combos are sorted by score in descending order."""
        # Create multiple games with 5 players to generate combos
        players = ['A', 'B', 'C', 'D', 'E']
        game = make_test_game(1, '2025-01-15', players=players)
        save_game(game)

        response = client.get('/api/lineup-combos?season=2025-26&team=U21&combo_size_range=5,5')
        data = response.get_json()

        if len(data['data']) > 1:
            # Check descending order
            scores = [c['avg_aggregate_game_score'] for c in data['data']]
            assert scores == sorted(scores, reverse=True)

    def test_api_filters_by_combo_size_range(self, client, clean_db):
        """Test that combo_size_range parameter correctly filters results."""
        # Create game with 7 players
        players = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
        game = make_test_game(1, '2025-01-15', players=players)
        save_game(game)

        # Request only 5-player combos
        response = client.get('/api/lineup-combos?season=2025-26&team=U21&combo_size_range=5,5&limit=20')
        data = response.get_json()

        # All returned combos should be size 5
        for combo in data['data']:
            assert combo['combo_size'] == 5

    def test_api_respects_limit_parameter(self, client, clean_db):
        """Test that limit parameter caps results correctly."""
        # Create game with many players
        players = list('ABCDEFGHIJ')  # 10 players
        game = make_test_game(1, '2025-01-15', players=players)
        save_game(game)

        # Request with limit of 2
        response = client.get('/api/lineup-combos?season=2025-26&team=U21&combo_size_range=5,5&limit=2')
        data = response.get_json()

        # Should not exceed limit
        assert len([c for c in data['data'] if c['combo_size'] == 5]) <= 2

    def test_api_handles_insufficient_players(self, client, clean_db):
        """Test that API handles games with insufficient players for combos."""
        # Create game with only 3 players
        players = ['A', 'B', 'C']
        game = make_test_game(1, '2025-01-15', players=players)
        save_game(game)

        # Request 5-player combos (can't be formed)
        response = client.get('/api/lineup-combos?season=2025-26&team=U21&combo_size_range=5,7')
        data = response.get_json()

        # Should return empty list (not combos with insufficient data note)
        assert data['data'] == []


class TestHTMLIntegration:
    """Integration tests for HTML rendering and frontend elements."""

    def test_stats_page_renders_player_trends_section(self, client, clean_db):
        """Test that player trends section is present on stats page."""
        response = client.get('/stats')
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        # Check for player trends section
        assert 'player-trends-search' in html
        assert 'Player Trends' in html
        assert 'show-trends-btn' in html

    def test_stats_page_renders_lineup_analysis_section(self, client, clean_db):
        """Test that lineup analysis section is present on stats page."""
        response = client.get('/stats')
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        # Check for lineup analysis section
        assert 'lineup-combos-table' in html
        assert 'lineup-combo-size' in html
        assert 'Lineup Analysis' in html

    def test_stats_page_includes_javascript(self, client, clean_db):
        """Test that JavaScript for charts is included on stats page."""
        response = client.get('/stats')
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        # Check for Chart.js references
        assert 'chart' in html.lower() or 'canvas' in html.lower()
        # Check for nonce attribute on script tags (CSP compliance)
        assert 'nonce=' in html  # Script tags have nonce attribute

    def test_stats_page_has_canvas_elements(self, client, clean_db):
        """Test that canvas elements exist for charts."""
        response = client.get('/stats')
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        # Check for chart canvas elements
        assert 'player-trends-trajectory-chart' in html
        assert 'player-trends-consistency-chart' in html
        assert '<canvas' in html


class TestEndToEndScenarios:
    """End-to-end scenarios testing complete user workflows."""

    def test_scenario_user_views_player_trends(self, client, clean_db):
        """Scenario: User selects players and views trends with charts."""
        # Setup: Create games with multiple players
        players = ['Alice', 'Bob', 'Charlie']
        for i in range(3):
            game = make_test_game(
                game_id=i+1,
                date=f'2025-01-{10 + i*7}',
                players=players,
                goals={'Alice': i+1, 'Bob': i, 'Charlie': i-1},
                assists={'Alice': 1, 'Bob': 0, 'Charlie': 1},
                plusminus={'Alice': 2, 'Bob': 1, 'Charlie': -1}
            )
            save_game(game)

        # Step 1: Load stats page (HTML present)
        response = client.get('/stats')
        assert response.status_code == 200
        assert 'player-trends-search' in response.get_data(as_text=True)

        # Step 2: Call API to get trends (simulates JavaScript fetch)
        api_response = client.get('/api/player-trends?season=2025-26&team=U21&players=Alice,Bob')
        assert api_response.status_code == 200
        trends_data = api_response.get_json()

        # Step 3: Verify data is present for visualization
        assert trends_data['success'] is True
        assert 'Alice' in trends_data['data']
        assert 'Bob' in trends_data['data']

        # Verify chart data is available
        assert len(trends_data['data']['Alice']['game_scores']) == 3
        assert trends_data['data']['Alice']['mean_score'] > 0

    def test_scenario_user_analyzes_lineup_combos(self, client, clean_db):
        """Scenario: User views lineup combination analysis with sorting."""
        # Setup: Create games with lineup data
        players = ['A', 'B', 'C', 'D', 'E', 'F']
        for i in range(2):
            game = make_test_game(
                game_id=i+1,
                date=f'2025-01-{10 + i*7}',
                players=players,
                goals={'A': 2, 'B': 1, 'C': 1, 'D': 0, 'E': 1, 'F': 0}
            )
            save_game(game)

        # Step 1: Load stats page
        response = client.get('/stats')
        assert response.status_code == 200
        assert 'lineup-combos-table' in response.get_data(as_text=True)

        # Step 2: Fetch lineup combos (simulates automatic load)
        api_response = client.get('/api/lineup-combos?season=2025-26&team=U21')
        assert api_response.status_code == 200
        combos_data = api_response.get_json()

        # Step 3: Verify table data structure
        assert combos_data['success'] is True
        assert isinstance(combos_data['data'], list)
        if len(combos_data['data']) > 0:
            combo = combos_data['data'][0]
            assert 'players' in combo
            assert 'win_percentage' in combo

    def test_scenario_user_filters_lineup_by_size(self, client, clean_db):
        """Scenario: User filters lineup table by combo size."""
        # Setup: Create game with 7 players
        players = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
        game = make_test_game(1, '2025-01-15', players=players)
        save_game(game)

        # Step 1: Load full combos
        response1 = client.get('/api/lineup-combos?season=2025-26&team=U21')
        assert response1.status_code == 200
        all_combos = response1.get_json()['data']

        # Step 2: Filter by size 5 only
        response2 = client.get('/api/lineup-combos?season=2025-26&team=U21&combo_size_range=5,5')
        assert response2.status_code == 200
        size_5_combos = response2.get_json()['data']

        # Step 3: Verify filtering worked
        for combo in size_5_combos:
            assert combo['combo_size'] == 5

        # Verify we have fewer results after filtering
        assert len(size_5_combos) <= len(all_combos)

    def test_scenario_invalid_input_shows_error(self, client, clean_db):
        """Scenario: User provides invalid input and sees error."""
        # Missing season parameter
        response = client.get('/api/player-trends?team=U21&players=Alice')
        assert response.status_code == 400
        error_data = response.get_json()
        assert 'error' in error_data
        assert 'season' in error_data['error'].lower()

    def test_scenario_no_data_shows_empty_state(self, client, clean_db):
        """Scenario: No games exist, UI shows empty state."""
        # Query nonexistent season
        response = client.get('/api/player-trends?season=0000-01&team=NONE&players=Alice')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data'] == {}

        # Query nonexistent combos
        response = client.get('/api/lineup-combos?season=0000-01&team=NONE')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data'] == []


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    def test_invalid_combo_size_range_format(self, client, clean_db):
        """Test error when combo_size_range has invalid format."""
        response = client.get('/api/lineup-combos?season=2025-26&team=U21&combo_size_range=5-7')
        assert response.status_code == 400
        assert 'format' in response.get_json()['error'].lower()

    def test_invalid_limit_value(self, client, clean_db):
        """Test error when limit is not an integer."""
        response = client.get('/api/lineup-combos?season=2025-26&team=U21&limit=abc')
        assert response.status_code == 400
        assert 'integer' in response.get_json()['error'].lower()

    def test_negative_limit_value(self, client, clean_db):
        """Test error when limit is negative."""
        response = client.get('/api/lineup-combos?season=2025-26&team=U21&limit=-1')
        assert response.status_code == 400
        assert 'at least 1' in response.get_json()['error'].lower()

    def test_special_characters_in_player_names(self, client, clean_db):
        """Test API handles special characters in player names."""
        players = ['O\'Brien', 'Jean-Luc', 'André']
        game = make_test_game(1, '2025-01-15', players=players)
        save_game(game)

        response = client.get('/api/player-trends?season=2025-26&team=U21&players=O%27Brien,Jean-Luc,Andr%C3%A9')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_empty_games_list_returns_empty_data(self, client, clean_db):
        """Test that empty games return empty data structures."""
        # No games added - DB is clean

        # Player trends should return empty dict
        response = client.get('/api/player-trends?season=2025-26&team=U21&players=Alice')
        data = response.get_json()
        assert data['data'] == {}

        # Combos should return empty list
        response = client.get('/api/lineup-combos?season=2025-26&team=U21')
        data = response.get_json()
        assert data['data'] == []
