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


@game_bp.route('/game/<int:game_id>/lineup/pdf')
def download_lineup_pdf(game_id):
    """Generate and download a compact multi-page A5 PDF of the lineup."""
    from reportlab.lib.pagesizes import A5
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    game, roster, player_map = _lineup_context(game_id)
    if game is None:
        return "Game not found", 404

    buf = io.BytesIO()
    PAGE_W, PAGE_H = A5
    MARGIN = 12 * mm
    doc = SimpleDocTemplate(
        buf,
        pagesize=A5,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=10 * mm, bottomMargin=10 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title', parent=styles['Normal'],
        fontSize=14, fontName='Helvetica-Bold',
        alignment=TA_CENTER, spaceAfter=2 * mm,
    )
    sub_style = ParagraphStyle(
        'Sub', parent=styles['Normal'],
        fontSize=9, alignment=TA_CENTER, spaceAfter=1 * mm,
    )
    section_style = ParagraphStyle(
        'Section', parent=styles['Normal'],
        fontSize=11, fontName='Helvetica-Bold',
        spaceBefore=2 * mm, spaceAfter=1 * mm,
        borderPad=1 * mm,
    )
    body_style = ParagraphStyle(
        'Body', parent=styles['Normal'],
        fontSize=10, leading=14,
    )

    def player_display(player_string):
        """Return '#NN  Surname F.' string."""
        parts = player_string.split(' - ', 1)
        num = parts[0].strip() if len(parts) > 1 else ''
        full = parts[1].strip() if len(parts) > 1 else player_string.strip()
        words = full.split()
        if len(words) > 1:
            name_fmt = words[0] + ' ' + words[1][0] + '.'
        else:
            name_fmt = full
        return (num, name_fmt)

    def player_table(players, col_width):
        """Build a ReportLab Table for a list of player strings."""
        rows = []
        for p in players:
            num, name = player_display(p)
            rows.append([num, name])
        if not rows:
            return None
        tbl = Table(rows, colWidths=[10 * mm, col_width - 10 * mm])
        tbl.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('LINEBELOW', (0, 0), (-1, -2), 0.3, colors.lightgrey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        return tbl

    col_w = PAGE_W - 2 * MARGIN
    story = []

    # ── Cover page ─────────────────────────────────────────────────────────
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph(game.get('home_team', ''), title_style))
    story.append(Paragraph('vs', sub_style))
    story.append(Paragraph(game.get('away_team', ''), title_style))
    story.append(Spacer(1, 4 * mm))

    meta_rows = []
    if game.get('date'):
        meta_rows.append(['Date', game['date']])
    if game.get('team'):
        meta_rows.append(['Team', game['team']])
    if game.get('season'):
        meta_rows.append(['Season', game['season']])
    refs = ', '.join(r for r in [game.get('referee1', ''), game.get('referee2', '')] if r)
    if refs:
        meta_rows.append(['Referees', refs])

    if meta_rows:
        meta_tbl = Table(meta_rows, colWidths=[22 * mm, col_w - 22 * mm])
        meta_tbl.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('LINEBELOW', (0, 0), (-1, -1), 0.3, colors.lightgrey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(meta_tbl)

    # ── Goalies page ────────────────────────────────────────────────────────
    goalies = game.get('goalies', [])
    if goalies:
        story.append(PageBreak())
        story.append(Paragraph('Goalies', section_style))
        tbl = player_table(goalies, col_w)
        if tbl:
            story.append(tbl)

    # ── One page per line ───────────────────────────────────────────────────
    for i, line in enumerate(game.get('lines', [])):
        if not line:
            continue
        story.append(PageBreak())
        story.append(Paragraph(f'Line {i + 1}', section_style))
        tbl = player_table(line, col_w)
        if tbl:
            story.append(tbl)

    # ── Special formations (2 per page) ────────────────────────────────────
    SPEC_KEYS = [
        ('pp1', 'PP1'), ('pp2', 'PP2'),
        ('bp1', 'BP1'), ('bp2', 'BP2'),
        ('6vs5', '6 vs 5'), ('stress_line', 'Stress Line'),
    ]
    spec = [(label, game[key]) for key, label in SPEC_KEYS if game.get(key)]
    for idx in range(0, len(spec), 2):
        chunk = spec[idx:idx + 2]
        story.append(PageBreak())
        for label, players in chunk:
            story.append(Paragraph(label, section_style))
            tbl = player_table(players, col_w)
            if tbl:
                story.append(tbl)
            story.append(Spacer(1, 4 * mm))

    doc.build(story)
    buf.seek(0)
    safe_home = "".join(c for c in game.get('home_team', 'home') if c.isalnum() or c in '-_')
    safe_away = "".join(c for c in game.get('away_team', 'away') if c.isalnum() or c in '-_')
    filename = f"lineup_{safe_home}_vs_{safe_away}.pdf"
    return send_file(buf, mimetype='application/pdf',
                     as_attachment=True, download_name=filename)
