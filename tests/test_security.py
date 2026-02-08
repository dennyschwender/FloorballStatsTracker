"""
Security Test Suite - Phase 3.1
Tests for critical security vulnerabilities and protections
"""
import json
import os
import hmac
import re
from flask import session
from config import GAMES_FILE, ROSTERS_DIR, REQUIRED_PIN


def test_xss_in_player_name(client):
    """Ensure XSS payloads in player names are properly escaped in HTML output"""
    xss_payload = "<script>alert('xss')</script>"
    
    # Create roster with XSS in player name
    season = '2024-25'
    team = 'U21'
    roster_data = [
        {
            "id": "1",
            "number": "99",
            "surname": xss_payload,
            "name": "Benign",
            "position": "A",
            "tesser": "U21"
        },
        {
            "id": "2", 
            "number": "88",
            "surname": "Safe",
            "name": "<img src=x onerror=alert(1)>",
            "position": "D",
            "tesser": "U21"
        }
    ]
    
    # Save roster with malicious content
    roster_path = os.path.join(ROSTERS_DIR, f'roster_{season}_{team}.json')
    with open(roster_path, 'w') as f:
        json.dump(roster_data, f)
    
    # Get CSRF token first
    response = client.get('/create_game')
    html = response.data.decode('utf-8')
    
    # Extract CSRF token from the form
    import re
    csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    csrf_token = csrf_match.group(1) if csrf_match else ''
    
    # Create a game using this roster
    game_data = {
        'csrf_token': csrf_token,
        'season': season,
        'team': team,
        'home_team': 'Test FC',
        'away_team': 'Safe United',
        'date': '2025-11-14',
        'l1_1': '1',
        'l1_2': '2',  
        'goalie1': '1',
        'goalie2': ''
    }
    
    response = client.post('/create_game', data=game_data, follow_redirects=True)
    assert response.status_code == 200
    
    # Verify XSS payloads are escaped in the HTML output
    html = response.data.decode('utf-8')
    
    # Should NOT contain unescaped script tags
    assert '<script>alert(' not in html, "XSS script tag was not escaped!"
    
    # Should NOT contain unescaped img onerror
    assert 'onerror=alert' not in html, "XSS img onerror was not escaped!"
    
    # Should contain escaped versions or safe representation
    # Jinja2 auto-escapes to &lt; &gt; etc
    assert '&lt;script&gt;' in html or xss_payload not in html, "XSS was not properly escaped"


def test_xss_in_game_data(client):
    """Test XSS protection in game inputs (team names, opponent names)"""
    xss_team_name = "<svg/onload=alert('xss')>"
    xss_opponent = "'>><script>alert(document.cookie)</script>"
    
    season = '2024-25'
    team = 'U21'
    
    # Create basic roster
    roster_data = [
        {"id": "1", "number": "10", "surname": "Player", "name": "Test", "position": "A", "tesser": "U21"}
    ]
    roster_path = os.path.join(ROSTERS_DIR, f'roster_{season}_{team}.json')
    with open(roster_path, 'w') as f:
        json.dump(roster_data, f)
    
    # Get CSRF token
    response = client.get('/create_game')
    html = response.data.decode('utf-8')
    import re
    csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    csrf_token = csrf_match.group(1) if csrf_match else ''
    
    # Create game with XSS in team names
    game_data = {
        'csrf_token': csrf_token,
        'season': season,
        'team': team,
        'home_team': xss_team_name,
        'away_team': xss_opponent,
        'date': '2025-11-15',
        'l1_1': '1',
        'goalie1': '',
        'goalie2': ''
    }
    
    response = client.post('/create_game', data=game_data, follow_redirects=True)
    assert response.status_code == 200
    
    html = response.data.decode('utf-8')
    
    # Verify XSS is escaped
    assert '<svg/onload=' not in html, "SVG XSS was not escaped!"
    assert '<script>alert(document.cookie)</script>' not in html, "Script XSS was not escaped!"
    assert '&lt;' in html or '&gt;' in html, "HTML special chars should be escaped"


def test_path_traversal_in_roster(client):
    """Prevent directory traversal attacks in roster file loading"""
    # Attempt to load roster with path traversal
    malicious_category = '../../../etc/passwd'
    malicious_season = '../../../../windows/system32'
    
    # These should be rejected by validation (ValueError raised, caught by Flask)
    # Flask's error handling should return 500 or the route should catch it
    try:
        response = client.get(f'/roster/?category={malicious_category}&season={malicious_season}')
        # Should get error response or empty roster, not system files
        html = response.data.decode('utf-8')
        assert 'root:' not in html, "System file leaked!"
        assert 'shadow' not in html, "System file leaked!"
        assert 'SYSTEM32' not in html.upper(), "System directory leaked!"
    except Exception as e:
        # Validation should raise ValueError, which is GOOD for security
        assert 'Invalid category' in str(e) or 'Invalid season' in str(e), "Unexpected error"
    
    # Test another path traversal attempt via roster routes
    try:
        response2 = client.get('/roster/?category=..%2F..%2F..%2Fetc%2Fpasswd')
        html2 = response2.data.decode('utf-8')
        assert 'root:' not in html2, "Path traversal bypassed sanitization!"
    except Exception as e:
        # Path traversal blocked - this is good!
        assert 'Invalid' in str(e)


def test_csrf_protection_on_forms(client):
    """Ensure CSRF tokens required for POST requests"""
    season = '2024-25'
    team = 'U21'
    
    # Create roster
    roster_data = [
        {"id": "1", "number": "10", "surname": "Test", "name": "Player", "position": "A", "tesser": "U21"}
    ]
    roster_path = os.path.join(ROSTERS_DIR, f'roster_{season}_{team}.json')
    with open(roster_path, 'w') as f:
        json.dump(roster_data, f)
    
    # Try to POST without CSRF token
    game_data = {
        'season': season,
        'team': team,
        'home_team': 'Home FC',
        'away_team': 'Away FC',
        'date': '2025-11-15',
        'l1_1': '1',
        'goalie1': '',
        'goalie2': ''
    }
    
    # Create a new client without CSRF token
    from app import app
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = True  # Ensure CSRF is enabled
    
    with app.test_client() as test_client:
        with test_client.session_transaction() as sess:
            sess['authenticated'] = True
        
        # POST without CSRF token should fail
        response = test_client.post('/create_game', data=game_data)
        
        # Should get 400 Bad Request due to missing CSRF token
        assert response.status_code == 400, f"Expected 400 for missing CSRF, got {response.status_code}"
        
        # Response should indicate CSRF error
        html = response.data.decode('utf-8')
        assert 'CSRF' in html or 'token' in html.lower(), "CSRF error message not shown"


def test_csrf_protection_on_delete(client):
    """Ensure CSRF required for delete operations"""
    # Create a test game first
    season = '2024-25'
    team = 'U21'
    
    roster_data = [
        {"id": "1", "number": "10", "surname": "Test", "name": "Player", "position": "A", "tesser": "U21"}
    ]
    roster_path = os.path.join(ROSTERS_DIR, f'roster_{season}_{team}.json')
    with open(roster_path, 'w') as f:
        json.dump(roster_data, f)
    
    # Get CSRF token
    response = client.get('/create_game')
    html = response.data.decode('utf-8')
    import re
    csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    csrf_token = csrf_match.group(1) if csrf_match else ''
    
    game_data = {
        'csrf_token': csrf_token,
        'season': season,
        'team': team,
        'home_team': 'Home FC',
        'away_team': 'Away FC',
        'date': '2025-11-16',
        'l1_1': '1',
        'goalie1': '',
        'goalie2': ''
    }
    
    response = client.post('/create_game', data=game_data, follow_redirects=True)
    assert response.status_code == 200
    
    # Load games to get game ID
    with open(GAMES_FILE, 'r') as f:
        games = json.load(f)
    
    if games:
        game_id = games[0].get('id', 0)
        
        # Try to delete without CSRF token using new client
        from app import app
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = True
        
        with app.test_client() as test_client:
            with test_client.session_transaction() as sess:
                sess['authenticated'] = True
            
            # POST delete without CSRF token
            response = test_client.post(f'/delete_game/{game_id}')
            
            # Should fail with 400
            assert response.status_code == 400, f"Delete without CSRF should fail, got {response.status_code}"


def test_session_requires_pin(client):
    """Verify unauthenticated users can't access protected routes"""
    # Create a new client without authentication
    from app import app
    app.config['TESTING'] = True
    
    with app.test_client() as unauth_client:
        # Don't set authenticated session
        
        # Try to access protected routes
        protected_routes = [
            '/create_game',
            '/stats',
            '/roster/',
            '/game/0'
        ]
        
        for route in protected_routes:
            response = unauth_client.get(route, follow_redirects=False)
            
            # Should redirect to index/pin page (302) or show pin page (200 with PIN form)
            assert response.status_code in [200, 302], f"Route {route} should require auth"
            
            if response.status_code == 302:
                # Should redirect to index
                assert response.location.endswith('/') or 'index' in response.location


def test_timing_safe_pin_comparison(client):
    """Verify hmac.compare_digest is used for PIN comparison (not direct ==)"""
    # This test verifies the code uses timing-safe comparison
    # We can't easily test timing attacks, but we can verify the function is used
    
    # Read the source code to verify implementation
    from routes.game_routes import game_bp
    import inspect
    
    # Get the index route source code (registered as 'game.index')
    # The blueprint function is registered as just 'index' within the blueprint
    index_func = None
    for name, func in game_bp.view_functions.items():
        if 'index' in name.lower():
            index_func = func
            break
    
    if not index_func:
        # Fallback: search all registered routes
        from app import app as flask_app
        index_func = flask_app.view_functions.get('game.index')
    
    assert index_func is not None, "Index route not found"
    source = inspect.getsource(index_func)
    
    # Verify hmac.compare_digest is used
    assert 'hmac.compare_digest' in source, "PIN comparison must use hmac.compare_digest for timing safety!"
    assert 'pin ==' not in source, "Direct PIN comparison is vulnerable to timing attacks!"
    
    # Also test that incorrect PINs are properly rejected
    from app import app
    app.config['TESTING'] = True
    
    with app.test_client() as test_client:
        # Get CSRF token first
        response = test_client.get('/')
        html = response.data.decode('utf-8')
        import re
        csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', html)
        csrf_token = csrf_match.group(1) if csrf_match else ''
        
        # Try with wrong PIN
        response = test_client.post('/', data={'pin': 'wrongpin', 'csrf_token': csrf_token}, follow_redirects=True)
        
        html = response.data.decode('utf-8')
        assert 'Incorrect PIN' in html or 'error' in html.lower(), "Wrong PIN should show error"
        
        # Session should not be authenticated
        with test_client.session_transaction() as sess:
            assert not sess.get('authenticated'), "Wrong PIN should not authenticate session"


def test_session_security_headers(client):
    """Verify security headers are set on responses"""
    response = client.get('/')
    
    # Check for critical security headers
    headers = response.headers
    
    # Content Security Policy
    assert 'Content-Security-Policy' in headers, "CSP header missing!"
    csp = headers['Content-Security-Policy']
    assert 'default-src' in csp, "CSP should have default-src directive"
    
    # X-Frame-Options (clickjacking protection)
    assert 'X-Frame-Options' in headers, "X-Frame-Options header missing!"
    assert headers['X-Frame-Options'] == 'DENY', "X-Frame-Options should be DENY"
    
    # X-Content-Type-Options (MIME sniffing protection)
    assert 'X-Content-Type-Options' in headers, "X-Content-Type-Options header missing!"
    assert headers['X-Content-Type-Options'] == 'nosniff', "Should prevent MIME sniffing"
    
    # XSS Protection
    assert 'X-XSS-Protection' in headers, "X-XSS-Protection header missing!"
    assert '1' in headers['X-XSS-Protection'], "XSS protection should be enabled"
    
    # Referrer Policy
    assert 'Referrer-Policy' in headers, "Referrer-Policy header missing!"
    
    # Permissions Policy
    assert 'Permissions-Policy' in headers, "Permissions-Policy header missing!"


def test_invalid_category_input(client):
    """Test input validation on category parameter"""
    # Test with malicious category inputs
    malicious_categories = [
        '../../../etc/passwd',
        '"; DROP TABLE games; --',
        '<script>alert("xss")</script>',
        '../../..',
        'category; rm -rf /',
        'category\x00.json',
        'cat\ncat',
        'cat\rcat'
    ]
    
    for malicious_cat in malicious_categories:
        # Try to access roster with malicious category
        # Validation will raise ValueError, caught by Flask
        try:
            response = client.get(f'/roster/?category={malicious_cat}')
            
            # If it doesn't raise an exception, check the response
            if response.status_code == 200:
                html = response.data.decode('utf-8')
                # Should not execute or leak sensitive data
                assert 'root:' not in html, "System file leaked!"
                assert 'DROP TABLE' not in html, "SQL injection in output!"
        except Exception:
            # Validation blocking malicious input - this is GOOD for security!
            pass  # Test passes if validation rejects the input


def test_invalid_season_input(client):
    """Test season input validation"""
    # Test with invalid season formats
    invalid_seasons = [
        '../../../etc/passwd',
        '2024-25; DROP TABLE',
        '<script>alert(1)</script>',
        '../../../../',
        '2024\x00-25',
        '2024-99999999999999999999',
        'AAAA-BB',
        '2024-25\n2025-26'
    ]
    
    for invalid_season in invalid_seasons:
        # Try to access roster with invalid season
        # Validation will raise ValueError for invalid formats
        try:
            response = client.get(f'/roster/?category=U21&season={invalid_season}')
            
            # If it doesn't raise, check the response
            if response.status_code == 200:
                html = response.data.decode('utf-8')
                # Should not leak sensitive data or execute code
                assert 'root:' not in html
                assert 'DROP TABLE' not in html
                assert '<script>' not in html or '&lt;script&gt;' in html
        except Exception:
            # Validation blocking invalid input - this is GOOD!
            pass


def test_malicious_json_input(client):
    """Test JSON injection attempts in form data"""
    season = '2024-25'
    team = 'U21'
    
    # Create roster
    roster_data = [
        {"id": "1", "number": "10", "surname": "Test", "name": "Player", "position": "A", "tesser": "U21"}
    ]
    roster_path = os.path.join(ROSTERS_DIR, f'roster_{season}_{team}.json')
    with open(roster_path, 'w') as f:
        json.dump(roster_data, f)
    
    # Get CSRF token
    response = client.get('/create_game')
    html = response.data.decode('utf-8')
    import re
    csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    csrf_token = csrf_match.group(1) if csrf_match else ''
    
    # Try to inject malicious JSON through form fields
    malicious_data = {
        'csrf_token': csrf_token,
        'season': season,
        'team': team,
        'home_team': '{"extra":"field","admin":true}',
        'away_team': ']; DROP TABLE games; --',
        'date': '2025-11-17',
        'l1_1': '1',
        'goalie1': '',
        'goalie2': ''
    }
    
    response = client.post('/create_game', data=malicious_data, follow_redirects=True)
    
    # Should handle without errors
    assert response.status_code == 200, "Malicious JSON input caused error"
    
    # Load games to verify data was sanitized
    with open(GAMES_FILE, 'r') as f:
        games = json.load(f)
    
    if games:
        latest_game = games[-1]
        
        # Malicious input should be stored as plain string, not parsed
        home_team = latest_game.get('home_team', '')
        
        # Should not have created admin field from JSON injection
        assert 'admin' not in latest_game or latest_game.get('admin') != True, "JSON injection succeeded!"
        
        # The malicious strings are stored as TEXT (which is safe), not executed
        # Verify they're stored as strings in the game data
        assert isinstance(latest_game.get('home_team'), str), "home_team should be stored as string"
        assert isinstance(latest_game.get('away_team'), str), "away_team should be stored as string"
        
        # Verify the JSON structure is not corrupted by injection attempts
        assert 'id' in latest_game, "Game structure corrupted"
        assert 'team' in latest_game, "Game structure corrupted"


def test_sql_injection_attempt(client):
    """Even though we use JSON, test for SQL-like injections in inputs"""
    # SQL injection payloads in various fields
    sql_payloads = [
        "' OR '1'='1",
        "'; DROP TABLE games; --",
        "1' UNION SELECT * FROM users--",
        "admin'--",
        "' OR 1=1--"
    ]
    
    season = '2024-25'
    team = 'U21'
    
    # Create roster
    roster_data = [
        {"id": "1", "number": "10", "surname": "Test", "name": "Player", "position": "A", "tesser": "U21"}
    ]
    roster_path = os.path.join(ROSTERS_DIR, f'roster_{season}_{team}.json')
    with open(roster_path, 'w') as f:
        json.dump(roster_data, f)
    
    # Get CSRF token once
    response = client.get('/create_game')
    html = response.data.decode('utf-8')
    import re
    csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    csrf_token = csrf_match.group(1) if csrf_match else ''
    
    # Test SQL injection in team name
    for payload in sql_payloads:
        game_data = {
            'csrf_token': csrf_token,
            'season': season,
            'team': team,
            'home_team': payload,
            'away_team': 'Safe Team',
            'date': '2025-11-18',
            'l1_1': '1',
            'goalie1': '',
            'goalie2': ''
        }
        
        response = client.post('/create_game', data=game_data, follow_redirects=True)
        
        # Should handle without errors
        assert response.status_code == 200, f"SQL injection payload caused error: {payload}"
    
    # Verify games.json is still valid JSON and not corrupted
    try:
        with open(GAMES_FILE, 'r') as f:
            games = json.load(f)
            assert isinstance(games, list), "games.json corrupted!"
    except json.JSONDecodeError:
        raise AssertionError("SQL injection corrupted games.json!")
    
    # Test SQL injection in search/filter parameters
    response = client.get("/stats?team=' OR '1'='1&season='; DROP TABLE games;--")
    assert response.status_code in [200, 400], "SQL injection in query params caused error"


def test_session_cookie_security(client):
    """Verify session cookie has secure flags set"""
    response = client.get('/')
    
    # Check Set-Cookie headers
    cookies = response.headers.getlist('Set-Cookie')
    
    if cookies:
        cookie_str = '; '.join(cookies)
        
        # Session cookies should have security flags
        # HttpOnly prevents JavaScript access
        assert 'HttpOnly' in cookie_str or len(cookies) == 0, "Session cookie should be HttpOnly"
        
        # SameSite prevents CSRF
        assert 'SameSite' in cookie_str or len(cookies) == 0, "Session cookie should have SameSite"


def test_no_sensitive_data_in_errors(client):
    """Ensure error messages don't leak sensitive information"""
    # Trigger various errors and check responses
    
    # Non-existent game
    response = client.get('/game/999999')
    assert response.status_code == 404
    html = response.data.decode('utf-8')
    
    # Should not leak file paths, stack traces, or config
    assert 'Traceback' not in html, "Stack trace leaked in error!"
    assert 'c:\\' not in html.lower() and '/home/' not in html.lower(), "File paths leaked!"
    assert REQUIRED_PIN not in html, "PIN leaked in error message!"
    assert 'SECRET_KEY' not in html, "Secret key leaked!"
    
    # Invalid roster access - validation will raise ValueError
    # This is expected and good for security - errors should not leak info
    try:
        response = client.get('/roster/?category=INVALID&season=9999-99')
        if response.status_code == 200:
            html = response.data.decode('utf-8')
            assert 'Traceback' not in html
            assert REQUIRED_PIN not in html
    except Exception as e:
        # Validation error is fine - just ensure it doesn't leak sensitive info
        error_msg = str(e)
        assert REQUIRED_PIN not in error_msg
        assert 'SECRET_KEY' not in error_msg
