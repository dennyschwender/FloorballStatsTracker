"""
Direct JSON editing route blueprint
"""
import json
from flask import Blueprint, request, render_template, redirect, url_for, abort
from services.game_service import load_games, save_games, find_game_by_id
from utils.auth_helpers import require_manage

json_bp = Blueprint('game_json', __name__)


@json_bp.route('/game/<int:game_id>/edit_json', methods=['GET', 'POST'])
def edit_game_json(game_id):
    guard = require_manage()
    if guard:
        return guard
    games = load_games()
    game = find_game_by_id(games, game_id)
    if not game:
        abort(404)

    if request.method == 'POST':
        try:
            json_data = request.form.get('json_data', '{}')
            updated_game = json.loads(json_data)
            updated_game['id'] = game_id
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

    json_data = json.dumps(game, indent=2, ensure_ascii=False)
    return render_template(
        'edit_game_json.html',
        game=game,
        game_id=game_id,
        json_data=json_data
    )
