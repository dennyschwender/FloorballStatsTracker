# Game Migration Script Guide

## Overview

The `migrate_games.py` script helps migrate old game data to match player names with the current roster format. It's particularly useful when historical games used nicknames or partial names instead of the standardized format.

## Features

- **Automatic Backup**: Creates a timestamped backup before any changes
- **Fuzzy Matching**: Uses similarity scoring to match player names (80% threshold)
- **Interactive Mode**: Manually select from candidate matches when uncertain
- **Comprehensive Coverage**: Migrates lines, goalies, and all formations (PP1, PP2, BP1, BP2, 6vs5, stress_line)
- **Detailed Reporting**: Shows all changes and warnings with similarity scores

## Usage

### Basic (Non-Interactive) Mode

```bash
python migrate_games.py
```

When prompted "Enable interactive mode? (yes/no) [no]:", press Enter or type "no".

This mode will:

- Automatically match players with similarity > 80%
- Show warnings for unmatched players
- Display a summary of all changes

### Interactive Mode

```bash
python migrate_games.py
```

When prompted "Enable interactive mode? (yes/no) [no]:", type "yes".

Interactive mode allows you to:

- See each game as it's processed
- Choose from top 10 candidate matches when automatic matching fails
- Skip players you want to leave unchanged

#### Interactive Selection Example

```text
--- Processing Game #0: 2025-11-14 - TIUH vs Interactive Test ---

  No automatic match for 'Diego' (best score: 0.53)
  Top 5 candidates:
    1. 11 - Bianchi Diego (score: 0.53)
    2. 25 - Delbiaggio Alex (score: 0.42)
    3. 33 - Giordani Davide (score: 0.38)
    4. 77 - Giudici Martino (score: 0.35)
    5. 82 - Moro Roy (score: 0.31)
    s. Skip (leave as 'Diego')
  Select option (1-5, s): 1
```

## Name Matching Priority

The script tries to match names in this order:

1. **Standard format**: `number - surname name` (e.g., "69 - Bazzuri Andrea")
2. **With nickname**: `number - nickname` (e.g., "69 - Andy")
3. **Nickname with surname**: `number - nickname surname`
4. **Name without number**: `surname name`
5. **Nickname only**: e.g., "Andy"
6. **Surname only**: e.g., "Bazzuri"

## Output Files

After running the script, you'll find:

- `gamesFiles/games_backup_YYYYMMDD_HHMMSS.json` - Backup of original games
- `gamesFiles/games.json` - Migrated games (if you chose to save)
- `gamesFiles/migration_report_YYYYMMDD_HHMMSS.json` - Detailed report of all changes

## Migration Report Structure

The detailed JSON report contains for each game:

```json
{
  "game_id": 99,
  "date": "2025-11-14",
  "home_team": "TIUH",
  "away_team": "Test Opponent",
  "changes": [
    "Line 1: 'Andy' → '69 - Bazzuri Andrea' (score: 1.00)"
  ],
  "warnings": [
    "Goalie: No match found for 'Diego' (best score: 0.53)"
  ]
}
```

## Tips

1. **Review Warnings**: Check the warnings to see which players couldn't be matched automatically
2. **Check Similarity Scores**: Scores close to 0.8 might need manual verification
3. **Use Interactive Mode**: For important historical data, use interactive mode to ensure accuracy
4. **Keep Backups**: The script creates backups, but keep your own as well
5. **Test First**: Try on a copy of your data first to see the results

## Troubleshooting

### "No roster found for category: X"

- The game has a team/category that doesn't have a corresponding roster file
- Create a roster file at `rosters/roster_X.json` or change the game's category

### Low Similarity Scores

- The player name is very different from roster entries
- Use interactive mode to manually select the correct player
- Consider updating the roster to include the nickname used in the game

### No Matches Found

- Check if the roster file exists and has players
- Verify the player is actually in the roster
- The name format might be completely different - use interactive mode

## Example Workflow

1. **Prepare**: Ensure all roster files are up to date in `rosters/` directory
2. **Run**: Execute `python migrate_games.py`
3. **Choose Mode**: Select interactive mode for careful migration
4. **Review**: Check the summary and warnings
5. **Save**: Confirm to save changes when satisfied
6. **Verify**: Check a few migrated games to ensure correctness

## Need Help?

If you encounter issues or need to customize the matching logic, the main functions to modify are:

- `find_best_match()` - Adjust similarity threshold or matching logic
- `create_player_variants()` - Add more name format variants
- `migrate_game()` - Change what gets migrated
