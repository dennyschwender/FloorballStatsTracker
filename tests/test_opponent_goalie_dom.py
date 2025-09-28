import json
import os

import pytest


def load_games_file():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    path = os.path.join(root, 'gamesFiles', 'games.json')
    with open(path, 'r') as f:
        return json.load(f)


def test_opponent_goalie_goals_span_present_and_numeric(client):
    games = load_games_file()
    # pick game id 2 (exists in fixture data used by dev)
    game_id = 2
    # guard: ensure game exists
    assert game_id < len(games)
    game = games[game_id]
    # expected value from stored file
    expected = 0
    if game.get('opponent_goalie_goals_conceded') and 'Opponent Goalie' in game['opponent_goalie_goals_conceded']:
        expected = game['opponent_goalie_goals_conceded']['Opponent Goalie']

    # fetch rendered page
    rv = client.get(f'/game/{game_id}')
    assert rv.status_code == 200
    html = rv.get_data(as_text=True)
    # The template adds an id only in dev runs; check both cases:
    if 'id="opponent-goalie-goals"' in html:
        # extract the span content
        start = html.find('id="opponent-goalie-goals"')
        # find the closing > of the span
        span_open = html.find('>', start)
        span_close = html.find('</span>', span_open)
        assert span_open != -1 and span_close != -1
        content = html[span_open+1:span_close].strip()
        # numeric content expected
        assert content.isdigit() or (content.replace('.', '', 1).isdigit() and content.count('.')<=1)
        assert int(float(content)) == int(expected)
    else:
        # Fallback: the server-side should still render a fw-bold span with the numeric value
        assert '<span class="fw-bold">' in html
        # best-effort: ensure the expected number appears near the Opponent Goalie header
        header_idx = html.find('Opponent Goalie')
        assert header_idx != -1
        snippet = html[header_idx: header_idx + 400]
        assert str(expected) in snippet
