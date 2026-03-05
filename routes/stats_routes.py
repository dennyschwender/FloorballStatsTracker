"""
Statistics routes blueprint
"""
from datetime import datetime
from flask import Blueprint, request, render_template
from services.game_service import load_games, ensure_game_stats
from services.stats_service import calculate_stats_optimized
from models.roster import get_all_seasons

stats_bp = Blueprint('stats', __name__)


@stats_bp.route('/stats')
def stats():
    games = load_games()
    # Normalise in-memory dicts for the template — do NOT write back to DB on a GET.
    for game in games:
        ensure_game_stats(game)
        if 'lines' not in game or not isinstance(game['lines'], list):
            game['lines'] = []
        if 'goalies' not in game or not isinstance(game['goalies'], list):
            game['goalies'] = []

    # Sort games by date (oldest first), use game id as stable tiebreaker
    def game_sort_key(game):
        date_str = game.get('date')
        try:
            date_val = datetime.strptime(date_str, '%Y-%m-%d') if date_str else datetime.min
        except Exception:
            date_val = datetime.min
        return (date_val, game.get('id', 0))

    games_sorted = sorted(games, key=game_sort_key, reverse=False)

    # Filter by season
    seasons = get_all_seasons()
    from models.team_settings import get_current_season as _cur_season
    _default_season = _cur_season()
    selected_season = request.args.get('season', _default_season if _default_season else None)
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
    hide_future_games = request.args.get('hide_future_games', 'false') == 'true'

    # Filter to last N games
    last_n_games = request.args.get('last_n_games', '')
    try:
        last_n = int(last_n_games) if last_n_games else None
    except ValueError:
        last_n = None
    if last_n and last_n > 0:
        games_sorted = games_sorted[-last_n:]

    # Calculate stats using optimized function
    stats_data = calculate_stats_optimized(games_sorted, hide_zero_stats)

    # Pre-sort player lists by avg/game DESC for each stat table
    _players = stats_data['players']
    _totals = stats_data['player_totals']
    def _sort(key):
        return sorted(_players, key=lambda p: _totals[p].get(key, 0), reverse=True)

    players_by_game_score      = _sort('avg_game_score')
    players_by_goals_assists   = _sort('avg_goals_assists')
    players_by_plusminus       = _sort('avg_plusminus')
    players_by_unforced_errors = _sort('avg_unforced_errors')
    players_by_sog             = _sort('avg_shots_on_goal')
    players_by_block_shots     = _sort('avg_block_shots')
    players_by_stolen_balls    = _sort('avg_stolen_balls')
    players_by_penalties_taken = _sort('avg_penalties_taken')
    players_by_penalties_drawn = _sort('avg_penalties_drawn')

    return render_template(
        'stats.html',
        players=stats_data['players'],
        players_by_game_score=players_by_game_score,
        players_by_goals_assists=players_by_goals_assists,
        players_by_plusminus=players_by_plusminus,
        players_by_unforced_errors=players_by_unforced_errors,
        players_by_sog=players_by_sog,
        players_by_block_shots=players_by_block_shots,
        players_by_stolen_balls=players_by_stolen_balls,
        players_by_penalties_taken=players_by_penalties_taken,
        players_by_penalties_drawn=players_by_penalties_drawn,
        player_totals=stats_data['player_totals'],
        goalies=stats_data['goalies'],
        goalie_data=stats_data['goalie_data'],
        opponent_goalie_data=stats_data['opponent_goalie_data'],
        games=stats_data['games_with_calculated_stats'],
        games_with_calculated_stats=stats_data['games_with_calculated_stats'],
        teams=teams,
        selected_team=selected_team,
        seasons=seasons,
        selected_season=selected_season,
        hide_zero_stats=hide_zero_stats,
        hide_future_games=hide_future_games,
        last_n_games=last_n_games
    )
