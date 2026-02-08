"""
Roster management routes blueprint
"""
import os
from flask import Blueprint, request, render_template, redirect, url_for, jsonify
from services.game_service import load_games
from models.roster import (
    load_roster, 
    save_roster, 
    get_all_categories_with_rosters,
    get_all_tesser_values,
    get_roster_file
)

roster_bp = Blueprint('roster', __name__, url_prefix='/roster')


@roster_bp.route('/')
def roster_list():
    category = request.args.get('category', '')
    season = request.args.get('season', '')
    all_categories = get_all_categories_with_rosters(season)
    
    if not category and all_categories:
        category = all_categories[0]
    
    roster = load_roster(category, season)
    # Sort roster by number
    roster_sorted = sorted(roster, key=lambda p: int(p.get('number', 999)))
    
    # Group players by position  
    by_position = {'A': [], 'C': [], 'D': [], 'P': []}
    for player in roster_sorted:
        pos = player.get('position', 'A')
        if pos in by_position:
            by_position[pos].append(player)
    
    # Group players by tesser/category
    by_category = {}
    for player in roster_sorted:
        tesser = player.get('tesser', 'U18')
        if tesser not in by_category:
            by_category[tesser] = []
        by_category[tesser].append(player)
    
    return render_template(
        'roster_list.html',
        roster=roster_sorted,
        by_position=by_position,
        by_category=by_category,
        categories=all_categories,
        category=category,
        season=season
    )


@roster_bp.route('/bulk_import', methods=['GET', 'POST'])
def roster_bulk_import():
    season = request.args.get('season', '')
    category = request.args.get('category', '')
    
    if request.method == 'POST':
        category = request.form.get('category', '')
        season = request.form.get('season', '')
        if not category:
            return redirect(url_for('roster.roster_bulk_import', season=season))
        
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
        return redirect(url_for('roster.roster_list', category=category, season=season))
    
    all_categories = get_all_categories_with_rosters(season)
    return render_template(
        'roster_bulk_import.html',
        categories=all_categories,
        category=category,
        season=season
    )


@roster_bp.route('/add', methods=['GET', 'POST'])
def roster_add():
    category = request.args.get('category', request.form.get('category', ''))
    season = request.args.get('season', request.form.get('season', ''))
    
    if request.method == 'POST':
        category = request.form.get('category', '')
        season = request.form.get('season', '')
        if not category:
            return redirect(url_for('roster.roster_add', season=season))
        
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
        return redirect(url_for('roster.roster_list', category=category, season=season))
    
    tesser_values = get_all_tesser_values()
    all_categories = get_all_categories_with_rosters(season)
    return render_template(
        'roster_form.html',
        player=None,
        categories=all_categories,
        category=category,
        season=season,
        tesser_values=tesser_values
    )


@roster_bp.route('/edit/<player_id>', methods=['GET', 'POST'])
def roster_edit(player_id):
    category = request.args.get('category', request.form.get('category', ''))
    season = request.args.get('season', request.form.get('season', ''))
    if not category:
        return redirect(url_for('roster.roster_list', season=season))
    
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
        return redirect(url_for('roster.roster_list', category=category, season=season))
    
    tesser_values = get_all_tesser_values()
    all_categories = get_all_categories_with_rosters(season)
    return render_template(
        'roster_form.html',
        player=player,
        categories=all_categories,
        category=category,
        season=season,
        tesser_values=tesser_values
    )


@roster_bp.route('/delete/<player_id>')
def roster_delete(player_id):
    category = request.args.get('category', '')
    season = request.args.get('season', '')
    if not category:
        return redirect(url_for('roster.roster_list', season=season))
    
    roster = load_roster(category, season)
    roster = [p for p in roster if p['id'] != player_id]
    save_roster(roster, category, season)
    return redirect(url_for('roster.roster_list', category=category, season=season))


@roster_bp.route('/bulk_delete', methods=['POST'])
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


@roster_bp.route('/delete_roster', methods=['POST'])
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
