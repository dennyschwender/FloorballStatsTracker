#!/usr/bin/env python3
"""
Script to migrate old games to match player names with roster data.

This script:
1. Creates a backup of games.json
2. Loads all games and rosters
3. Attempts to match player names in games with roster entries
4. Updates games with standardized player names
"""

import json
import os
import shutil
from datetime import datetime
from difflib import SequenceMatcher

# File paths
GAMES_FILE = 'gamesFiles/games.json'
ROSTERS_DIR = 'rosters'

def similarity(a, b):
    """Calculate similarity ratio between two strings."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def load_json(filepath):
    """Load JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: {filepath} not found")
        return []
    except json.JSONDecodeError as e:
        print(f"Error decoding {filepath}: {e}")
        return []

def save_json(filepath, data):
    """Save data to JSON file."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def backup_games():
    """Create a backup of games.json."""
    if not os.path.exists(GAMES_FILE):
        print(f"No {GAMES_FILE} found to backup")
        return None
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f'gamesFiles/games_backup_{timestamp}.json'
    shutil.copy(GAMES_FILE, backup_path)
    print(f"✓ Backup created: {backup_path}")
    return backup_path

def load_all_rosters():
    """Load all roster files from the rosters directory."""
    rosters = {}
    
    if not os.path.exists(ROSTERS_DIR):
        print(f"Warning: {ROSTERS_DIR} directory not found")
        return rosters
    
    for filename in os.listdir(ROSTERS_DIR):
        if filename.startswith('roster_') and filename.endswith('.json'):
            # Extract category name from filename: roster_CATEGORY.json
            category = filename.replace('roster_', '').replace('.json', '')
            filepath = os.path.join(ROSTERS_DIR, filename)
            roster = load_json(filepath)
            rosters[category] = roster
            print(f"✓ Loaded roster: {category} ({len(roster)} players)")
    
    return rosters

def create_player_variants(player):
    """
    Create all possible name variants for a player.
    Returns a list of variants to match against.
    """
    variants = []
    number = player.get('number', '')
    surname = player.get('surname', '').strip()
    name = player.get('name', '').strip()
    nickname = player.get('nickname', '').strip()
    
    # Standard format: "number - surname name"
    if number and surname and name:
        variants.append(f"{number} - {surname} {name}")
    
    # With nickname if available
    if number and nickname:
        variants.append(f"{number} - {nickname}")
        if surname:
            variants.append(f"{number} - {nickname} {surname}")
    
    # Without number
    if surname and name:
        variants.append(f"{surname} {name}")
    if nickname:
        variants.append(nickname)
    
    # Surname only
    if surname:
        variants.append(surname)
    
    return variants

def get_all_matches(player_string, roster):
    """
    Get all players sorted by similarity score.
    Returns list of tuples: (player_dict, standardized_name, score)
    """
    if not player_string or not roster:
        return []
    
    matches = []
    
    for player in roster:
        variants = create_player_variants(player)
        best_score = 0
        
        for variant in variants:
            score = similarity(player_string, variant)
            if score > best_score:
                best_score = score
        
        if best_score > 0:
            number = player.get('number', '')
            surname = player.get('surname', '')
            name = player.get('name', '')
            standardized = f"{number} - {surname} {name}"
            matches.append((player, standardized, best_score))
    
    # Sort by score descending
    matches.sort(key=lambda x: x[2], reverse=True)
    return matches

def find_best_match(player_string, roster, interactive=False):
    """
    Find the best matching player in the roster for a given player string.
    Returns tuple: (standardized_name or None, similarity_score)
    If interactive=True, prompts user to select from top matches when score < 0.8
    """
    if not player_string or not roster:
        return None, 0.0
    
    matches = get_all_matches(player_string, roster)
    
    if not matches:
        return None, 0.0
    
    best_player, best_standardized, best_score = matches[0]
    
    # Automatic match if similarity > 0.8 (80%)
    if best_score > 0.8:
        return best_standardized, best_score
    
    # Interactive mode: show options to user
    if interactive and matches:
        print(f"\n  No automatic match for '{player_string}' (best score: {best_score:.2f})")
        print(f"  Top {min(10, len(matches))} candidates:")
        
        for i, (player, standardized, score) in enumerate(matches[:10], 1):
            print(f"    {i}. {standardized} (score: {score:.2f})")
        
        print(f"    s. Skip (leave as '{player_string}')")
        
        while True:
            choice = input(f"  Select option (1-{min(10, len(matches))}, s): ").strip().lower()
            
            if choice == 's':
                return None, best_score
            
            try:
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < min(10, len(matches)):
                    selected = matches[choice_idx]
                    return selected[1], selected[2]
                else:
                    print(f"  Invalid choice. Please enter 1-{min(10, len(matches))} or 's'")
            except ValueError:
                print(f"  Invalid input. Please enter a number or 's'")
    
    return None, best_score

def migrate_game(game, rosters, interactive=False):
    """
    Migrate a single game to match player names with roster.
    Returns the migrated game and a report of changes.
    If interactive=True, prompts user to select matches for warnings.
    """
    report = {
        'game_id': game.get('id', 'unknown'),
        'date': game.get('date', 'unknown'),
        'home_team': game.get('home_team', ''),
        'away_team': game.get('away_team', ''),
        'changes': [],
        'warnings': []
    }
    
    # Get the team/category for this game
    team = game.get('team', '')
    if not team:
        report['warnings'].append("No team/category specified")
        return game, report
    
    # Find matching roster
    roster = rosters.get(team)
    if not roster:
        report['warnings'].append(f"No roster found for category: {team}")
        return game, report
    
    # Migrate lines
    if 'lines' in game:
        for line_idx, line in enumerate(game['lines']):
            new_line = []
            for player_string in line:
                matched_name, score = find_best_match(player_string, roster, interactive)
                if matched_name:
                    new_line.append(matched_name)
                    if matched_name != player_string:
                        report['changes'].append(
                            f"Line {line_idx + 1}: '{player_string}' → '{matched_name}' (score: {score:.2f})"
                        )
                else:
                    new_line.append(player_string)
                    report['warnings'].append(
                        f"Line {line_idx + 1}: No match found for '{player_string}' (best score: {score:.2f})"
                    )
            game['lines'][line_idx] = new_line
    
    # Migrate goalies
    if 'goalies' in game:
        new_goalies = []
        for goalie_string in game['goalies']:
            matched_name, score = find_best_match(goalie_string, roster, interactive)
            if matched_name:
                new_goalies.append(matched_name)
                if matched_name != goalie_string:
                    report['changes'].append(
                        f"Goalie: '{goalie_string}' → '{matched_name}' (score: {score:.2f})"
                    )
            else:
                new_goalies.append(goalie_string)
                report['warnings'].append(
                    f"Goalie: No match found for '{goalie_string}' (best score: {score:.2f})"
                )
        game['goalies'] = new_goalies
    
    # Migrate formations
    for formation_key in ['pp1', 'pp2', 'bp1', 'bp2', '6vs5', 'stress_line']:
        if formation_key in game:
            new_formation = []
            for player_string in game[formation_key]:
                matched_name, score = find_best_match(player_string, roster, interactive)
                if matched_name:
                    new_formation.append(matched_name)
                    if matched_name != player_string:
                        report['changes'].append(
                            f"{formation_key.upper()}: '{player_string}' → '{matched_name}' (score: {score:.2f})"
                        )
                else:
                    new_formation.append(player_string)
                    report['warnings'].append(
                        f"{formation_key.upper()}: No match found for '{player_string}' (best score: {score:.2f})"
                    )
            game[formation_key] = new_formation
    
    # Migrate stats dictionaries (goals, assists, plusminus, saves, unforced_errors, etc.)
    stats_keys = ['goals', 'assists', 'plusminus', 'saves', 'unforced_errors', 
                  'opponent_goalie_saves', 'opponent_goalie_goals_conceded']
    
    for stat_key in stats_keys:
        if stat_key in game and isinstance(game[stat_key], dict):
            new_stats = {}
            for player_string, value in game[stat_key].items():
                matched_name, score = find_best_match(player_string, roster, interactive)
                if matched_name:
                    new_stats[matched_name] = value
                    if matched_name != player_string:
                        report['changes'].append(
                            f"{stat_key}: '{player_string}' → '{matched_name}' (value: {value}, score: {score:.2f})"
                        )
                else:
                    new_stats[player_string] = value
                    report['warnings'].append(
                        f"{stat_key}: No match found for '{player_string}' (value: {value}, best score: {score:.2f})"
                    )
            game[stat_key] = new_stats
    
    return game, report

def main():
    """Main migration function."""
    print("=" * 80)
    print("GAME MIGRATION SCRIPT")
    print("=" * 80)
    print()
    
    # Step 1: Backup
    print("Step 1: Creating backup...")
    backup_path = backup_games()
    if not backup_path:
        print("No games to migrate. Exiting.")
        return
    print()
    
    # Step 2: Load data
    print("Step 2: Loading data...")
    games = load_json(GAMES_FILE)
    rosters = load_all_rosters()
    print(f"✓ Loaded {len(games)} games")
    print()
    
    if not games:
        print("No games found. Exiting.")
        return
    
    if not rosters:
        print("No rosters found. Exiting.")
        return
    
    # Ask for interactive mode
    print("Interactive mode allows you to manually select from candidate matches")
    print("when automatic matching is uncertain (score < 80%).")
    interactive_response = input("Enable interactive mode? (yes/no) [no]: ").lower().strip()
    interactive = interactive_response == 'yes'
    print()
    
    # Step 3: Migrate games
    print("Step 3: Migrating games...")
    print()
    
    all_reports = []
    migrated_games = []
    
    for game_idx, game in enumerate(games):
        if interactive:
            print(f"\n--- Processing Game #{game_idx}: {game.get('date', 'unknown')} - {game.get('home_team', '')} vs {game.get('away_team', '')} ---")
        migrated_game, report = migrate_game(game, rosters, interactive)
        migrated_games.append(migrated_game)
        all_reports.append(report)
        
        # Print report for each game (skip in interactive mode as it's shown inline)
        if not interactive and (report['changes'] or report['warnings']):
            print(f"Game #{game_idx}: {report['date']} - {report['home_team']} vs {report['away_team']}")
            if report['changes']:
                print(f"  Changes: {len(report['changes'])}")
                for change in report['changes'][:3]:  # Show first 3 changes
                    print(f"    • {change}")
                if len(report['changes']) > 3:
                    print(f"    ... and {len(report['changes']) - 3} more")
            if report['warnings']:
                print(f"  ⚠ Warnings: {len(report['warnings'])}")
                for warning in report['warnings'][:2]:  # Show first 2 warnings
                    print(f"    • {warning}")
                if len(report['warnings']) > 2:
                    print(f"    ... and {len(report['warnings']) - 2} more")
            print()
    
    # Step 4: Summary
    print("=" * 80)
    print("MIGRATION SUMMARY")
    print("=" * 80)
    total_changes = sum(len(r['changes']) for r in all_reports)
    total_warnings = sum(len(r['warnings']) for r in all_reports)
    games_changed = sum(1 for r in all_reports if r['changes'])
    
    print(f"Total games processed: {len(games)}")
    print(f"Games with changes: {games_changed}")
    print(f"Total player name updates: {total_changes}")
    print(f"Total warnings: {total_warnings}")
    print()
    
    # Step 5: Save or dry run
    if total_changes > 0:
        response = input("Save migrated games? (yes/no): ").lower().strip()
        if response == 'yes':
            save_json(GAMES_FILE, migrated_games)
            print(f"✓ Saved migrated games to {GAMES_FILE}")
            print(f"✓ Backup available at: {backup_path}")
            
            # Save detailed report
            report_path = f'gamesFiles/migration_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            save_json(report_path, all_reports)
            print(f"✓ Detailed report saved to: {report_path}")
        else:
            print("Migration cancelled. No changes saved.")
            print(f"Backup remains at: {backup_path}")
    else:
        print("No changes needed. All games already match roster data.")
    
    print()
    print("Migration complete!")

if __name__ == '__main__':
    main()
