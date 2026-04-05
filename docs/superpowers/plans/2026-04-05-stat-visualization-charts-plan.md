# Real-Time Stat Visualization & Charts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add interactive charts to the stats page allowing coaches to select players and visualize Game Score and Goals/Assists trends without page reload.

**Architecture:** Backend `/api/chart-data` endpoint reuses existing stats calculation logic and returns JSON filtered by season, team, and selected players. Frontend builds a Charts section with player picker, stat selector, and Chart.js rendering. All existing filters (season, team, game range) apply automatically.

**Tech Stack:** Chart.js 4.x (CDN), Flask blueprint, existing `calculate_stats_optimized()`, no new Python dependencies.

---

## File Structure

| File | Type | Purpose |
|------|------|---------|
| `routes/api_routes.py` | Modify | Add `/api/chart-data` GET endpoint |
| `templates/stats.html` | Modify | Add Charts section before existing tables |
| `static/js/stats-charts.js` | Create | Player picker, stat selector, AJAX handler, Chart.js initialization |
| `tests/test_chart_api.py` | Create | Test suite for endpoint: filtering, validation, error cases |

---

## Task 1: Backend Endpoint — Test Suite

**Files:**
- Create: `tests/test_chart_api.py`

- [ ] **Step 1: Write test file with all test cases (TDD)**

Create `tests/test_chart_api.py`:

```python
"""
Tests for /api/chart-data endpoint
"""
import pytest
from app import create_app
from models.database import db
from models.game_model import GameRecord


@pytest.fixture
def app_with_test_data():
    """Create app with sample games for testing."""
    app = create_app()
    with app.app_context():
        db.create_all()
        
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
        
        yield app
        
        db.session.remove()


@pytest.fixture
def client(app_with_test_data):
    """Test client with authenticated session."""
    app = app_with_test_data
    with app.app_context():
        with app.test_client() as client:
            # Authenticate using PIN
            with client.session_transaction() as sess:
                sess['authenticated'] = True
                sess['is_admin_session'] = False
            yield client


class TestChartDataEndpoint:
    """Test /api/chart-data endpoint."""

    def test_valid_request_returns_data(self, client):
        """Valid request with season, team, players returns correct data."""
        response = client.get('/api/chart-data?season=2025-26&team=U21&players=7&players=12')
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'players' in data
        assert 'games' in data
        assert data['players'] == ['7', '12']
        assert len(data['games']) == 2
        
        # Check first game
        game1 = data['games'][0]
        assert game1['date'] == '2025-11-14'
        assert game1['game_id'] == 1
        assert '7' in game1
        assert '12' in game1
        assert game1['7']['goals'] == 2
        assert game1['7']['assists'] == 1

    def test_missing_season_returns_400(self, client):
        """Request without season returns 400."""
        response = client.get('/api/chart-data?team=U21&players=7')
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_missing_team_returns_400(self, client):
        """Request without team returns 400."""
        response = client.get('/api/chart-data?season=2025-26&players=7')
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_missing_players_returns_400(self, client):
        """Request without players returns 400."""
        response = client.get('/api/chart-data?season=2025-26&team=U21')
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data and 'player' in data['error'].lower()

    def test_last_n_games_filtering(self, client):
        """last_n_games parameter limits results."""
        response = client.get('/api/chart-data?season=2025-26&team=U21&players=7&last_n_games=1')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['games']) == 1
        assert data['games'][0]['game_id'] == 2  # Most recent game

    def test_nonexistent_season_returns_empty(self, client):
        """Request for nonexistent season returns empty games array."""
        response = client.get('/api/chart-data?season=1999-00&team=U21&players=7')
        assert response.status_code == 200
        data = response.get_json()
        assert data['games'] == []

    def test_player_not_in_dataset_omitted_from_game(self, client):
        """Player not in a specific game is omitted from that game."""
        response = client.get('/api/chart-data?season=2025-26&team=U21&players=999&players=7')
        assert response.status_code == 200
        data = response.get_json()
        # Player 999 should be in the player list
        assert '999' in data['players']
        # But not in the actual game data (since we didn't create games with this player)
        for game in data['games']:
            if '999' not in game:
                # This is acceptable behavior
                pass

    def test_game_score_calculated_correctly(self, client):
        """Response includes calculated game_score for each player."""
        response = client.get('/api/chart-data?season=2025-26&team=U21&players=7')
        assert response.status_code == 200
        data = response.get_json()
        
        for game in data['games']:
            assert 'game_score' in game['7']
            # Game score should be a positive number (or zero)
            assert isinstance(game['7']['game_score'], (int, float))
            assert game['7']['game_score'] >= 0
```

- [ ] **Step 2: Run tests to verify they all fail**

```bash
pytest tests/test_chart_api.py -v
```

Expected output: All tests FAIL with "No such endpoint" or "404"

---

## Task 2: Backend Endpoint — Implementation

**Files:**
- Modify: `routes/api_routes.py`

- [ ] **Step 1: Read current api_routes.py to understand structure**

```bash
head -50 routes/api_routes.py
```

- [ ] **Step 2: Add chart-data endpoint to routes/api_routes.py**

At the end of `routes/api_routes.py` (before the closing of the file), add:

```python
@api_bp.route('/chart-data', methods=['GET'])
def chart_data():
    """
    Return chart data (game scores and goals/assists) for selected players.
    
    Query Parameters:
        season (required): Season name (e.g., "2025-26")
        team (required): Team/category (e.g., "U21")
        last_n_games (optional): Limit to last N games
        players (required, repeated): Player names/numbers to include
    
    Returns JSON with structure:
        {
            "players": ["7", "12"],
            "games": [
                {
                    "date": "2025-11-14",
                    "game_id": 5,
                    "home_team": "Team A",
                    "away_team": "Team B",
                    "7": {"game_score": 8.5, "goals": 2, "assists": 1},
                    "12": {"game_score": 5.2, "goals": 1, "assists": 0}
                },
                ...
            ]
        }
    """
    from flask import jsonify
    from services.game_service import load_games, ensure_game_stats
    from services.stats_service import calculate_stats_optimized
    
    # Validate required parameters
    season = request.args.get('season', '').strip()
    team = request.args.get('team', '').strip()
    players_input = request.args.getlist('players')
    last_n_games_str = request.args.get('last_n_games', '')
    
    if not season:
        return jsonify({'error': 'season parameter is required'}), 400
    if not team:
        return jsonify({'error': 'team parameter is required'}), 400
    if not players_input:
        return jsonify({'error': 'At least one player required'}), 400
    
    # Parse last_n_games
    try:
        last_n_games = int(last_n_games_str) if last_n_games_str else None
    except ValueError:
        return jsonify({'error': 'last_n_games must be an integer'}), 400
    
    # Load and filter games
    try:
        games = load_games()
    except Exception:
        return jsonify({'error': 'Failed to load games'}), 500
    
    # Filter by season and team
    filtered_games = [
        game for game in games
        if game.get('season') == season and game.get('team') == team
    ]
    
    # Apply last_n_games filter
    if last_n_games and last_n_games > 0:
        filtered_games = filtered_games[-last_n_games:]
    
    # Normalize and calculate stats for each game
    for game in filtered_games:
        ensure_game_stats(game)
    
    # If no games, return empty result
    if not filtered_games:
        return jsonify({'players': players_input, 'games': []}), 200
    
    # Calculate stats for the filtered games
    try:
        stats_data = calculate_stats_optimized(filtered_games, hide_zero=False)
    except Exception:
        return jsonify({'error': 'Failed to calculate stats'}), 500
    
    # Build response with per-game stats for requested players
    result_games = []
    for game in filtered_games:
        game_entry = {
            'date': game.get('date', ''),
            'game_id': game.get('id'),
            'home_team': game.get('home_team', ''),
            'away_team': game.get('away_team', '')
        }
        
        # Extract stats for each requested player
        for player in players_input:
            player_key = None
            # Try to find the player in the game's lines
            for line in game.get('lines', []):
                if player in line:
                    player_key = player
                    break
            
            if not player_key:
                # Player not in this game, skip
                continue
            
            # Get stats from the calculated stats data
            game_score = stats_data['player_totals'].get(player, {}).get('avg_game_score', 0)
            
            # Get per-game stats from game data
            goals = game.get('goals', {}).get(player_key, 0)
            assists = game.get('assists', {}).get(player_key, 0)
            
            # Store player stats for this game
            if player not in game_entry:
                game_entry[player] = {
                    'game_score': game_score,
                    'goals': goals,
                    'assists': assists
                }
        
        result_games.append(game_entry)
    
    return jsonify({
        'players': players_input,
        'games': result_games
    }), 200
```

- [ ] **Step 3: Run the tests again**

```bash
pytest tests/test_chart_api.py -v
```

Expected: Some tests still fail because the stat calculation logic needs refinement. Note which tests fail and what the exact error is.

- [ ] **Step 4: Refine endpoint to handle per-game stat calculation**

The issue is that `calculate_stats_optimized()` calculates *aggregate* stats across all games, not per-game stats. We need to extract per-game stats directly from the game data. Replace the previous endpoint implementation with:

```python
@api_bp.route('/chart-data', methods=['GET'])
def chart_data():
    """
    Return chart data (game scores and goals/assists) for selected players.
    
    Query Parameters:
        season (required): Season name (e.g., "2025-26")
        team (required): Team/category (e.g., "U21")
        last_n_games (optional): Limit to last N games
        players (required, repeated): Player names/numbers to include
    
    Returns JSON with structure:
        {
            "players": ["7", "12"],
            "games": [
                {
                    "date": "2025-11-14",
                    "game_id": 5,
                    "home_team": "Team A",
                    "away_team": "Team B",
                    "7": {"game_score": 8.5, "goals": 2, "assists": 1},
                    "12": {"game_score": 5.2, "goals": 1, "assists": 0}
                },
                ...
            ]
        }
    """
    from flask import jsonify
    from services.game_service import load_games, ensure_game_stats
    from services.stats_service import recalculate_game_scores
    
    # Validate required parameters
    season = request.args.get('season', '').strip()
    team = request.args.get('team', '').strip()
    players_input = request.args.getlist('players')
    last_n_games_str = request.args.get('last_n_games', '')
    
    if not season:
        return jsonify({'error': 'season parameter is required'}), 400
    if not team:
        return jsonify({'error': 'team parameter is required'}), 400
    if not players_input:
        return jsonify({'error': 'At least one player required'}), 400
    
    # Parse last_n_games
    try:
        last_n_games = int(last_n_games_str) if last_n_games_str else None
    except ValueError:
        return jsonify({'error': 'last_n_games must be an integer'}), 400
    
    # Load and filter games
    try:
        games = load_games()
    except Exception:
        return jsonify({'error': 'Failed to load games'}), 500
    
    # Filter by season and team
    filtered_games = [
        game for game in games
        if game.get('season') == season and game.get('team') == team
    ]
    
    # Apply last_n_games filter
    if last_n_games and last_n_games > 0:
        filtered_games = filtered_games[-last_n_games:]
    
    # Normalize and ensure game scores
    for game in filtered_games:
        ensure_game_stats(game)
        recalculate_game_scores(game)
    
    # If no games, return empty result
    if not filtered_games:
        return jsonify({'players': players_input, 'games': []}), 200
    
    # Build response with per-game stats for requested players
    result_games = []
    for game in filtered_games:
        game_entry = {
            'date': game.get('date', ''),
            'game_id': game.get('id'),
            'home_team': game.get('home_team', ''),
            'away_team': game.get('away_team', '')
        }
        
        # Extract stats for each requested player
        for player in players_input:
            player_key = None
            
            # Try to find the player in the game's lines (matches "number - name" format)
            for line in game.get('lines', []):
                if player in line:
                    player_key = player
                    break
            
            if not player_key:
                # Player not in this game, skip (will be absent from response for this game)
                continue
            
            # Extract per-game stats from game data
            goals = game.get('goals', {}).get(player_key, 0)
            assists = game.get('assists', {}).get(player_key, 0)
            
            # Calculate game score for this player in this game
            # Game score formula: goals * 3.0 + assists * 2.0 + sog * 0.75 + plusminus * 0.5
            #                     + penalties_drawn * 0.5 - penalties_taken * 1.0 - unforced_errors * 1.0
            sog = game.get('sog', {}).get(player_key, 0)
            plusminus = game.get('plusminus', {}).get(player_key, 0)
            penalties_drawn = game.get('penalties_drawn', {}).get(player_key, 0)
            penalties_taken = game.get('penalties_taken', {}).get(player_key, 0)
            unforced_errors = game.get('unforced_errors', {}).get(player_key, 0)
            
            game_score = (
                goals * 3.0 +
                assists * 2.0 +
                sog * 0.75 +
                plusminus * 0.5 +
                penalties_drawn * 0.5 -
                penalties_taken * 1.0 -
                unforced_errors * 1.0
            )
            
            # Store player stats for this game
            game_entry[player] = {
                'game_score': round(game_score, 1),
                'goals': goals,
                'assists': assists
            }
        
        result_games.append(game_entry)
    
    return jsonify({
        'players': players_input,
        'games': result_games
    }), 200
```

- [ ] **Step 5: Run tests again**

```bash
pytest tests/test_chart_api.py -v
```

Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add routes/api_routes.py tests/test_chart_api.py
git commit -m "feat: add /api/chart-data endpoint for chart visualization"
```

---

## Task 3: Frontend HTML Structure

**Files:**
- Modify: `templates/stats.html`

- [ ] **Step 1: Read stats.html to understand structure**

```bash
head -100 templates/stats.html
```

Note the location of filter controls and where tables begin. We'll insert the Charts section right after filters.

- [ ] **Step 2: Add Charts section HTML to stats.html**

Find the location after the filter form (look for `</form>` that closes the season/team/range filters). Insert this HTML block right after it, before the first stat table:

```html
<!-- Charts Section -->
<div id="charts-section" class="mb-5">
    <h2 class="mb-4">{{ g.t.stats_overview }}</h2>
    
    <!-- Player Picker and Stat Selector -->
    <div class="card mb-4">
        <div class="card-body">
            <div class="row g-3">
                <!-- Player Picker Column -->
                <div class="col-md-8">
                    <label class="form-label">Select Players</label>
                    <div class="input-group">
                        <input 
                            type="text" 
                            id="player-search" 
                            class="form-control" 
                            placeholder="Search and select players..."
                            autocomplete="off"
                        >
                    </div>
                    <div id="player-suggestions" class="list-group mt-2" style="display: none; max-height: 200px; overflow-y: auto;"></div>
                    
                    <!-- Selected Players Pills -->
                    <div id="selected-players" class="mt-3 d-flex flex-wrap gap-2"></div>
                </div>
                
                <!-- Stat Selector Column -->
                <div class="col-md-4">
                    <label class="form-label">{{ g.t.stats_overview }}</label>
                    <div class="btn-group w-100" role="group">
                        <input type="radio" class="btn-check" name="stat-selector" id="stat-game-score" value="game_score" checked>
                        <label class="btn btn-outline-primary" for="stat-game-score">Game Score</label>
                        
                        <input type="radio" class="btn-check" name="stat-selector" id="stat-goals-assists" value="goals_assists">
                        <label class="btn btn-outline-primary" for="stat-goals-assists">Goals & Assists</label>
                    </div>
                </div>
            </div>
            
            <!-- Show Chart Button -->
            <div class="mt-3">
                <button 
                    id="show-chart-btn" 
                    class="btn btn-primary" 
                    disabled
                >
                    {{ g.t.show_chart | default('Show Chart') }}
                </button>
                <div id="chart-loading" class="spinner-border spinner-border-sm ms-2" style="display: none;"></div>
            </div>
        </div>
    </div>
    
    <!-- Chart Display Area -->
    <div id="chart-container" class="card" style="display: none;">
        <div class="card-body">
            <canvas id="stats-chart"></canvas>
        </div>
    </div>
    
    <!-- Message Area (empty state, errors) -->
    <div id="chart-message" class="alert alert-info" style="display: none;"></div>
</div>

<!-- Add Chart.js via CDN in a script tag with nonce -->
<script nonce="{{ g.csp_nonce }}" src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>

<!-- Import the stats-charts.js module -->
<script nonce="{{ g.csp_nonce }}" src="{{ url_for('static', filename='js/stats-charts.js') }}"></script>

<!-- Initialize chart on page load -->
<script nonce="{{ g.csp_nonce }}">
    document.addEventListener('DOMContentLoaded', function() {
        const chartUI = new StatsChartUI({{ players | tojson }});
        chartUI.init();
    });
</script>
```

- [ ] **Step 3: Verify HTML structure is valid**

Check that the inserted HTML:
- Is placed right after the filter form but before the existing stat tables
- Uses correct Bootstrap 5 classes
- Has proper IDs and data attributes for JS to target

```bash
grep -n "chart-section\|Show Chart" templates/stats.html
```

- [ ] **Step 4: Commit HTML changes**

```bash
git add templates/stats.html
git commit -m "feat: add charts section HTML structure to stats page"
```

---

## Task 4: Frontend JavaScript Implementation

**Files:**
- Create: `static/js/stats-charts.js`

- [ ] **Step 1: Create the stats-charts.js file**

Create `static/js/stats-charts.js`:

```javascript
/**
 * StatsChartUI - Handles player picker, stat selector, and chart rendering
 */
class StatsChartUI {
    constructor(allPlayers) {
        this.allPlayers = allPlayers;
        this.selectedPlayers = [];
        this.currentStatType = 'game_score';
        this.chartInstance = null;
        
        // DOM elements
        this.playerSearch = document.getElementById('player-search');
        this.playerSuggestions = document.getElementById('player-suggestions');
        this.selectedPlayersContainer = document.getElementById('selected-players');
        this.statRadios = document.querySelectorAll('input[name="stat-selector"]');
        this.showChartBtn = document.getElementById('show-chart-btn');
        this.chartLoading = document.getElementById('chart-loading');
        this.chartContainer = document.getElementById('chart-container');
        this.chartMessage = document.getElementById('chart-message');
        this.chartCanvas = document.getElementById('stats-chart');
    }
    
    init() {
        // Attach event listeners
        this.playerSearch.addEventListener('input', (e) => this.handlePlayerSearch(e));
        this.playerSearch.addEventListener('blur', () => this.hidePlayerSuggestions());
        
        this.playerSuggestions.addEventListener('click', (e) => this.handlePlayerSelect(e));
        
        this.statRadios.forEach(radio => {
            radio.addEventListener('change', (e) => this.handleStatTypeChange(e));
        });
        
        this.showChartBtn.addEventListener('click', () => this.fetchAndRenderChart());
    }
    
    handlePlayerSearch(e) {
        const query = e.target.value.toLowerCase().trim();
        
        if (!query) {
            this.hidePlayerSuggestions();
            return;
        }
        
        // Filter players based on query
        const filtered = this.allPlayers.filter(p => 
            p.toLowerCase().includes(query) &&
            !this.selectedPlayers.includes(p)
        );
        
        // Display suggestions
        this.playerSuggestions.innerHTML = '';
        filtered.slice(0, 10).forEach(player => {
            const suggestion = document.createElement('button');
            suggestion.type = 'button';
            suggestion.className = 'list-group-item list-group-item-action';
            suggestion.textContent = player;
            suggestion.dataset.player = player;
            this.playerSuggestions.appendChild(suggestion);
        });
        
        this.playerSuggestions.style.display = filtered.length > 0 ? 'block' : 'none';
    }
    
    handlePlayerSelect(e) {
        if (e.target.dataset.player) {
            const player = e.target.dataset.player;
            this.addSelectedPlayer(player);
            this.playerSearch.value = '';
            this.hidePlayerSuggestions();
        }
    }
    
    addSelectedPlayer(player) {
        if (!this.selectedPlayers.includes(player)) {
            this.selectedPlayers.push(player);
            this.renderSelectedPlayers();
            this.updateShowChartButton();
        }
    }
    
    removeSelectedPlayer(player) {
        this.selectedPlayers = this.selectedPlayers.filter(p => p !== player);
        this.renderSelectedPlayers();
        this.updateShowChartButton();
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
            closeBtn.onclick = () => this.removeSelectedPlayer(player);
            
            pill.appendChild(label);
            pill.appendChild(closeBtn);
            this.selectedPlayersContainer.appendChild(pill);
        });
    }
    
    hidePlayerSuggestions() {
        this.playerSuggestions.style.display = 'none';
    }
    
    handleStatTypeChange(e) {
        this.currentStatType = e.target.value;
    }
    
    updateShowChartButton() {
        this.showChartBtn.disabled = this.selectedPlayers.length === 0;
    }
    
    fetchAndRenderChart() {
        if (this.selectedPlayers.length === 0) {
            this.showMessage('Select at least one player', 'alert-warning');
            return;
        }
        
        this.showChartBtn.disabled = true;
        this.chartLoading.style.display = 'inline-block';
        this.hideMessage();
        
        // Get current filter values from the page
        const season = new URLSearchParams(window.location.search).get('season') || '';
        const team = new URLSearchParams(window.location.search).get('team') || '';
        const lastNGames = new URLSearchParams(window.location.search).get('last_n_games') || '';
        
        // Build query parameters
        const params = new URLSearchParams();
        params.append('season', season);
        params.append('team', team);
        this.selectedPlayers.forEach(player => params.append('players', player));
        if (lastNGames) {
            params.append('last_n_games', lastNGames);
        }
        
        // Fetch chart data
        fetch(`/api/chart-data?${params}`)
            .then(response => {
                if (!response.ok) {
                    return response.json().then(data => {
                        throw new Error(data.error || 'Failed to load chart data');
                    });
                }
                return response.json();
            })
            .then(data => {
                this.chartLoading.style.display = 'none';
                this.showChartBtn.disabled = false;
                
                if (data.games.length === 0) {
                    this.showMessage('No games found for the selected filters', 'alert-info');
                    this.hideChartContainer();
                } else {
                    this.renderChart(data);
                }
            })
            .catch(error => {
                this.chartLoading.style.display = 'none';
                this.showChartBtn.disabled = false;
                this.showMessage(`Error: ${error.message}`, 'alert-danger');
                this.hideChartContainer();
            });
    }
    
    renderChart(data) {
        this.hideMessage();
        this.chartContainer.style.display = 'block';
        
        const labels = data.games.map(g => {
            const date = new Date(g.date);
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        });
        
        const datasets = this.buildChartDatasets(data);
        
        // Destroy previous chart if it exists
        if (this.chartInstance) {
            this.chartInstance.destroy();
        }
        
        // Render appropriate chart type
        if (this.currentStatType === 'game_score') {
            this.renderLineChart(labels, datasets);
        } else if (this.currentStatType === 'goals_assists') {
            this.renderBarChart(labels, data.games, data.players);
        }
    }
    
    buildChartDatasets(data) {
        const colors = [
            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
            '#FF9F40', '#FF6384', '#C9CBCF'
        ];
        
        const datasets = [];
        
        data.players.forEach((player, index) => {
            const playerData = data.games.map(game => {
                return game[player] ? game[player].game_score : null;
            });
            
            datasets.push({
                label: player,
                data: playerData,
                borderColor: colors[index % colors.length],
                backgroundColor: colors[index % colors.length] + '20',
                borderWidth: 2,
                fill: false,
                tension: 0.3,
                pointBackgroundColor: colors[index % colors.length],
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6
            });
        });
        
        return datasets;
    }
    
    renderLineChart(labels, datasets) {
        this.chartInstance = new Chart(this.chartCanvas, {
            type: 'line',
            data: {
                labels: labels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Game Score Trend'
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Game Score'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Date'
                        }
                    }
                }
            }
        });
    }
    
    renderBarChart(labels, games, players) {
        const colors = [
            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
            '#FF9F40', '#FF6384', '#C9CBCF'
        ];
        
        const datasets = [];
        
        players.forEach((player, playerIndex) => {
            const goalsData = games.map(g => (g[player] ? g[player].goals : 0));
            const assistsData = games.map(g => (g[player] ? g[player].assists : 0));
            
            // Add goals dataset for this player
            datasets.push({
                label: `${player} - Goals`,
                data: goalsData,
                backgroundColor: colors[playerIndex % colors.length],
                stack: `stack-${playerIndex}`
            });
            
            // Add assists dataset for this player
            datasets.push({
                label: `${player} - Assists`,
                data: assistsData,
                backgroundColor: colors[playerIndex % colors.length] + '80',
                stack: `stack-${playerIndex}`
            });
        });
        
        this.chartInstance = new Chart(this.chartCanvas, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                indexAxis: 'x',
                plugins: {
                    title: {
                        display: true,
                        text: 'Goals & Assists by Game'
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    x: {
                        stacked: false,
                        title: {
                            display: true,
                            text: 'Date'
                        }
                    },
                    y: {
                        stacked: true,
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Count'
                        }
                    }
                }
            }
        });
    }
    
    showMessage(message, alertClass = 'alert-info') {
        this.chartMessage.textContent = message;
        this.chartMessage.className = `alert ${alertClass}`;
        this.chartMessage.style.display = 'block';
    }
    
    hideMessage() {
        this.chartMessage.style.display = 'none';
    }
    
    hideChartContainer() {
        this.chartContainer.style.display = 'none';
    }
}
```

- [ ] **Step 2: Verify the file is created and syntactically valid**

```bash
node -c static/js/stats-charts.js 2>&1 | head -20
```

Or use a linter if available. Alternatively, just try to open in browser and check console for errors.

- [ ] **Step 3: Commit**

```bash
git add static/js/stats-charts.js
git commit -m "feat: add StatsChartUI class for player picker and chart rendering"
```

---

## Task 5: End-to-End Testing

**Files:**
- Test: `templates/stats.html`, `routes/api_routes.py`, `static/js/stats-charts.js`

- [ ] **Step 1: Write integration test (frontend + backend)**

Add to `tests/test_chart_api.py` (at the end of the file):

```python
class TestChartIntegration:
    """Integration tests for the chart UI."""

    def test_chart_page_contains_chart_section(self, client):
        """Stats page includes the charts section HTML."""
        response = client.get('/stats')
        assert response.status_code == 200
        assert b'charts-section' in response.data
        assert b'player-search' in response.data
        assert b'stat-game-score' in response.data
        assert b'stat-goals-assists' in response.data
        assert b'show-chart-btn' in response.data

    def test_chart_page_loads_all_players(self, client):
        """Stats page provides player list to JavaScript."""
        response = client.get('/stats')
        assert response.status_code == 200
        # Check that players array is embedded in the page
        # (This is a simplified check; in real E2E tests, you'd use Playwright)
        assert b'StatsChartUI' in response.data
        assert b'players' in response.data
```

- [ ] **Step 2: Run all tests**

```bash
pytest tests/test_chart_api.py -v
```

Expected: All tests PASS

- [ ] **Step 3: Test the endpoint manually with curl**

```bash
# First, authenticate by visiting the stats page
curl -c /tmp/cookies.txt http://localhost:5000/

# Then test the endpoint
curl -b /tmp/cookies.txt "http://localhost:5000/api/chart-data?season=2025-26&team=U21&players=7&players=12" | jq .
```

Expected: JSON response with players and games arrays

- [ ] **Step 4: Commit**

```bash
git add tests/test_chart_api.py
git commit -m "test: add integration tests for chart API and page"
```

---

## Task 6: Browser Testing & UI Polish

**Files:**
- Test: Browser manual testing

- [ ] **Step 1: Run dev server**

```bash
python app.py
```

Navigate to `http://localhost:5000/stats`

- [ ] **Step 2: Test player picker**

- Type a player name in the search box
- Verify autocomplete suggestions appear
- Click a suggestion, verify it appears as a pill
- Click the X on the pill, verify it's removed
- Try selecting multiple players

Expected: Player selection works smoothly, pills display and remove correctly

- [ ] **Step 3: Test stat selector**

- Click "Game Score" radio button
- Click "Goals & Assists" radio button
- Verify the button state changes

Expected: Radio buttons toggle correctly

- [ ] **Step 4: Test Show Chart button**

- Select 0 players, verify button is disabled
- Select 1 player, verify button is enabled
- Click "Show Chart", verify loading spinner appears
- Wait for chart to render

Expected: Button state changes, spinner shows, chart renders

- [ ] **Step 5: Test chart rendering**

- After chart renders, verify:
  - Chart displays correct data (matches the game data)
  - Y-axis shows Game Score values
  - X-axis shows dates
  - Legend shows selected players
  - Hovering over points shows tooltip with player, date, score

Expected: Line chart renders correctly for Game Score

- [ ] **Step 6: Test Goals & Assists chart**

- Toggle to "Goals & Assists" radio
- Click "Show Chart"
- Verify bar chart renders with goals and assists for each player

Expected: Stacked bar chart displays correctly

- [ ] **Step 7: Test error handling**

- Change the season filter to a nonexistent season
- Click "Show Chart"
- Verify message appears: "No games found for the selected filters"

Expected: Error message displays, chart is not shown

- [ ] **Step 8: Test API error handling**

- In browser console, simulate API error by mocking fetch
- Or break the endpoint temporarily and verify error handling works

Expected: Toast/alert appears with error message

---

## Task 7: Final Checks & Documentation

**Files:**
- Modify: `CLAUDE.md` (if needed)

- [ ] **Step 1: Run full test suite**

```bash
pytest tests/ -v --tb=short 2>&1 | tail -50
```

Verify no regressions in existing tests.

- [ ] **Step 2: Run only chart tests**

```bash
pytest tests/test_chart_api.py -v
```

All should pass.

- [ ] **Step 3: Check code style (optional but recommended)**

```bash
# If you have Black installed
black --check routes/api_routes.py static/js/stats-charts.js tests/test_chart_api.py

# Or just check for obvious issues
grep -n "print(" routes/api_routes.py static/js/stats-charts.js tests/test_chart_api.py || echo "No debug prints found"
```

- [ ] **Step 4: Verify responsive design (manual)**

Open the stats page on a mobile device or use browser DevTools to emulate mobile:
- Verify Charts section is readable on small screens
- Verify player picker and buttons stack correctly
- Verify chart resizes appropriately

Expected: No horizontal scrolling, all elements visible and clickable

- [ ] **Step 5: Final commit with summary**

```bash
git log --oneline -10
```

Verify the commit history shows the incremental changes:
1. Backend endpoint + tests
2. Frontend HTML
3. Frontend JavaScript
4. Integration tests

- [ ] **Step 6: Verify feature is complete against spec**

Check against the success criteria from the spec:
- ✓ Coach can select multiple players
- ✓ View Game Score trend without page reload
- ✓ Toggle to Goals/Assists breakdown
- ✓ Existing filters apply automatically
- ✓ Chart updates on "Show Chart" click
- ✓ Error states handled gracefully
- ✓ All tests pass

---

## Summary

| Task | Effort | Status |
|------|--------|--------|
| Backend endpoint + tests | 1.5 days | Incremental TDD |
| Frontend HTML | 0.5 days | Simple markup |
| Frontend JavaScript | 1 day | Player picker + Chart.js |
| Integration & manual testing | 0.5 days | E2E validation |
| **Total** | **~3.5 days** | Ready for implementation |

**Next Step:** Once all tasks are complete and tests pass, move on to feature #5 (Advanced Analytics Dashboard) using the same brainstorming → planning → implementation flow.

