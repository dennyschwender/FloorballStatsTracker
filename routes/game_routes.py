"""
Game management routes blueprint
"""
import io
import json
import hmac
from datetime import datetime
from flask import Blueprint, request, render_template, redirect, url_for, session, g, send_file
from config import REQUIRED_PIN, PERIODS
from services.game_service import (
    load_games, save_games, find_game_by_id, ensure_game_ids,
    ensure_game_stats, ensure_player_stats, build_formation_from_form,
    delete_game_by_id,
)
from services.stats_service import recalculate_game_scores
from models.roster import load_roster, get_all_seasons

game_bp = Blueprint('game', __name__)


@game_bp.route('/', methods=['GET', 'POST'])
def index():
    if not session.get('authenticated'):
        if request.method == 'POST':
            pin = request.form.get('pin', '')
            # Security: Use timing-safe comparison to prevent timing attacks
            if hmac.compare_digest(pin, REQUIRED_PIN):
                session['authenticated'] = True
                session.permanent = True  # Enable session timeout
                return redirect(url_for('game.index'))
            else:
                return render_template('pin.html', error='Incorrect PIN')
        return render_template('pin.html')
    
    games = load_games()
    if ensure_game_ids(games):
        save_games(games)
    
    # Sort games by date (descending, newest first), then by creation order (id)
    def game_sort_key(game):
        date_str = game.get('date')
        try:
            date_val = datetime.strptime(date_str, '%Y-%m-%d') if date_str else datetime.min
        except Exception:
            date_val = datetime.min
        return (date_val, -games.index(game))

    games_sorted = sorted(games, key=game_sort_key, reverse=True)
    
    # Filter by season
    seasons = get_all_seasons()
    selected_season = request.args.get('season')
    if selected_season:
        games_sorted = [
            game for game in games_sorted if game.get('season') == selected_season
        ]
    
    # Filter by team
    selected_team = request.args.get('team')
    if selected_team:
        filtered_games = [
            game for game in games_sorted if game.get('team') == selected_team
        ]
    else:
        filtered_games = games_sorted
    
    latest_game_id = None
    if filtered_games:
        # Find the latest game for the selected team (or all games)
        latest_game_id = games.index(filtered_games[0])
    
    return render_template(
        'index.html',
        games=games_sorted,
        latest_game_id=latest_game_id,
        seasons=seasons,
        selected_season=selected_season,
        selected_team=selected_team
    )


@game_bp.route('/game/<int:game_id>')
def game_details(game_id):
    games = load_games()
    if ensure_game_ids(games):
        save_games(games)
    game = find_game_by_id(games, game_id)
    if not game:
        return "Game not found", 404
    
    # ensure current game id is available to templates (fallback)
    g.current_game_id = game_id
    
    # Load roster to get player nicknames
    roster = []
    if 'team' in game and game['team']:
        season = game.get('season', '')
        roster = load_roster(game['team'], season) if season else load_roster(game['team'])
    
    # Create a mapping from full name to nickname
    player_nicknames = {}
    for player in roster:
        number = player.get('number', '')
        surname = player.get('surname', '')
        name = player.get('name', '')
        nickname = player.get('nickname', '')
        if number and surname and name:
            full_name = f"{number} - {surname} {name}"
            if nickname:
                player_nicknames[full_name] = f"{number} - {nickname}"
            else:
                player_nicknames[full_name] = full_name
    
    # --- Error management: ensure all required fields exist and set defaults if missing ---
    changed = False
    # Ensure 'result' exists and has all periods
    if 'result' not in game or not isinstance(game['result'], dict):
        game['result'] = {p: {"home": 0, "away": 0} for p in PERIODS}
        changed = True
    else:
        for p in PERIODS:
            if p not in game['result'] or not isinstance(game['result'][p], dict):
                game['result'][p] = {"home": 0, "away": 0}
                changed = True
            else:
                if 'home' not in game['result'][p]:
                    game['result'][p]['home'] = 0
                    changed = True
                if 'away' not in game['result'][p]:
                    game['result'][p]['away'] = 0
                    changed = True
    # Ensure 'current_period' exists
    if 'current_period' not in game:
        game['current_period'] = '1'
        changed = True
    # Ensure 'lines' exists
    if 'lines' not in game or not isinstance(game['lines'], list):
        game['lines'] = []
        changed = True
    # Ensure 'goalies' exists
    if 'goalies' not in game or not isinstance(game['goalies'], list):
        game['goalies'] = []
        changed = True
    # Ensure 'opponent_goalie_enabled' exists (boolean flag)
    if 'opponent_goalie_enabled' not in game:
        game['opponent_goalie_enabled'] = False
        changed = True
    # Ensure stat dicts exist
    ensure_game_stats(game)
    # Also ensure goalie stats
    for stat in ['goalie_plusminus', 'saves', 'goals_conceded',
                 'opponent_goalie_saves', 'opponent_goalie_goals_conceded']:
        if stat not in game or not isinstance(game[stat], dict):
            game[stat] = {}
            changed = True
    if changed:
        # Find and update game by ID
        for i, game_item in enumerate(games):
            if game_item.get('id') == game_id:
                games[i] = game
                break
        save_games(games)
    # --- End error management ---
    
    # Ensure game scores are calculated (for backward compatibility with old games)
    if 'game_scores' not in game or 'goalie_game_scores' not in game:
        recalculate_game_scores(game)
        # Save the updated game with calculated scores
        for i, game_item in enumerate(games):
            if game_item.get('id') == game_id:
                games[i] = game
                break
        save_games(games)
    
    return render_template(
        'game_details.html',
        game=game,
        game_id=game_id,
        games=games,
        player_nicknames=player_nicknames
    )


@game_bp.route('/create_game', methods=['GET', 'POST'])
def create_game():
    if request.method == 'POST':
        season = request.form.get('season', '')
        team = request.form.get('team')
        home_team = request.form.get('home_team')
        away_team = request.form.get('away_team')
        date = request.form.get('date')
        referee1 = request.form.get('referee1', '')
        referee2 = request.form.get('referee2', '')
        
        # Direct lineup entry from form
        roster = load_roster(team, season)
        player_map = {p['id']: p for p in roster}
        
        # Build lines from form number inputs (position 1-5)
        lines = []
        for i in range(1, 5):
            line_players_with_position = []
            # Collect all form fields for this line
            for player_id in player_map.keys():
                position_value = request.form.get(f'l{i}_{player_id}', '').strip()
                if position_value:
                    player = player_map.get(player_id)
                    if player:
                        try:
                            pos_num = int(position_value)
                            line_players_with_position.append({
                                'position': pos_num,
                                'name': f"{player['number']} - {player['surname']} {player['name']}"
                            })
                        except ValueError:
                            pass
            
            # Sort by position number and extract names
            line_players_with_position.sort(key=lambda x: x['position'])
            line_players = [p['name'] for p in line_players_with_position]
            lines.append(line_players)
        
        # Get goalies from dropdown selections
        goalies = []
        for i in range(1, 3):
            goalie_id = request.form.get(f'goalie{i}', '')
            if goalie_id:
                player = player_map.get(goalie_id)
                if player:
                    goalies.append(f"{player['number']} - {player['surname']} {player['name']}")

        # Check if opponent goalie tracking should be enabled
        enable_opponent_goalie = request.form.get('enable_opponent_goalie') == 'on'
        
        # Check if game should be excluded from statistics
        exclude_from_stats = request.form.get('exclude_from_stats') == 'on'

        # Initialize period results
        result = {p: {"home": 0, "away": 0} for p in PERIODS}
        games = load_games()
        # Assign a unique id (max id + 1)
        if games:
            max_id = max([game_item.get('id', i) for i, game_item in enumerate(games)])
            new_id = max_id + 1
        else:
            new_id = 0
        game = {
            'id': new_id,
            'season': season,
            'team': team,
            'home_team': home_team,
            'away_team': away_team,
            'date': date,
            'referee1': referee1,
            'referee2': referee2,
            'lines': lines,
            'goalies': goalies,
            'opponent_goalie_enabled': enable_opponent_goalie,
            'exclude_from_stats': exclude_from_stats,
            'result': result,
            'current_period': '1',
        }
        
        # Store formations from direct form entry with position numbers
        formation_keys = ['pp1', 'pp2', 'bp1', 'bp2', '6vs5', 'stress_line']
        formations = build_formation_from_form(request.form, formation_keys, player_map)
        for key, players in formations.items():
            game[key] = players
        
        games.append(game)
        save_games(games)
        return redirect(url_for('game.index'))
    
    # GET request - load seasons (categories loaded dynamically via API)
    seasons = get_all_seasons()
    return render_template('game_form.html', categories=[], seasons=seasons)


@game_bp.route('/modify_game/<int:game_id>', methods=['GET', 'POST'])
def modify_game(game_id):
    games = load_games()
    game = find_game_by_id(games, game_id)
    if not game:
        return "Game not found", 404
    
    if request.method == 'POST':
        season = request.form.get('season', '')
        team = request.form.get('team')
        home_team = request.form.get('home_team')
        away_team = request.form.get('away_team')
        date = request.form.get('date')
        referee1 = request.form.get('referee1', '')
        referee2 = request.form.get('referee2', '')
        
        # Direct lineup entry from form
        roster = load_roster(team, season)
        player_map = {p['id']: p for p in roster}
        
        # Build lines from form number inputs (position 1-5)
        lines = []
        for i in range(1, 5):
            line_players_with_position = []
            # Collect all form fields for this line
            for player_id in player_map.keys():
                position_value = request.form.get(f'l{i}_{player_id}', '').strip()
                if position_value:
                    player = player_map.get(player_id)
                    if player:
                        try:
                            pos_num = int(position_value)
                            line_players_with_position.append({
                                'position': pos_num,
                                'name': f"{player['number']} - {player['surname']} {player['name']}"
                            })
                        except ValueError:
                            pass
            
            # Sort by position number and extract names
            line_players_with_position.sort(key=lambda x: x['position'])
            line_players = [p['name'] for p in line_players_with_position]
            lines.append(line_players)
        
        # Get goalies from dropdown selections
        goalies = []
        for i in range(1, 3):
            goalie_id = request.form.get(f'goalie{i}', '')
            if goalie_id:
                player = player_map.get(goalie_id)
                if player:
                    goalies.append(f"{player['number']} - {player['surname']} {player['name']}")

        # Check if opponent goalie tracking should be enabled (backward compatibility)
        has_opponent_stats = (
            'opponent_goalie_saves' in game and game['opponent_goalie_saves']) or (
            'opponent_goalie_goals_conceded' in game and game['opponent_goalie_goals_conceded'])
        enable_opponent_goalie = request.form.get('enable_opponent_goalie') == 'on' or has_opponent_stats
        
        # Check if game should be excluded from statistics
        exclude_from_stats = request.form.get('exclude_from_stats') == 'on'

        game['season'] = season
        game['team'] = team
        game['home_team'] = home_team
        game['away_team'] = away_team
        game['date'] = date
        game['referee1'] = referee1
        game['referee2'] = referee2
        game['lines'] = lines
        game['goalies'] = goalies
        game['opponent_goalie_enabled'] = enable_opponent_goalie
        game['exclude_from_stats'] = exclude_from_stats
        
        # Store formations from direct form entry with position numbers
        formation_keys = ['pp1', 'pp2', 'bp1', 'bp2', '6vs5', 'stress_line']
        formations = build_formation_from_form(request.form, formation_keys, player_map)
        for key, players in formations.items():
            game[key] = players
        
        if 'result' not in game:
            game['result'] = {p: {"home": 0, "away": 0} for p in PERIODS}
        if 'current_period' not in game:
            game['current_period'] = '1'
        
        # Find and update game by ID
        for i, game_item in enumerate(games):
            if game_item.get('id') == game_id:
                games[i] = game
                break
        save_games(games)
        return redirect(url_for('game.game_details', game_id=game_id))
    
    # GET request - load seasons for the form
    seasons = get_all_seasons()
    return render_template(
        'game_form.html',
        game=game,
        modify=True,
        game_id=game_id,
        categories=[],
        seasons=seasons
    )


@game_bp.route('/action/<int:game_id>/<player>')
def player_action(game_id, player):
    action = request.args.get('action')
    games = load_games()
    game = find_game_by_id(games, game_id)
    if not game:
        return "Game not found", 404
    
    # Track stats in dicts on the game object
    ensure_game_stats(game)
    ensure_player_stats(game, player)
    
    # Period result tracking
    period = game.get('current_period', '1')
    if 'result' not in game:
        game['result'] = {p: {"home": 0, "away": 0} for p in PERIODS}
    
    if action == 'plus':
        game['plusminus'][player] += 1
    elif action == 'minus':
        game['plusminus'][player] -= 1
    elif action == 'goal':
        game['goals'][player] += 1
        game['result'][period]['home'] += 1
        # Auto-increment opponent goalie goals conceded
        if game.get('opponent_goalie_enabled', False):
            if 'opponent_goalie_goals_conceded' not in game:
                game['opponent_goalie_goals_conceded'] = {}
            if "Opponent Goalie" not in game['opponent_goalie_goals_conceded']:
                game['opponent_goalie_goals_conceded']["Opponent Goalie"] = 0
            game['opponent_goalie_goals_conceded']["Opponent Goalie"] += 1
    elif action == 'goal_minus':
        if game['goals'][player] > 0:
            game['goals'][player] -= 1
            if game['result'][period]['home'] > 0:
                game['result'][period]['home'] -= 1
            # Auto-decrement opponent goalie goals conceded
            if game.get('opponent_goalie_enabled', False):
                if 'opponent_goalie_goals_conceded' not in game:
                    game['opponent_goalie_goals_conceded'] = {}
                if "Opponent Goalie" in game['opponent_goalie_goals_conceded'] and \
                   game['opponent_goalie_goals_conceded']["Opponent Goalie"] > 0:
                    game['opponent_goalie_goals_conceded']["Opponent Goalie"] -= 1
    elif action == 'assist':
        game['assists'][player] += 1
    elif action == 'assist_minus':
        if game['assists'][player] > 0:
            game['assists'][player] -= 1
    elif action == 'unforced_error':
        game['unforced_errors'][player] += 1
    elif action == 'unforced_error_minus':
        if game['unforced_errors'][player] > 0:
            game['unforced_errors'][player] -= 1
    elif action == 'shot_on_goal':
        game['shots_on_goal'][player] += 1
    elif action == 'shot_on_goal_minus':
        if game['shots_on_goal'][player] > 0:
            game['shots_on_goal'][player] -= 1
    elif action == 'penalty_taken':
        game['penalties_taken'][player] += 1
    elif action == 'penalty_taken_minus':
        if game['penalties_taken'][player] > 0:
            game['penalties_taken'][player] -= 1
    elif action == 'penalty_drawn':
        game['penalties_drawn'][player] += 1
    elif action == 'penalty_drawn_minus':
        if game['penalties_drawn'][player] > 0:
            game['penalties_drawn'][player] -= 1
    
    # Find and update game by ID
    for i, game_item in enumerate(games):
        if game_item.get('id') == game_id:
            games[i] = game
            break
    
    # Recalculate game scores after stat changes
    recalculate_game_scores(game)
    save_games(games)
    
    # Preserve edit mode if present
    if request.args.get('edit') == '1':
        return redirect(url_for('game.game_details', game_id=game_id, edit=1))
    return redirect(url_for('game.game_details', game_id=game_id))


@game_bp.route('/action_line/<int:game_id>/<int:line_idx>')
def line_action(game_id, line_idx):
    action = request.args.get('action')
    games = load_games()
    game = find_game_by_id(games, game_id)
    if not game:
        return "Game not found", 404
    if line_idx < 0 or line_idx >= len(game['lines']):
        return "Line not found", 404
    
    if 'plusminus' not in game:
        game['plusminus'] = {}
    if 'goals' not in game:
        game['goals'] = {}
    if 'assists' not in game:
        game['assists'] = {}
    
    # Period result tracking - done once per line action
    period = game.get('current_period', '1')
    if 'result' not in game:
        game['result'] = {p: {"home": 0, "away": 0} for p in PERIODS}
    
    # Handle line-level actions that affect score and opponent goalie stats
    if action == 'goal':
        # Home team goal in current period - increment ONCE for the line
        game['result'][period]['home'] += 1
        # Auto-increment opponent goalie goals conceded ONCE for the line
        if game.get('opponent_goalie_enabled', False):
            if 'opponent_goalie_goals_conceded' not in game:
                game['opponent_goalie_goals_conceded'] = {}
            if "Opponent Goalie" not in game['opponent_goalie_goals_conceded']:
                game['opponent_goalie_goals_conceded']["Opponent Goalie"] = 0
            game['opponent_goalie_goals_conceded']["Opponent Goalie"] += 1
    
    for player in game['lines'][line_idx]:
        ensure_player_stats(game, player)
        if action == 'plus':
            game['plusminus'][player] += 1
        elif action == 'minus':
            game['plusminus'][player] -= 1
        elif action == 'goal':
            game['goals'][player] += 1
        elif action == 'assist':
            game['assists'][player] += 1
    
    # Find and update game by ID
    for i, game_item in enumerate(games):
        if game_item.get('id') == game_id:
            games[i] = game
            break
    
    # Recalculate game scores after stat changes
    recalculate_game_scores(game)
    save_games(games)
    
    if request.args.get('edit') == '1':
        return redirect(url_for('game.game_details', game_id=game_id, edit=1))
    return redirect(url_for('game.game_details', game_id=game_id))


@game_bp.route('/action_goalie/<int:game_id>/<goalie>')
def goalie_action(game_id, goalie):
    action = request.args.get('action')
    games = load_games()
    game = find_game_by_id(games, game_id)
    if not game:
        return "Game not found", 404
    
    # Initialize goalie stats if not present
    for stat in ['goalie_plusminus', 'saves', 'goals_conceded', 'assists']:
        if stat not in game:
            game[stat] = {}
        if goalie not in game[stat]:
            game[stat][goalie] = 0
    
    # Period result tracking
    period = game.get('current_period', '1')
    if 'result' not in game:
        game['result'] = {p: {"home": 0, "away": 0} for p in PERIODS}
    
    if action == 'plus':
        game['goalie_plusminus'][goalie] += 1
    elif action == 'minus':
        game['goalie_plusminus'][goalie] -= 1
    elif action == 'save':
        game['saves'][goalie] += 1
    elif action == 'save_minus':
        if game['saves'][goalie] > 0:
            game['saves'][goalie] -= 1
    elif action == 'goal_conceded':
        game['goals_conceded'][goalie] += 1
        # Away team goal in current period
        game['result'][period]['away'] += 1
    elif action == 'goal_conceded_minus':
        if game['goals_conceded'][goalie] > 0:
            game['goals_conceded'][goalie] -= 1
            if game['result'][period]['away'] > 0:
                game['result'][period]['away'] -= 1
    elif action == 'assist':
        game['assists'][goalie] += 1
    elif action == 'assist_minus':
        if game['assists'][goalie] > 0:
            game['assists'][goalie] -= 1
    
    # Find and update game by ID
    for i, game_item in enumerate(games):
        if game_item.get('id') == game_id:
            games[i] = game
            break
    
    # Recalculate game scores after stat changes
    recalculate_game_scores(game)
    save_games(games)
    
    if request.args.get('edit') == '1':
        return redirect(url_for('game.game_details', game_id=game_id, edit=1))
    return redirect(url_for('game.game_details', game_id=game_id))


@game_bp.route('/action_opponent_goalie/<int:game_id>')
def opponent_goalie_action(game_id):
    action = request.args.get('action')
    games = load_games()
    game = find_game_by_id(games, game_id)
    if not game:
        return "Game not found", 404

    # Always use "Opponent Goalie" as the key
    opponent_goalie = "Opponent Goalie"

    # Initialize opponent goalie stats if not present
    if 'opponent_goalie_saves' not in game:
        game['opponent_goalie_saves'] = {}
    if 'opponent_goalie_goals_conceded' not in game:
        game['opponent_goalie_goals_conceded'] = {}
    if opponent_goalie not in game['opponent_goalie_saves']:
        game['opponent_goalie_saves'][opponent_goalie] = 0
    if opponent_goalie not in game['opponent_goalie_goals_conceded']:
        game['opponent_goalie_goals_conceded'][opponent_goalie] = 0
    
    # Period result tracking
    period = game.get('current_period', '1')
    if 'result' not in game:
        game['result'] = {p: {"home": 0, "away": 0} for p in PERIODS}

    if action == 'save':
        game['opponent_goalie_saves'][opponent_goalie] += 1
    elif action == 'save_minus':
        if game['opponent_goalie_saves'][opponent_goalie] > 0:
            game['opponent_goalie_saves'][opponent_goalie] -= 1
    elif action == 'goal_conceded':
        game['opponent_goalie_goals_conceded'][opponent_goalie] += 1
        # Home team goal in current period (our goal = opponent goalie goal conceded)
        game['result'][period]['home'] += 1
    elif action == 'goal_conceded_minus':
        if game['opponent_goalie_goals_conceded'][opponent_goalie] > 0:
            game['opponent_goalie_goals_conceded'][opponent_goalie] -= 1
            if game['result'][period]['home'] > 0:
                game['result'][period]['home'] -= 1
    
    # Find and update game by ID
    for i, game_item in enumerate(games):
        if game_item.get('id') == game_id:
            games[i] = game
            break
    
    # Recalculate game scores after stat changes
    recalculate_game_scores(game)
    save_games(games)
    
    if request.args.get('edit') == '1':
        return redirect(url_for('game.game_details', game_id=game_id, edit=1))
    return redirect(url_for('game.game_details', game_id=game_id))


@game_bp.route('/reset_game/<int:game_id>')
def reset_game(game_id):
    games = load_games()
    game = find_game_by_id(games, game_id)
    if not game:
        return "Game not found", 404
    
    # Reset player stats
    ensure_game_stats(game)
    for line in game.get('lines', []):
        for player in line:
            for stat in ['plusminus', 'goals', 'assists', 'unforced_errors', 'shots_on_goal', 
                         'penalties_taken', 'penalties_drawn']:
                game[stat][player] = 0
    
    # Reset goalie stats
    for stat in ['goalie_plusminus', 'saves', 'goals_conceded']:
        if stat not in game:
            game[stat] = {}
        for goalie in game.get('goalies', []):
            game[stat][goalie] = 0
    
    # Reset opponent goalie stats (use fixed "Opponent Goalie" key)
    for stat in ['opponent_goalie_saves', 'opponent_goalie_goals_conceded']:
        if stat not in game:
            game[stat] = {}
        if game.get('opponent_goalie_enabled', False):
            game[stat]["Opponent Goalie"] = 0
    
    # Reset period results
    if 'result' not in game or not isinstance(game['result'], dict):
        game['result'] = {p: {"home": 0, "away": 0} for p in PERIODS}
    else:
        for p in PERIODS:
            game['result'][p] = {"home": 0, "away": 0}
    
    # Find and update game by ID
    for i, game_item in enumerate(games):
        if game_item.get('id') == game_id:
            games[i] = game
            break
    
    # Recalculate game scores after reset
    recalculate_game_scores(game)
    save_games(games)
    
    if request.args.get('edit') == '1':
        return redirect(url_for('game.game_details', game_id=game_id, edit=1))
    return redirect(url_for('game.game_details', game_id=game_id))


@game_bp.route('/delete_game/<int:game_id>', methods=['POST'])
def delete_game(game_id):
    game = find_game_by_id(load_games(), game_id)
    if not game:
        return "Game not found", 404
    delete_game_by_id(game_id)
    return redirect(url_for('game.index'))


@game_bp.route('/set_period/<int:game_id>/<period>')
def set_period(game_id, period):
    games = load_games()
    game = find_game_by_id(games, game_id)
    if not game:
        return "Game not found", 404
    
    if period not in PERIODS:
        return f"Invalid period '{period}'", 400

    game['current_period'] = period
    # Find and update game by ID
    for i, game_item in enumerate(games):
        if game_item.get('id') == game_id:
            games[i] = game
            break
    save_games(games)
    return redirect(url_for('game.game_details', game_id=game_id))


@game_bp.route('/game/<int:game_id>/edit_json', methods=['GET', 'POST'])
def edit_game_json(game_id):
    games = load_games()
    game = find_game_by_id(games, game_id)
    if not game:
        return "Game not found", 404
    
    if request.method == 'POST':
        try:
            # Parse the JSON from the form
            json_data = request.form.get('json_data', '{}')
            updated_game = json.loads(json_data)
            
            # Preserve the game ID
            updated_game['id'] = game_id
            
            # Update the game in the games list
            for i, game_item in enumerate(games):
                if game_item.get('id') == game_id:
                    games[i] = updated_game
                    break
            
            save_games(games)
            return redirect(url_for('game.game_details', game_id=game_id))
        except json.JSONDecodeError as e:
            error_message = f"Invalid JSON: {str(e)}"
            return render_template(
                'edit_game_json.html',
                game=game,
                game_id=game_id,
                json_data=request.form.get('json_data', ''),
                error=error_message
            )
    
    # GET request - show the JSON editor
    json_data = json.dumps(game, indent=2, ensure_ascii=False)
    return render_template(
        'edit_game_json.html',
        game=game,
        game_id=game_id,
        json_data=json_data
    )


def _lineup_context(game_id):
    """Shared helper: load game + roster for lineup views."""
    games = load_games()
    game = find_game_by_id(games, game_id)
    if not game:
        return None, None, None
    roster = []
    if game.get('team'):
        season = game.get('season', '')
        roster = load_roster(game['team'], season) if season else load_roster(game['team'])
    player_map = {}
    for player in roster:
        key = f"{player['number']} - {player['surname']} {player['name']}"
        player_map[key] = player
    return game, roster, player_map


@game_bp.route('/game/<int:game_id>/lineup')
def view_game_lineup(game_id):
    game, roster, player_map = _lineup_context(game_id)
    if game is None:
        return "Game not found", 404
    return render_template('game_lineup.html', game=game, roster=roster, player_map=player_map)


@game_bp.route('/game/<int:game_id>/lineup/eink')
def view_game_lineup_eink(game_id):
    """E-ink friendly paginated lineup view."""
    game, roster, player_map = _lineup_context(game_id)
    if game is None:
        return "Game not found", 404
    return render_template('game_lineup_eink.html', game=game, roster=roster, player_map=player_map)


# ── Device profiles for e-reader PDF export ────────────────────────────────
# Page dimensions are the physical screen area.
# Tolino Shine (6"): 1448×1072 px @ 300 ppi → ~122.7×90.7 mm
# Xteink X4 (4.3"): 800×600 px portrait @ ~233 ppi → ~87×65 mm
_EINK_DEVICES = {
    'tolino': dict(
        label='Tolino Shine',
        # ── PDF (mm) ────────────────────────────────────────────────────────
        page_w=90, page_h=122, margin=7,
        title_fs=20, vs_fs=13, section_fs=16,
        meta_fs=12, player_fs=14,
        toc_title_fs=13, toc_item_fs=12,
        num_w=14, meta_label_w=18,
        cell_pad=5, hr_thick=1.5,
        spec_spacer=5,
        # ── EPUB fixed-layout (CSS px) ──────────────────────────────────────
        epub_vw=600, epub_vh=800,
        epub_title_fs=30, epub_vs_fs=18, epub_section_fs=24,
        epub_meta_fs=15, epub_player_fs=18, epub_toc_fs=15, epub_pad=10,
    ),
    'xteink': dict(
        label='Xteink X4',
        # ── PDF (mm) ────────────────────────────────────────────────────────
        page_w=65, page_h=87, margin=5,
        title_fs=14, vs_fs=9, section_fs=11,
        meta_fs=9, player_fs=10,
        toc_title_fs=9, toc_item_fs=9,
        num_w=10, meta_label_w=13,
        cell_pad=3, hr_thick=1.0,
        spec_spacer=3,
        # ── EPUB fixed-layout (CSS px) ──────────────────────────────────────
        epub_vw=400, epub_vh=533,
        epub_title_fs=20, epub_vs_fs=12, epub_section_fs=16,
        epub_meta_fs=11, epub_player_fs=12, epub_toc_fs=11, epub_pad=6,
    ),
}


@game_bp.route('/game/<int:game_id>/lineup/pdf')
def download_lineup_pdf(game_id):
    """Generate an e-reader PDF of the lineup.  ?device=tolino|xteink"""
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
        HRFlowable,
    )
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER

    device_key = request.args.get('device', 'tolino')
    p = _EINK_DEVICES.get(device_key, _EINK_DEVICES['tolino'])

    game, roster, player_map = _lineup_context(game_id)
    if game is None:
        return "Game not found", 404

    # ── Page geometry ────────────────────────────────────────────────────────
    PAGE_W = p['page_w'] * mm
    PAGE_H = p['page_h'] * mm
    MARGIN = p['margin'] * mm
    COL_W  = PAGE_W - 2 * MARGIN
    NUM_W  = p['num_w'] * mm
    PAD    = p['cell_pad']

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=(PAGE_W, PAGE_H),
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
    )

    # ── Styles ───────────────────────────────────────────────────────────────
    def _ps(name, font='Helvetica', size=10, align=None, **kw):
        kwargs = dict(fontName=font, fontSize=size, leading=round(size * 1.25))
        if align is not None:
            kwargs['alignment'] = align
        kwargs.update(kw)
        return ParagraphStyle(name, **kwargs)

    title_style     = _ps('T', 'Helvetica-Bold', p['title_fs'],    TA_CENTER,
                          spaceAfter=2 * mm)
    vs_style        = _ps('V', 'Helvetica',      p['vs_fs'],       TA_CENTER,
                          spaceAfter=2 * mm)
    section_style   = _ps('S', 'Helvetica-Bold', p['section_fs'],
                          spaceAfter=2 * mm, spaceBefore=1 * mm)
    meta_lbl_style  = _ps('ML', 'Helvetica-Bold', p['meta_fs'])
    meta_val_style  = _ps('MV', 'Helvetica',       p['meta_fs'])
    player_style    = _ps('PV', 'Helvetica',        p['player_fs'])
    player_bold     = _ps('PB', 'Helvetica-Bold',   p['player_fs'])
    toc_title_style = _ps('TT', 'Helvetica-Bold', p['toc_title_fs'],
                          spaceBefore=2 * mm, spaceAfter=1 * mm)
    toc_item_style  = _ps('TI', 'Helvetica',      p['toc_item_fs'])

    def hr():
        return HRFlowable(width='100%', thickness=p['hr_thick'],
                          color=colors.black, spaceAfter=1.5 * mm, spaceBefore=0)

    def fmt_player(s):
        parts = s.split(' - ', 1)
        num   = parts[0].strip() if len(parts) > 1 else ''
        full  = parts[1].strip() if len(parts) > 1 else s.strip()
        words = full.split()
        name  = (words[0] + ' ' + words[1][0] + '.') if len(words) > 1 else full
        return num, name

    def player_table(players):
        rows = [[Paragraph(num, player_bold), Paragraph(nm, player_style)]
                for num, nm in (fmt_player(pl) for pl in players)]
        if not rows:
            return None
        tbl = Table(rows, colWidths=[NUM_W, COL_W - NUM_W])
        tbl.setStyle(TableStyle([
            ('FONTSIZE',      (0, 0), (-1, -1), p['player_fs']),
            ('ALIGN',         (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN',         (1, 0), (1, -1), 'LEFT'),
            ('TOPPADDING',    (0, 0), (-1, -1), PAD),
            ('BOTTOMPADDING', (0, 0), (-1, -1), PAD),
            ('LINEBELOW',     (0, 0), (-1, -2), 0.5, colors.black),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        return tbl

    # ── Content helpers ──────────────────────────────────────────────────────
    SPEC_KEYS = [
        ('pp1', 'PP1'), ('pp2', 'PP2'),
        ('bp1', 'BP1'), ('bp2', 'BP2'),
        ('6vs5', '6 vs 5'), ('stress_line', 'Stress Line'),
    ]
    spec    = [(label, game[k]) for k, label in SPEC_KEYS if game.get(k)]
    goalies = game.get('goalies', [])
    lines   = [l for l in game.get('lines', []) if l]

    toc_entries = ['Game Info']
    if goalies:
        toc_entries.append('Goalies')
    for i in range(len(lines)):
        toc_entries.append(f'Line {i + 1}')
    for i in range(0, len(spec), 2):
        toc_entries.append(' / '.join(lbl for lbl, _ in spec[i:i + 2]))

    story = []

    # ── Cover ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(game.get('home_team', ''), title_style))
    story.append(Paragraph('vs', vs_style))
    story.append(Paragraph(game.get('away_team', ''), title_style))
    story.append(hr())

    meta_rows = []
    for key, label in [('date', 'Date'), ('team', 'Team'),
                       ('season', 'Season')]:
        if game.get(key):
            meta_rows.append([Paragraph(f'<b>{label}</b>', meta_lbl_style),
                              Paragraph(game[key], meta_val_style)])
    refs = ', '.join(r for r in [game.get('referee1', ''),
                                  game.get('referee2', '')] if r)
    if refs:
        meta_rows.append([Paragraph('<b>Refs</b>', meta_lbl_style),
                          Paragraph(refs, meta_val_style)])
    if meta_rows:
        lw = p['meta_label_w'] * mm
        mt = Table(meta_rows, colWidths=[lw, COL_W - lw])
        mt.setStyle(TableStyle([
            ('TOPPADDING',    (0, 0), (-1, -1), PAD),
            ('BOTTOMPADDING', (0, 0), (-1, -1), PAD),
            ('LINEBELOW',     (0, 0), (-1, -1), 0.4, colors.grey),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(mt)
        story.append(Spacer(1, 2 * mm))

    story.append(Paragraph('Contents', toc_title_style))
    for idx, entry in enumerate(toc_entries):
        story.append(Paragraph(f'{idx + 1}.  {entry}', toc_item_style))

    # ── Goalies ──────────────────────────────────────────────────────────────
    if goalies:
        story.append(PageBreak())
        story.append(Paragraph('Goalies', section_style))
        story.append(hr())
        tbl = player_table(goalies)
        if tbl:
            story.append(tbl)

    # ── Lines (one per page) ─────────────────────────────────────────────────
    for i, line in enumerate(lines):
        story.append(PageBreak())
        story.append(Paragraph(f'Line {i + 1}', section_style))
        story.append(hr())
        tbl = player_table(line)
        if tbl:
            story.append(tbl)

    # ── Special formations (2 per page) ──────────────────────────────────────
    for idx in range(0, len(spec), 2):
        story.append(PageBreak())
        for label, players in spec[idx:idx + 2]:
            story.append(Paragraph(label, section_style))
            story.append(hr())
            tbl = player_table(players)
            if tbl:
                story.append(tbl)
            story.append(Spacer(1, p['spec_spacer'] * mm))

    doc.build(story)
    buf.seek(0)
    safe_home = ''.join(c for c in game.get('home_team', 'home')
                        if c.isalnum() or c in '-_')
    safe_away = ''.join(c for c in game.get('away_team', 'away')
                        if c.isalnum() or c in '-_')
    filename = f"lineup_{safe_home}_vs_{safe_away}_{device_key}.pdf"
    return send_file(buf, mimetype='application/pdf',
                     as_attachment=True, download_name=filename)


@game_bp.route('/game/<int:game_id>/lineup/epub')
def download_lineup_epub(game_id):
    """Generate a fixed-layout EPUB of the lineup.  ?device=tolino|xteink"""
    import zipfile
    import html as _h

    device_key = request.args.get('device', 'tolino')
    p = _EINK_DEVICES.get(device_key, _EINK_DEVICES['tolino'])

    game, roster, player_map = _lineup_context(game_id)
    if game is None:
        return "Game not found", 404

    VW  = p['epub_vw']
    VH  = p['epub_vh']
    PAD = p['epub_pad']

    def e(s):
        return _h.escape(str(s) if s else '')

    def fmt_player(s):
        parts = s.split(' - ', 1)
        num   = parts[0].strip() if len(parts) > 1 else ''
        full  = parts[1].strip() if len(parts) > 1 else s.strip()
        words = full.split()
        name  = (words[0] + ' ' + words[1][0] + '.') if len(words) > 1 else full
        return num, name

    def players_html(players):
        if not players:
            return ''
        rows = ''.join(
            f'<div class="prow">'
            f'<span class="num">{e(n)}</span>'
            f'<span class="name">{e(nm)}</span>'
            f'</div>'
            for n, nm in (fmt_player(pl) for pl in players)
        )
        return f'<div class="players">{rows}</div>'

    def make_page(body_html, title=''):
        return (
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<html xmlns="http://www.w3.org/1999/xhtml" '
            f'xmlns:epub="http://www.idpf.org/2007/ops">\n'
            f'<head>\n'
            f'  <meta charset="UTF-8"/>\n'
            f'  <meta name="viewport" content="width={VW}, height={VH}"/>\n'
            f'  <title>{e(title)}</title>\n'
            f'  <link rel="stylesheet" type="text/css" href="style.css"/>\n'
            f'</head>\n'
            f'<body><div class="page">{body_html}</div></body>\n'
            f'</html>'
        )

    # ── Content helpers ──────────────────────────────────────────────────────
    SPEC_KEYS = [
        ('pp1', 'PP1'), ('pp2', 'PP2'),
        ('bp1', 'BP1'), ('bp2', 'BP2'),
        ('6vs5', '6 vs 5'), ('stress_line', 'Stress Line'),
    ]
    spec    = [(label, game[k]) for k, label in SPEC_KEYS if game.get(k)]
    goalies = game.get('goalies', [])
    lines   = [l for l in game.get('lines', []) if l]

    toc_entries = ['Game Info']
    if goalies:
        toc_entries.append('Goalies')
    for i in range(len(lines)):
        toc_entries.append(f'Line {i + 1}')
    for i in range(0, len(spec), 2):
        toc_entries.append(' / '.join(lbl for lbl, _ in spec[i:i + 2]))

    pages = []   # (page_id, title, xhtml_string)

    # Cover
    meta_rows = ''
    for key, label in [('date', 'Date'), ('team', 'Team'), ('season', 'Season')]:
        if game.get(key):
            meta_rows += (
                f'<div class="mrow">'
                f'<span class="ml">{e(label)}</span>'
                f'<span class="mv">{e(game[key])}</span>'
                f'</div>'
            )
    refs = ', '.join(r for r in [game.get('referee1', ''), game.get('referee2', '')] if r)
    if refs:
        meta_rows += (
            f'<div class="mrow">'
            f'<span class="ml">Refs</span>'
            f'<span class="mv">{e(refs)}</span>'
            f'</div>'
        )
    toc_items = ''.join(f'<li>{e(entry)}</li>' for entry in toc_entries)
    cover_body = (
        f'<h1 class="title">{e(game.get("home_team", ""))}</h1>'
        f'<div class="vs">vs</div>'
        f'<h1 class="title">{e(game.get("away_team", ""))}</h1>'
        f'<hr/>'
        + (f'<div class="meta">{meta_rows}</div>' if meta_rows else '')
        + f'<div class="toc-h">Contents</div><ol class="toc">{toc_items}</ol>'
    )
    game_title = f"{game.get('home_team', '')} vs {game.get('away_team', '')}"
    pages.append(('page_000', 'Cover', make_page(cover_body, game_title)))

    n = 1
    if goalies:
        body = f'<h2 class="section">Goalies</h2><hr/>{players_html(goalies)}'
        pages.append((f'page_{n:03d}', 'Goalies', make_page(body, 'Goalies')))
        n += 1

    for i, line in enumerate(lines):
        t = f'Line {i + 1}'
        body = f'<h2 class="section">{t}</h2><hr/>{players_html(line)}'
        pages.append((f'page_{n:03d}', t, make_page(body, t)))
        n += 1

    for si in range(0, len(spec), 2):
        chunk = spec[si:si + 2]
        t = ' / '.join(lbl for lbl, _ in chunk)
        body = ''.join(
            f'<h2 class="section">{e(lbl)}</h2><hr/>{players_html(pl)}'
            f'<div class="gap"></div>'
            for lbl, pl in chunk
        )
        pages.append((f'page_{n:03d}', t, make_page(body, t)))
        n += 1

    # ── CSS ──────────────────────────────────────────────────────────────────
    tf = p['epub_title_fs']; vsf = p['epub_vs_fs']; sf = p['epub_section_fs']
    mf = p['epub_meta_fs'];  pf  = p['epub_player_fs'];  tf2 = p['epub_toc_fs']
    css = f'''
* {{box-sizing:border-box;margin:0;padding:0;}}
body {{width:{VW}px;height:{VH}px;overflow:hidden;
  font-family:'Courier New',Courier,monospace;background:#fff;color:#000;}}
.page {{width:{VW}px;height:{VH}px;padding:{PAD}px;overflow:hidden;}}
h1.title {{font-size:{tf}px;text-align:center;font-weight:bold;
  line-height:1.2;margin-bottom:{PAD // 2}px;}}
.vs {{font-size:{vsf}px;text-align:center;margin-bottom:{PAD // 2}px;}}
h2.section {{font-size:{sf}px;font-weight:bold;
  margin-bottom:{PAD // 2}px;margin-top:{PAD // 4}px;}}
hr {{border:none;border-top:2px solid #000;margin:{PAD // 2}px 0;}}
.meta {{width:100%;font-size:{mf}px;margin-bottom:{PAD // 2}px;}}
.mrow {{display:-webkit-box;display:flex;padding:{PAD // 2}px 0;
  border-bottom:1px solid #ccc;}}
.ml {{font-weight:bold;width:28%;-webkit-box-flex:0;flex-shrink:0;}}
.mv {{-webkit-box-flex:1;flex:1;}}
.toc-h {{font-size:{tf2}px;font-weight:bold;
  margin-top:{PAD}px;margin-bottom:{PAD // 2}px;}}
ol.toc {{font-size:{tf2}px;padding-left:18px;line-height:1.6;}}
.players {{width:100%;font-size:{pf}px;}}
.prow {{display:-webkit-box;display:flex;padding:{PAD // 2}px 0;
  border-bottom:1px solid #000;}}
.prow:last-child {{border-bottom:none;}}
.num {{font-weight:bold;text-align:right;width:15%;
  -webkit-box-flex:0;flex-shrink:0;padding-right:6px;}}
.name {{-webkit-box-flex:1;flex:1;}}
.gap {{height:{PAD * 2}px;}}
'''

    # ── EPUB XML ─────────────────────────────────────────────────────────────
    container_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
        '<rootfiles>'
        '<rootfile full-path="OEBPS/content.opf"'
        ' media-type="application/oebps-package+xml"/>'
        '</rootfiles></container>'
    )

    manifest_pages = '\n'.join(
        f'    <item id="{pid}" href="{pid}.xhtml"'
        f' media-type="application/xhtml+xml"/>'
        for pid, _, _ in pages
    )
    spine_items = '\n'.join(
        f'    <itemref idref="{pid}"'
        f' properties="rendition:page-spread-center"/>'
        for pid, _, _ in pages
    )
    ht = e(game.get('home_team', ''))
    at = e(game.get('away_team', ''))
    opf = (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<package xmlns="http://www.idpf.org/2007/opf"'
        f' xmlns:dc="http://purl.org/dc/elements/1.1/"'
        f' version="3.0" unique-identifier="uid">'
        f'<metadata>'
        f'<dc:identifier id="uid">lineup-{game_id}-{device_key}</dc:identifier>'
        f'<dc:title>{ht} vs {at}</dc:title>'
        f'<dc:language>en</dc:language>'
        f'<meta property="rendition:layout">pre-paginated</meta>'
        f'<meta property="rendition:spread">none</meta>'
        f'<meta property="rendition:viewport">width={VW}, height={VH}</meta>'
        f'</metadata>'
        f'<manifest>'
        f'<item id="nav" href="nav.xhtml"'
        f' media-type="application/xhtml+xml" properties="nav"/>'
        f'<item id="style" href="style.css" media-type="text/css"/>'
        f'{manifest_pages}'
        f'</manifest>'
        f'<spine>{spine_items}</spine>'
        f'</package>'
    )

    nav_items = '\n'.join(
        f'  <li><a href="{pid}.xhtml">{e(ptitle)}</a></li>'
        for pid, ptitle, _ in pages
    )
    nav = (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<!DOCTYPE html>'
        f'<html xmlns="http://www.w3.org/1999/xhtml"'
        f' xmlns:epub="http://www.idpf.org/2007/ops">'
        f'<head><meta charset="UTF-8"/><title>Navigation</title></head>'
        f'<body><nav epub:type="toc" id="toc"><ol>\n{nav_items}\n</ol></nav></body>'
        f'</html>'
    )

    # ── Build ZIP ─────────────────────────────────────────────────────────────
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        info = zipfile.ZipInfo('mimetype')
        info.compress_type = zipfile.ZIP_STORED
        zf.writestr(info, 'application/epub+zip')
        zf.writestr('META-INF/container.xml', container_xml)
        zf.writestr('OEBPS/content.opf', opf)
        zf.writestr('OEBPS/nav.xhtml', nav)
        zf.writestr('OEBPS/style.css', css)
        for pid, _, xhtml in pages:
            zf.writestr(f'OEBPS/{pid}.xhtml', xhtml)
    buf.seek(0)
    safe_home = ''.join(c for c in game.get('home_team', 'home')
                        if c.isalnum() or c in '-_')
    safe_away = ''.join(c for c in game.get('away_team', 'away')
                        if c.isalnum() or c in '-_')
    filename = f"lineup_{safe_home}_vs_{safe_away}_{device_key}.epub"
    return send_file(buf, mimetype='application/epub+zip',
                     as_attachment=True, download_name=filename)
