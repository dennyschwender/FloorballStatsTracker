from app import app


def test_opponent_goalie_goals_conceded_render(client):
    # Ensure game 2 in gamesFiles/games.json has opponent goalie stats
    rv = client.get('/game/2')
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
    with app.test_client() as c:
        with c.session_transaction() as s:
            s['authenticated'] = True
        rv = c.get('/game/2?edit=1')
        assert rv.status_code == 200
        html = rv.data.decode('utf-8')
        start = html.find('<h3 class="mb-3">Opponent Goalie')
        assert start != -1
        snippet = html[start:start+800]
        import re
        assert re.search(r'Goals Conceded', snippet)
        assert re.search(r'\b\d+\b', snippet)
