# Real-Time Stat Visualization & Charts Design

**Date:** 2026-04-05  
**Scope:** Add interactive charts to the stats page for visualizing Game Score and Goals/Assists trends  
**Success Criteria:** Coaches can select players and view their performance trends across custom game ranges without page reload  

---

## Overview

The stats page currently displays player performance as tables (Game Score, Goals/Assists, Plus/Minus, etc.). This design adds a **Charts section** above the tables, allowing coaches to visualize trends and compare selected players across a season or custom date range.

### Primary Use Cases

1. **Trend analysis** — "How is player #7 scoring as the season progresses?"
2. **Comparison** — "Which of these three players is performing best?"
3. **Diagnostic hunting** — "Why did we underperform in these last 5 games?"

Charts operate at two levels:
- **Game Score:** aggregated performance metric (single line per player)
- **Goals & Assists:** detailed breakdown (grouped bars per game)

---

## Architecture

### Backend: `/api/chart-data` Endpoint

**Location:** `routes/api_routes.py`

**Request:**
```
GET /api/chart-data?season=2025-26&team=U21&last_n_games=10&players=7&players=12
```

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `season` | string | Yes | Season name (e.g., "2025-26") |
| `team` | string | Yes | Team/category (e.g., "U21") |
| `last_n_games` | int | No | Limit results to last N games (0 or omitted = all) |
| `players` | list (repeated) | Yes | Player names/numbers to include (must have ≥1) |

**Response:**
```json
{
  "players": ["7", "12"],
  "games": [
    {
      "date": "2025-11-14",
      "game_id": 5,
      "home_team": "Team A",
      "away_team": "Team B",
      "7": {
        "game_score": 8.5,
        "goals": 2,
        "assists": 1
      },
      "12": {
        "game_score": 5.2,
        "goals": 1,
        "assists": 0
      }
    },
    {
      "date": "2025-11-21",
      "game_id": 6,
      "home_team": "Team B",
      "away_team": "Team A",
      "7": {
        "game_score": 6.3,
        "goals": 1,
        "assists": 2
      },
      "12": {
        "game_score": 7.1,
        "goals": 2,
        "assists": 1
      }
    }
  ]
}
```

**Implementation:**
- Load games filtered by season, team, game range (reuse existing `load_games()` and filtering logic from `routes/stats_routes.py`)
- Call `ensure_game_stats()` on each game to normalize structure
- Call `calculate_stats_optimized()` to compute per-game and aggregate stats
- Filter result to only include requested players
- Return JSON

**Validation:**
- If `season` or `team` missing/invalid, return 400 with error message
- If no `players` specified, return 400: "At least one player required"
- If no games match the filter, return 200 with empty `games` array
- If a player is not in the dataset, omit from response for that game (client chart will show gap)

---

### Frontend: Charts Section

**Location:** New section in `templates/stats.html` (before the existing stat tables)

**Components:**

1. **Player Picker**
   - Autocomplete/searchable dropdown listing all players from the roster
   - Multi-select capability (select one, then add another)
   - Selected players displayed as removable pills/badges
   - Sourced from the `players` list passed to the template (already computed by `stats_bp`)

2. **Stat Selector**
   - Two radio buttons or tab buttons: "Game Score" and "Goals & Assists"
   - Default selection: "Game Score"

3. **Chart Rendering**
   - **Game Score chart:** Line chart
     - X-axis: game date (formatted as "Nov 14", "Nov 21", etc.)
     - Y-axis: game score
     - One line per selected player, distinct color
     - Tooltip on hover showing player, date, score
   
   - **Goals & Assists chart:** Stacked bar chart
     - X-axis: game date
     - Y-axis: count (goals + assists)
     - Two segments per bar: goals (one color) and assists (different color)
     - One set of bars per selected player (grouped)
     - Tooltip on hover showing breakdown

4. **"Show Chart" Button**
   - Triggers AJAX call to `/api/chart-data` with current selections
   - Disabled if no players selected
   - Shows loading spinner while fetching
   - Button text changes post-click: "Update Chart" or "Refresh Chart"

**Auto-Applied Filters:**
- The existing season, team, and game-range filters (already on the page) automatically apply to chart requests
- No separate filter controls within the Charts section

**Interaction Flow:**
1. Coach opens stats page (default: current season, all teams, all games)
2. Coach uses the page's season/team filters to narrow scope
3. Coach clicks into the Charts section
4. Coach selects 1-3 players from the picker
5. Coach selects "Game Score" or "Goals & Assists"
6. Coach clicks "Show Chart"
7. Chart renders immediately with the selected players' data

---

## Error Handling & Edge Cases

| Scenario | Behavior |
|----------|----------|
| No players selected | Button disabled, hint text: "Select at least one player" |
| No games in filtered range | Message in chart area: "No games found for the selected filters" |
| Player not in dataset | Chart renders with other players; selected player omitted from that game |
| API error (e.g., 500) | Toast/alert: "Failed to load chart data. Please try again." Button reverts to enabled |
| Invalid query params (missing season/team) | Return 400; client shows error message |

---

## Data Flow

```
Existing filters (season, team, game range) on page
                    ↓
            Coach selects players
                    ↓
            Coach clicks "Show Chart"
                    ↓
        Frontend constructs /api/chart-data?season=...&team=...&players=...
                    ↓
            Backend loads games, filters, calculates stats
                    ↓
            Returns JSON (games + player stats per game)
                    ↓
        Frontend receives JSON, passes to Chart.js
                    ↓
            Chart renders (line or bar, depending on stat selector)
```

---

## Testing

### Backend Tests (`tests/test_chart_api.py`)
- **Valid request:** Selected players' stats are returned correctly
- **Filtering by season:** Only games matching season are included
- **Filtering by team:** Only games matching team are included
- **Filtering by game range (last_n_games):** Results are capped correctly
- **Missing season/team:** Returns 400 with error
- **Empty player list:** Returns 400 with error
- **No games in range:** Returns 200 with empty `games` array
- **Player not in dataset:** Player omitted from response for that game

### Frontend Tests
- **Player picker:** Multi-select works, pills display correctly, remove works
- **Stat selector:** Toggling between Game Score and Goals/Assists updates state
- **Show Chart button:** Disabled when no players; enabled when ≥1 player selected
- **Chart rendering:** Chart.js renders correctly for both stat types
- **API error handling:** Toast appears on 400/500, button reverts to enabled

### Integration Tests
- **End-to-end:** Select season → select team → select player → click Show Chart → verify chart displays correct data

---

## Dependencies & Libraries

- **Chart.js** (4.x) — via CDN (https://cdn.jsdelivr.net/npm/chart.js)
- No new Python dependencies required (reuses existing `calculate_stats_optimized()`)

---

## File Changes

| File | Change |
|------|--------|
| `routes/api_routes.py` | Add `/api/chart-data` endpoint |
| `templates/stats.html` | Add Charts section (player picker, stat selector, chart area) |
| `static/js/stats-charts.js` | New file: Chart.js initialization, AJAX handler, player picker logic |
| `tests/test_chart_api.py` | New file: endpoint tests |

---

## Non-Goals (Out of Scope)

- Real-time stat updates during game (stats page is post-game view)
- Mobile chart optimization (responsive design via Chart.js responsive plugin)
- Historical season comparisons (single season only, per coach feedback)
- Export chart as image/PDF (Phase 2, covered by Comprehensive Export feature)

---

## Success Criteria

✓ Coach can select multiple players and view Game Score trend without page reload  
✓ Coach can toggle to Goals/Assists breakdown  
✓ Existing filters (season, team, game range) apply automatically  
✓ Chart updates on "Show Chart" click  
✓ Error states handled gracefully (no blank pages)  
✓ All backend and frontend tests pass  

