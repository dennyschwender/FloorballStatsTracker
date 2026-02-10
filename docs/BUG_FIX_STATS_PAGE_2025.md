# Stats Page Bug Fix and Testing Enhancement

**Date:** February 10, 2026  
**Issue:** Stats page was only displaying one game column instead of all games

## Bug Description

When accessing the `/stats` page, only a single game was visible in the tables (Plus/Minus, Goals/Assists, etc.) despite having 8 games in the database. Additionally, a Jinja2 error was occurring:

```
jinja2.exceptions.UndefinedError: 'tuple object' has no attribute 'save_percentages'
```

## Root Cause

In [services/stats_service.py](../services/stats_service.py), the `calculate_stats_optimized` function was returning `games_with_calculated_stats` as a list of tuples:

```python
games_with_stats.append((game, game_calculated))
```

The stats template expected game objects with calculated fields directly accessible (e.g., `game.save_percentages`), but was receiving tuples instead, causing:
1. Template errors when trying to access attributes on tuples
2. Games not being properly passed to the template

Additionally, [routes/stats_routes.py](../routes/stats_routes.py) was not passing the `games` variable to the template, only `games_with_calculated_stats`.

## Fixes Applied

### 1. Fixed stats_service.py (Line ~149-158)

**Before:**
```python
games_with_stats.append((game, game_calculated))
```

**After:**
```python
# Merge calculated stats into game object
game['game_scores'] = game_calculated['game_scores']
game['save_percentages'] = game_calculated['save_percentages']
game['goalie_game_scores'] = game_calculated['goalie_game_scores']
game['opponent_save_percentage'] = game_calculated['opponent_save_percentage']
games_with_stats.append(game)
```

### 2. Fixed stats_routes.py (Line ~64-84)

**Before:**
```python
return render_template(
    'stats.html',
    ...
    games_with_calculated_stats=stats_data['games_with_calculated_stats'],
    ...
    hide_zero_stats=hide_zero_stats
)
```

**After:**
```python
hide_future_games = request.args.get('hide_future_games', 'false') == 'true'

return render_template(
    'stats.html',
    ...
    games=stats_data['games_with_calculated_stats'],
    games_with_calculated_stats=stats_data['games_with_calculated_stats'],
    ...
    hide_zero_stats=hide_zero_stats,
    hide_future_games=hide_future_games
)
```

## Testing Enhancement

Created comprehensive test suite [tests/test_stats_page_display.py](../tests/test_stats_page_display.py) with 10 tests that specifically verify:

### Key Tests

1. **test_all_games_displayed_in_tables** - Verifies all games appear with correct team names and dates
2. **test_game_columns_in_plusminus_table** - Counts game columns in Plus/Minus table
3. **test_game_columns_in_goals_assists_table** - Counts game columns in Goals/Assists table
4. **test_stats_data_structure_integrity** - Ensures no Jinja2 template errors
5. **test_game_with_calculated_stats_fields** - Validates game objects have required calculated fields (game_scores, save_percentages, goalie_game_scores, opponent_save_percentage)
6. **test_stats_page_renders_without_jinja_errors** - Integration test for complete page rendering
7. **test_multiple_games_multiple_players** - Tests multiple games with different player combinations
8. **test_season_filter_shows_correct_games** - Validates season filtering
9. **test_team_filter_shows_correct_games** - Validates team/category filtering
10. **test_no_games_displays_gracefully** - Ensures page handles empty games list

### Test Results

All 10 new tests pass successfully:

```
tests/test_stats_page_display.py::TestStatsPageGameDisplay::test_all_games_displayed_in_tables PASSED
tests/test_stats_page_display.py::TestStatsPageGameDisplay::test_game_columns_in_plusminus_table PASSED
tests/test_stats_page_display.py::TestStatsPageGameDisplay::test_game_columns_in_goals_assists_table PASSED
tests/test_stats_page_display.py::TestStatsPageGameDisplay::test_stats_data_structure_integrity PASSED
tests/test_stats_page_display.py::TestStatsPageGameDisplay::test_multiple_games_multiple_players PASSED
tests/test_stats_page_display.py::TestStatsPageGameDisplay::test_no_games_displays_gracefully PASSED
tests/test_stats_page_display.py::TestStatsPageGameDisplay::test_game_with_calculated_stats_fields PASSED
tests/test_stats_page_display.py::TestStatsPageGameDisplay::test_stats_page_renders_without_jinja_errors PASSED
tests/test_stats_page_display.py::TestStatsPageGameDisplay::test_season_filter_shows_correct_games PASSED
tests/test_stats_page_display.py::TestStatsPageGameDisplay::test_team_filter_shows_correct_games PASSED
```

## Why Previous Tests Didn't Catch This

The existing tests (e.g., in `test_game_score.py`) only verified:
- HTTP 200 response status
- Presence of specific text strings like "Game Score"
- Specific calculated values

They did **not** verify:
- The actual number of game columns in tables
- The data structure of games passed to templates
- That Jinja2 could access game attributes without errors

The new test suite specifically addresses these gaps and would immediately catch this type of bug in the future.

## Files Modified

1. `services/stats_service.py` - Fixed game data structure
2. `routes/stats_routes.py` - Added missing template variable and filter parameter
3. `tests/test_stats_page_display.py` - **NEW** comprehensive test suite

## Verification

After fixes:
- All 8 games now display correctly in stats page tables
- No Jinja2 template errors
- Season and team filtering work correctly
- All new tests pass
