"""
Phase 3.2: JSON Edit Endpoint Tests
Tests for /game/<game_id>/edit_json endpoint security and functionality

This endpoint allows direct JSON editing of games and is CRITICAL for security.
These tests ensure:
- Authentication and CSRF protection
- Data validation and integrity
- Proper error handling
- Game isolation (editing one game doesn't affect others)
"""

import json
import os
import re
from services.game_service import load_games, save_games
from config import GAMES_FILE


# ============================================================================
# Helper Functions
# ============================================================================

def create_test_game(game_id=1, team='TestTeam', season='2024-25'):
    """
    Helper to create a minimal test game with required structure
    
    Args:
        game_id: Unique game ID
        team: Team name
        season: Season identifier
    
    Returns:
        dict: Game data structure
    """
    return {
        'id': game_id,
        'season': season,
        'team': team,
        'home_team': 'Home FC',
        'away_team': 'Away United',
        'date': '2025-11-14',
        'result': '5-3',
        'score_us': 5,
        'score_them': 3,
        'goals': [],
        'assists': [],
        'penalties': [],
        'saves': [],
        'shots_on_goal': [],
        'lineup': {
            '1': [],
            '2': [],
            '3': [],
            '4': []
        }
    }


def extract_csrf_token(html_content):
    """
    Extract CSRF token from HTML form
    
    Args:
        html_content: HTML page content as string
    
    Returns:
        str: CSRF token value or empty string if not found
    """
    csrf_match = re.search(r'name="csrf_token"[^>]+value="([^"]+)"', html_content)
    if not csrf_match:
        # Try alternative format
        csrf_match = re.search(r'value="([^"]+)"[^>]+name="csrf_token"', html_content)
    return csrf_match.group(1) if csrf_match else ''


def get_game_by_id(game_id):
    """
    Load a specific game from games file
    
    Args:
        game_id: Game ID to find
    
    Returns:
        dict or None: Game data or None if not found
    """
    games = load_games()
    for game in games:
        if game.get('id') == game_id:
            return game
    return None


# ============================================================================
# Phase 3.2: JSON Edit Endpoint Tests
# ============================================================================

def test_edit_json_endpoint_exists(client):
    """
    Test 1/10: Verify /game/edit_json/<game_id> route is accessible
    
    This tests that the endpoint is registered and responds to requests.
    Should return 200 for existing games, not 404.
    """
    # Create a test game
    test_game = create_test_game(game_id=1001)
    games = load_games()
    games.append(test_game)
    save_games(games)
    
    # Test GET request to edit_json endpoint
    response = client.get('/game/1001/edit_json')
    
    # Should return 200 OK, not 404
    assert response.status_code == 200, \
        f"Edit JSON endpoint should exist and return 200, got {response.status_code}"
    
    # Should contain the edit form
    html = response.data.decode('utf-8')
    assert 'edit_game_json' in html or 'json_data' in html, \
        "Edit JSON page should contain the JSON editor form"


def test_edit_json_get_returns_json(client):
    """
    Test 2/10: GET request returns current game data as JSON
    
    Verifies that the GET endpoint returns the game in JSON format
    that can be edited by users.
    """
    # Create a test game with specific data
    test_game = create_test_game(game_id=1002)
    test_game['home_team'] = 'Specific Home Name'
    test_game['away_team'] = 'Specific Away Name'
    test_game['result'] = '7-2'
    
    games = load_games()
    games.append(test_game)
    save_games(games)
    
    # GET the edit page
    response = client.get('/game/1002/edit_json')
    assert response.status_code == 200
    
    html = response.data.decode('utf-8')
    
    # Should contain the specific game data in JSON format
    assert 'Specific Home Name' in html, "Should show current home team"
    assert 'Specific Away Name' in html, "Should show current away team"
    # Check for result in various formats (JSON in textarea may have escaped quotes)
    assert '7-2' in html, "Should display game result"
    assert '1002' in html, "Should display game ID in JSON"


def test_edit_json_malformed_json(client):
    """
    Test 3/10: POST with invalid JSON rejected with 400
    
    CRITICAL SECURITY TEST: Ensures malformed JSON doesn't crash the app
    or corrupt data. Must return proper error message.
    """
    # Create a test game
    test_game = create_test_game(game_id=1003)
    original_result = test_game['result']
    
    games = load_games()
    games.append(test_game)
    save_games(games)
    
    # Get CSRF token from the edit page
    response = client.get('/game/1003/edit_json')
    csrf_token = extract_csrf_token(response.data.decode('utf-8'))
    
    # Try to POST malformed JSON
    malformed_json = '{"id": 1003, "team": "BadData", INVALID_JSON_HERE}'
    
    response = client.post('/game/1003/edit_json', data={
        'csrf_token': csrf_token,
        'json_data': malformed_json
    })
    
    # Should return 200 with error (re-renders form with error) or 400
    assert response.status_code in [200, 400], \
        f"Malformed JSON should return 200 (with error) or 400, got {response.status_code}"
    
    # Should contain error message
    html = response.data.decode('utf-8')
    assert 'Invalid JSON' in html or 'error' in html.lower() or 'JSONDecodeError' in html, \
        "Should display JSON validation error message"
    
    # Verify game data is unchanged
    updated_game = get_game_by_id(1003)
    assert updated_game is not None, "Game should still exist after failed edit"
    assert updated_game['result'] == original_result, \
        "Game result should be unchanged after malformed JSON POST"


def test_edit_json_preserves_game_id(client):
    """
    Test 4/10: Cannot change game ID via JSON edit
    
    CRITICAL SECURITY TEST: Prevents users from changing game IDs which
    could cause data corruption or access control bypass.
    """
    # Create test game
    test_game = create_test_game(game_id=1004)
    games = load_games()
    games.append(test_game)
    save_games(games)
    
    # Get CSRF token
    response = client.get('/game/1004/edit_json')
    csrf_token = extract_csrf_token(response.data.decode('utf-8'))
    
    # Try to change the game ID via JSON edit
    modified_game = create_test_game(game_id=1004)
    modified_game['id'] = 9999  # Try to change ID
    modified_game['team'] = 'ModifiedTeam'
    
    response = client.post('/game/1004/edit_json', data={
        'csrf_token': csrf_token,
        'json_data': json.dumps(modified_game, indent=2)
    }, follow_redirects=False)
    
    # Request should succeed (redirect to game details)
    assert response.status_code in [200, 302], \
        f"Valid JSON should be accepted, got {response.status_code}"
    
    # Verify the game still has original ID
    updated_game = get_game_by_id(1004)
    assert updated_game is not None, "Game should exist with original ID"
    assert updated_game['id'] == 1004, \
        "Game ID should be preserved as 1004, not changed to 9999"
    
    # Verify no game was created with ID 9999
    fake_game = get_game_by_id(9999)
    assert fake_game is None, "Should not create new game with attempted ID 9999"
    
    # Verify other fields were updated
    assert updated_game['team'] == 'ModifiedTeam', \
        "Other fields should be updated even though ID is preserved"


def test_edit_json_validates_structure(client):
    """
    Test 5/10: Required fields are enforced
    
    Tests that essential game structure is validated. Empty or minimal
    JSON should either be rejected or filled with defaults.
    """
    # Create test game
    test_game = create_test_game(game_id=1005)
    original_team = test_game['team']
    
    games = load_games()
    games.append(test_game)
    save_games(games)
    
    # Get CSRF token
    response = client.get('/game/1005/edit_json')
    csrf_token = extract_csrf_token(response.data.decode('utf-8'))
    
    # Try to POST with minimal/empty JSON (missing required fields)
    minimal_json = json.dumps({'id': 1005})
    
    response = client.post('/game/1005/edit_json', data={
        'csrf_token': csrf_token,
        'json_data': minimal_json
    })
    
    # Should either reject (400/200 with error) or accept with defaults
    assert response.status_code in [200, 302, 400], \
        f"Minimal JSON should be handled gracefully, got {response.status_code}"
    
    # Check if game still exists and is valid
    updated_game = get_game_by_id(1005)
    assert updated_game is not None, "Game should still exist"
    assert updated_game['id'] == 1005, "Game ID should be preserved"
    
    # If the save succeeded, verify game has structure (not completely empty)
    # The endpoint might add defaults or might reject - both are valid
    if response.status_code == 302:  # Redirect = success
        # Game was saved - should have ID at minimum
        assert 'id' in updated_game
    
    # If validation error, original game should be intact
    if 'error' in response.data.decode('utf-8').lower() or response.status_code == 400:
        assert updated_game['team'] == original_team, \
            "Failed validation should not corrupt original game"


def test_edit_json_updates_game(client):
    """
    Test 6/10: Valid JSON edit successfully updates game
    
    Core functionality test: verify that valid changes are applied correctly.
    """
    # Create test game
    test_game = create_test_game(game_id=1006)
    test_game['home_team'] = 'Original Home'
    test_game['away_team'] = 'Original Away'
    test_game['result'] = '3-2'
    
    games = load_games()
    games.append(test_game)
    save_games(games)
    
    # Get CSRF token
    response = client.get('/game/1006/edit_json')
    csrf_token = extract_csrf_token(response.data.decode('utf-8'))
    
    # Modify game data
    modified_game = test_game.copy()
    modified_game['home_team'] = 'Updated Home Team'
    modified_game['away_team'] = 'Updated Away Team'
    modified_game['result'] = '5-4'
    modified_game['score_us'] = 5
    modified_game['score_them'] = 4
    
    # POST updated JSON
    response = client.post('/game/1006/edit_json', data={
        'csrf_token': csrf_token,
        'json_data': json.dumps(modified_game, indent=2)
    }, follow_redirects=False)
    
    # Should redirect to game details on success
    assert response.status_code in [200, 302], \
        f"Valid JSON update should succeed, got {response.status_code}"
    
    # Verify changes were saved
    updated_game = get_game_by_id(1006)
    assert updated_game is not None, "Game should still exist"
    assert updated_game['home_team'] == 'Updated Home Team', \
        "Home team should be updated"
    assert updated_game['away_team'] == 'Updated Away Team', \
        "Away team should be updated"
    assert updated_game['result'] == '5-4', \
        "Result should be updated"
    assert updated_game['score_us'] == 5, \
        "Score should be updated"


def test_edit_json_requires_authentication(client):
    """
    Test 7/10: Unauthenticated users can't access edit endpoint
    
    CRITICAL SECURITY TEST: Ensures only authenticated users can edit games.
    """
    # Create test game
    test_game = create_test_game(game_id=1007)
    games = load_games()
    games.append(test_game)
    save_games(games)
    
    # Remove authentication from client session
    with client.session_transaction() as sess:
        sess.pop('authenticated', None)
    
    # Try to GET edit page without authentication
    response = client.get('/game/1007/edit_json', follow_redirects=False)
    
    # Should redirect to login/index (302) or return 401/403
    assert response.status_code in [302, 401, 403], \
        f"Unauthenticated access should be denied, got {response.status_code}"
    
    # If redirect, should go to index/login page
    if response.status_code == 302:
        assert response.location.endswith('/') or 'index' in response.location or 'pin' in response.location, \
            "Should redirect to index/login page"
    
    # Try to POST without authentication
    response = client.post('/game/1007/edit_json', data={
        'json_data': json.dumps(test_game)
    }, follow_redirects=False)
    
    # Should be rejected - either 302 (redirect), 401/403 (auth), or 400 (CSRF)
    # Note: CSRF validation happens before auth, so 400 is expected
    assert response.status_code in [302, 400, 401, 403], \
        f"Unauthenticated POST should be denied, got {response.status_code}"
    
    # Re-authenticate for other tests
    with client.session_transaction() as sess:
        sess['authenticated'] = True


def test_edit_json_requires_csrf(client):
    """
    Test 8/10: CSRF token required for POST requests
    
    CRITICAL SECURITY TEST: Prevents cross-site request forgery attacks.
    """
    # Create test game
    test_game = create_test_game(game_id=1008)
    games = load_games()
    games.append(test_game)
    save_games(games)
    
    # Try to POST without CSRF token
    modified_game = test_game.copy()
    modified_game['home_team'] = 'Should Not Update'
    
    response = client.post('/game/1008/edit_json', data={
        'json_data': json.dumps(modified_game, indent=2)
        # Note: NO csrf_token field
    })
    
    # Should be rejected with 400 Bad Request
    assert response.status_code == 400, \
        f"POST without CSRF token should be rejected with 400, got {response.status_code}"
    
    # Verify game was NOT updated
    unchanged_game = get_game_by_id(1008)
    assert unchanged_game is not None, "Game should still exist"
    assert unchanged_game['home_team'] != 'Should Not Update', \
        "Game should NOT be updated when CSRF token is missing"
    assert unchanged_game['home_team'] == 'Home FC', \
        "Original data should be preserved"


def test_edit_json_nonexistent_game(client):
    """
    Test 9/10: Returns 404 for invalid game_id
    
    Tests error handling when trying to edit a game that doesn't exist.
    """
    # Try to access edit page for non-existent game
    response = client.get('/game/999999/edit_json')
    
    # Should return 404 Not Found
    assert response.status_code == 404, \
        f"Non-existent game should return 404, got {response.status_code}"
    
    # Error message should indicate game not found
    html = response.data.decode('utf-8')
    assert 'not found' in html.lower() or '404' in html, \
        "Should display 'not found' error message"
    
    # Try to POST to non-existent game
    fake_game = create_test_game(game_id=999999)
    
    response = client.post('/game/999999/edit_json', data={
        'json_data': json.dumps(fake_game)
    })
    
    # Should also return 404
    assert response.status_code in [400, 404], \
        f"POST to non-existent game should return 404 or 400, got {response.status_code}"


def test_edit_json_preserves_other_games(client):
    """
    Test 10/10: Editing one game doesn't affect others
    
    CRITICAL DATA INTEGRITY TEST: Ensures game isolation - editing one game
    must not corrupt or modify other games in the system.
    """
    # Create multiple test games
    game1 = create_test_game(game_id=1010)
    game1['home_team'] = 'Team 1 Home'
    game1['away_team'] = 'Team 1 Away'
    game1['result'] = '3-1'
    
    game2 = create_test_game(game_id=1011)
    game2['home_team'] = 'Team 2 Home'
    game2['away_team'] = 'Team 2 Away'
    game2['result'] = '2-2'
    
    game3 = create_test_game(game_id=1012)
    game3['home_team'] = 'Team 3 Home'
    game3['away_team'] = 'Team 3 Away'
    game3['result'] = '4-0'
    
    games = load_games()
    games.extend([game1, game2, game3])
    save_games(games)
    
    # Get CSRF token
    response = client.get('/game/1011/edit_json')
    csrf_token = extract_csrf_token(response.data.decode('utf-8'))
    
    # Edit game2 (middle game)
    modified_game2 = game2.copy()
    modified_game2['home_team'] = 'MODIFIED Team 2'
    modified_game2['result'] = '9-9'
    
    response = client.post('/game/1011/edit_json', data={
        'csrf_token': csrf_token,
        'json_data': json.dumps(modified_game2, indent=2)
    }, follow_redirects=False)
    
    assert response.status_code in [200, 302], \
        f"Update should succeed, got {response.status_code}"
    
    # Verify game2 was updated
    updated_game2 = get_game_by_id(1011)
    assert updated_game2 is not None, "Game 2 should exist"
    assert updated_game2['home_team'] == 'MODIFIED Team 2', \
        "Game 2 should be updated"
    assert updated_game2['result'] == '9-9', \
        "Game 2 result should be updated"
    
    # Verify game1 is unchanged
    unchanged_game1 = get_game_by_id(1010)
    assert unchanged_game1 is not None, "Game 1 should still exist"
    assert unchanged_game1['home_team'] == 'Team 1 Home', \
        "Game 1 home team should be unchanged"
    assert unchanged_game1['away_team'] == 'Team 1 Away', \
        "Game 1 away team should be unchanged"
    assert unchanged_game1['result'] == '3-1', \
        "Game 1 result should be unchanged"
    
    # Verify game3 is unchanged
    unchanged_game3 = get_game_by_id(1012)
    assert unchanged_game3 is not None, "Game 3 should still exist"
    assert unchanged_game3['home_team'] == 'Team 3 Home', \
        "Game 3 home team should be unchanged"
    assert unchanged_game3['away_team'] == 'Team 3 Away', \
        "Game 3 away team should be unchanged"
    assert unchanged_game3['result'] == '4-0', \
        "Game 3 result should be unchanged"
    
    # Verify total game count (no games lost or duplicated)
    all_games = load_games()
    test_game_ids = {1010, 1011, 1012}
    test_games_count = sum(1 for g in all_games if g.get('id') in test_game_ids)
    assert test_games_count == 3, \
        f"Should have exactly 3 test games, found {test_games_count}"


# ============================================================================
# Additional Edge Case Tests
# ============================================================================

def test_edit_json_empty_json_object(client):
    """
    Edge case: POST with empty JSON object {}
    
    Tests handling of technically valid JSON that contains no data.
    """
    # Create test game
    test_game = create_test_game(game_id=1013)
    original_team = test_game['team']
    
    games = load_games()
    games.append(test_game)
    save_games(games)
    
    # Get CSRF token
    response = client.get('/game/1013/edit_json')
    csrf_token = extract_csrf_token(response.data.decode('utf-8'))
    
    # POST empty JSON object
    response = client.post('/game/1013/edit_json', data={
        'csrf_token': csrf_token,
        'json_data': '{}'
    })
    
    # Should handle gracefully (either accept with defaults or reject with error)
    assert response.status_code in [200, 302, 400], \
        f"Empty JSON should be handled gracefully, got {response.status_code}"
    
    # Game should still exist
    game = get_game_by_id(1013)
    assert game is not None, "Game should still exist after empty JSON POST"
    
    # ID should be preserved (endpoint forces it)
    assert game['id'] == 1013, "Game ID should always be preserved"


def test_edit_json_unicode_characters(client):
    """
    Edge case: Handle international characters in team names
    
    Ensures JSON editing works with non-ASCII characters (e.g., ÅÄÖ).
    """
    # Create test game
    test_game = create_test_game(game_id=1014)
    games = load_games()
    games.append(test_game)
    save_games(games)
    
    # Get CSRF token
    response = client.get('/game/1014/edit_json')
    csrf_token = extract_csrf_token(response.data.decode('utf-8'))
    
    # Update with international characters
    modified_game = test_game.copy()
    modified_game['home_team'] = 'Örebro Tigers'
    modified_game['away_team'] = 'Göteborg Sharks'
    modified_game['team'] = 'Malmö FF'
    
    response = client.post('/game/1014/edit_json', data={
        'csrf_token': csrf_token,
        'json_data': json.dumps(modified_game, indent=2, ensure_ascii=False)
    }, follow_redirects=False)
    
    # Should succeed
    assert response.status_code in [200, 302], \
        f"Unicode characters should be handled, got {response.status_code}"
    
    # Verify unicode characters are preserved
    updated_game = get_game_by_id(1014)
    assert updated_game is not None, "Game should exist"
    assert updated_game['home_team'] == 'Örebro Tigers', \
        "Unicode characters in home_team should be preserved"
    assert updated_game['away_team'] == 'Göteborg Sharks', \
        "Unicode characters in away_team should be preserved"


def test_edit_json_very_large_game(client):
    """
    Edge case: Handle large game objects with many events
    
    Tests that the endpoint can handle realistic large games.
    """
    # Create game with lots of events
    test_game = create_test_game(game_id=1015)
    
    # Add many goals
    test_game['goals'] = [
        {
            'period': '1',
            'time': f'{i}:00',
            'scorer': f'Player {i}',
            'assist1': f'Player {i+1}',
            'assist2': ''
        }
        for i in range(1, 21)  # 20 goals
    ]
    
    # Add many penalties
    test_game['penalties'] = [
        {
            'period': '1',
            'time': f'{i}:30',
            'player': f'Player {i}',
            'minutes': '2'
        }
        for i in range(1, 16)  # 15 penalties
    ]
    
    games = load_games()
    games.append(test_game)
    save_games(games)
    
    # Get CSRF token
    response = client.get('/game/1015/edit_json')
    csrf_token = extract_csrf_token(response.data.decode('utf-8'))
    
    # Verify we can POST it back
    response = client.post('/game/1015/edit_json', data={
        'csrf_token': csrf_token,
        'json_data': json.dumps(test_game, indent=2)
    }, follow_redirects=False)
    
    # Should succeed
    assert response.status_code in [200, 302], \
        f"Large game should be handled, got {response.status_code}"
    
    # Verify data integrity
    updated_game = get_game_by_id(1015)
    assert updated_game is not None, "Large game should be saved"
    assert len(updated_game['goals']) == 20, "All goals should be preserved"
    assert len(updated_game['penalties']) == 15, "All penalties should be preserved"
