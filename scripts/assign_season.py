#!/usr/bin/env python3
"""
Quick script to assign a season to existing games and rosters.
Usage: python assign_season.py <season_name>
Example: python assign_season.py 2024-25
"""

import json
import os
import sys
import shutil
from datetime import datetime

ROSTERS_DIR = 'rosters'
GAMES_FILE = 'gamesFiles/games.json'

def assign_season_to_rosters(season):
    """Rename roster files to include season: roster_U21.json -> roster_2024-25_U21.json"""
    if not os.path.exists(ROSTERS_DIR):
        print(f"❌ Rosters directory not found: {ROSTERS_DIR}")
        return
    
    renamed_count = 0
    for filename in os.listdir(ROSTERS_DIR):
        if filename.startswith('roster_') and filename.endswith('.json') and '_' not in filename[7:-5]:
            # Old format: roster_U21.json
            old_path = os.path.join(ROSTERS_DIR, filename)
            category = filename[7:-5]  # Extract category (e.g., "U21")
            new_filename = f'roster_{season}_{category}.json'
            new_path = os.path.join(ROSTERS_DIR, new_filename)
            
            if os.path.exists(new_path):
                print(f"⚠️  Skipping {filename} - {new_filename} already exists")
                continue
            
            shutil.move(old_path, new_path)
            print(f"✅ Renamed: {filename} → {new_filename}")
            renamed_count += 1
    
    print(f"\n📊 Renamed {renamed_count} roster file(s)")

def assign_season_to_games(season):
    """Add season field to all games in games.json"""
    if not os.path.exists(GAMES_FILE):
        print(f"❌ Games file not found: {GAMES_FILE}")
        return
    
    # Backup first
    backup_file = f"{GAMES_FILE}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(GAMES_FILE, backup_file)
    print(f"💾 Created backup: {backup_file}")
    
    # Load games
    with open(GAMES_FILE, 'r', encoding='utf-8') as f:
        games = json.load(f)
    
    # Update games
    updated_count = 0
    for game in games:
        if 'season' not in game or not game['season']:
            game['season'] = season
            updated_count += 1
    
    # Save games
    with open(GAMES_FILE, 'w', encoding='utf-8') as f:
        json.dump(games, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Updated {updated_count} game(s) with season '{season}'")
    print(f"📊 Total games in file: {len(games)}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python assign_season.py <season_name>")
        print("Example: python assign_season.py 2024-25")
        sys.exit(1)
    
    season = sys.argv[1]
    
    print(f"🏒 Assigning season '{season}' to existing data...\n")
    
    # Assign season to rosters
    print("📋 Processing rosters...")
    assign_season_to_rosters(season)
    
    print("\n" + "="*50 + "\n")
    
    # Assign season to games
    print("🎮 Processing games...")
    assign_season_to_games(season)
    
    print("\n" + "="*50)
    print("✨ Migration complete!")

if __name__ == '__main__':
    main()
