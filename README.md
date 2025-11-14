# Floorball Stats Tracker

A comprehensive web application for tracking floorball game statistics, player performance, team management, and season organization. Built with Flask and Bootstrap 5, featuring bilingual support (English/Italian).

## 🏒 Key Features

### Season Management

- **Multi-Season Support**: Organize games and rosters by season (e.g., 2024-25, 2025-26)
- **Season Filtering**: Filter games, stats, and rosters by specific seasons
- **Automatic Season Detection**: System automatically identifies available seasons from your data
- **Season Migration Tool**: Easy migration of existing data to season-based structure

### Game Management

- **Create Game**: Add games with season, category, teams, date, referees, lines, and goalies
- **Modify Game**: Edit all game details including lineup and formations
- **Delete Game**: Remove games from the database (with confirmation)
- **Reset Stats**: Reset all player, goalie, and period stats for a game to zero
- **Game Filtering**: Filter by season and team/category
- **Season-Based Categories**: Category dropdown loads dynamically based on selected season

### Player Actions (per game)

- **Plus/Minus Tracking**: Increment or decrement player plus/minus stats
- **Goals & Assists**: Track goals and assists (automatically updates period results)
- **Unforced Errors**: Track player mistakes and turnovers
- **Line Actions**: Apply stats to entire lines with a single click
- **Real-time Updates**: All stats update immediately in the interface

### Goalie Statistics

- **Saves Tracking**: Record saves for each goalie
- **Goals Conceded**: Track goals against (affects period results)
- **Save Percentage**: Automatic calculation of save percentage per game and overall
- **Multiple Goalies**: Support for multiple goalies per game
- **Opponent Goalie Tracking**: Optional tracking of opponent goalie stats

### Period & Result Tracking

- **4 Periods**: Support for periods 1, 2, 3, and Overtime
- **Period Switching**: Easy navigation between periods during game
- **Automatic Score Calculation**: Real-time score updates based on goal tracking
- **Period Summaries**: View goals per period with running totals

### Statistics Overview

- **Comprehensive Stats Tables**:
  - Plus/Minus standings
  - Goals & Assists with totals
  - Unforced Errors tracking
  - Goalie Save Percentages
- **Sortable Tables**: Click column headers to sort by any metric
- **Multi-Level Filtering**:
  - Filter by season
  - Filter by team/category
  - Hide players with zero stats
- **Per-Game Breakdown**: See individual game performance for each player

### Team Roster Management

- **Season-Based Rosters**: Manage separate rosters for each season and category
- **Player Details**: Track number, name, surname, nickname, position, and category (tesser)
- **Bulk Import**: Import entire rosters from CSV or formatted text
- **Player CRUD**: Add, edit, and delete players individually
- **Position Organization**: Players organized by position (A/C/D/P)
- **Automatic File Naming**: Rosters saved as `roster_SEASON_CATEGORY.json`

### Game Lineup Management

- **Convocation System**: Select which players are called up for each game
- **4 Playing Lines**: Define L1, L2, L3, L4 with position-based selection
- **Special Formations**:
  - PP1, PP2 (Power Play)
  - BP1, BP2 (Box Play/Penalty Kill)
  - 6vs5 (Extra Attacker)
  - Stress Line (High-pressure situations)
- **Starting Goalies**: Select up to 2 starting goalies
- **Category Counters**: Real-time count of players by category (U18/U21/U21 DP/U16)
- **Position Counters**: Track players by position (A/C/D/P)
- **Hide Inactive Players**: Filter view to show only selected players
- **Print-Friendly View**: Clean layout for printing game sheets

### Security & Localization

- **PIN Protection**: Secure access via configurable PIN (set via `FLOORBALL_PIN` env variable)
- **Bilingual Interface**: Full English and Italian language support
- **Language Toggle**: Switch languages on the fly from any page

### UI/UX

- **Responsive Design**: Optimized for desktop, tablet, and mobile
- **Bootstrap 5**: Modern, clean interface with intuitive navigation
- **Edit Mode Toggle**: Separate viewing and editing modes
- **Keyboard Shortcuts**: Quick actions via keyboard (where applicable)
- **Success/Error Messages**: Clear feedback for all actions
- **Confirmation Dialogs**: Safety checks for destructive operations

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/dennyschwender/floorball_stats_tracker.git
   cd floorball_stats_tracker
   ```

1. Create and activate a virtual environment (recommended):

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

1. Set up your PIN (optional, default is "1234"):

   ```bash
   export FLOORBALL_PIN="your_secure_pin"
   ```

1. Run the application:

   ```bash
   python app.py
   ```

1. Open your browser and navigate to:

   ```text
   http://127.0.0.1:5000
   ```

## 🐳 Docker Deployment

### Using Docker Compose (Recommended)

1. Build and start the container:

   ```bash
   docker-compose up -d
   ```

1. Access the application at `http://localhost:5000`

1. Stop the container:

   ```bash
   docker-compose down
   ```

### Using Docker Directly

1. Build the image:

   ```bash
   docker build -t floorball-stats-tracker .
   ```

1. Run the container:

   ```bash
   docker run -d -p 5000:5000 \
     -e FLOORBALL_PIN="your_secure_pin" \
     -v $(pwd)/gamesFiles:/app/gamesFiles \
     -v $(pwd)/rosters:/app/rosters \
     floorball-stats-tracker
   ```

## 📁 Data Storage

All data is stored in JSON format for easy backup and portability:

- **Games**: `gamesFiles/games.json` - All game data including stats and lineups
- **Rosters**: `rosters/roster_SEASON_CATEGORY.json` - Team rosters by season and category
- **Backups**: `gamesFiles/games_backup_*.json` - Automatic backups created during migrations

### Data Structure

#### Game Data

```json
{
  "id": 0,
  "season": "2025-26",
  "team": "U21",
  "home_team": "Team A",
  "away_team": "Team B",
  "date": "2025-11-14",
  "referee1": "Referee Name",
  "referee2": "Referee Name",
  "lines": [["1 - Player Name", ...], ...],
  "goalies": ["30 - Goalie Name"],
  "plusminus": {"1 - Player Name": 2},
  "goals": {"1 - Player Name": 1},
  "assists": {"1 - Player Name": 1},
  "unforced_errors": {"1 - Player Name": 0},
  "saves": {"30 - Goalie Name": 25},
  "goals_conceded": {"30 - Goalie Name": 3},
  "result": {
    "1": {"home": 2, "away": 1},
    "2": {"home": 1, "away": 2},
    "3": {"home": 0, "away": 0},
    "OT": {"home": 0, "away": 0}
  },
  "current_period": "1"
}
```

#### Roster Data

```json
[
  {
    "id": "uuid-string",
    "number": 7,
    "surname": "Doe",
    "name": "John",
    "nickname": "JD",
    "position": "C",
    "tesser": "U21"
  }
]
```

## 🛠️ Utility Scripts

Located in the `scripts/` directory:

### assign_season.py

Migrate existing games and rosters to use season identifiers.

```bash
python scripts/assign_season.py 2025-26
```

This will:

- Rename `roster_U21.json` → `roster_2025-26_U21.json`
- Add `"season": "2025-26"` to all games
- Create automatic backups

### backup_games.py

Create a timestamped backup of your games file.

```bash
python scripts/backup_games.py
```

Creates: `gamesFiles/games_backup_YYYYMMDD_HHMMSS.json`

### migrate_games.py

Perform data structure migrations and updates.

```bash
python scripts/migrate_games.py
```

### fix_remote_migration.sh

Fix file paths after deployment (for server environments).

```bash
bash scripts/fix_remote_migration.sh
```

## 📖 User Guide

### Getting Started

1. **Set Your Season**: When creating your first roster or game, establish a season naming convention (e.g., "2025-26")
1. **Create Rosters**: Go to Team Roster → Create New Roster → Enter season and category
1. **Import Players**: Use Bulk Import or add players individually
1. **Create Games**: Navigate to Create Game → Select season → Select category → Fill in game details
1. **Track Stats**: During the game, use the game view to track stats in real-time

### Season Management Best Practices

- Use consistent season naming: "YYYY-YY" format (e.g., "2024-25", "2025-26")
- Create rosters for each season separately
- Filter views by season to focus on current data
- Use the migration script when transitioning seasons

### Roster Management Tips

- Keep player numbers unique within a category
- Use full names for better tracking
- Set correct positions for proper game lineup organization
- Update rosters at the start of each season

### Game Day Workflow

1. Create game with season and category
1. Select players for convocation
1. Set up your 4 lines and special formations
1. Choose starting goalies
1. Print game sheet if needed
1. During game: track stats by period
1. Review stats overview after game

## 🔧 Configuration

### Environment Variables

- `FLOORBALL_PIN`: Access PIN for the application (default: "1234")
- `FLASK_ENV`: Set to "development" for debug mode (default: "production")

### Customization

The application supports customization through:

- **Categories**: Modify `CATEGORIES` in `app.py` to add/remove team categories
- **Periods**: Modify `PERIODS` in `app.py` to change period names
- **Translations**: Edit translation dictionaries in `app.py` for English and Italian
- **Styling**: Customize CSS in `templates/` files or add to `static/` folder

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:

- Code style and structure
- Testing requirements
- Pull request process
- Bug reporting

## 📋 Migration Guide

See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for detailed instructions on:

- Migrating from old versions
- Data structure changes
- Season system migration
- Troubleshooting common issues

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🐛 Troubleshooting

### Common Issues

**Issue**: Categories not loading when creating a game

- **Solution**: Ensure you've selected a season first. Categories load dynamically based on the selected season.

**Issue**: Roster file not found

- **Solution**: Check that your roster file follows the naming convention: `roster_SEASON_CATEGORY.json`

**Issue**: Stats not saving

- **Solution**: Ensure `gamesFiles/` directory has write permissions

**Issue**: PIN not working

- **Solution**: Check that `FLOORBALL_PIN` environment variable is set correctly

### Data Recovery

If you experience data issues:

1. Check `gamesFiles/` for automatic backups (`games_backup_*.json`)
1. Restore from the most recent backup
1. Use migration scripts to update data structure if needed

## 📞 Support

For issues, questions, or feature requests:

- Open an issue on GitHub
- Check existing documentation in `docs/` folder
- Review [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for upgrade help

---

**Version**: 2.0.0 (Season Management Update)
**Last Updated**: November 2025
**Maintainer**: Denny Schwender
