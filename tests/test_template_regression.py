from app import app


def test_opponent_goalie_goals_conceded_render(client):
    """Check that opponent goalie goals conceded renders correctly in game detail template."""
    import json
    import os
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    path = os.path.join(root, 'gamesFiles', 'games.json')
    with open(path, 'r') as f:
        games = json.load(f)
    
    if not games:
        import pytest
        pytest.skip("No games in test data")
    
    # Use first game's actual ID
    game_id = games[0].get('id', 0)
    rv = client.get(f'/game/{game_id}')
    assert rv.status_code == 200
    html = rv.data.decode('utf-8')
    # Find the opponent goalie table section and ensure a numeric goals conceded is present
    start = html.find('<h3 class="mb-3">Opponent Goalie')
    assert start != -1
    snippet = html[start:start+800]
    # Expect at least one digit in the Goals Conceded column (e.g., '3')
    import re
    assert re.search(r'Goals Conceded', snippet)
    assert re.search(r'\b\d+\b', snippet)


def test_opponent_goalie_render_in_edit_mode():
    import json
    import os
    from app import app
    
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    path = os.path.join(root, 'gamesFiles', 'games.json')
    with open(path, 'r') as f:
        games = json.load(f)
    
    if not games:
        import pytest
        pytest.skip("No games in test data")
    
    # Use first game's actual ID
    game_id = games[0].get('id', 0)
    
    with app.test_client() as c:
        with c.session_transaction() as s:
            s['authenticated'] = True
        rv = c.get(f'/game/{game_id}?edit=1')
        assert rv.status_code == 200
        html = rv.data.decode('utf-8')
        start = html.find('<h3 class="mb-3">Opponent Goalie')
        assert start != -1
        snippet = html[start:start+800]
        import re
        assert re.search(r'Goals Conceded', snippet)
        assert re.search(r'\b\d+\b', snippet)
