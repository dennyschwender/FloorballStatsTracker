"""
API endpoints blueprint
"""
from flask import Blueprint, request, jsonify
from models.roster import get_all_categories_with_rosters, load_roster

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
    roster = load_roster(category, season)
    roster_sorted = sorted(roster, key=lambda p: int(p.get('number', 999)))
    return jsonify(roster_sorted)
