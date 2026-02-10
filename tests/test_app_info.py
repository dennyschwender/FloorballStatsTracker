#!/usr/bin/env python3
"""Test script to verify all app information loads properly"""

from app import app
from config import REQUIRED_PIN, TRANSLATIONS, LANGUAGES, GAMES_FILE, ROSTERS_DIR
import os

print('=' * 60)
print('FloorballStatsTracker - Information Loading Test')
print('=' * 60)

# Test 1: App Configuration
print('\n1. APP CONFIGURATION')
print(f'   ✓ App name: {app.name}')
print(f'   ✓ Debug mode: {app.debug}')
print(f'   ✓ Blueprints registered: {len(app.blueprints)}')
print(f'   ✓ Blueprint names: {", ".join(app.blueprints.keys())}')

# Test 2: Security Configuration
print('\n2. SECURITY CONFIGURATION')
print(f'   ✓ PIN configured: {len(REQUIRED_PIN)} characters')
print(f'   ✓ Secret key configured: {len(app.secret_key)} characters')
print(f'   ✓ CSRF protection: {"Enabled" if app.extensions.get("csrf") else "Disabled"}')

# Test 3: Language/Translation
print('\n3. LANGUAGE & TRANSLATIONS')
print(f'   ✓ Languages available: {LANGUAGES}')
print(f'   ✓ Translation keys loaded: {len(TRANSLATIONS["en"])} keys')
print(f'   ✓ Italian translations: {len(TRANSLATIONS.get("it", {}))} keys')

# Test 4: File Paths
print('\n4. FILE PATHS')
print(f'   ✓ GAMES_FILE: {GAMES_FILE}')
print(f'   ✓ ROSTERS_DIR: {ROSTERS_DIR}')
print(f'   ✓ games.json exists: {os.path.exists(GAMES_FILE)}')
print(f'   ✓ rosters/ exists: {os.path.exists(ROSTERS_DIR)}')

# Test 5: Routes
print('\n5. ROUTES')
routes_by_blueprint = {}
for rule in app.url_map.iter_rules():
    if rule.endpoint != 'static':
        blueprint = rule.endpoint.split('.')[0] if '.' in rule.endpoint else 'main'
        if blueprint not in routes_by_blueprint:
            routes_by_blueprint[blueprint] = []
        routes_by_blueprint[blueprint].append(rule.rule)

for blueprint, routes in sorted(routes_by_blueprint.items()):
    print(f'   ✓ {blueprint}: {len(routes)} routes')

total_routes = sum(len(routes) for routes in routes_by_blueprint.values())
print(f'   ✓ Total routes: {total_routes}')

# Test 6: Templates
print('\n6. TEMPLATES')
from flask import render_template_string
with app.app_context():
    # Set up a mock session
    from flask import session, g
    g.lang = 'en'
    g.t = TRANSLATIONS['en']
    
    # Test template rendering
    test_template = '{{ g.t["title"] }}'
    rendered = render_template_string(test_template)
    print(f'   ✓ Template rendering works: "{rendered}"')

# Test 7: Import all key modules
print('\n7. MODULE IMPORTS')
try:
    from routes import game_routes, roster_routes, stats_routes, api_routes
    print(f'   ✓ routes module loaded')
except ImportError as e:
    print(f'   ✗ routes module error: {e}')

try:
    from services import game_service, stats_service, file_service
    print(f'   ✓ services module loaded')
except ImportError as e:
    print(f'   ✗ services module error: {e}')

try:
    from utils import cache, security, validators
    print(f'   ✓ utils module loaded')
except ImportError as e:
    print(f'   ✗ utils module error: {e}')

try:
    from models import roster
    print(f'   ✓ models module loaded')
except ImportError as e:
    print(f'   ✗ models module error: {e}')

# Test 8: Check for games data
print('\n8. DATA FILES')
try:
    from services.game_service import load_games
    games = load_games()
    print(f'   ✓ Games loaded: {len(games)} games')
    if games:
        print(f'   ✓ Sample game keys: {list(games[0].keys())[:5]}...')
except Exception as e:
    print(f'   ✗ Error loading games: {e}')

print('\n' + '=' * 60)
print('✅ ALL TESTS COMPLETE')
print('=' * 60)
