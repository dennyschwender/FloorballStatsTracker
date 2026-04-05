# Advanced Analytics Dashboard Design

**Date:** 2026-04-05  
**Scope:** Add Player Trends and Lineup Analysis sections to stats page  
**Success Criteria:** Coaches can analyze player performance trajectories, consistency, and identify high-performing core player combinations  

---

## Overview

The Advanced Analytics Dashboard extends the existing stats page with two new analytical views:

1. **Player Trends Dashboard** — Analyze individual player development across the season with trajectory, consistency, and outlier detection
2. **Lineup Analysis** — Identify which core player combinations (4-7 players) achieve the highest aggregate Game Scores when playing together

This builds on the Chart Visualization feature (just shipped) and reuses Chart.js, player picker patterns, and stats calculation infrastructure.

---

## Architecture

### Backend: Stats Calculation Functions

**Location:** `services/stats_service.py`

Add two new public functions:

#### `calculate_player_trends(games, players=None)`

Takes filtered games list and optional player names. Returns per-player trend data.

**Input:**
- `games`: List of game dicts (already filtered by season/team/date range)
- `players`: Optional list of player names to include (default: all players in games)

**Output:** Dictionary
```python
{
    "7 - Player Seven": {
        "game_scores": [8.5, 6.2, 9.1, 7.8, ...],  # Game scores in chronological order
        "game_ids": [1, 2, 3, 4, ...],               # Corresponding game IDs
        "mean_score": 7.8,
        "std_dev": 1.2,
        "min_score": 6.2,
        "max_score": 9.1,
        "outliers": [
            {"game_id": 3, "score": 9.1, "type": "high", "z_score": 1.08},
            {"game_id": 2, "score": 6.2, "type": "low", "z_score": -1.30}
        ]  # Games with |z_score| > 1.0
    },
    "12 - Player Twelve": { ... }
}
```

**Algorithm:**
1. For each requested player, extract their Game Score from each game
2. Calculate mean and std dev across all games
3. Identify outliers (|z_score| > 1.0)
4. Return all stats in chronological order

**Edge Cases:**
- Player not in any games → omit from result
- Player in <3 games → include but note in outliers (insufficient data)
- No games in filter → return empty dict

---

#### `calculate_lineup_combinations(games, combo_size_range=(5, 7))`

Identifies core player combinations and their performance metrics.

**Input:**
- `games`: List of game dicts (filtered by season/team)
- `combo_size_range`: Tuple (min_size, max_size) for combo sizes to analyze (default: 5-7 players)

**Output:** List of combination dicts
```python
[
    {
        "combo_id": "combo_1",
        "players": ["7 - Player Seven", "12 - Player Twelve", "15 - Player Fifteen", ...],
        "combo_size": 5,
        "games_played_together": 12,
        "wins": 9,
        "losses": 3,
        "win_percentage": 75.0,
        "avg_goal_differential": 2.1,
        "avg_aggregate_game_score": 42.3,
        "game_ids": [1, 2, 4, 5, ...]  # Games where ALL players in combo played
    },
    { ... }
]
```

**Algorithm:**
1. Get all unique players from games
2. For each combo size (5, 6, 7):
   a. Generate combinations of top N players (by total Game Score across season)
   b. For each combo, find games where ALL players in the combo were present
   c. Calculate metrics for those games only:
      - Win count: Games where team's final goals > opponent's final goals
      - Loss count: Games where team's final goals < opponent's final goals
      - Goal differential: (Team's goals - Opponent's goals) per game, then average
      - Aggregate Game Score: Sum of all combo players' individual Game Scores per game, then average
3. Sort by Aggregate Game Score descending
4. Return top N combinations per size (limit parameter, default 10)

**Edge Cases:**
- Combo not played together in any game → include but show "0 games"
- Insufficient data (<3 games together) → include but note

---

### Frontend: Stats Page Extension

**Location:** `templates/stats.html`

Insert two new sections after existing stat tables and before closing tags.

#### Section 1: Player Trends Dashboard

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
            <div id="trends-player-suggestions" class="list-group mt-2" style="display: none;"></div>
            <div id="trends-selected-players" class="mt-3 d-flex flex-wrap gap-2"></div>
            <button id="trends-show-btn" class="btn btn-primary mt-3" disabled>Show Trends</button>
        </div>
    </div>
    
    <!-- Three-Panel Dashboard -->
    <div id="trends-container" style="display: none;">
        <div class="row mb-4">
            <!-- Trajectory Panel -->
            <div class="col-lg-6">
                <div class="card">
                    <div class="card-header">
                        <h5>Performance Trajectory</h5>
                    </div>
                    <div class="card-body">
                        <canvas id="trends-trajectory-chart"></canvas>
                        <div id="trends-trajectory-message" class="alert alert-info mt-2" style="display: none;"></div>
                    </div>
                </div>
            </div>
            
            <!-- Consistency Panel -->
            <div class="col-lg-6">
                <div class="card">
                    <div class="card-header">
                        <h5>Performance Consistency</h5>
                    </div>
                    <div class="card-body">
                        <canvas id="trends-consistency-chart"></canvas>
                        <div id="trends-consistency-message" class="alert alert-info mt-2" style="display: none;"></div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Outliers Panel -->
        <div class="card">
            <div class="card-header">
                <h5>Best & Worst Performances</h5>
            </div>
            <div class="card-body">
                <div id="trends-outliers-table">
                    <!-- Table will be rendered here -->
                </div>
                <div id="trends-outliers-message" class="alert alert-info" style="display: none;"></div>
            </div>
        </div>
    </div>
    
    <hr class="my-5">
</div>
```

#### Section 2: Lineup Analysis

```html
<!-- Lineup Analysis -->
<div id="lineup-section" class="mt-5">
    <h2 class="mb-4">Core Lineup Performance</h2>
    
    <!-- Combo Selector -->
    <div class="card mb-4">
        <div class="card-body">
            <label class="form-label">Analyze Top Player Combinations</label>
            <div>
                <button class="btn btn-sm btn-outline-primary active" data-combo-size="5">Top 5</button>
                <button class="btn btn-sm btn-outline-primary" data-combo-size="6">Top 6</button>
                <button class="btn btn-sm btn-outline-primary" data-combo-size="7">Top 7</button>
            </div>
            <button id="lineup-show-btn" class="btn btn-primary mt-3">Show Analysis</button>
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
                    <!-- Rows will be rendered here -->
                </tbody>
            </table>
        </div>
        <div id="lineup-message" class="alert alert-info" style="display: none;"></div>
    </div>
</div>
```

---

### Frontend: JavaScript Implementation

**Location:** `static/js/analytics-dashboard.js`

#### `PlayerTrendsUI` class

Handles player selection, trend calculation display, and chart rendering.

**Responsibilities:**
- Player picker with autocomplete (search, add, remove)
- Fetch player trends data from `/api/player-trends` endpoint
- Render trajectory line chart (Game Score over season)
- Render consistency box plot (score distribution)
- Render outliers table (best/worst games)

**Key methods:**
- `init()` — Attach event listeners
- `handlePlayerSearch()` — Filter players, show suggestions
- `addPlayer()`, `removePlayer()` — Update selected players
- `fetchTrends()` — AJAX call to backend
- `renderTrajectoryChart()` — Line chart using Chart.js
- `renderConsistencyChart()` — Box plot using Chart.js
- `renderOutliersTable()` — HTML table from outlier data

**Chart Details:**
- **Trajectory:** Line chart, x=game date, y=game score, one line per player
- **Consistency:** Box plot showing [min, Q1, median, Q3, max] for each player, overlaid
- **Outliers:** Table with columns: Player, Game ID, Date, Score, Type (High/Low), Z-Score

---

#### `LineupAnalysisUI` class

Handles combo selector and lineup matrix display.

**Responsibilities:**
- Combo size selector (5, 6, 7 player buttons)
- Fetch lineup data from `/api/lineup-combos` endpoint
- Render combo matrix table with sortable columns
- Interactive highlighting (click row to highlight players)

**Key methods:**
- `init()` — Attach event listeners
- `selectComboSize()` — Update selected size, trigger fetch
- `fetchCombos()` — AJAX call to backend
- `renderMatrix()` — Render table rows, attach sort listeners
- `sortMatrix()` — Re-sort by column (Win %, Goal Diff, Score)

---

### Backend API Endpoints

#### `GET /api/player-trends`

**Query Parameters:**
- `season` (required) — Season name
- `team` (required) — Team category
- `players` (optional, multi-valued) — Player names to include (default: all)
- `last_n_games` (optional) — Limit to last N games

**Response:** 
```json
{
  "players": {
    "7 - Player Seven": {
      "game_scores": [8.5, 6.2, ...],
      "game_ids": [1, 2, ...],
      "mean_score": 7.8,
      "std_dev": 1.2,
      "min_score": 6.2,
      "max_score": 9.1,
      "outliers": [...]
    },
    ...
  },
  "metadata": {
    "games_analyzed": 12,
    "season": "2025-26",
    "team": "U21"
  }
}
```

---

#### `GET /api/lineup-combos`

**Query Parameters:**
- `season` (required) — Season name
- `team` (required) — Team category
- `combo_size` (optional) — Size of combos to return (5, 6, or 7; default: 5)
- `limit` (optional) — Max combos to return (default: 10)

**Response:**
```json
{
  "combos": [
    {
      "combo_id": "combo_1",
      "players": ["7 - Player Seven", "12 - Player Twelve", ...],
      "combo_size": 5,
      "games_played_together": 12,
      "wins": 9,
      "losses": 3,
      "win_percentage": 75.0,
      "avg_goal_differential": 2.1,
      "avg_aggregate_game_score": 42.3,
      "game_ids": [1, 2, 4, ...]
    },
    ...
  ],
  "metadata": {
    "season": "2025-26",
    "team": "U21",
    "combo_size": 5,
    "total_combos": 10
  }
}
```

---

## Data Flow

```
Stats page loads
    ↓
Backend (stats_routes.py):
  1. load_games() and filter by season/team/date
  2. calculate_player_trends(filtered_games)
  3. calculate_lineup_combinations(filtered_games)
  4. Pass data to template: trends_data, lineup_data
    ↓
Frontend (analytics-dashboard.js):
  1. PlayerTrendsUI.init() — Attach listeners
  2. LineupAnalysisUI.init() — Attach listeners
  3. User selects players → fetchTrends() → /api/player-trends
  4. User clicks "Show Analysis" → fetchCombos() → /api/lineup-combos
  5. JavaScript renders charts + tables
    ↓
Charts rendered with Chart.js
Tables rendered with Bootstrap
```

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| No players in filter | Show "No data available" message |
| Player in <3 games | Include in trends, note "insufficient data" for outliers |
| Combo played 0 games together | Show row with "0" games, display "—" for Win %, Goal Diff, Score (not applicable) |
| API error | Show alert with error message, include error details |
| Empty game set (no games in filter) | Show "No games found for the selected filters" message |

---

## Testing

### Backend Tests
- `test_calculate_player_trends()` — Verify mean, std dev, outlier calculation
- `test_player_trends_edge_cases()` — <3 games, missing players, empty data
- `test_calculate_lineup_combinations()` — Verify combo identification and metrics
- `test_lineup_combos_edge_cases()` — 0 games together, insufficient data

### Frontend Tests (Manual)
- Player picker autocomplete and multi-select
- Trajectory chart renders with correct lines
- Consistency box plot displays for selected players
- Outliers table shows best/worst games
- Combo size buttons toggle correctly
- Matrix table sorts by column
- Responsive on mobile

---

## Dependencies

- **Chart.js 4.x** — Already loaded (from charts feature)
- **Bootstrap 5** — Already loaded
- **No new Python dependencies**

---

## Non-Goals (Out of Scope)

- Predictive modeling / season projections
- Injury tracking
- Export to PDF
- Real-time updates during games
- Win/loss prediction

---

## Success Criteria

✓ Coaches can select players and view their performance trajectory over season  
✓ Consistency view shows score variability and distribution  
✓ Outliers table highlights best and worst performances  
✓ Core lineup combos identified by highest aggregate Game Score  
✓ Win/loss and goal differential metrics shown for each combo  
✓ All existing stats page functionality unaffected  
✓ All tests pass  
✓ No regressions in existing features  

