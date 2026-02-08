"""
Statistics routes blueprint
"""
from datetime import datetime
from flask import Blueprint, request, render_template
from services.game_service import load_games, save_games, ensure_game_stats
from services.stats_service import calculate_stats_optimized
from models.roster import get_all_seasons

stats_bp = Blueprint('stats', __name__)


@stats_bp.route('/stats')
def stats():
    games = load_games()
    # Data checking and defaulting for missing fields
    changed = False
    for game in games:
        old_changed = changed
        ensure_game_stats(game)
        # Check if game was modified
        if not old_changed and any(stat not in game or not isinstance(game[stat], dict) 
                                   for stat in ['plusminus', 'goals', 'assists', 'unforced_errors',
                                               'shots_on_goal', 'penalties_taken', 'penalties_drawn',
                                               'saves', 'goals_conceded']):
            changed = True
        if 'lines' not in game or not isinstance(game['lines'], list):
            game['lines'] = []
            changed = True
        if 'goalies' not in game or not isinstance(game['goalies'], list):
            game['goalies'] = []
            changed = True
    if changed:
        save_games(games)
    
    # Sort games by date (oldest first)
    def game_sort_key(game):
        date_str = game.get('date')
        try:
            date_val = datetime.strptime(date_str, '%Y-%m-%d') if date_str else datetime.min
        except Exception:
            date_val = datetime.min
        return (date_val, -games.index(game))

    games_sorted = sorted(games, key=game_sort_key, reverse=False)
    
    # Filter by season
    seasons = get_all_seasons()
    selected_season = request.args.get('season')
    if selected_season:
        games_sorted = [
            game for game in games_sorted if game.get('season') == selected_season
        ]
    
    # Filter by team/category
    teams = sorted(set(game.get('team', '') for game in games if game.get('team')))
    selected_team = request.args.get('team')
    if selected_team:
        games_sorted = [
            game for game in games_sorted if game.get('team') == selected_team
        ]
    
    # Get filter parameters
    hide_zero_stats = request.args.get('hide_zero_stats', 'false') == 'true'
    
    # Calculate stats using optimized function
    stats_data = calculate_stats_optimized(games_sorted, hide_zero_stats)
    
    return render_template(
        'stats.html',
        players=stats_data['players'],
        player_totals=stats_data['player_totals'],
        goalies=stats_data['goalies'],
        goalie_data=stats_data['goalie_data'],
        opponent_goalie_data=stats_data['opponent_goalie_data'],
        games_with_calculated_stats=stats_data['games_with_calculated_stats'],
        teams=teams,
        selected_team=selected_team,
        seasons=seasons,
        selected_season=selected_season,
        hide_zero_stats=hide_zero_stats
    )
