import os
import json
from flask import Flask, request, render_template, redirect, url_for, session, g
from datetime import datetime
REQUIRED_PIN = os.environ.get('FLOORBALL_PIN', '1717')

GAMES_FILE = 'gamesFiles/games.json'

# Ensure games.json exists before anything else
if not os.path.exists(GAMES_FILE):
    with open(GAMES_FILE, 'w') as f:
        json.dump([], f)


app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev_secret')
app.config['DEFAULT_LANG'] = os.environ.get('DEFAULT_LANG', 'en')


# Template helper: format YYYY-MM-DD -> DD.MM.YYYY
def format_date(date_str):
    try:
        if not date_str:
            return date_str
        parts = str(date_str).split('-')
        if len(parts) == 3:
            return f"{parts[2]}.{parts[1]}.{parts[0]}"
    except Exception:
        pass
    return date_str


# Expose helper to Jinja templates
app.jinja_env.globals['format_date'] = format_date


# Language support
LANGUAGES = ['en', 'it']
TRANSLATIONS = {
    'en': {
        'brand': 'Floorball Stats',
        'create_game': 'Create Game',
        'stats': 'Statistics',
        'create_new_game': 'Create New Game',
        'all_teams': 'All Teams',
        'go_to_latest_game': 'Go to Latest Game',
        'stats_btn': 'Stats',
        'title': 'Floorball Stats Tracker',
        'all_games': 'All Games',
        'all_games_for': 'All Games for',
        'view': 'View',
        'no_games': 'No games found. Create a new game to get started!',
        'back_to_home': 'Back to Home',
        'modify_game': 'Modify Game',
        'reset_stats': 'Reset Stats',
        'confirm_reset_title': 'Confirm Reset',
        'confirm_reset_body': 'Are you sure you want to reset all stats for this game?',
        'confirm_reset_cancel': 'Cancel',
        'confirm_reset_confirm': 'Reset',
        'edit_mode': 'Edit Mode',
        'switch_game': 'Switch game',
        'line': 'Line',
        'player': 'Player',
        'plusminus': '+/-',
        'goals': 'Goals',
        'assists': 'Assists',
        'errors': 'Errors',
        'actions': 'Actions',
        'goal': 'Goal',
        'save': 'Save',
        'delete_game': 'Delete Game',
        'cancel': 'Cancel',
        'save_changes': 'Save Changes',
        'enter_access_pin': 'Enter Access PIN',
        'enter': 'Enter',
        'pin_placeholder': 'PIN',
        'stats_overview': 'Stats Overview',
        'category': 'Category:',
        'plus_minus': 'Plus/Minus',
        'goals_assists': 'Goals / Assists',
        'unforced_errors': 'Unforced Errors',
        'goalie_save_percent': 'Goalie Save Percentages',
        'all': 'All',
        'plus_all': '+1 All',
        'minus_all': '-1 All',
        'change': 'Change',
        'lang_en': 'English',
        'lang_it': 'Italiano',
        'incorrect_pin': 'Incorrect PIN',
        'opponent_goalie_not_enabled': 'Opponent goalie tracking not enabled for this game',
        'goalies': 'Goalies',
        'goalie': 'Goalie',
        'opponent_goalie': 'Opponent Goalie',
        'saves': 'Saves',
        'goals_conceded': 'Goals Conceded',
        'save_percent': 'Save %',
        'home_team': 'Home Team',
        'away_team': 'Away Team',
        'date': 'Date',
        'line_players': 'Line {n} Players (comma separated)',
        'goalie_name': 'Goalie {n} Name',
        'track_opponent_goalie': 'Track Opponent Goalie Stats',
        'total': 'Total',
        'average': 'Average',
        'delete_confirm': 'Are you sure you want to delete this game?',
    },
    'it': {
        'brand': 'Floorball Stats',
        'create_game': 'Crea Partita',
        'stats': 'Statistiche',
        'create_new_game': 'Crea nuova partita',
        'all_teams': 'Tutte le squadre',
        'go_to_latest_game': 'Vai all’ultima partita',
        'stats_btn': 'Statistiche',
        'title': 'Floorball Stats Tracker',
        'all_games': 'Tutte le partite',
        'all_games_for': 'Tutte le partite per',
        'view': 'Vedi',
        'no_games': 'Nessuna partita trovata. Crea una nuova partita per iniziare!',
        'back_to_home': 'Torna alla home',
        'modify_game': 'Modifica Partita',
        'reset_stats': 'Resetta statistiche',
        'confirm_reset_title': 'Conferma reset',
        'confirm_reset_body': 'Sei sicuro di voler resettare tutte le statistiche per questa partita?',
        'confirm_reset_cancel': 'Annulla',
        'confirm_reset_confirm': 'Resetta',
        'edit_mode': 'Modalità modifica',
        'switch_game': 'Cambia partita',
        'line': 'Linea',
        'player': 'Giocatore',
        'plusminus': '+/-',
        'goals': 'Gol',
        'assists': 'Assist',
        'errors': 'Errori',
        'actions': 'Azioni',
        'goal': 'Rete',
        'save': 'Salva',
        'delete_game': 'Elimina partita',
        'cancel': 'Annulla',
        'save_changes': 'Salva modifiche',
        'enter_access_pin': 'Inserisci PIN di accesso',
        'enter': 'Accedi',
        'pin_placeholder': 'PIN',
        'stats_overview': 'Panoramica Statistiche',
        'category': 'Categoria:',
        'plus_minus': 'Plus/Minus',
        'goals_assists': 'Gol / Assist',
        'unforced_errors': 'Errori non forzati',
        'goalie_save_percent': 'Percentuali salvataggi portieri',
        'all': 'Tutte',
        'plus_all': '+1 Tutti',
        'minus_all': '-1 Tutti',
        'change': 'Cambia',
        'lang_en': 'Inglese',
        'lang_it': 'Italiano',
        'incorrect_pin': 'PIN non corretto',
        'opponent_goalie_not_enabled': 'Il monitoraggio del portiere avversario non è abilitato per questa partita',
        'goalies': 'Portieri',
        'opponent_goalie': 'Portiere avversario',
        'saves': 'Parate',
        'goals_conceded': 'Gol subiti',
        'save_percent': 'Percentuale parate',
        'home_team': 'Squadra di casa',
        'away_team': 'Squadra ospite',
        'date': 'Data',
        'line_players': 'Linea {n} giocatori (separati da virgola)',
        'goalie_name': 'Nome portiere {n}',
        'track_opponent_goalie': 'Monitora il portiere avversario',
        'total': 'Totale',
        'average': 'Media',
        'delete_confirm': 'Sei sicuro di voler eliminare questa partita?',
    }
}


@app.before_request
def set_language():
    # default language (can be overridden by session)
    default = app.config.get('DEFAULT_LANG', 'en')
    lang = session.get('lang', default)
    if lang not in LANGUAGES:
        lang = default
    g.lang = lang
    g.t = TRANSLATIONS[lang]
    # Expose current game id (if any) to templates in a stable way
    try:
        vid = request.view_args.get('game_id') if request.view_args else None
    except Exception:
        vid = None
    g.current_game_id = vid

# Route to change language


@app.route('/set_language', methods=['POST'])
def set_language_route():
    default = app.config.get('DEFAULT_LANG', 'en')
    lang = request.form.get('lang', default)
    if lang not in LANGUAGES:
        lang = default
    session['lang'] = lang
    # Redirect back to previous page or home
    ref = request.referrer or url_for('index')
    return redirect(ref)


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
    for i, game in enumerate(games):
        if 'id' in game:
            try:
                max_id = max(max_id, int(game['id']))
            except Exception:
                pass
        else:
            max_id = max(max_id, i)
    for i, game in enumerate(games):
        if 'id' not in game:
            max_id += 1
            game['id'] = max_id
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
    # Sort games by date (descending, newest first), then by creation order
    # (id)

    def game_sort_key(game):
        date_str = game.get('date')
        try:
            date_val = datetime.strptime(
                date_str, '%Y-%m-%d') if date_str else datetime.min
        except Exception:
            date_val = datetime.min
        return (date_val, -games.index(game))

    games_sorted = sorted(games, key=game_sort_key, reverse=True)
    selected_team = request.args.get('team')
    if selected_team:
        filtered_games = [
            game for game in games_sorted if game.get('team') == selected_team]
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
        selected_team=selected_team)

# Add a before_request to protect all routes except static and pin


@app.before_request
def require_login():
    allowed_routes = ['index', 'static']
    if request.endpoint not in allowed_routes and not session.get(
            'authenticated'):
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
    # ensure current game id is available to templates (fallback)
    g.current_game_id = game_id
    # --- Error management: ensure all required fields exist and set defaults if missing ---
    changed = False
    # Ensure 'result' exists and has all periods
    if 'result' not in game or not isinstance(game['result'], dict):
        game['result'] = {p: {"home": 0, "away": 0} for p in PERIODS}
        changed = True
    else:
        for p in PERIODS:
            if p not in game['result'] or not isinstance(
                    game['result'][p], dict):
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
    for stat in [
        'plusminus',
        'goals',
        'assists',
        'unforced_errors',
        'goalie_plusminus',
        'saves',
        'goals_conceded',
        'opponent_goalie_saves',
            'opponent_goalie_goals_conceded']:
        if stat not in game or not isinstance(game[stat], dict):
            game[stat] = {}
            changed = True
    if changed:
        games[game_id] = game
        save_games(games)
    # --- End error management ---
    return render_template(
        'game_details.html',
        game=game,
        game_id=game_id,
        games=games)

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
            lines.append([p.strip()
                         for p in line_players.split(',') if p.strip()])
        goalies = []
        for i in range(1, 3):
            goalie = request.form.get(f'goalie{i}', '')
            if goalie.strip():
                goalies.append(goalie.strip())

        # Check if opponent goalie tracking should be enabled (backward compatibility)
        # For existing games, enable if they had opponent stats or if
        # explicitly requested
        has_opponent_stats = (
            'opponent_goalie_saves' in game and game['opponent_goalie_saves']) or (
            'opponent_goalie_goals_conceded' in game and game['opponent_goalie_goals_conceded'])
        enable_opponent_goalie = request.form.get(
            'enable_opponent_goalie') == 'on' or has_opponent_stats

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
    return render_template(
        'game_form.html',
        game=game,
        modify=True,
        game_id=game_id)

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
    if 'unforced_errors' not in game:
        game['unforced_errors'] = {}
    if player not in game['plusminus']:
        game['plusminus'][player] = 0
    if player not in game['goals']:
        game['goals'][player] = 0
    if player not in game['assists']:
        game['assists'][player] = 0
    if player not in game['unforced_errors']:
        game['unforced_errors'][player] = 0
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
        # Auto-increment opponent goalie goals conceded (if opponent goalie
        # tracking is enabled)
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
            # Auto-decrement opponent goalie goals conceded (if opponent goalie
            # tracking is enabled)
            if game.get('opponent_goalie_enabled', False):
                if 'opponent_goalie_goals_conceded' not in game:
                    game['opponent_goalie_goals_conceded'] = {}
                # Always use "Opponent Goalie" as the key
                if "Opponent Goalie" in game['opponent_goalie_goals_conceded'] and game[
                        'opponent_goalie_goals_conceded']["Opponent Goalie"] > 0:
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
            # Always use "Opponent Goalie" as the key
            if "Opponent Goalie" not in game['opponent_goalie_goals_conceded']:
                game['opponent_goalie_goals_conceded']["Opponent Goalie"] = 0
            game['opponent_goalie_goals_conceded']["Opponent Goalie"] += 1
    
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
            lines.append([p.strip()
                         for p in line_players.split(',') if p.strip()])
        goalies = []
        for i in range(1, 3):
            goalie = request.form.get(f'goalie{i}', '')
            if goalie.strip():
                goalies.append(goalie.strip())

        # Check if opponent goalie tracking should be enabled
        enable_opponent_goalie = request.form.get(
            'enable_opponent_goalie') == 'on'

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
        # Home team goal in current period (our goal = opponent goalie goal
        # conceded)
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
    for stat in ['plusminus', 'goals', 'assists', 'unforced_errors']:
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

# Stats page: filter by category, collect all players, order games by
# date, compute per-game and total stats


@app.route('/stats')
def stats():
    games = load_games()
    # Data checking and defaulting for missing fields
    changed = False
    for game in games:
        for stat in [
            'plusminus',
            'goals',
            'assists',
            'unforced_errors',
            'saves',
                'goals_conceded']:
            if stat not in game or not isinstance(game[stat], dict):
                game[stat] = {}
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
            date_val = datetime.strptime(
                date_str, '%Y-%m-%d') if date_str else datetime.min
        except Exception:
            date_val = datetime.min
        return (date_val, -games.index(game))

    games_sorted = sorted(games, key=game_sort_key, reverse=False)
    # Filter by team/category
    teams = sorted(set(game.get('team', '') for game in games if game.get('team')))
    selected_team = request.args.get('team')
    if selected_team:
        games_sorted = [
            game for game in games_sorted if game.get('team') == selected_team]
    # Collect all players
    player_set = set()
    for game in games_sorted:
        for line in game.get('lines', []):
            player_set.update(line)
    players = sorted(player_set)
    # Prepare per-player totals
    player_totals = {p: {'plusminus': 0, 'goals': 0,
                         'assists': 0, 'unforced_errors': 0} for p in players}
    for game in games_sorted:
        for p in players:
            player_totals[p]['plusminus'] += game.get(
                'plusminus', {}).get(p, 0)
            player_totals[p]['goals'] += game.get('goals', {}).get(p, 0)
            player_totals[p]['assists'] += game.get('assists', {}).get(p, 0)
            player_totals[p]['unforced_errors'] += game.get(
                'unforced_errors', {}).get(p, 0)

    # Collect all goalies
    goalie_set = set()
    for game in games_sorted:
        goalie_set.update(game.get('goalies', []))
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

    # Collect opponent goalies from games where opponent goalie tracking is
    # enabled
    opponent_goalie_data = {
        'games': [],
        'total_saves': 0,
        'total_goals_conceded': 0,
        'average_save_percentage': 0
    }

    # Calculate save percentages for each game
    for game in games_sorted:
        # Add save percentage calculation for each goalie in this game
        game['save_percentages'] = {}
        for goalie in goalies:
            saves = game.get('saves', {}).get(goalie, 0)
            goals_conceded = game.get('goals_conceded', {}).get(goalie, 0)
            total_shots = saves + goals_conceded

            if total_shots > 0:
                save_percentage = (saves / total_shots) * 100
                game['save_percentages'][goalie] = save_percentage
                goalie_data[goalie]['games'].append(save_percentage)
                goalie_data[goalie]['total_saves'] += saves
                goalie_data[goalie]['total_goals_conceded'] += goals_conceded
            else:
                game['save_percentages'][goalie] = None

        # Handle opponent goalie stats if tracking is enabled for this game
        if game.get('opponent_goalie_enabled', False):
            opponent_saves = game.get(
                'opponent_goalie_saves', {}).get(
                'Opponent Goalie', 0)
            opponent_goals_conceded = game.get(
                'opponent_goalie_goals_conceded', {}).get(
                'Opponent Goalie', 0)
            opponent_total_shots = opponent_saves + opponent_goals_conceded

            if opponent_total_shots > 0:
                opponent_save_percentage = (
                    opponent_saves / opponent_total_shots) * 100
                game['opponent_save_percentage'] = opponent_save_percentage
                opponent_goalie_data['games'].append(opponent_save_percentage)
                opponent_goalie_data['total_saves'] += opponent_saves
                opponent_goalie_data['total_goals_conceded'] += opponent_goals_conceded
            else:
                game['opponent_save_percentage'] = None
        else:
            game['opponent_save_percentage'] = None

    # Calculate average save percentages
    for goalie in goalies:
        total_saves = goalie_data[goalie]['total_saves']
        total_goals_conceded = goalie_data[goalie]['total_goals_conceded']
        total_shots = total_saves + total_goals_conceded

        if total_shots > 0:
            goalie_data[goalie]['average_save_percentage'] = (
                total_saves / total_shots) * 100
        else:
            goalie_data[goalie]['average_save_percentage'] = None

    # Calculate average save percentage for opponent goalie
    opponent_total_saves = opponent_goalie_data['total_saves']
    opponent_total_goals_conceded = opponent_goalie_data['total_goals_conceded']
    opponent_total_shots = opponent_total_saves + opponent_total_goals_conceded

    if opponent_total_shots > 0:
        opponent_goalie_data['average_save_percentage'] = (
            opponent_total_saves / opponent_total_shots) * 100
    else:
        opponent_goalie_data['average_save_percentage'] = None

    return render_template(
        'stats.html',
        games=games_sorted,
        players=players,
        player_totals=player_totals,
        goalies=goalies,
        goalie_data=goalie_data,
        opponent_goalie_data=opponent_goalie_data,
        teams=teams,
        selected_team=selected_team)

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
