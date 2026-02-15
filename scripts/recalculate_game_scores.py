"""
Script to recalculate all game scores with the updated goalie formula.

This script updates all existing games to use the new goalie GS formula:
- Old: GS = (0.10 × Saves) - (0.25 × Goals Conceded)
- New: GS = (0.15 × Saves) - (0.40 × Goals Conceded)

Run this after updating the goalie GS formula to update historical data.
"""
import sys
import os

# Add parent directory to path so we can import from the app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.game_service import load_games, save_games
from services.stats_service import recalculate_game_scores


def main():
    """Recalculate game scores for all games."""
    print("Loading games...")
    games = load_games()
    
    if not games:
        print("No games found.")
        return
    
    print(f"Found {len(games)} games. Recalculating game scores...")
    
    updated_count = 0
    for i, game in enumerate(games, 1):
        print(f"Processing game {i}/{len(games)}: {game.get('home_team', 'Unknown')} vs {game.get('away_team', 'Unknown')} ({game.get('date', 'No date')})")
        
        # Recalculate all game scores for this game
        recalculate_game_scores(game)
        updated_count += 1
    
    print(f"\nSaving {updated_count} updated games...")
    save_games(games)
    
    print("✅ Game scores recalculated successfully!")
    print(f"\nSummary:")
    print(f"  - Total games processed: {updated_count}")
    print(f"  - New goalie formula: GS = (0.15 × Saves) - (0.40 × Goals Conceded)")


if __name__ == '__main__':
    main()
