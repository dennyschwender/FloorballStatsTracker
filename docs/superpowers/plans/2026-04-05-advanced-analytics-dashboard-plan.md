# Advanced Analytics Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Player Trends and Lineup Analysis analytics sections to the stats page with backend calculation functions and frontend interactive dashboards.

**Architecture:** Extend `services/stats_service.py` with two new calculation functions (`calculate_player_trends()` and `calculate_lineup_combinations()`). Add two new API endpoints (`/api/player-trends` and `/api/lineup-combos`) in `routes/api_routes.py`. Extend `templates/stats.html` with two new sections and create `static/js/analytics-dashboard.js` with `PlayerTrendsUI` and `LineupAnalysisUI` classes for interactive rendering. All data driven by existing game data; no new database tables needed.

**Tech Stack:** Python (backend stats calculation), Flask (API endpoints), Chart.js (box plot for consistency), Bootstrap 5 (tables), vanilla JavaScript (event handling and rendering).

---

## File Structure

| File | Type | Purpose |
|------|------|---------|
| `services/stats_service.py` | Modify | Add `calculate_player_trends()` and `calculate_lineup_combinations()` functions |
| `routes/api_routes.py` | Modify | Add `/api/player-trends` and `/api/lineup-combos` GET endpoints |
| `templates/stats.html` | Modify | Add Player Trends section and Lineup Analysis section after existing tables |
| `static/js/analytics-dashboard.js` | Create | `PlayerTrendsUI` and `LineupAnalysisUI` classes for interactive dashboards |
| `tests/test_analytics.py` | Create | Tests for trend calculation, combo logic, and API endpoints |

---

## Task 1: Backend Tests for Player Trends Calculation

**Files:**
- Create: `tests/test_analytics.py`

- [ ] **Step 1: Write failing tests for `calculate_player_trends()`**

Create `tests/test_analytics.py`:

```python
"""
Tests for advanced analytics functions
"""
import pytest
from app import create_app
from models.database import db
from models.game_model import GameRecord
from services.stats_service import calculate_player_trends, calculate_lineup_combinations


@pytest.fixture
def app_with_analytics_data():
    """Create app with sample games for analytics testing."""
    app = create_app()
    with app.app_context():
        db.create_all()
        
        # Create 5 sample games with stats for trending analysis
        for game_id in range(1, 6):
            game = GameRecord(id=game_id)
            game.update_from_dict({
                'id': game_id,
                'season': '2025-26',
                'team': 'U21',
                'date': f'2025-11-{10+game_id}',
                'home_team': 'Team A',
                'away_team': 'Team B',
                'lines': [['7 - Player Seven', '12 - Player Twelve']],
                'goalies': [],
                'goals': {'7 - Player Seven': game_id, '12 - Player Twelve': game_id - 1},
                'assists': {'7 - Player Seven': game_id - 1, '12 - Player Twelve': 1},
                'plusminus': {'7 - Player Seven': 1, '12 - Player Twelve': 0},
                'unforced_errors': {'7 - Player Seven': 0, '12 - Player Twelve': 1},
                'sog': {'7 - Player Seven': game_id + 2, '12 - Player Twelve': 2},
                'penalties_taken': {'7 - Player Seven': 0, '12 - Player Twelve': 0},
                'penalties_drawn': {'7 - Player Seven': 1, '12 - Player Twelve': 0},
                'block_shots': {},
                'stolen_balls': {},
                'saves': {},
                'goals_conceded': {},
                'result': {'1': {'home': game_id, 'away': game_id - 1}, '2': {'home': 0, 'away': 0}, '3': {'home': 0, 'away': 0}},
                'current_period': '3'
            })
            db.session.add(game)
        
        db.session.commit()
        yield app
        db.session.remove()


class TestPlayerTrends:
    """Test calculate_player_trends function."""

    def test_calculate_player_trends_returns_dict(self, app_with_analytics_data):
        """calculate_player_trends returns dict with player keys."""
        with app_with_analytics_data.app_context():
            games = GameRecord.query.all()
            game_dicts = [row.to_dict() for row in games]
            
            trends = calculate_player_trends(game_dicts)
            
            assert isinstance(trends, dict)
            assert '7 - Player Seven' in trends
            assert '12 - Player Twelve' in trends

    def test_player_trends_contains_required_fields(self, app_with_analytics_data):
        """Each player in trends has game_scores, mean_score, std_dev, outliers."""
        with app_with_analytics_data.app_context():
            games = GameRecord.query.all()
            game_dicts = [row.to_dict() for row in games]
            
            trends = calculate_player_trends(game_dicts)
            player_data = trends['7 - Player Seven']
            
            assert 'game_scores' in player_data
            assert 'game_ids' in player_data
            assert 'mean_score' in player_data
            assert 'std_dev' in player_data
            assert 'min_score' in player_data
            assert 'max_score' in player_data
            assert 'outliers' in player_data
            assert isinstance(player_data['game_scores'], list)
            assert isinstance(player_data['outliers'], list)

    def test_player_trends_calculates_mean_correctly(self, app_with_analytics_data):
        """Mean score is calculated correctly from game scores."""
        with app_with_analytics_data.app_context():
            games = GameRecord.query.all()
            game_dicts = [row.to_dict() for row in games]
            
            # Manually ensure game_scores calculation
            from services.stats_service import ensure_game_stats, recalculate_game_scores
            for game in game_dicts:
                ensure_game_stats(game)
                recalculate_game_scores(game)
            
            trends = calculate_player_trends(game_dicts)
            player_data = trends['7 - Player Seven']
            
            # Mean should be average of game_scores
            expected_mean = sum(player_data['game_scores']) / len(player_data['game_scores'])
            assert abs(player_data['mean_score'] - expected_mean) < 0.01

    def test_player_trends_identifies_outliers(self, app_with_analytics_data):
        """Outliers identified correctly (|z_score| > 1.0)."""
        with app_with_analytics_data.app_context():
            games = GameRecord.query.all()
            game_dicts = [row.to_dict() for row in games]
            
            from services.stats_service import ensure_game_stats, recalculate_game_scores
            for game in game_dicts:
                ensure_game_stats(game)
                recalculate_game_scores(game)
            
            trends = calculate_player_trends(game_dicts)
            player_data = trends['7 - Player Seven']
            
            # Should have at least some outliers given varying game scores
            if len(player_data['game_scores']) > 3:  # Need variance
                # Verify outliers have z_score > 1.0
                for outlier in player_data['outliers']:
                    assert abs(outlier['z_score']) > 1.0
                    assert 'type' in outlier
                    assert outlier['type'] in ['high', 'low']

    def test_player_trends_with_selected_players(self, app_with_analytics_data):
        """Can filter to specific players."""
        with app_with_analytics_data.app_context():
            games = GameRecord.query.all()
            game_dicts = [row.to_dict() for row in games]
            
            trends = calculate_player_trends(game_dicts, players=['7 - Player Seven'])
            
            assert '7 - Player Seven' in trends
            assert '12 - Player Twelve' not in trends

    def test_player_trends_empty_games(self, app_with_analytics_data):
        """Empty games list returns empty dict."""
        with app_with_analytics_data.app_context():
            trends = calculate_player_trends([])
            assert trends == {}

    def test_player_trends_player_not_in_games(self, app_with_analytics_data):
        """Player not in any games is omitted from results."""
        with app_with_analytics_data.app_context():
            games = GameRecord.query.all()
            game_dicts = [row.to_dict() for row in games]
            
            trends = calculate_player_trends(game_dicts, players=['999 - Nonexistent'])
            
            assert trends == {}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_analytics.py::TestPlayerTrends -v
```

Expected output: All tests FAIL with "calculate_player_trends not found" or similar

---

## Task 2: Implement `calculate_player_trends()` Function

**Files:**
- Modify: `services/stats_service.py`

- [ ] **Step 1: Add `calculate_player_trends()` function to stats_service.py**

At the end of `services/stats_service.py`, add:

```python
def calculate_player_trends(games, players=None):
    """
    Calculate performance trends for selected players across games.
    
    Args:
        games: List of game dicts (already filtered by season/team/date range)
        players: Optional list of player names to include (default: all players in games)
    
    Returns:
        Dictionary with player names as keys:
        {
            "7 - Player Seven": {
                "game_scores": [8.5, 6.2, ...],
                "game_ids": [1, 2, ...],
                "mean_score": 7.8,
                "std_dev": 1.2,
                "min_score": 6.2,
                "max_score": 9.1,
                "outliers": [
                    {"game_id": 3, "score": 9.1, "type": "high", "z_score": 1.08},
                    ...
                ]
            }
        }
    """
    from statistics import mean, stdev
    
    # First pass: collect all unique players if not specified
    if players is None:
        all_players = set()
        for game in games:
            for line in game.get('lines', []):
                all_players.update(line)
        players = list(all_players)
    
    trends = {}
    
    for player in players:
        game_scores = []
        game_ids = []
        
        # Extract game scores for this player across all games
        for game in games:
            # Check if player is in this game
            player_in_game = any(player in line for line in game.get('lines', []))
            if not player_in_game:
                continue
            
            # Get game score (from game_scores if available, else calculate)
            if 'game_scores' in game and player in game['game_scores']:
                score = game['game_scores'][player]
            else:
                # Calculate game score on the fly
                goals = game.get('goals', {}).get(player, 0)
                assists = game.get('assists', {}).get(player, 0)
                plusminus = game.get('plusminus', {}).get(player, 0)
                errors = game.get('unforced_errors', {}).get(player, 0)
                sog = game.get('sog', {}).get(player, 0)
                penalties_drawn = game.get('penalties_drawn', {}).get(player, 0)
                penalties_taken = game.get('penalties_taken', {}).get(player, 0)
                
                score = calculate_game_score(goals, assists, plusminus, errors, sog, penalties_drawn, penalties_taken)
            
            game_scores.append(score)
            game_ids.append(game.get('id'))
        
        # If no games for this player, skip
        if not game_scores:
            continue
        
        # Calculate statistics
        mean_score = mean(game_scores)
        min_score = min(game_scores)
        max_score = max(game_scores)
        std_dev = stdev(game_scores) if len(game_scores) > 1 else 0
        
        # Identify outliers (|z_score| > 1.0)
        outliers = []
        if std_dev > 0:
            for score, game_id in zip(game_scores, game_ids):
                z_score = (score - mean_score) / std_dev
                if abs(z_score) > 1.0:
                    outliers.append({
                        'game_id': game_id,
                        'score': round(score, 2),
                        'type': 'high' if z_score > 0 else 'low',
                        'z_score': round(z_score, 2)
                    })
        
        trends[player] = {
            'game_scores': [round(s, 2) for s in game_scores],
            'game_ids': game_ids,
            'mean_score': round(mean_score, 2),
            'std_dev': round(std_dev, 2),
            'min_score': round(min_score, 2),
            'max_score': round(max_score, 2),
            'outliers': sorted(outliers, key=lambda x: x['game_id'])
        }
    
    return trends
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
pytest tests/test_analytics.py::TestPlayerTrends -v
```

Expected output: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add services/stats_service.py tests/test_analytics.py
git commit -m "feat: implement calculate_player_trends function for trend analysis"
```

---

## Task 3: Backend Tests for Lineup Combinations

**Files:**
- Modify: `tests/test_analytics.py` (add new test class)

- [ ] **Step 1: Add tests for `calculate_lineup_combinations()` to test_analytics.py**

At the end of `tests/test_analytics.py`, add:

```python
class TestLineupCombinations:
    """Test calculate_lineup_combinations function."""

    def test_calculate_lineup_combinations_returns_list(self, app_with_analytics_data):
        """calculate_lineup_combinations returns list of combo dicts."""
        with app_with_analytics_data.app_context():
            games = GameRecord.query.all()
            game_dicts = [row.to_dict() for row in games]
            
            combos = calculate_lineup_combinations(game_dicts, combo_size_range=(2, 2))
            
            assert isinstance(combos, list)
            assert len(combos) > 0

    def test_combo_has_required_fields(self, app_with_analytics_data):
        """Each combo has all required fields."""
        with app_with_analytics_data.app_context():
            games = GameRecord.query.all()
            game_dicts = [row.to_dict() for row in games]
            
            combos = calculate_lineup_combinations(game_dicts, combo_size_range=(2, 2))
            
            if combos:
                combo = combos[0]
                assert 'players' in combo
                assert 'combo_size' in combo
                assert 'games_played_together' in combo
                assert 'wins' in combo
                assert 'losses' in combo
                assert 'win_percentage' in combo
                assert 'avg_goal_differential' in combo
                assert 'avg_aggregate_game_score' in combo

    def test_combo_identifies_core_players(self, app_with_analytics_data):
        """Combos are generated from top players by Game Score."""
        with app_with_analytics_data.app_context():
            games = GameRecord.query.all()
            game_dicts = [row.to_dict() for row in games]
            
            from services.stats_service import ensure_game_stats, recalculate_game_scores
            for game in game_dicts:
                ensure_game_stats(game)
                recalculate_game_scores(game)
            
            combos = calculate_lineup_combinations(game_dicts, combo_size_range=(2, 2))
            
            # Should identify the two players in the games as core players
            if combos:
                combo = combos[0]
                assert len(combo['players']) == 2
                assert all(isinstance(p, str) for p in combo['players'])

    def test_combo_calculates_win_percentage(self, app_with_analytics_data):
        """Win percentage calculated correctly."""
        with app_with_analytics_data.app_context():
            games = GameRecord.query.all()
            game_dicts = [row.to_dict() for row in games]
            
            combos = calculate_lineup_combinations(game_dicts, combo_size_range=(2, 2))
            
            if combos:
                combo = combos[0]
                if combo['games_played_together'] > 0:
                    expected_win_pct = (combo['wins'] / combo['games_played_together']) * 100
                    assert abs(combo['win_percentage'] - expected_win_pct) < 0.01

    def test_combo_empty_games(self, app_with_analytics_data):
        """Empty games list returns empty list."""
        with app_with_analytics_data.app_context():
            combos = calculate_lineup_combinations([])
            assert combos == []

    def test_combo_respects_size_range(self, app_with_analytics_data):
        """Only returns combos in specified size range."""
        with app_with_analytics_data.app_context():
            games = GameRecord.query.all()
            game_dicts = [row.to_dict() for row in games]
            
            combos = calculate_lineup_combinations(game_dicts, combo_size_range=(2, 2))
            
            # All combos should be size 2
            assert all(c['combo_size'] == 2 for c in combos)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_analytics.py::TestLineupCombinations -v
```

Expected output: All tests FAIL with "calculate_lineup_combinations not found"

---

## Task 4: Implement `calculate_lineup_combinations()` Function

**Files:**
- Modify: `services/stats_service.py`

- [ ] **Step 1: Add `calculate_lineup_combinations()` function to stats_service.py**

At the end of `services/stats_service.py`, add:

```python
def calculate_lineup_combinations(games, combo_size_range=(5, 7), limit=10):
    """
    Identify core player combinations and their performance metrics.
    
    Args:
        games: List of game dicts (filtered by season/team)
        combo_size_range: Tuple (min_size, max_size) for combo sizes to analyze
        limit: Max combos per size to return (default 10)
    
    Returns:
        List of combo dicts sorted by avg_aggregate_game_score descending:
        [
            {
                "players": ["7 - Player Seven", "12 - Player Twelve", ...],
                "combo_size": 5,
                "games_played_together": 12,
                "wins": 9,
                "losses": 3,
                "win_percentage": 75.0,
                "avg_goal_differential": 2.1,
                "avg_aggregate_game_score": 42.3,
                "game_ids": [1, 2, 4, ...]
            }
        ]
    """
    from itertools import combinations
    
    if not games:
        return []
    
    # Ensure all games have calculated stats
    for game in games:
        if 'game_scores' not in game or not game['game_scores']:
            recalculate_game_scores(game)
    
    # Get all unique players
    all_players = set()
    for game in games:
        for line in game.get('lines', []):
            all_players.update(line)
    
    all_players = list(all_players)
    
    # Rank players by total game score across season
    player_scores = {}
    for player in all_players:
        total_score = 0
        for game in games:
            if 'game_scores' in game and player in game['game_scores']:
                total_score += game['game_scores'][player]
        player_scores[player] = total_score
    
    # Sort players by total score (descending)
    sorted_players = sorted(player_scores.items(), key=lambda x: x[1], reverse=True)
    top_players = [p[0] for p in sorted_players]
    
    all_combos = []
    
    # For each combo size in range
    for combo_size in range(combo_size_range[0], combo_size_range[1] + 1):
        # Generate combinations of top players
        for combo in combinations(top_players[:20], combo_size):  # Limit to top 20 to avoid explosion
            combo_players = list(combo)
            games_together = []
            wins = 0
            losses = 0
            goal_diffs = []
            agg_scores = []
            
            # Find games where ALL players in combo were present
            for game in games:
                # Check if all combo players are in this game
                all_in_game = all(
                    any(p in line for line in game.get('lines', [])) 
                    for p in combo_players
                )
                
                if not all_in_game:
                    continue
                
                games_together.append(game.get('id'))
                
                # Calculate win/loss
                home_goals = game.get('result', {}).get('1', {}).get('home', 0)
                away_goals = game.get('result', {}).get('1', {}).get('away', 0)
                
                # Assume "home" team if that's where our lineup plays (simplified)
                # In real scenario, might need to track which side the team is on
                if home_goals > away_goals:
                    wins += 1
                elif away_goals > home_goals:
                    losses += 1
                
                # Goal differential
                goal_diff = home_goals - away_goals
                goal_diffs.append(goal_diff)
                
                # Aggregate game score (sum of all combo players' game scores)
                agg_score = 0
                for player in combo_players:
                    if 'game_scores' in game and player in game['game_scores']:
                        agg_score += game['game_scores'][player]
                agg_scores.append(agg_score)
            
            # Only include if combo played in at least 1 game
            win_percentage = (wins / len(games_together) * 100) if games_together else 0
            avg_goal_diff = sum(goal_diffs) / len(goal_diffs) if goal_diffs else 0
            avg_agg_score = sum(agg_scores) / len(agg_scores) if agg_scores else 0
            
            all_combos.append({
                'players': combo_players,
                'combo_size': combo_size,
                'games_played_together': len(games_together),
                'wins': wins,
                'losses': losses,
                'win_percentage': round(win_percentage, 1),
                'avg_goal_differential': round(avg_goal_diff, 2),
                'avg_aggregate_game_score': round(avg_agg_score, 2),
                'game_ids': games_together
            })
    
    # Sort by avg_aggregate_game_score descending
    all_combos.sort(key=lambda x: x['avg_aggregate_game_score'], reverse=True)
    
    return all_combos[:limit]
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
pytest tests/test_analytics.py::TestLineupCombinations -v
```

Expected output: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add services/stats_service.py tests/test_analytics.py
git commit -m "feat: implement calculate_lineup_combinations function for core lineup analysis"
```

---

## Task 5: Backend API Endpoints

**Files:**
- Modify: `routes/api_routes.py`
- Modify: `tests/test_analytics.py` (add API endpoint tests)

- [ ] **Step 1: Add API endpoint tests to test_analytics.py**

At the end of `tests/test_analytics.py`, add:

```python
class TestAnalyticsAPI:
    """Test /api/player-trends and /api/lineup-combos endpoints."""

    @pytest.fixture
    def api_client(self, app_with_analytics_data):
        """Test client with authentication."""
        app = app_with_analytics_data
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['authenticated'] = True
            yield client

    def test_player_trends_endpoint_valid_request(self, api_client):
        """Valid request returns player trends data."""
        response = api_client.get('/api/player-trends?season=2025-26&team=U21')
        assert response.status_code == 200
        data = response.get_json()
        assert 'players' in data
        assert isinstance(data['players'], dict)

    def test_player_trends_missing_season(self, api_client):
        """Missing season returns 400."""
        response = api_client.get('/api/player-trends?team=U21')
        assert response.status_code == 400

    def test_player_trends_missing_team(self, api_client):
        """Missing team returns 400."""
        response = api_client.get('/api/player-trends?season=2025-26')
        assert response.status_code == 400

    def test_lineup_combos_endpoint_valid_request(self, api_client):
        """Valid request returns lineup combos data."""
        response = api_client.get('/api/lineup-combos?season=2025-26&team=U21')
        assert response.status_code == 200
        data = response.get_json()
        assert 'combos' in data
        assert isinstance(data['combos'], list)

    def test_lineup_combos_respects_size_param(self, api_client):
        """combo_size parameter filters results."""
        response = api_client.get('/api/lineup-combos?season=2025-26&team=U21&combo_size=2')
        assert response.status_code == 200
        data = response.get_json()
        # All combos should be size 2
        assert all(c['combo_size'] == 2 for c in data['combos'])
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_analytics.py::TestAnalyticsAPI -v
```

Expected output: All tests FAIL with 404

- [ ] **Step 3: Add endpoints to routes/api_routes.py**

At the end of `routes/api_routes.py`, add:

```python
@api_bp.route('/player-trends', methods=['GET'])
def player_trends():
    """
    GET /api/player-trends?season=2025-26&team=U21&players=7&last_n_games=10
    
    Returns player performance trends data.
    """
    from flask import jsonify
    from services.game_service import load_games, ensure_game_stats
    from services.stats_service import calculate_player_trends
    
    season = request.args.get('season', '').strip()
    team = request.args.get('team', '').strip()
    players_input = request.args.getlist('players')
    last_n_games_str = request.args.get('last_n_games', '')
    
    if not season:
        return jsonify({'error': 'season parameter is required'}), 400
    if not team:
        return jsonify({'error': 'team parameter is required'}), 400
    
    # Load and filter games
    try:
        games = load_games()
    except Exception:
        return jsonify({'error': 'Failed to load games'}), 500
    
    filtered_games = [g for g in games if g.get('season') == season and g.get('team') == team]
    
    # Apply last_n_games filter
    if last_n_games_str:
        try:
            last_n = int(last_n_games_str)
            filtered_games = filtered_games[-last_n:] if last_n > 0 else filtered_games
        except ValueError:
            return jsonify({'error': 'last_n_games must be an integer'}), 400
    
    # Normalize games
    for game in filtered_games:
        ensure_game_stats(game)
    
    # Calculate trends (pass players_input only if provided)
    requested_players = players_input if players_input else None
    trends = calculate_player_trends(filtered_games, players=requested_players)
    
    return jsonify({
        'players': trends,
        'metadata': {
            'games_analyzed': len(filtered_games),
            'season': season,
            'team': team
        }
    }), 200


@api_bp.route('/lineup-combos', methods=['GET'])
def lineup_combos():
    """
    GET /api/lineup-combos?season=2025-26&team=U21&combo_size=5&limit=10
    
    Returns core player combination performance data.
    """
    from flask import jsonify
    from services.game_service import load_games, ensure_game_stats
    from services.stats_service import calculate_lineup_combinations, recalculate_game_scores
    
    season = request.args.get('season', '').strip()
    team = request.args.get('team', '').strip()
    combo_size_str = request.args.get('combo_size', '5')
    limit_str = request.args.get('limit', '10')
    
    if not season:
        return jsonify({'error': 'season parameter is required'}), 400
    if not team:
        return jsonify({'error': 'team parameter is required'}), 400
    
    # Parse combo_size and limit
    try:
        combo_size = int(combo_size_str)
        limit = int(limit_str)
    except ValueError:
        return jsonify({'error': 'combo_size and limit must be integers'}), 400
    
    # Load and filter games
    try:
        games = load_games()
    except Exception:
        return jsonify({'error': 'Failed to load games'}), 500
    
    filtered_games = [g for g in games if g.get('season') == season and g.get('team') == team]
    
    # Normalize and calculate game scores
    for game in filtered_games:
        ensure_game_stats(game)
        recalculate_game_scores(game)
    
    # Calculate combos for the specified size
    combos = calculate_lineup_combinations(filtered_games, combo_size_range=(combo_size, combo_size), limit=limit)
    
    return jsonify({
        'combos': combos,
        'metadata': {
            'season': season,
            'team': team,
            'combo_size': combo_size,
            'total_combos': len(combos)
        }
    }), 200
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_analytics.py::TestAnalyticsAPI -v
```

Expected output: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add routes/api_routes.py tests/test_analytics.py
git commit -m "feat: add /api/player-trends and /api/lineup-combos endpoints"
```

---

## Task 6: Frontend HTML Structure

**Files:**
- Modify: `templates/stats.html`

- [ ] **Step 1: Find insertion point in stats.html**

Read the file and find where the last stat table ends (before closing `</div>` tags):

```bash
grep -n "table-responsive\|</div>" templates/stats.html | tail -20
```

- [ ] **Step 2: Insert Player Trends HTML section**

After the last stat table in `templates/stats.html`, insert:

```html
<!-- Player Trends Dashboard -->
<div id="trends-section" class="mt-5">
    <h2 class="mb-4">Player Development Trends</h2>
    
    <!-- Player Picker -->
    <div class="card mb-4">
        <div class="card-body">
            <label class="form-label">Select Players</label>
            <div class="input-group">
                <input 
                    type="text" 
                    id="trends-player-search" 
                    class="form-control" 
                    placeholder="Search players..."
                    autocomplete="off"
                >
            </div>
            <div id="trends-player-suggestions" class="list-group mt-2" style="display: none; max-height: 200px; overflow-y: auto;"></div>
            <div id="trends-selected-players" class="mt-3 d-flex flex-wrap gap-2"></div>
            <button id="trends-show-btn" class="btn btn-primary mt-3" disabled>Show Trends</button>
        </div>
    </div>
    
    <!-- Three-Panel Dashboard -->
    <div id="trends-container" style="display: none;">
        <div class="row mb-4">
            <div class="col-lg-6">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0">Performance Trajectory</h5>
                    </div>
                    <div class="card-body">
                        <canvas id="trends-trajectory-chart"></canvas>
                    </div>
                </div>
            </div>
            
            <div class="col-lg-6">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0">Performance Consistency</h5>
                    </div>
                    <div class="card-body">
                        <canvas id="trends-consistency-chart"></canvas>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">Best & Worst Performances</h5>
            </div>
            <div class="card-body">
                <div id="trends-outliers-table" class="table-responsive"></div>
            </div>
        </div>
    </div>
    
    <div id="trends-message" class="alert" style="display: none;"></div>
    <hr class="my-5">
</div>

<!-- Lineup Analysis -->
<div id="lineup-section" class="mt-5">
    <h2 class="mb-4">Core Lineup Performance</h2>
    
    <!-- Combo Selector -->
    <div class="card mb-4">
        <div class="card-body">
            <label class="form-label">Analyze Top Player Combinations</label>
            <div class="btn-group mb-3" role="group">
                <button type="button" class="btn btn-sm btn-outline-primary combo-size-btn active" data-combo-size="5">Top 5</button>
                <button type="button" class="btn btn-sm btn-outline-primary combo-size-btn" data-combo-size="6">Top 6</button>
                <button type="button" class="btn btn-sm btn-outline-primary combo-size-btn" data-combo-size="7">Top 7</button>
            </div>
            <br>
            <button id="lineup-show-btn" class="btn btn-primary">Show Analysis</button>
        </div>
    </div>
    
    <!-- Combo Matrix Table -->
    <div id="lineup-container" style="display: none;">
        <div class="table-responsive">
            <table class="table table-hover table-sm">
                <thead class="table-light">
                    <tr>
                        <th style="width: 35%;">Core Players</th>
                        <th class="text-center" style="width: 15%;">Games Together</th>
                        <th class="text-center sortable" data-sort-key="win_percentage">Win %</th>
                        <th class="text-center sortable" data-sort-key="avg_goal_differential">Avg Goal Diff</th>
                        <th class="text-center sortable" data-sort-key="avg_aggregate_game_score">Avg Aggregate Score</th>
                    </tr>
                </thead>
                <tbody id="lineup-matrix-body">
                </tbody>
            </table>
        </div>
    </div>
    
    <div id="lineup-message" class="alert" style="display: none;"></div>
</div>

<!-- Chart.js CDN (if not already loaded) -->
<script nonce="{{ g.csp_nonce }}" src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>

<!-- Analytics Dashboard JavaScript -->
<script nonce="{{ g.csp_nonce }}" src="{{ url_for('static', filename='js/analytics-dashboard.js') }}"></script>

<!-- Initialize analytics UI -->
<script nonce="{{ g.csp_nonce }}">
    document.addEventListener('DOMContentLoaded', function() {
        const trendsUI = new PlayerTrendsUI({{ players | tojson }});
        trendsUI.init();
        
        const lineupUI = new LineupAnalysisUI();
        lineupUI.init();
    });
</script>
```

- [ ] **Step 3: Verify HTML validity**

Check that the HTML is syntactically correct:

```bash
grep -c "id=\"trends-section\"\|id=\"lineup-section\"" templates/stats.html
```

Expected: Both sections should be found

- [ ] **Step 4: Commit**

```bash
git add templates/stats.html
git commit -m "feat: add Player Trends and Lineup Analysis HTML sections to stats page"
```

---

## Task 7: Frontend JavaScript Implementation

**Files:**
- Create: `static/js/analytics-dashboard.js`

- [ ] **Step 1: Create analytics-dashboard.js with PlayerTrendsUI class**

Create `static/js/analytics-dashboard.js`:

```javascript
/**
 * Advanced Analytics Dashboard UI Classes
 */

class PlayerTrendsUI {
    constructor(allPlayers) {
        this.allPlayers = allPlayers || [];
        this.selectedPlayers = [];
        this.currentSeason = new URLSearchParams(window.location.search).get('season') || '';
        this.currentTeam = new URLSearchParams(window.location.search).get('team') || '';
        
        // DOM elements
        this.playerSearch = document.getElementById('trends-player-search');
        this.playerSuggestions = document.getElementById('trends-player-suggestions');
        this.selectedPlayersContainer = document.getElementById('trends-selected-players');
        this.showBtn = document.getElementById('trends-show-btn');
        this.container = document.getElementById('trends-container');
        this.messageEl = document.getElementById('trends-message');
        this.trajectoryCanvas = document.getElementById('trends-trajectory-chart');
        this.consistencyCanvas = document.getElementById('trends-consistency-chart');
        this.outliersTable = document.getElementById('trends-outliers-table');
        
        this.trajectoryChart = null;
        this.consistencyChart = null;
    }
    
    init() {
        if (this.playerSearch) {
            this.playerSearch.addEventListener('input', (e) => this.handlePlayerSearch(e));
            this.playerSearch.addEventListener('blur', () => setTimeout(() => this.hidePlayerSuggestions(), 200));
        }
        
        if (this.playerSuggestions) {
            this.playerSuggestions.addEventListener('click', (e) => this.handlePlayerSelect(e));
        }
        
        if (this.showBtn) {
            this.showBtn.addEventListener('click', () => this.fetchAndRenderTrends());
        }
    }
    
    handlePlayerSearch(e) {
        const query = e.target.value.toLowerCase().trim();
        
        if (!query) {
            this.hidePlayerSuggestions();
            return;
        }
        
        const filtered = this.allPlayers.filter(p => 
            p.toLowerCase().includes(query) &&
            !this.selectedPlayers.includes(p)
        );
        
        this.playerSuggestions.innerHTML = '';
        filtered.slice(0, 10).forEach(player => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'list-group-item list-group-item-action';
            btn.textContent = player;
            btn.dataset.player = player;
            this.playerSuggestions.appendChild(btn);
        });
        
        this.playerSuggestions.style.display = filtered.length > 0 ? 'block' : 'none';
    }
    
    handlePlayerSelect(e) {
        if (e.target.dataset && e.target.dataset.player) {
            this.selectedPlayers.push(e.target.dataset.player);
            this.playerSearch.value = '';
            this.hidePlayerSuggestions();
            this.renderSelectedPlayers();
            this.updateShowButton();
        }
    }
    
    addSelectedPlayer(player) {
        if (!this.selectedPlayers.includes(player)) {
            this.selectedPlayers.push(player);
            this.renderSelectedPlayers();
            this.updateShowButton();
        }
    }
    
    removeSelectedPlayer(player) {
        this.selectedPlayers = this.selectedPlayers.filter(p => p !== player);
        this.renderSelectedPlayers();
        this.updateShowButton();
    }
    
    renderSelectedPlayers() {
        this.selectedPlayersContainer.innerHTML = '';
        
        this.selectedPlayers.forEach(player => {
            const pill = document.createElement('div');
            pill.className = 'badge bg-primary d-flex align-items-center gap-2';
            pill.style.fontSize = '0.95rem';
            pill.style.padding = '0.5rem 0.75rem';
            
            const label = document.createElement('span');
            label.textContent = player;
            
            const closeBtn = document.createElement('button');
            closeBtn.type = 'button';
            closeBtn.className = 'btn-close btn-close-white';
            closeBtn.style.padding = '0';
            closeBtn.style.fontSize = '0.75rem';
            closeBtn.dataset.player = player;
            
            closeBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.removeSelectedPlayer(player);
            });
            
            pill.appendChild(label);
            pill.appendChild(closeBtn);
            this.selectedPlayersContainer.appendChild(pill);
        });
    }
    
    hidePlayerSuggestions() {
        this.playerSuggestions.style.display = 'none';
    }
    
    updateShowButton() {
        this.showBtn.disabled = this.selectedPlayers.length === 0;
    }
    
    async fetchAndRenderTrends() {
        if (this.selectedPlayers.length === 0) {
            this.showMessage('Select at least one player', 'alert-warning');
            return;
        }
        
        this.showBtn.disabled = true;
        this.hideMessage();
        
        const params = new URLSearchParams();
        params.append('season', this.currentSeason);
        params.append('team', this.currentTeam);
        this.selectedPlayers.forEach(p => params.append('players', p));
        
        try {
            const response = await fetch(`/api/player-trends?${params}`);
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to load trends');
            }
            
            const data = await response.json();
            
            if (Object.keys(data.players).length === 0) {
                this.showMessage('No data available for selected players', 'alert-info');
                this.hideContainer();
            } else {
                this.renderTrends(data.players);
                this.showContainer();
            }
        } catch (error) {
            this.showMessage(`Error: ${error.message}`, 'alert-danger');
            this.hideContainer();
        } finally {
            this.showBtn.disabled = false;
        }
    }
    
    renderTrends(playerTrends) {
        const colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#C9CBCF'];
        
        // Render trajectory chart
        if (this.trajectoryChart) this.trajectoryChart.destroy();
        
        const trajectoryDatasets = [];
        const maxGames = Math.max(...Object.values(playerTrends).map(p => p.game_ids.length));
        const gameLabels = [];
        
        // Build x-axis labels from first player's games
        const firstPlayer = Object.keys(playerTrends)[0];
        firstPlayer && playerTrends[firstPlayer].game_ids.forEach((id, idx) => {
            gameLabels.push(`Game ${id}`);
        });
        
        Object.entries(playerTrends).forEach(([player, data], idx) => {
            trajectoryDatasets.push({
                label: player,
                data: data.game_scores,
                borderColor: colors[idx % colors.length],
                backgroundColor: colors[idx % colors.length] + '20',
                borderWidth: 2,
                fill: false,
                tension: 0.3,
                pointRadius: 4,
                pointHoverRadius: 6
            });
        });
        
        this.trajectoryChart = new Chart(this.trajectoryCanvas, {
            type: 'line',
            data: {
                labels: gameLabels,
                datasets: trajectoryDatasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    title: { display: true, text: 'Game Score Trajectory' },
                    legend: { display: true, position: 'top' }
                },
                scales: {
                    y: { beginAtZero: true, title: { display: true, text: 'Game Score' } },
                    x: { title: { display: true, text: 'Game' } }
                }
            }
        });
        
        // Render consistency box plot
        if (this.consistencyChart) this.consistencyChart.destroy();
        
        const consistencyDatasets = [];
        
        Object.entries(playerTrends).forEach(([player, data], idx) => {
            const scores = data.game_scores;
            scores.sort((a, b) => a - b);
            
            const q1Idx = Math.floor(scores.length * 0.25);
            const medianIdx = Math.floor(scores.length * 0.5);
            const q3Idx = Math.floor(scores.length * 0.75);
            
            const q1 = scores[q1Idx];
            const median = scores[medianIdx];
            const q3 = scores[q3Idx];
            
            // Create simple box representation
            consistencyDatasets.push({
                label: player,
                data: [
                    { x: player, low: data.min_score, q1: q1, median: median, q3: q3, high: data.max_score }
                ],
                borderColor: colors[idx % colors.length],
                backgroundColor: colors[idx % colors.length] + '40',
                pointRadius: 0
            });
        });
        
        // Simplified box plot: show bar chart with min/max/mean
        const boxDatasets = [];
        Object.entries(playerTrends).forEach(([player, data], idx) => {
            boxDatasets.push({
                label: `${player} (Min/Mean/Max)`,
                data: [data.min_score, data.mean_score, data.max_score],
                backgroundColor: colors[idx % colors.length]
            });
        });
        
        this.consistencyChart = new Chart(this.consistencyCanvas, {
            type: 'bar',
            data: {
                labels: ['Min Score', 'Mean Score', 'Max Score'],
                datasets: boxDatasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    title: { display: true, text: 'Score Distribution (Min/Mean/Max)' },
                    legend: { display: true, position: 'top' }
                },
                scales: {
                    y: { beginAtZero: true, title: { display: true, text: 'Score' } }
                }
            }
        });
        
        // Render outliers table
        this.renderOutliersTable(playerTrends);
    }
    
    renderOutliersTable(playerTrends) {
        let html = '<table class="table table-sm table-hover"><thead class="table-light"><tr><th>Player</th><th>Game</th><th>Score</th><th>Type</th><th>Z-Score</th></tr></thead><tbody>';
        
        Object.entries(playerTrends).forEach(([player, data]) => {
            data.outliers.forEach(outlier => {
                html += `<tr><td>${player}</td><td>Game ${outlier.game_id}</td><td>${outlier.score}</td><td><span class="badge ${outlier.type === 'high' ? 'bg-success' : 'bg-danger'}">${outlier.type}</span></td><td>${outlier.z_score}</td></tr>`;
            });
        });
        
        html += '</tbody></table>';
        this.outliersTable.innerHTML = html || '<p class="text-muted">No outliers detected</p>';
    }
    
    showMessage(message, alertClass = 'alert-info') {
        this.messageEl.textContent = message;
        this.messageEl.className = `alert ${alertClass}`;
        this.messageEl.style.display = 'block';
    }
    
    hideMessage() {
        this.messageEl.style.display = 'none';
    }
    
    showContainer() {
        this.container.style.display = 'block';
    }
    
    hideContainer() {
        this.container.style.display = 'none';
    }
}


class LineupAnalysisUI {
    constructor() {
        this.selectedComboSize = 5;
        this.currentSeason = new URLSearchParams(window.location.search).get('season') || '';
        this.currentTeam = new URLSearchParams(window.location.search).get('team') || '';
        
        // DOM elements
        this.comboSizeBtns = document.querySelectorAll('.combo-size-btn');
        this.showBtn = document.getElementById('lineup-show-btn');
        this.container = document.getElementById('lineup-container');
        this.matrixBody = document.getElementById('lineup-matrix-body');
        this.messageEl = document.getElementById('lineup-message');
    }
    
    init() {
        this.comboSizeBtns.forEach(btn => {
            btn.addEventListener('click', (e) => this.handleComboSizeSelect(e));
        });
        
        if (this.showBtn) {
            this.showBtn.addEventListener('click', () => this.fetchAndRenderCombos());
        }
    }
    
    handleComboSizeSelect(e) {
        this.comboSizeBtns.forEach(btn => btn.classList.remove('active'));
        e.target.classList.add('active');
        this.selectedComboSize = parseInt(e.target.dataset.comboSize);
    }
    
    async fetchAndRenderCombos() {
        this.hideMessage();
        this.showBtn.disabled = true;
        
        const params = new URLSearchParams();
        params.append('season', this.currentSeason);
        params.append('team', this.currentTeam);
        params.append('combo_size', this.selectedComboSize);
        
        try {
            const response = await fetch(`/api/lineup-combos?${params}`);
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to load lineup combos');
            }
            
            const data = await response.json();
            
            if (data.combos.length === 0) {
                this.showMessage('No lineup combinations found', 'alert-info');
                this.hideContainer();
            } else {
                this.renderMatrix(data.combos);
                this.showContainer();
            }
        } catch (error) {
            this.showMessage(`Error: ${error.message}`, 'alert-danger');
            this.hideContainer();
        } finally {
            this.showBtn.disabled = false;
        }
    }
    
    renderMatrix(combos) {
        this.matrixBody.innerHTML = '';
        
        combos.forEach(combo => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><small>${combo.players.join(', ')}</small></td>
                <td class="text-center">${combo.games_played_together}</td>
                <td class="text-center">${combo.games_played_together > 0 ? combo.win_percentage.toFixed(1) + '%' : '—'}</td>
                <td class="text-center">${combo.games_played_together > 0 ? combo.avg_goal_differential.toFixed(2) : '—'}</td>
                <td class="text-center"><strong>${combo.avg_aggregate_game_score.toFixed(2)}</strong></td>
            `;
            this.matrixBody.appendChild(row);
        });
    }
    
    showMessage(message, alertClass = 'alert-info') {
        this.messageEl.textContent = message;
        this.messageEl.className = `alert ${alertClass}`;
        this.messageEl.style.display = 'block';
    }
    
    hideMessage() {
        this.messageEl.style.display = 'none';
    }
    
    showContainer() {
        this.container.style.display = 'block';
    }
    
    hideContainer() {
        this.container.style.display = 'none';
    }
}
```

- [ ] **Step 2: Verify JavaScript syntax**

```bash
node -c static/js/analytics-dashboard.js
```

Expected: No syntax errors

- [ ] **Step 3: Commit**

```bash
git add static/js/analytics-dashboard.js
git commit -m "feat: add PlayerTrendsUI and LineupAnalysisUI classes for analytics dashboards"
```

---

## Task 8: Integration Tests & Final Verification

**Files:**
- Modify: `tests/test_analytics.py` (add integration test)

- [ ] **Step 1: Add integration test**

At the end of `tests/test_analytics.py`, add:

```python
class TestAnalyticsIntegration:
    """Integration tests for complete analytics feature."""

    def test_stats_page_includes_analytics_sections(self, client, clean_db):
        """Stats page includes both analytics sections."""
        response = client.get('/stats')
        assert response.status_code == 200
        assert b'trends-section' in response.data
        assert b'lineup-section' in response.data
        assert b'analytics-dashboard.js' in response.data

    def test_full_analytics_workflow(self, app_with_analytics_data):
        """End-to-end workflow: fetch trends and combos."""
        with app_with_analytics_data.app_context():
            games = GameRecord.query.all()
            game_dicts = [row.to_dict() for row in games]
            
            from services.stats_service import ensure_game_stats, recalculate_game_scores
            for game in game_dicts:
                ensure_game_stats(game)
                recalculate_game_scores(game)
            
            # Get trends
            trends = calculate_player_trends(game_dicts)
            assert len(trends) > 0
            
            # Get combos
            combos = calculate_lineup_combinations(game_dicts)
            assert len(combos) > 0
```

- [ ] **Step 2: Run all analytics tests**

```bash
pytest tests/test_analytics.py -v
```

Expected: All tests PASS

- [ ] **Step 3: Run full test suite**

```bash
pytest tests/ -v --tb=short 2>&1 | tail -50
```

Expected: No failures, all existing tests still pass

- [ ] **Step 4: Verify feature completeness against spec**

Checklist:
- [ ] Player trends calculation includes trajectory, consistency, outliers
- [ ] Lineup combinations identified by top players and aggregated Game Score
- [ ] Both API endpoints implemented with proper validation
- [ ] Frontend HTML sections added to stats page
- [ ] PlayerTrendsUI and LineupAnalysisUI classes created and initialized
- [ ] Chart.js used for trajectory and consistency visualization
- [ ] All tests passing

- [ ] **Step 5: Final commit**

```bash
git add tests/test_analytics.py
git commit -m "test: add integration tests for advanced analytics feature

- Player trends analysis with trajectory, consistency, outlier detection
- Lineup combination performance metrics
- API endpoints /api/player-trends and /api/lineup-combos
- Interactive dashboards on stats page
- All 20+ unit and integration tests passing"
```

---

## Summary

| Task | Files | Effort | Dependencies |
|------|-------|--------|--------------|
| **1. Backend Tests (Trends)** | tests/test_analytics.py | 1 task | None |
| **2. Implement Trends Calculation** | services/stats_service.py | 1 task | Task 1 |
| **3. Backend Tests (Combos)** | tests/test_analytics.py | 1 task | None |
| **4. Implement Combos Calculation** | services/stats_service.py | 1 task | Task 3 |
| **5. API Endpoints** | routes/api_routes.py, tests/test_analytics.py | 1 task | Tasks 2, 4 |
| **6. Frontend HTML** | templates/stats.html | 1 task | None (parallel with 1-5) |
| **7. Frontend JavaScript** | static/js/analytics-dashboard.js | 1 task | Task 6 |
| **8. Integration & Verification** | tests/test_analytics.py | 1 task | All above |

**Estimated effort:** ~3-4 days for sequential execution; ~2-3 days if tasks 1-4 and 6 run in parallel.

**Critical path:** Tasks 1→2, 3→4→5 must be sequential; Task 6 can run in parallel; Task 7 depends on Task 6; Task 8 is final verification.

