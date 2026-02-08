"""
Roster data model and management functions
"""
import os
import json
from config import ROSTERS_DIR
from utils.security import sanitize_filename, validate_category, validate_season


def get_roster_file(category, season=None):
    """Get the roster file path for a specific category and season.
    
    Security: Validates inputs and prevents path traversal attacks.
    """
    # Security: Validate category input
    if not category or not validate_category(category):
        raise ValueError("Invalid category")
    
    # Security: Validate season input
    if season and not validate_season(season):
        raise ValueError("Invalid season format")
    
    # Security: Sanitize components
    safe_category = sanitize_filename(category)
    
    if season and season.strip():
        safe_season = sanitize_filename(season)
        filename = f'roster_{safe_season}_{safe_category}.json'
    else:
        # For backward compatibility, return old format if no season specified
        filename = f'roster_{safe_category}.json'
    
    # Security: Ensure the path stays within ROSTERS_DIR
    filepath = os.path.join(ROSTERS_DIR, filename)
    filepath = os.path.abspath(filepath)
    
    # Verify the resolved path is still within ROSTERS_DIR
    if not filepath.startswith(os.path.abspath(ROSTERS_DIR)):
        raise ValueError("Path traversal attempt detected")
    
    return filepath


def load_roster(category=None, season=None):
    """Load roster for a specific category and season. If no category, return empty list."""
    if not category:
        return []
    
    roster_file = get_roster_file(category, season)
    try:
        if os.path.exists(roster_file):
            with open(roster_file, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return []


def save_roster(roster, category, season=None):
    """Save roster for a specific category and season"""
    roster_file = get_roster_file(category, season)
    with open(roster_file, 'w') as f:
        json.dump(roster, f, indent=2)


def get_all_seasons():
    """Get list of all unique seasons from roster files"""
    seasons = set()
    
    # Ensure rosters directory exists
    if not os.path.exists(ROSTERS_DIR):
        return sorted(seasons)
    
    # Scan for all roster_*.json files
    for filename in os.listdir(ROSTERS_DIR):
        if filename.startswith('roster_') and filename.endswith('.json'):
            # Extract season and category from filename: roster_SEASON_CATEGORY.json or roster_CATEGORY.json
            parts = filename[7:-5].split('_', 1)  # Remove 'roster_' prefix and '.json' suffix
            if len(parts) == 2:
                seasons.add(parts[0])  # First part is season
    
    return sorted(seasons, reverse=True)  # Most recent season first


def get_all_categories_with_rosters(season=None):
    """Get list of all categories that have roster files by scanning the rosters directory"""
    categories = set()
    
    # Ensure rosters directory exists
    if not os.path.exists(ROSTERS_DIR):
        return sorted(categories)
    
    # Scan for all roster_*.json files
    for filename in os.listdir(ROSTERS_DIR):
        if filename.startswith('roster_') and filename.endswith('.json'):
            # Extract category name from filename
            parts = filename[7:-5].split('_', 1)  # Remove 'roster_' prefix and '.json' suffix
            if season and season.strip():
                # Filter by season: roster_SEASON_CATEGORY.json
                if len(parts) == 2 and parts[0] == season:
                    categories.add(parts[1])
            else:
                # Get all categories (with or without season)
                if len(parts) == 2:
                    categories.add(parts[1])
                elif len(parts) == 1:
                    categories.add(parts[0])  # Old format without season
    
    # Sort alphabetically
    return sorted(categories)


def get_all_tesser_values():
    """Get list of all unique tesser/category values from all rosters"""
    tesser_values = set()
    # Scan all roster files
    all_categories = get_all_categories_with_rosters()
    for category in all_categories:
        roster = load_roster(category)
        for player in roster:
            if 'tesser' in player and player['tesser']:
                tesser_values.add(player['tesser'])
    # Return sorted list
    return sorted(tesser_values)
