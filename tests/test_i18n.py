def test_default_language_is_english(client):
    # default / should render English title
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'Floorball Stats Tracker' in rv.data


def test_switch_language_to_italian(client):
    # set language to Italian and verify translated header
    rv = client.post('/set_language', data={'lang': 'it'}, follow_redirects=True)
    assert rv.status_code in (200, 302)
    # After setting lang, next page load should show Italian strings
    rv2 = client.get('/')
    assert rv2.status_code == 200
    # Check for Italian translation - "no_games" message appears when there are no games
    assert b'Nessuna partita trovata' in rv2.data or b'Crea una nuova partita' in rv2.data


def test_switch_back_to_english(client):
    rv = client.post('/set_language', data={'lang': 'en'}, follow_redirects=True)
    assert rv.status_code in (200, 302)
    rv2 = client.get('/')
    assert rv2.status_code == 200
    # Check for English translation - "no_games" message appears when there are no games
    assert b'No games found' in rv2.data or b'Create a new game' in rv2.data
