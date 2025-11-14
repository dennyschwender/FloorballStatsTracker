# Season Management Guide

This guide explains how to use the season management features in Floorball Stats Tracker.

## Overview

Season management allows you to organize your games and rosters by season (e.g., "2024-25", "2025-26"). This makes it easy to:
- Keep historical data organized
- Filter stats by specific seasons
- Manage multiple teams across different seasons
- Archive old seasons while keeping them accessible

## Season Naming Convention

We recommend using the format `YYYY-YY` for season names:
- `2024-25` for the 2024-2025 season
- `2025-26` for the 2025-2026 season
- etc.

This format:
- Sorts chronologically
- Is internationally recognized
- Clearly indicates the season span

## Creating Rosters with Seasons

### Method 1: Through the Web Interface

1. Navigate to **Team Roster**
2. If no season is selected, the most recent season will be auto-selected
3. Click **Create New Roster**
4. Enter:
   - **Season Name**: e.g., "2025-26"
   - **Category**: e.g., "U21", "U18", "NLB"
5. Click **Create**
6. Add players to your roster

### Method 2: Bulk Import

1. Navigate to **Team Roster**
2. Select your season
3. Click **Bulk Import**
4. Enter season and category
5. Paste your roster data
6. Click **Import**

### File Structure

Rosters are saved as: `rosters/roster_SEASON_CATEGORY.json`

Example:
- `roster_2025-26_U21.json`
- `roster_2025-26_U18.json`
- `roster_2024-25_U21.json`

## Creating Games with Seasons

When creating a new game:

1. Navigate to **Create Game**
2. **Select Season First**: Choose from the dropdown (most recent at top)
3. **Select Category**: The dropdown will populate with categories that have rosters for the selected season
4. Fill in remaining details (teams, date, referees)
5. Select players and set up lines

**Important**: You must select a season before selecting a category. The category list is filtered based on the selected season.

## Filtering by Season

### Stats Page

1. Navigate to **Statistics**
2. Use the **Season** dropdown at the top
3. Select a specific season or "All Seasons"
4. Optionally filter by **Category** as well

This will show stats only for games in the selected season.

### Homepage

1. On the main page, use the **Season** dropdown
2. Optionally combine with the **Team** filter
3. Games are filtered to show only those matching your criteria

### Roster Page

1. Navigate to **Team Roster**
2. Use the **Season** dropdown
3. Only rosters for that season will be displayed

## Migrating Existing Data

If you have existing games and rosters without season information:

### Using the Migration Script

```bash
python scripts/assign_season.py 2025-26
```

This will:
1. **Backup your data** automatically
2. **Rename roster files**: `roster_U21.json` → `roster_2025-26_U21.json`
3. **Update all games**: Add `"season": "2025-26"` to each game
4. **Show a summary** of changes made

The script is safe and creates backups before making any changes.

### Manual Migration

If you prefer manual control:

1. **Backup your data**:
   ```bash
   python scripts/backup_games.py
   cp rosters/roster_*.json rosters/backup/
   ```

2. **Rename roster files**:
   ```bash
   mv rosters/roster_U21.json rosters/roster_2025-26_U21.json
   ```

3. **Edit games.json**: Add `"season": "2025-26"` to each game object

## Multi-Season Workflow

### Starting a New Season

1. **Create new rosters** for the new season
2. You can copy players from the previous season if needed:
   - Open old roster file
   - Copy player data
   - Import to new season via Bulk Import

3. **Start creating games** for the new season

### Viewing Historical Data

- Use season filters on Stats and Homepage
- Old rosters remain accessible by selecting their season
- All data is preserved and queryable

### Archive Old Seasons

To archive (but not delete) old season data:

1. Create a backup:
   ```bash
   python scripts/backup_games.py
   ```

2. Move old roster files to an archive folder:
   ```bash
   mkdir -p rosters/archive/2024-25
   mv rosters/roster_2024-25_*.json rosters/archive/2024-25/
   ```

3. The old games remain in `games.json` but won't show up in "current season" filters

## Best Practices

### 1. Consistent Naming
- Always use the same format for season names
- Use `YYYY-YY` format for clarity
- Don't include extra text (e.g., avoid "Season 2025-26" - just use "2025-26")

### 2. One Season at a Time
- When creating games, stay focused on one season
- Don't mix players from different seasons in the same game

### 3. Regular Backups
```bash
# Before starting a new season
python scripts/backup_games.py

# After major roster changes
python scripts/backup_games.py
```

### 4. Clean Transitions
- Finish entering all games for a season before starting the next
- Archive or backup old season data
- Create fresh rosters for the new season

### 5. Testing
- Test your workflow with a dummy season first (e.g., "TEST-25")
- Delete test data before going live
- Verify filters work as expected

## Troubleshooting

### "No categories available" when creating a game

**Cause**: No rosters exist for the selected season

**Solution**:
1. Select the correct season
2. Go to Team Roster
3. Create a roster for that season and category
4. Return to Create Game

### Roster file not found

**Cause**: File name doesn't match expected format

**Solution**:
- Ensure file is named: `roster_SEASON_CATEGORY.json`
- Check for typos in season or category names
- Verify file is in `rosters/` directory

### Games showing in wrong season

**Cause**: Game has wrong season field or no season field

**Solution**:
1. Backup your data
2. Edit `gamesFiles/games.json`
3. Find the game (search by teams or date)
4. Update the `"season"` field
5. Save and reload the app

### Season not appearing in dropdowns

**Cause**: No rosters or games exist for that season

**Solution**:
- Seasons are auto-detected from existing rosters
- Create at least one roster to make a season appear

## API for Developers

### Get all seasons
```
GET /api/seasons
```

Returns array of season strings.

### Get categories for a season
```
GET /api/categories?season=2025-26
```

Returns array of category strings for that season.

### Get roster for season and category
```
GET /api/roster/U21?season=2025-26
```

Returns array of player objects.

## Data Structures

### Season-aware Roster File
```json
[
  {
    "id": "uuid",
    "number": 7,
    "surname": "Doe",
    "name": "John",
    "nickname": "JD",
    "position": "C",
    "tesser": "U21"
  }
]
```

File: `rosters/roster_2025-26_U21.json`

### Season-aware Game Object
```json
{
  "id": 0,
  "season": "2025-26",
  "team": "U21",
  "home_team": "Team A",
  "away_team": "Team B",
  "date": "2025-11-14",
  ...
}
```

## Examples

### Example 1: Starting Your First Season

```bash
# 1. Create rosters via web interface
# Navigate to Team Roster → Create New Roster
# Season: 2025-26, Category: U21

# 2. Add players
# Use web interface or bulk import

# 3. Create your first game
# Navigate to Create Game
# Select Season: 2025-26
# Select Category: U21
# Fill in details
```

### Example 2: Migrating from Non-Season Data

```bash
# 1. Backup everything
python scripts/backup_games.py

# 2. Run migration
python scripts/assign_season.py 2025-26

# 3. Verify in web interface
# Check that games have season
# Check that rosters are renamed
# Test filtering by season
```

### Example 3: Managing Multiple Seasons

```bash
# Your rosters folder:
rosters/
  roster_2023-24_U21.json
  roster_2023-24_U18.json
  roster_2024-25_U21.json
  roster_2024-25_U18.json
  roster_2025-26_U21.json  # Current season
  roster_2025-26_U18.json

# Filter to current season in web interface
# Old data remains accessible via season filter
```

---

**Need Help?** Check the main [README.md](../README.md) or open an issue on GitHub.
