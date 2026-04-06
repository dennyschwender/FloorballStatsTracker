"""
API endpoints blueprint
"""
from flask import Blueprint, request, jsonify
from models.roster import get_all_categories_with_rosters, load_roster
from services.stats_service import calculate_player_trends, calculate_lineup_combinations

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/categories')
def get_categories_by_season():
    """API endpoint to get categories by season"""
    season = request.args.get('season', '')
    categories = get_all_categories_with_rosters(season)
    return jsonify(categories)


@api_bp.route('/roster/<category>')
def get_roster_by_category(category):
    """API endpoint to get roster by category"""
    # Don't validate against hardcoded CATEGORIES - allow any category
    # load_roster() will return an empty list if the roster doesn't exist
    season = request.args.get('season', '')
    include_hidden = request.args.get('include_hidden', 'false').lower() == 'true'

    roster = load_roster(category, season)

    # Filter out hidden players unless explicitly requested
    if not include_hidden:
        roster = [p for p in roster if not p.get('hidden', False)]

    roster_sorted = sorted(roster, key=lambda p: int(p.get('number', 999)))
    return jsonify(roster_sorted)


@api_bp.route('/chart-data', methods=['GET'])
def chart_data():
    """Return chart data for selected players across filtered games.

    Query parameters:
    - season (required): Season name like "2025-26"
    - team (required): Team/category like "U21"
    - players (required, multi-valued): List of player names/numbers
    - last_n_games (optional): Integer to limit results

    Returns JSON with players list and games array containing player stats.
    """
    from services.game_service import load_games

    # 1. Validate required parameters
    season = request.args.get('season', '').strip()
    team = request.args.get('team', '').strip()
    players_input = request.args.getlist('players')
    last_n_games_str = request.args.get('last_n_games', '')

    # Return 400 for missing required parameters
    if not season:
        return jsonify({'error': 'season parameter is required'}), 400
    if not team:
        return jsonify({'error': 'team parameter is required'}), 400
    if not players_input:
        return jsonify({'error': 'At least one player required'}), 400

    # 2. Load and filter games
    games = load_games()
    filtered_games = [g for g in games if g.get('season') == season and g.get('team') == team]

    # Apply last_n_games limit (keep most recent games)
    if last_n_games_str:
        try:
            last_n = int(last_n_games_str)
            filtered_games = filtered_games[-last_n:] if last_n > 0 else filtered_games
        except ValueError:
            return jsonify({'error': 'last_n_games must be an integer'}), 400

    # 3. Build response with per-game stats for requested players
    result_games = []
    for game in filtered_games:
        game_entry = {
            'date': game.get('date'),
            'game_id': game.get('id'),
            'home_team': game.get('home_team'),
            'away_team': game.get('away_team'),
        }

        # For each requested player, extract their stats from this game
        for player in players_input:
            # Check if player is in this game's lines
            player_in_game = any(player in line for line in game.get('lines', []))

            if not player_in_game:
                continue  # Skip this player for this game

            # Extract per-game stats
            goals = game.get('goals', {}).get(player, 0)
            assists = game.get('assists', {}).get(player, 0)
            sog = game.get('sog', {}).get(player, 0)
            plusminus = game.get('plusminus', {}).get(player, 0)
            penalties_drawn = game.get('penalties_drawn', {}).get(player, 0)
            penalties_taken = game.get('penalties_taken', {}).get(player, 0)
            unforced_errors = game.get('unforced_errors', {}).get(player, 0)

            # Calculate game score using the test formula:
            # goals*3.0 + assists*2.0 + sog*0.75 + plusminus*0.5 + penalties_drawn*0.5 - penalties_taken*1.0 - errors*1.0
            game_score = (
                goals * 3.0 +
                assists * 2.0 +
                sog * 0.75 +
                plusminus * 0.5 +
                penalties_drawn * 0.5 -
                penalties_taken * 1.0 -
                unforced_errors * 1.0
            )

            game_entry[player] = {
                'game_score': round(game_score, 2),
                'goals': goals,
                'assists': assists,
            }

        result_games.append(game_entry)

    return jsonify({
        'players': players_input,
        'games': result_games,
    }), 200


@api_bp.route('/player-trends', methods=['GET'])
def player_trends():
    """Return player performance trends for selected players.

    Query parameters:
    - season (required): Season name like "2025-26"
    - team (required): Team/category like "U21"
    - players (required): Comma-separated list of player names

    Returns JSON with player trends including game scores, statistics, and outliers.
    """
    from services.game_service import load_games

    # 1. Validate required parameters
    season = request.args.get('season', '').strip()
    team = request.args.get('team', '').strip()
    players_param = request.args.get('players', '').strip()

    # Return 400 for missing required parameters
    if not season:
        return jsonify({'error': 'season parameter is required'}), 400
    if not team:
        return jsonify({'error': 'team parameter is required'}), 400
    if not players_param:
        return jsonify({'error': 'players parameter is required'}), 400

    # Parse comma-separated player list
    players_list = [p.strip() for p in players_param.split(',') if p.strip()]
    if not players_list:
        return jsonify({'error': 'players parameter cannot be empty'}), 400

    # 2. Load and filter games
    games = load_games()
    filtered_games = [g for g in games if g.get('season') == season and g.get('team') == team]

    # 3. Calculate player trends
    trends_result = calculate_player_trends(filtered_games, players=players_list)

    # 4. Return response
    return jsonify({
        'success': True,
        'data': trends_result
    }), 200


@api_bp.route('/lineup-combos', methods=['GET'])
def lineup_combos():
    """Return lineup combination analysis for the specified season and team.

    Query parameters:
    - season (required): Season name like "2025-26"
    - team (required): Team/category like "U21"
    - combo_size_range (optional): Comma-separated min,max (default "5,7")
    - limit (optional): Max combos per size (default 10)

    Returns JSON with lineup combinations and their performance metrics.
    """
    from services.game_service import load_games

    # 1. Validate required parameters
    season = request.args.get('season', '').strip()
    team = request.args.get('team', '').strip()

    # Return 400 for missing required parameters
    if not season:
        return jsonify({'error': 'season parameter is required'}), 400
    if not team:
        return jsonify({'error': 'team parameter is required'}), 400

    # 2. Parse optional parameters
    combo_size_range_str = request.args.get('combo_size_range', '5,7').strip()
    limit_str = request.args.get('limit', '10').strip()

    # Parse combo_size_range
    try:
        combo_parts = combo_size_range_str.split(',')
        if len(combo_parts) != 2:
            return jsonify({'error': 'combo_size_range must be format "min,max"'}), 400
        min_size = int(combo_parts[0].strip())
        max_size = int(combo_parts[1].strip())
        combo_size_range = (min_size, max_size)
    except ValueError:
        return jsonify({'error': 'combo_size_range values must be integers'}), 400

    # Parse limit
    try:
        limit = int(limit_str)
        if limit < 1:
            return jsonify({'error': 'limit must be at least 1'}), 400
    except ValueError:
        return jsonify({'error': 'limit must be an integer'}), 400

    # 3. Load and filter games
    games = load_games()
    filtered_games = [g for g in games if g.get('season') == season and g.get('team') == team]

    # 4. Calculate lineup combinations
    combos_result = calculate_lineup_combinations(filtered_games, combo_size_range=combo_size_range, limit=limit)

    # 5. Return response
    return jsonify({
        'success': True,
        'data': combos_result
    }), 200
