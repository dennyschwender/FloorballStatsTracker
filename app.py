import os
import json
from flask import Flask, request, render_template, redirect, url_for, session, g, jsonify
from urllib.parse import urlparse
from datetime import datetime
REQUIRED_PIN = os.environ.get('FLOORBALL_PIN', '1717')

GAMES_FILE = 'gamesFiles/games.json'
ROSTERS_DIR = 'rosters'

# Ensure rosters directory exists
if not os.path.exists(ROSTERS_DIR):
    os.makedirs(ROSTERS_DIR)

# Ensure games.json exists before anything else
if not os.path.exists(GAMES_FILE):
    with open(GAMES_FILE, 'w') as f:
        json.dump([], f)

# Define available categories
CATEGORIES = ['U18', 'U21', 'U16', 'Senior']


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
        'referee1': 'Referee 1',
        'referee2': 'Referee 2',
        'referees': 'Referees',
        'notes': 'Notes',
        'season': 'Season',
        'select_season': 'Select Season',
        'create_season': 'Create New Season',
        'season_name': 'Season Name',
        'all_seasons': 'All Seasons',
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
        'roster': 'Team Roster',
        'roster_management': 'Roster Management',
        'add_player': 'Add Player',
        'bulk_import': 'Bulk Import',
        'edit_player': 'Edit Player',
        'delete_player': 'Delete Player',
        'number': 'Number',
        'surname': 'Surname',
        'name': 'Name',
        'nickname': 'Nickname',
        'position': 'Position',
        'position_a': 'Attacker',
        'position_c': 'Center',
        'position_d': 'Defender',
        'position_p': 'Goalie',
        'tesser': 'Category',
        'select_roster': 'Roster',
        'select_category': 'Select Category',
        'u18': 'U18',
        'u21': 'U21',
        'u21_dp': 'U21 DP',
        'u16': 'U16',
        'no_players': 'No players in roster. Add players to get started!',
        'formations': 'Formations',
        'pp1': 'PP1',
        'pp2': 'PP2',
        'bp1': 'BP1',
        'bp2': 'BP2',
        '6vs5': '6vs5',
        'stress_line': 'Stress Line',
        'convocato': 'Called Up',
        'summary': 'Summary',
        'by_position': 'By Position',
        'by_category': 'By Category',
        'use_for_game': 'Use for Game',
        'bulk_import_title': 'Bulk Import Players',
        'bulk_import_instructions': 'Paste player data below (one player per line). Format: Number, Surname, Name, Position, Category, Nickname',
        'bulk_import_example': 'Example: 10, Smith, John, A, U18, Johnny',
        'bulk_import_format': 'Supported formats: Tab-separated (from Excel/Sheets) or Comma-separated',
        'bulk_data': 'Player Data',
        'import_players': 'Import Players',
        'or_manual': 'Or enter manually',
        'starting_goalies': 'Starting Goalies',
        'first_goalie': 'Starting Goalie',
        'second_goalie': 'Backup Goalie',
        'lineup': 'Complete Lineup',
        'select_goalie': 'Select Goalie',
        'select_starting_goalie': 'Select Starting Goalie',
        'select_starting_goalie_instruction': 'Check goalies in the roster above, then select which one starts',
        'hide_inactive_players': 'Hide players without number',
        'select_category': 'Select Category',
        'error_loading_roster': 'Error loading roster for this category',
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
        'referee1': 'Arbitro 1',
        'referee2': 'Arbitro 2',
        'referees': 'Arbitri',
        'notes': 'Note',
        'season': 'Stagione',
        'select_season': 'Seleziona Stagione',
        'create_season': 'Crea Nuova Stagione',
        'season_name': 'Nome Stagione',
        'all_seasons': 'Tutte le Stagioni',
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
        'roster': 'Rosa della Squadra',
        'roster_management': 'Gestione Rosa',
        'add_player': 'Aggiungi Giocatore',
        'bulk_import': 'Importazione Massiva',
        'edit_player': 'Modifica Giocatore',
        'delete_player': 'Elimina Giocatore',
        'number': 'Numero',
        'surname': 'Cognome',
        'name': 'Nome',
        'nickname': 'Soprannome',
        'position': 'Posizione',
        'position_a': 'Attaccante',
        'position_c': 'Centro',
        'position_d': 'Difensore',
        'position_p': 'Portiere',
        'tesser': 'Tesser',
        'select_roster': 'Rosa',
        'select_category': 'Seleziona Categoria',
        'u18': 'U18',
        'u21': 'U21',
        'u21_dp': 'U21 DP',
        'u16': 'U16',
        'no_players': 'Nessun giocatore nella rosa. Aggiungi giocatori per iniziare!',
        'formations': 'Formazioni',
        'pp1': 'PP1',
        'pp2': 'PP2',
        'bp1': 'BP1',
        'bp2': 'BP2',
        '6vs5': '6vs5',
        'stress_line': 'Linea Stress',
        'convocato': 'Convocato',
        'summary': 'Riepilogo',
        'by_position': 'Per Posizione',
        'by_category': 'Per Categoria',
        'use_for_game': 'Usa per Partita',
        'bulk_import_title': 'Importazione Massiva Giocatori',
        'bulk_import_instructions': 'Incolla i dati dei giocatori qui sotto (un giocatore per riga). Formato: Numero, Cognome, Nome, Posizione, Tesser, Soprannome',
        'bulk_import_example': 'Esempio: 10, Rossi, Mario, A, U18, Marietto',
        'bulk_import_format': 'Formati supportati: Separati da tabulazione (da Excel/Sheets) o separati da virgola',
        'bulk_data': 'Dati Giocatori',
        'import_players': 'Importa Giocatori',
        'or_manual': 'Oppure inserisci manualmente',
        'starting_goalies': 'Portieri Titolari',
        'first_goalie': 'Portiere Titolare',
        'second_goalie': 'Portiere di Riserva',
        'lineup': 'Formazione Completa',
        'select_goalie': 'Seleziona Portiere',
        'select_starting_goalie': 'Seleziona Portiere Titolare',
        'select_starting_goalie_instruction': 'Seleziona i portieri nel roster sopra, poi scegli chi parte titolare',
        'hide_inactive_players': 'Nascondi giocatori senza numero',
        'select_category': 'Seleziona Categoria',
        'error_loading_roster': 'Errore nel caricamento del roster per questa categoria',
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
    # Redirect back to previous page or home safely
    ref = request.referrer or url_for('index')
    # Remove backslashes which some browsers accept
    safe_ref = ref.replace('\\', '')
    parsed = urlparse(safe_ref)
    if not parsed.netloc and not parsed.scheme:
        return redirect(safe_ref)
    return redirect(url_for('index'))

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


def get_roster_file(category, season=None):
    """Get the roster file path for a specific category and season"""
    if season and season.strip():
        return os.path.join(ROSTERS_DIR, f'roster_{season}_{category}.json')
    # For backward compatibility, return old format if no season specified
    return os.path.join(ROSTERS_DIR, f'roster_{category}.json')


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


def find_game_by_id(games, game_id):
    """Find a game by its ID field (not array index)"""
    for game in games:
        if game.get('id') == game_id:
            return game
    return None


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


def ensure_game_ids(games):
    changed = False
    seen_ids = set()
    # Find current max id
    max_id = -1
    for i, game in enumerate(games):
        if 'id' in game:
            try:
                game_id = int(game['id'])
                max_id = max(max_id, game_id)
            except Exception:
                pass
        else:
            max_id = max(max_id, i)
    
    # Assign IDs to games without one and fix duplicates
    for i, game in enumerate(games):
        if 'id' not in game or game['id'] in seen_ids:
            # Missing ID or duplicate ID
            max_id += 1
            game['id'] = max_id
            changed = True
        seen_ids.add(game['id'])
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
    
    # Filter by season
    seasons = get_all_seasons()
    selected_season = request.args.get('season')
    if selected_season:
        games_sorted = [
            game for game in games_sorted if game.get('season') == selected_season]
    
    # Filter by team
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
        seasons=seasons,
        selected_season=selected_season,
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
        # Find and update game by ID
        for i, game_item in enumerate(games):
            if game_item.get('id') == game_id:
                games[i] = game
                break
        save_games(games)
    # --- End error management ---
    return render_template(
        'game_details.html',
        game=game,
        game_id=game_id,
        games=games,
        player_nicknames=player_nicknames)

# Modify game page


@app.route('/modify_game/<int:game_id>', methods=['GET', 'POST'])
def modify_game(game_id):
    games = load_games()
    game = find_game_by_id(games, game_id)
    if not game:
        return "Game not found", 404
    if request.method == 'POST':
        season = request.form.get('season', game.get('season', ''))
        team = request.form.get('team')
        home_team = request.form.get('home_team')
        away_team = request.form.get('away_team')
        date = request.form.get('date')
        referee1 = request.form.get('referee1', '').strip()
        referee2 = request.form.get('referee2', '').strip()
        
        # Load roster for player lookup
        roster = load_roster(team, season) if team else load_roster()
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
        # For existing games, enable if they had opponent stats or if
        # explicitly requested
        has_opponent_stats = (
            'opponent_goalie_saves' in game and game['opponent_goalie_saves']) or (
            'opponent_goalie_goals_conceded' in game and game['opponent_goalie_goals_conceded'])
        enable_opponent_goalie = request.form.get(
            'enable_opponent_goalie') == 'on' or has_opponent_stats

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
        
        # Store formations from direct form entry with position numbers
        for formation_key in ['pp1', 'pp2', 'bp1', 'bp2', '6vs5', 'stress_line']:
            formation_players_with_position = []
            # Collect all form fields for this formation
            for player_id in player_map.keys():
                position_value = request.form.get(f'{formation_key}_{player_id}', '').strip()
                if position_value:
                    player = player_map.get(player_id)
                    if player:
                        try:
                            pos_num = int(position_value)
                            formation_players_with_position.append({
                                'position': pos_num,
                                'name': f"{player['number']} - {player['surname']} {player['name']}"
                            })
                        except ValueError:
                            pass
            
            # Sort by position number and extract names
            formation_players_with_position.sort(key=lambda x: x['position'])
            formation_players = [p['name'] for p in formation_players_with_position]
            game[formation_key] = formation_players
        
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
        return redirect(url_for('game_details', game_id=game_id))
    
    # GET request - load seasons for the form
    seasons = get_all_seasons()
    return render_template(
        'game_form.html',
        game=game,
        modify=True,
        game_id=game_id,
        categories=[],
        seasons=seasons)

# Plus/minus, goal, assist action for a player


@app.route('/action/<int:game_id>/<player>')
def player_action(game_id, player):
    action = request.args.get('action')
    games = load_games()
    game = find_game_by_id(games, game_id)
    if not game:
        return "Game not found", 404
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
    # Find and update game by ID
    for i, game_item in enumerate(games):
        if game_item.get('id') == game_id:
            games[i] = game
            break
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
    # Find and update game by ID
    for i, game_item in enumerate(games):
        if game_item.get('id') == game_id:
            games[i] = game
            break
    save_games(games)
    if request.args.get('edit') == '1':
        return redirect(url_for('game_details', game_id=game_id, edit=1))
    return redirect(url_for('game_details', game_id=game_id))


# Edit game JSON directly
@app.route('/game/<int:game_id>/edit_json', methods=['GET', 'POST'])
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
            return redirect(url_for('game_details', game_id=game_id))
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


# View game lineup (for printing)
@app.route('/game/<int:game_id>/lineup')
def view_game_lineup(game_id):
    games = load_games()
    game = find_game_by_id(games, game_id)
    if not game:
        return "Game not found", 404
    
    # Load roster to get player details including nicknames
    roster = []
    if 'team' in game and game['team']:
        roster = load_roster(game['team'])
    
    # Create a player map by "number - surname name" for quick lookup
    player_map = {}
    for player in roster:
        key = f"{player['number']} - {player['surname']} {player['name']}"
        player_map[key] = player
    
    return render_template('game_lineup.html', game=game, roster=roster, player_map=player_map)

# Game creation form


@app.route('/create_game', methods=['GET', 'POST'])
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
            'result': result,
            'current_period': '1',
        }
        
        # Store formations from direct form entry with position numbers
        for formation_key in ['pp1', 'pp2', 'bp1', 'bp2', '6vs5', 'stress_line']:
            formation_players_with_position = []
            # Collect all form fields for this formation
            for player_id in player_map.keys():
                position_value = request.form.get(f'{formation_key}_{player_id}', '').strip()
                if position_value:
                    player = player_map.get(player_id)
                    if player:
                        try:
                            pos_num = int(position_value)
                            formation_players_with_position.append({
                                'position': pos_num,
                                'name': f"{player['number']} - {player['surname']} {player['name']}"
                            })
                        except ValueError:
                            pass
            
            # Sort by position number and extract names
            formation_players_with_position.sort(key=lambda x: x['position'])
            formation_players = [p['name'] for p in formation_players_with_position]
            game[formation_key] = formation_players
        
        games.append(game)
        save_games(games)
        return redirect(url_for('index'))
    
    # GET request - load seasons (categories loaded dynamically via API)
    seasons = get_all_seasons()
    return render_template('game_form.html', categories=[], seasons=seasons)


@app.route('/api/categories')
def get_categories_by_season():
    """API endpoint to get categories by season"""
    season = request.args.get('season', '')
    categories = get_all_categories_with_rosters(season)
    return jsonify(categories)


@app.route('/api/roster/<category>')
def get_roster_by_category(category):
    """API endpoint to get roster by category"""
    if category not in CATEGORIES:
        return jsonify({'error': 'Invalid category'}), 400
    
    season = request.args.get('season', '')
    roster = load_roster(category, season)
    roster_sorted = sorted(roster, key=lambda p: int(p.get('number', 999)))
    return jsonify(roster_sorted)

# Goalie stat actions: plus, minus, save, goal_conceded


@app.route('/action_goalie/<int:game_id>/<goalie>')
def goalie_action(game_id, goalie):
    action = request.args.get('action')
    games = load_games()
    game = find_game_by_id(games, game_id)
    if not game:
        return "Game not found", 404
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
    # Find and update game by ID
    for i, game_item in enumerate(games):
        if game_item.get('id') == game_id:
            games[i] = game
            break
    save_games(games)
    if request.args.get('edit') == '1':
        return redirect(url_for('game_details', game_id=game_id, edit=1))
    return redirect(url_for('game_details', game_id=game_id))

# Opponent Goalie stat actions: save, goal_conceded


@app.route('/action_opponent_goalie/<int:game_id>')
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
        # Home team goal in current period (our goal = opponent goalie goal
        # conceded)
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
    save_games(games)
    if request.args.get('edit') == '1':
        return redirect(url_for('game_details', game_id=game_id, edit=1))
    return redirect(url_for('game_details', game_id=game_id))

# Route to reset all stats for a game


@app.route('/reset_game/<int:game_id>')
def reset_game(game_id):
    games = load_games()
    game = find_game_by_id(games, game_id)
    if not game:
        return "Game not found", 404
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
    # Find and update game by ID
    for i, game_item in enumerate(games):
        if game_item.get('id') == game_id:
            games[i] = game
            break
    save_games(games)
    if request.args.get('edit') == '1':
        return redirect(url_for('game_details', game_id=game_id, edit=1))
    return redirect(url_for('game_details', game_id=game_id))


# (debug route removed)

# Delete game route


@app.route('/delete_game/<int:game_id>', methods=['POST'])
def delete_game(game_id):
    games = load_games()
    game = find_game_by_id(games, game_id)
    if not game:
        return "Game not found", 404
    games = [g for g in games if g.get('id') != game_id]
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
    
    # Filter by season
    seasons = get_all_seasons()
    selected_season = request.args.get('season')
    if selected_season:
        games_sorted = [
            game for game in games_sorted if game.get('season') == selected_season]
    
    # Filter by team/category
    teams = sorted(set(game.get('team', '') for game in games if game.get('team')))
    selected_team = request.args.get('team')
    if selected_team:
        games_sorted = [
            game for game in games_sorted if game.get('team') == selected_team]
    
    # Get filter parameters
    hide_zero_stats = request.args.get('hide_zero_stats', 'false') == 'true'
    
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
            
            # FALLBACK: If goals_conceded is 0 but the goalie has saves recorded,
            # infer goals conceded from the game result (away team score)
            # This handles cases where goals_conceded wasn't manually tracked
            if goals_conceded == 0 and saves > 0:
                # Calculate total away goals from all periods
                result = game.get('result', {})
                if result:
                    away_goals = sum(period_result.get('away', 0) for period_result in result.values())
                    # Only use this fallback if there are away goals
                    if away_goals > 0:
                        # If this goalie played (has saves), attribute the away goals to them
                        # In future, this should be split among goalies based on ice time
                        goals_conceded = away_goals
            
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

    # Apply filters to players list
    filtered_players = []
    for player in players:
        # Filter: Hide players with all stats = 0
        if hide_zero_stats:
            totals = player_totals[player]
            if (totals['plusminus'] == 0 and totals['goals'] == 0 and 
                totals['assists'] == 0 and totals['unforced_errors'] == 0):
                continue
        
        filtered_players.append(player)
    
    # Apply filters to goalies list
    filtered_goalies = []
    for goalie in goalies:
        # Filter: Hide goalies with zero stats
        if hide_zero_stats:
            data = goalie_data[goalie]
            if data['total_saves'] == 0 and data['total_goals_conceded'] == 0:
                continue
        
        filtered_goalies.append(goalie)

    return render_template(
        'stats.html',
        games=games_sorted,
        players=filtered_players,
        player_totals=player_totals,
        goalies=filtered_goalies,
        goalie_data=goalie_data,
        opponent_goalie_data=opponent_goalie_data,
        seasons=seasons,
        selected_season=selected_season,
        teams=teams,
        selected_team=selected_team,
        hide_zero_stats=hide_zero_stats)

# Set period route


@app.route('/set_period/<int:game_id>/<period>')
def set_period(game_id, period):
    games = load_games()
    game = find_game_by_id(games, game_id)
    if not game:
        return "Game not found", 404
    if period not in PERIODS:
        return "Invalid period", 400
    game['current_period'] = period
    # Find and update game by ID
    for i, game_item in enumerate(games):
        if game_item.get('id') == game_id:
            games[i] = game
            break
    save_games(games)
    # Preserve edit mode if present
    edit = request.args.get('edit')
    if edit == '1':
        return redirect(url_for('game_details', game_id=game_id, edit=1))
    return redirect(url_for('game_details', game_id=game_id))


# ===== ROSTER MANAGEMENT ROUTES =====

@app.route('/roster')
def roster_list():
    # Get category and season from query parameters
    selected_category = request.args.get('category', '')
    selected_season = request.args.get('season', '')
    
    # Get all existing seasons
    all_seasons = get_all_seasons()
    
    # If no season selected but seasons exist, redirect to first season
    if not selected_season and all_seasons and not selected_category:
        return redirect(url_for('roster_list', season=all_seasons[0]))
    
    # Get categories for selected season
    existing_rosters = get_all_categories_with_rosters(selected_season)
    
    roster = load_roster(selected_category, selected_season) if selected_category else []
    # Sort by number - handle non-numeric values
    def sort_key(player):
        try:
            return (0, int(player.get('number', 999)))
        except (ValueError, TypeError):
            # Non-numeric values sorted alphabetically after numeric
            return (1, str(player.get('number', '')))
    
    roster_sorted = sorted(roster, key=sort_key)
    return render_template('roster_list.html', roster=roster_sorted, 
                         existing_rosters=existing_rosters,
                         all_seasons=all_seasons,
                         selected_category=selected_category,
                         selected_season=selected_season)


@app.route('/roster/bulk_import', methods=['GET', 'POST'])
def roster_bulk_import():
    category = request.args.get('category', request.form.get('category', ''))
    season = request.args.get('season', request.form.get('season', ''))
    
    if request.method == 'POST':
        category = request.form.get('category', '')
        season = request.form.get('season', '')
        if not category:
            return redirect(url_for('roster_bulk_import', season=season))
        
        roster = load_roster(category, season)
        # Get the maximum current ID
        max_id = 0
        for player in roster:
            try:
                max_id = max(max_id, int(player.get('id', 0)))
            except:
                pass
        
        # Process bulk data
        players_data = request.form.get('bulk_data', '')
        lines = [line.strip() for line in players_data.strip().split('\n') if line.strip()]
        
        added_count = 0
        for line in lines:
            # Split by tab or comma
            if '\t' in line:
                parts = line.split('\t')
            else:
                parts = [p.strip() for p in line.split(',')]
            
            if len(parts) >= 4:  # At least number, surname, name, position
                max_id += 1
                new_player = {
                    'id': str(max_id),
                    'number': parts[0].strip(),
                    'surname': parts[1].strip(),
                    'name': parts[2].strip(),
                    'position': parts[3].strip().upper() if len(parts[3].strip()) <= 1 else 'A',
                    'tesser': parts[4].strip() if len(parts) > 4 else 'U18',
                    'nickname': parts[5].strip() if len(parts) > 5 else ''
                }
                roster.append(new_player)
                added_count += 1
        
        save_roster(roster, category, season)
        return redirect(url_for('roster_list', category=category, season=season))
    
    all_categories = get_all_categories_with_rosters(season)
    return render_template('roster_bulk_import.html', categories=all_categories, category=category, season=season)


@app.route('/roster/add', methods=['GET', 'POST'])
def roster_add():
    category = request.args.get('category', request.form.get('category', ''))
    season = request.args.get('season', request.form.get('season', ''))
    
    if request.method == 'POST':
        category = request.form.get('category', '')
        season = request.form.get('season', '')
        if not category:
            return redirect(url_for('roster_add', season=season))
        
        roster = load_roster(category, season)
        new_player = {
            'id': str(len(roster) + 1),
            'number': request.form.get('number', ''),
            'surname': request.form.get('surname', ''),
            'name': request.form.get('name', ''),
            'nickname': request.form.get('nickname', ''),
            'position': request.form.get('position', 'A'),
            'tesser': request.form.get('tesser', 'U18')
        }
        roster.append(new_player)
        save_roster(roster, category, season)
        return redirect(url_for('roster_list', category=category, season=season))
    
    tesser_values = get_all_tesser_values()
    all_categories = get_all_categories_with_rosters(season)
    return render_template('roster_form.html', player=None, categories=all_categories, category=category, season=season, tesser_values=tesser_values)


@app.route('/roster/edit/<player_id>', methods=['GET', 'POST'])
def roster_edit(player_id):
    category = request.args.get('category', request.form.get('category', ''))
    season = request.args.get('season', request.form.get('season', ''))
    if not category:
        return redirect(url_for('roster_list', season=season))
    
    roster = load_roster(category, season)
    player = next((p for p in roster if p['id'] == player_id), None)
    if not player:
        return "Player not found", 404
    
    if request.method == 'POST':
        category = request.form.get('category', '')
        season = request.form.get('season', '')
        player['number'] = request.form.get('number', '')
        player['surname'] = request.form.get('surname', '')
        player['name'] = request.form.get('name', '')
        player['nickname'] = request.form.get('nickname', '')
        player['position'] = request.form.get('position', 'A')
        player['tesser'] = request.form.get('tesser', 'U18')
        save_roster(roster, category, season)
        return redirect(url_for('roster_list', category=category, season=season))
    
    tesser_values = get_all_tesser_values()
    all_categories = get_all_categories_with_rosters(season)
    return render_template('roster_form.html', player=player, categories=all_categories, category=category, season=season, tesser_values=tesser_values)


@app.route('/roster/delete/<player_id>')
def roster_delete(player_id):
    category = request.args.get('category', '')
    season = request.args.get('season', '')
    if not category:
        return redirect(url_for('roster_list', season=season))
    
    roster = load_roster(category, season)
    roster = [p for p in roster if p['id'] != player_id]
    save_roster(roster, category, season)
    return redirect(url_for('roster_list', category=category, season=season))


@app.route('/roster/bulk_delete', methods=['POST'])
def roster_bulk_delete():
    try:
        data = request.get_json()
        category = data.get('category', '')
        season = data.get('season', '')
        player_ids = data.get('player_ids', [])
        
        if not category or not player_ids:
            return jsonify({'success': False, 'error': 'Missing category or player IDs'})
        
        roster = load_roster(category, season)
        # Remove players with IDs in the list
        roster = [p for p in roster if p['id'] not in player_ids]
        save_roster(roster, category, season)
        
        return jsonify({'success': True, 'deleted_count': len(player_ids)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/roster/delete_roster', methods=['POST'])
def delete_roster():
    try:
        data = request.get_json()
        category = data.get('category', '')
        
        if not category:
            return jsonify({'success': False, 'error': 'Missing category'})
        
        # Check if any games use this roster
        games = load_games()
        games_using_roster = [g for g in games if g.get('team') == category]
        
        if games_using_roster and not data.get('force', False):
            # Return warning with game count
            return jsonify({
                'success': False, 
                'warning': True,
                'game_count': len(games_using_roster),
                'message': f'{len(games_using_roster)} game(s) are using this roster. Deleting it will not affect existing game data, but you won\'t be able to load this roster for those games anymore.'
            })
        
        # Delete the roster file
        roster_file = get_roster_file(category)
        if os.path.exists(roster_file):
            os.remove(roster_file)
            return jsonify({'success': True, 'message': 'Roster deleted successfully'})
        else:
            return jsonify({'success': False, 'error': 'Roster file not found'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


if __name__ == '__main__':
    # Only enable debug mode if running directly with python app.py
    app.run(debug=True)
# When run with gunicorn or another WSGI server, debug is off by default
