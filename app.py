
import os
import json
from flask import Flask, request, render_template, redirect, url_for, session
REQUIRED_PIN = os.environ.get('FLOORBALL_PIN', '1717')


GAMES_FILE = 'gamesFiles/games.json'

# Ensure games.json exists before anything else
if not os.path.exists(GAMES_FILE):
    with open(GAMES_FILE, 'w') as f:
        json.dump([], f)

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev_secret')

def load_games():
    try:
        with open(GAMES_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return []

def save_games(games):
    with open(GAMES_FILE, 'w') as f:
        json.dump(games, f, indent=2)


# Home page: show latest game and create/switch options
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
    selected_team = request.args.get('team')
    if selected_team:
        filtered_games = [g for g in games if g.get('team') == selected_team]
    else:
        filtered_games = games
    latest_game_id = None
    if filtered_games:
        # Find the latest game for the selected team (or all games)
        latest_game_id = games.index(filtered_games[-1])
    return render_template('index.html', games=games, latest_game_id=latest_game_id, selected_team=selected_team)
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
    if game_id < 0 or game_id >= len(games):
        return "Game not found", 404
    game = games[game_id]
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
        lines = []
        for i in range(1, 5):
            line_players = request.form.get(f'line{i}', '')
            lines.append([p.strip() for p in line_players.split(',') if p.strip()])
        goalies = []
        for i in range(1, 3):
            goalie = request.form.get(f'goalie{i}', '')
            if goalie.strip():
                goalies.append(goalie.strip())
        game['team'] = team
        game['home_team'] = home_team
        game['away_team'] = away_team
        game['lines'] = lines
        game['goalies'] = goalies
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
    if action == 'plus':
        game['plusminus'][player] += 1
    elif action == 'minus':
        game['plusminus'][player] -= 1
    elif action == 'goal':
        game['goals'][player] += 1
    elif action == 'goal_minus':
        if game['goals'][player] > 0:
            game['goals'][player] -= 1
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

# Game creation form
@app.route('/create_game', methods=['GET', 'POST'])
def create_game():
    if request.method == 'POST':
        team = request.form.get('team')
        home_team = request.form.get('home_team')
        away_team = request.form.get('away_team')
        lines = []
        for i in range(1, 5):
            line_players = request.form.get(f'line{i}', '')
            lines.append([p.strip() for p in line_players.split(',') if p.strip()])
        goalies = []
        for i in range(1, 3):
            goalie = request.form.get(f'goalie{i}', '')
            if goalie.strip():
                goalies.append(goalie.strip())
        game = {
            'team': team,
            'home_team': home_team,
            'away_team': away_team,
            'lines': lines,
            'goalies': goalies
        }
        games = load_games()
        games.append(game)
        save_games(games)
        return redirect(url_for('index'))
    return render_template('game_form.html')


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
    elif action == 'goal_conceded_minus':
        if game['goals_conceded'][goalie] > 0:
            game['goals_conceded'][goalie] -= 1
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

if __name__ == '__main__':
    app.run(debug=True)
