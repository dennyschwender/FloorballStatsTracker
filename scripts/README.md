# Scripts Documentation

This directory contains utility scripts for managing your Floorball Stats Tracker data.

## Available Scripts

### 1. assign_season.py

**Purpose**: Migrate existing games and rosters to use season identifiers.

**Usage**:
```bash
python scripts/assign_season.py <season_name>
```

**Example**:
```bash
python scripts/assign_season.py 2025-26
```

**What it does**:
- ✅ Creates automatic backup of games.json
- ✅ Renames roster files: `roster_U21.json` → `roster_2025-26_U21.json`
- ✅ Adds `"season": "2025-26"` field to all games without a season
- ✅ Shows summary of changes made
- ✅ Skips files that already have seasons

**Output Example**:
```
🏒 Assigning season '2025-26' to existing data...

📋 Processing rosters...
✅ Renamed: roster_U21.json → roster_2025-26_U21.json
✅ Renamed: roster_U18.json → roster_2025-26_U18.json
📊 Renamed 2 roster file(s)

==================================================

🎮 Processing games...
💾 Created backup: gamesFiles/games.json.backup_20251114_153045
✅ Updated 15 game(s) with season '2025-26'
📊 Total games in file: 15

==================================================
✨ Migration complete!
```

**When to use**:
- First time setting up seasons
- Migrating from old version without season support
- Assigning a season to imported data

**Safety**:
- Creates backup before making any changes
- Skips files that already match the target format
- Non-destructive (original backup preserved)

---

### 2. backup_games.py

**Purpose**: Create a timestamped backup of your games file.

**Usage**:
```bash
python scripts/backup_games.py
```

**What it does**:
- ✅ Creates backup in `gamesFiles/` directory
- ✅ Uses timestamp in filename: `games_backup_YYYYMMDD_HHMMSS.json`
- ✅ Preserves all game data exactly as-is
- ✅ Confirms backup location

**Output Example**:
```
💾 Creating backup of games.json...
✅ Backup created: gamesFiles/games_backup_20251114_153045.json
```

**When to use**:
- Before making manual edits to games.json
- Before running migration scripts
- Before starting a new season
- As regular safety backups
- Before bulk operations

**Recommended Schedule**:
- Weekly during active season
- Before any data migration
- After major tournaments/events
- Before updating the application

---

### 3. migrate_games.py

**Purpose**: Perform data structure migrations and schema updates.

**Usage**:
```bash
python scripts/migrate_games.py
```

**What it does**:
- ✅ Creates backup before migration
- ✅ Updates game data structures
- ✅ Ensures all required fields exist
- ✅ Adds default values for missing fields
- ✅ Reports migration summary

**Common Migrations**:
- Adding new stat fields (e.g., `unforced_errors`)
- Adding opponent goalie tracking
- Updating period result structure
- Converting player ID formats

**Output Example**:
```
🔄 Starting migration...
💾 Backup created: gamesFiles/games_backup_20251114_153045.json
✅ Migrated 15 games
📊 Added 'unforced_errors' field to 15 games
📊 Added 'opponent_goalie_enabled' to 10 games
✨ Migration complete!
```

**When to use**:
- After upgrading the application
- When instructed in release notes
- To fix data structure issues
- To add new features to existing games

**Important**:
- Always review the migration script before running
- Keep the backup file until verified
- Test on a copy first if unsure

---

### 4. fix_remote_migration.sh

**Purpose**: Fix file paths after server deployment or directory moves.

**Usage**:
```bash
bash scripts/fix_remote_migration.sh
```

**What it does**:
- ✅ Moves files from `.gamesFiles/` to `gamesFiles/`
- ✅ Updates file permissions
- ✅ Ensures correct directory structure
- ✅ Reports moved files

**When to use**:
- After deploying to a new server
- After restoring from backup
- When file paths are incorrect
- After migrating hosting environments

**Output Example**:
```
📁 Checking directory structure...
✅ Found .gamesFiles/ directory
🔄 Moving files to gamesFiles/...
✅ Moved games.json
✅ Moved 5 backup files
✅ Updated permissions
🗑️  Removed old .gamesFiles/ directory
✨ Migration complete!
```

---

## Common Workflows

### Starting Fresh with Seasons

```bash
# 1. Backup current data
python scripts/backup_games.py

# 2. Assign season to existing data
python scripts/assign_season.py 2025-26

# 3. Verify in web interface
# Navigate to Team Roster and Games to confirm
```

### Before Major Updates

```bash
# 1. Create backup
python scripts/backup_games.py

# 2. Note the backup filename for rollback if needed

# 3. Proceed with update
git pull  # or your update method

# 4. Run migrations if needed
python scripts/migrate_games.py
```

### After Server Deployment

```bash
# 1. Deploy application
# ... deployment commands ...

# 2. Fix paths if needed
bash scripts/fix_remote_migration.sh

# 3. Verify files are in correct location
ls -la gamesFiles/
ls -la rosters/
```

### Regular Maintenance

```bash
# Weekly backup during active season
python scripts/backup_games.py

# Clean up old backups (keep last 5)
cd gamesFiles/
ls -t games_backup_*.json | tail -n +6 | xargs rm -f
```

## Troubleshooting

### Script Not Found

**Error**: `python: can't open file 'assign_season.py'`

**Solution**: Make sure you're in the project root directory:
```bash
cd /path/to/floorball_stats_tracker
python scripts/assign_season.py 2025-26
```

### Permission Denied

**Error**: `Permission denied: 'gamesFiles/games.json'`

**Solution**: Check file permissions:
```bash
chmod 644 gamesFiles/games.json
chmod 755 gamesFiles/
```

### JSON Decode Error

**Error**: `JSONDecodeError: Expecting value`

**Solution**: Your games.json may be corrupted
```bash
# Restore from latest backup
cp gamesFiles/games_backup_YYYYMMDD_HHMMSS.json gamesFiles/games.json
```

### File Already Exists

**Warning**: `⚠️ Skipping roster_U21.json - roster_2025-26_U21.json already exists`

**Meaning**: File already migrated - this is safe to ignore

**Action**: 
- If the old file still exists, you can safely delete it
- Or keep it as a backup

## Advanced Usage

### Migrating to a Specific Season Pattern

```bash
# Migrate all to 2024-25
python scripts/assign_season.py 2024-25

# Then create new rosters for 2025-26
# Use web interface to create rosters for new season
```

### Batch Backups

```bash
# Create backup with custom note in filename
python scripts/backup_games.py

# Rename with note
mv gamesFiles/games_backup_*.json \
   gamesFiles/games_backup_before_tournament_20251114.json
```

### Combining Scripts

```bash
# Complete season transition
python scripts/backup_games.py && \
python scripts/assign_season.py 2025-26 && \
echo "✅ Season transition complete!"
```

## Safety Tips

1. **Always backup first**: Run `backup_games.py` before any migration
2. **Test in development**: Try scripts on a copy of your data first
3. **Verify after migration**: Check web interface to ensure data looks correct
4. **Keep backups**: Don't delete backup files until verified
5. **Document changes**: Note what you did and when in a log file

## Getting Help

If you encounter issues:

1. Check the output messages - they often explain the problem
2. Verify your file structure matches expectations
3. Review the [MIGRATION_GUIDE.md](../MIGRATION_GUIDE.md)
4. Check that you have the required Python packages installed
5. Open an issue on GitHub with:
   - Script name and command used
   - Error message (full output)
   - Your environment (OS, Python version)

---

**Scripts Location**: `scripts/`
**Last Updated**: November 2025
