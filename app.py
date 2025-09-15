import os
import json
from flask import Flask, request, render_template, redirect, url_for, session
from collections import defaultdict
from datetime import datetime
REQUIRED_PIN = os.environ.get('FLOORBALL_PIN', '1717')

GAMES_FILE = 'gamesFiles/games.json'

# Ensure games.json exists before anything else
if not os.path.exists(GAMES_FILE):
    with open(GAMES_FILE, 'w') as f:
        json.dump([], f)

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev_secret')

PERIODS = ["1", "2", "3", "OT"]

def load_games():
    try:
        with open(GAMES_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return []

def save_games(games):
    with open(GAMES_FILE, 'w') as f:
        json.dump(games, f, indent=2)

def ensure_game_ids(games):
    changed = False
    # Find current max id
    max_id = -1
    for i, g in enumerate(games):
        if 'id' in g:
            try:
                max_id = max(max_id, int(g['id']))
            except Exception:
                pass
        else:
            max_id = max(max_id, i)
    for i, g in enumerate(games):
        if 'id' not in g:
            max_id += 1
            g['id'] = max_id
            changed = True
    return changed

# Home page: show latest game and create/switch options
@app.route('/', methods=['GET', 'POST'])
def index():
    if not session.get('authenticated'):
        if request.method == 'POST':
            pin = request.form.get('pin')
            if pin == REQUIRED_PIN:
                session['authenticated'] = True
                return redirect(url_for('index'))
            else:
                return render_template('pin.html', error='Incorrect PIN')
        return render_template('pin.html')
    games = load_games()
    if ensure_game_ids(games):
        save_games(games)
    # Sort games by date (descending, newest first), then by creation order (id)
    def game_sort_key(g):
        date_str = g.get('date')
        try:
            date_val = datetime.strptime(date_str, '%Y-%m-%d') if date_str else datetime.min
        except Exception:
            date_val = datetime.min
        return (date_val, -games.index(g))
    games_sorted = sorted(games, key=game_sort_key, reverse=True)
    selected_team = request.args.get('team')
    if selected_team:
        filtered_games = [g for g in games_sorted if g.get('team') == selected_team]
    else:
        filtered_games = games_sorted
    latest_game_id = None
    if filtered_games:
        # Find the latest game for the selected team (or all games)
        latest_game_id = games.index(filtered_games[0])
    return render_template('index.html', games=games_sorted, latest_game_id=latest_game_id, selected_team=selected_team)

# Add a before_request to protect all routes except static and pin
@app.before_request
def require_login():
    allowed_routes = ['index', 'static']
    if request.endpoint not in allowed_routes and not session.get('authenticated'):
        return redirect(url_for('index'))

# Game details with plus/minus, goal, assist actions
@app.route('/game/<int:game_id>')
def game_details(game_id):
    games = load_games()
    if ensure_game_ids(games):
        save_games(games)
    if game_id < 0 or game_id >= len(games):
        return "Game not found", 404
    game = games[game_id]
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
    for stat in ['plusminus', 'goals', 'assists', 'goalie_plusminus', 'saves', 'goals_conceded', 'opponent_goalie_saves', 'opponent_goalie_goals_conceded']:
        if stat not in game or not isinstance(game[stat], dict):
            game[stat] = {}
            changed = True
    if changed:
        games[game_id] = game
        save_games(games)
    # --- End error management ---
    return render_template('game_details.html', game=game, game_id=game_id, games=games)

# Modify game page
@app.route('/modify_game/<int:game_id>', methods=['GET', 'POST'])
def modify_game(game_id):
    games = load_games()
    if game_id < 0 or game_id >= len(games):
        return "Game not found", 404
    game = games[game_id]
    if request.method == 'POST':
        team = request.form.get('team')
        home_team = request.form.get('home_team')
        away_team = request.form.get('away_team')
        date = request.form.get('date')
        lines = []
        for i in range(1, 5):
            line_players = request.form.get(f'line{i}', '')
            lines.append([p.strip() for p in line_players.split(',') if p.strip()])
        goalies = []
        for i in range(1, 3):
            goalie = request.form.get(f'goalie{i}', '')
            if goalie.strip():
                goalies.append(goalie.strip())
        
        # Check if opponent goalie tracking should be enabled (backward compatibility)
        # For existing games, enable if they had opponent stats or if explicitly requested
        has_opponent_stats = ('opponent_goalie_saves' in game and game['opponent_goalie_saves']) or \
                           ('opponent_goalie_goals_conceded' in game and game['opponent_goalie_goals_conceded'])
        enable_opponent_goalie = request.form.get('enable_opponent_goalie') == 'on' or has_opponent_stats
        
        game['team'] = team
        game['home_team'] = home_team
        game['away_team'] = away_team
        game['date'] = date
        game['lines'] = lines
        game['goalies'] = goalies
        game['opponent_goalie_enabled'] = enable_opponent_goalie
        if 'result' not in game:
            game['result'] = {p: {"home": 0, "away": 0} for p in PERIODS}
        if 'current_period' not in game:
            game['current_period'] = '1'
        games[game_id] = game
        save_games(games)
        return redirect(url_for('game_details', game_id=game_id))
    return render_template('game_form.html', game=game, modify=True, game_id=game_id)

# Plus/minus, goal, assist action for a player
@app.route('/action/<int:game_id>/<player>')
def player_action(game_id, player):
    action = request.args.get('action')
    games = load_games()
    if game_id < 0 or game_id >= len(games):
        return "Game not found", 404
    game = games[game_id]
    # Track stats in dicts on the game object
    if 'plusminus' not in game:
        game['plusminus'] = {}
    if 'goals' not in game:
        game['goals'] = {}
    if 'assists' not in game:
        game['assists'] = {}
    if player not in game['plusminus']:
        game['plusminus'][player] = 0
    if player not in game['goals']:
        game['goals'][player] = 0
    if player not in game['assists']:
        game['assists'][player] = 0
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
        # Home team goal in current period
        game['result'][period]['home'] += 1
        # Auto-increment opponent goalie goals conceded (if opponent goalie tracking is enabled)
        if game.get('opponent_goalie_enabled', False):
            if 'opponent_goalie_goals_conceded' not in game:
                game['opponent_goalie_goals_conceded'] = {}
            # Always use "Opponent Goalie" as the key
            if "Opponent Goalie" not in game['opponent_goalie_goals_conceded']:
                game['opponent_goalie_goals_conceded']["Opponent Goalie"] = 0
            game['opponent_goalie_goals_conceded']["Opponent Goalie"] += 1
    elif action == 'goal_minus':
        if game['goals'][player] > 0:
            game['goals'][player] -= 1
            if game['result'][period]['home'] > 0:
                game['result'][period]['home'] -= 1
            # Auto-decrement opponent goalie goals conceded (if opponent goalie tracking is enabled)
            if game.get('opponent_goalie_enabled', False):
                if 'opponent_goalie_goals_conceded' not in game:
                    game['opponent_goalie_goals_conceded'] = {}
                # Always use "Opponent Goalie" as the key
                if "Opponent Goalie" in game['opponent_goalie_goals_conceded'] and game['opponent_goalie_goals_conceded']["Opponent Goalie"] > 0:
                    game['opponent_goalie_goals_conceded']["Opponent Goalie"] -= 1
    elif action == 'assist':
        game['assists'][player] += 1
    elif action == 'assist_minus':
        if game['assists'][player] > 0:
            game['assists'][player] -= 1
    games[game_id] = game
    save_games(games)
    # Preserve edit mode if present
    if request.args.get('edit') == '1':
        return redirect(url_for('game_details', game_id=game_id, edit=1))
    return redirect(url_for('game_details', game_id=game_id))

# Plus/minus, goal, assist action for a whole line
@app.route('/action_line/<int:game_id>/<int:line_idx>')
def line_action(game_id, line_idx):
    action = request.args.get('action')
    games = load_games()
    if game_id < 0 or game_id >= len(games):
        return "Game not found", 404
    game = games[game_id]
    if line_idx < 0 or line_idx >= len(game['lines']):
        return "Line not found", 404
    if 'plusminus' not in game:
        game['plusminus'] = {}
    if 'goals' not in game:
        game['goals'] = {}
    if 'assists' not in game:
        game['assists'] = {}
    for player in game['lines'][line_idx]:
        if player not in game['plusminus']:
            game['plusminus'][player] = 0
        if player not in game['goals']:
            game['goals'][player] = 0
        if player not in game['assists']:
            game['assists'][player] = 0
        if action == 'plus':
            game['plusminus'][player] += 1
        elif action == 'minus':
            game['plusminus'][player] -= 1
        elif action == 'goal':
            game['goals'][player] += 1
        elif action == 'assist':
            game['assists'][player] += 1
    games[game_id] = game
    save_games(games)
    if request.args.get('edit') == '1':
        return redirect(url_for('game_details', game_id=game_id, edit=1))
    return redirect(url_for('game_details', game_id=game_id))

# Game creation form
@app.route('/create_game', methods=['GET', 'POST'])
def create_game():
    if request.method == 'POST':
        team = request.form.get('team')
        home_team = request.form.get('home_team')
        away_team = request.form.get('away_team')
        date = request.form.get('date')
        lines = []
        for i in range(1, 5):
            line_players = request.form.get(f'line{i}', '')
            lines.append([p.strip() for p in line_players.split(',') if p.strip()])
        goalies = []
        for i in range(1, 3):
            goalie = request.form.get(f'goalie{i}', '')
            if goalie.strip():
                goalies.append(goalie.strip())
        
        # Check if opponent goalie tracking should be enabled
        enable_opponent_goalie = request.form.get('enable_opponent_goalie') == 'on'
        
        # Initialize period results
        result = {p: {"home": 0, "away": 0} for p in PERIODS}
        games = load_games()
        # Assign a unique id (max id + 1)
        if games:
            max_id = max([g.get('id', i) for i, g in enumerate(games)])
            new_id = max_id + 1
        else:
            new_id = 0
        game = {
            'id': new_id,
            'team': team,
            'home_team': home_team,
            'away_team': away_team,
            'date': date,
            'lines': lines,
            'goalies': goalies,
            'opponent_goalie_enabled': enable_opponent_goalie,
            'result': result,
            'current_period': '1',
        }
        games.append(game)
        save_games(games)
        return redirect(url_for('index'))
    return render_template('game_form.html')

# Goalie stat actions: plus, minus, save, goal_conceded
@app.route('/action_goalie/<int:game_id>/<goalie>')
def goalie_action(game_id, goalie):
    action = request.args.get('action')
    games = load_games()
    if game_id < 0 or game_id >= len(games):
        return "Game not found", 404
    game = games[game_id]
    # Initialize goalie stats if not present
    if 'goalie_plusminus' not in game:
        game['goalie_plusminus'] = {}
    if 'saves' not in game:
        game['saves'] = {}
    if 'goals_conceded' not in game:
        game['goals_conceded'] = {}
    if 'assists' not in game:
        game['assists'] = {}
    if goalie not in game['goalie_plusminus']:
        game['goalie_plusminus'][goalie] = 0
    if goalie not in game['saves']:
        game['saves'][goalie] = 0
    if goalie not in game['goals_conceded']:
        game['goals_conceded'][goalie] = 0
    if goalie not in game['assists']:
        game['assists'][goalie] = 0
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
    games[game_id] = game
    save_games(games)
    if request.args.get('edit') == '1':
        return redirect(url_for('game_details', game_id=game_id, edit=1))
    return redirect(url_for('game_details', game_id=game_id))

# Opponent Goalie stat actions: save, goal_conceded
@app.route('/action_opponent_goalie/<int:game_id>')
def opponent_goalie_action(game_id):
    action = request.args.get('action')
    games = load_games()
    if game_id < 0 or game_id >= len(games):
        return "Game not found", 404
    game = games[game_id]
    
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
    games[game_id] = game
    save_games(games)
    if request.args.get('edit') == '1':
        return redirect(url_for('game_details', game_id=game_id, edit=1))
    return redirect(url_for('game_details', game_id=game_id))

# Route to reset all stats for a game
@app.route('/reset_game/<int:game_id>')
def reset_game(game_id):
    games = load_games()
    if game_id < 0 or game_id >= len(games):
        return "Game not found", 404
    game = games[game_id]
    # Reset player stats
    for stat in ['plusminus', 'goals', 'assists']:
        if stat not in game:
            game[stat] = {}
        for line in game.get('lines', []):
            for player in line:
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
    games[game_id] = game
    save_games(games)
    if request.args.get('edit') == '1':
        return redirect(url_for('game_details', game_id=game_id, edit=1))
    return redirect(url_for('game_details', game_id=game_id))

# Delete game route
@app.route('/delete_game/<int:game_id>', methods=['POST'])
def delete_game(game_id):
    games = load_games()
    if game_id < 0 or game_id >= len(games):
        return "Game not found", 404
    games.pop(game_id)
    save_games(games)
    return redirect(url_for('index'))

# Stats page: filter by category, collect all players, order games by date, compute per-game and total stats
@app.route('/stats')
def stats():
    games = load_games()
    # Data checking and defaulting for missing fields
    changed = False
    for g in games:
        for stat in ['plusminus', 'goals', 'assists', 'saves', 'goals_conceded']:
            if stat not in g or not isinstance(g[stat], dict):
                g[stat] = {}
                changed = True
        if 'lines' not in g or not isinstance(g['lines'], list):
            g['lines'] = []
            changed = True
        if 'goalies' not in g or not isinstance(g['goalies'], list):
            g['goalies'] = []
            changed = True
    if changed:
        save_games(games)
    # Sort games by date (newest first)
    def game_sort_key(g):
        date_str = g.get('date')
        try:
            date_val = datetime.strptime(date_str, '%Y-%m-%d') if date_str else datetime.min
        except Exception:
            date_val = datetime.min
        return (date_val, -games.index(g))
    games_sorted = sorted(games, key=game_sort_key, reverse=True)
    # Filter by team/category
    teams = sorted(set(g.get('team', '') for g in games if g.get('team')))
    selected_team = request.args.get('team')
    if selected_team:
        games_sorted = [g for g in games_sorted if g.get('team') == selected_team]
    # Collect all players
    player_set = set()
    for g in games_sorted:
        for line in g.get('lines', []):
            player_set.update(line)
    players = sorted(player_set)
    # Prepare per-player totals
    player_totals = {p: {'plusminus': 0, 'goals': 0, 'assists': 0} for p in players}
    for g in games_sorted:
        for p in players:
            player_totals[p]['plusminus'] += g.get('plusminus', {}).get(p, 0)
            player_totals[p]['goals'] += g.get('goals', {}).get(p, 0)
            player_totals[p]['assists'] += g.get('assists', {}).get(p, 0)
    
    # Collect all goalies
    goalie_set = set()
    for g in games_sorted:
        goalie_set.update(g.get('goalies', []))
    goalies = sorted(goalie_set)
    
    # Prepare goalie save percentages with per-game data
    goalie_data = {}
    for goalie in goalies:
        goalie_data[goalie] = {
            'games': [],
            'total_saves': 0,
            'total_goals_conceded': 0,
            'average_save_percentage': 0
        }
    
    # Collect opponent goalies from games where opponent goalie tracking is enabled
    opponent_goalie_data = {
        'games': [],
        'total_saves': 0,
        'total_goals_conceded': 0,
        'average_save_percentage': 0
    }
    
    # Calculate save percentages for each game
    for g in games_sorted:
        # Add save percentage calculation for each goalie in this game
        g['save_percentages'] = {}
        for goalie in goalies:
            saves = g.get('saves', {}).get(goalie, 0)
            goals_conceded = g.get('goals_conceded', {}).get(goalie, 0)
            total_shots = saves + goals_conceded
            
            if total_shots > 0:
                save_percentage = (saves / total_shots) * 100
                g['save_percentages'][goalie] = save_percentage
                goalie_data[goalie]['games'].append(save_percentage)
                goalie_data[goalie]['total_saves'] += saves
                goalie_data[goalie]['total_goals_conceded'] += goals_conceded
            else:
                g['save_percentages'][goalie] = None
                
        # Handle opponent goalie stats if tracking is enabled for this game
        if g.get('opponent_goalie_enabled', False):
            opponent_saves = g.get('opponent_goalie_saves', {}).get('Opponent Goalie', 0)
            opponent_goals_conceded = g.get('opponent_goalie_goals_conceded', {}).get('Opponent Goalie', 0)
            opponent_total_shots = opponent_saves + opponent_goals_conceded
            
            if opponent_total_shots > 0:
                opponent_save_percentage = (opponent_saves / opponent_total_shots) * 100
                g['opponent_save_percentage'] = opponent_save_percentage
                opponent_goalie_data['games'].append(opponent_save_percentage)
                opponent_goalie_data['total_saves'] += opponent_saves
                opponent_goalie_data['total_goals_conceded'] += opponent_goals_conceded
            else:
                g['opponent_save_percentage'] = None
        else:
            g['opponent_save_percentage'] = None
    
    # Calculate average save percentages
    for goalie in goalies:
        total_saves = goalie_data[goalie]['total_saves']
        total_goals_conceded = goalie_data[goalie]['total_goals_conceded']
        total_shots = total_saves + total_goals_conceded
        
        if total_shots > 0:
            goalie_data[goalie]['average_save_percentage'] = (total_saves / total_shots) * 100
        else:
            goalie_data[goalie]['average_save_percentage'] = None
            
    # Calculate average save percentage for opponent goalie
    opponent_total_saves = opponent_goalie_data['total_saves']
    opponent_total_goals_conceded = opponent_goalie_data['total_goals_conceded']
    opponent_total_shots = opponent_total_saves + opponent_total_goals_conceded
    
    if opponent_total_shots > 0:
        opponent_goalie_data['average_save_percentage'] = (opponent_total_saves / opponent_total_shots) * 100
    else:
        opponent_goalie_data['average_save_percentage'] = None
    
    return render_template('stats.html', games=games_sorted, players=players, player_totals=player_totals, 
                         goalies=goalies, goalie_data=goalie_data, opponent_goalie_data=opponent_goalie_data, 
                         teams=teams, selected_team=selected_team)

# Set period route
@app.route('/set_period/<int:game_id>/<period>')
def set_period(game_id, period):
    games = load_games()
    if game_id < 0 or game_id >= len(games):
        return "Game not found", 404
    game = games[game_id]
    if period not in PERIODS:
        return "Invalid period", 400
    game['current_period'] = period
    games[game_id] = game
    save_games(games)
    # Preserve edit mode if present
    edit = request.args.get('edit')
    if edit == '1':
        return redirect(url_for('game_details', game_id=game_id, edit=1))
    return redirect(url_for('game_details', game_id=game_id))

if __name__ == '__main__':
    # Only enable debug mode if running directly with python app.py
    app.run(debug=True)
# When run with gunicorn or another WSGI server, debug is off by default
