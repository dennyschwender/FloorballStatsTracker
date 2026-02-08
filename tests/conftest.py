import sys
import os

# ensure project root is on sys.path so tests can import app
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest  # noqa: E402
from app import app  # noqa: E402
import os


# Preserve games.json across tests by backing it up and restoring after each test session
@pytest.fixture(autouse=True)
def preserve_games_file():
    ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    games_path = os.path.join(ROOT, 'gamesFiles', 'games.json')
    orig = None
    if os.path.exists(games_path):
        with open(games_path, 'r') as f:
            orig = f.read()
    yield
    # restore
    if orig is None:
        try:
            os.remove(games_path)
        except OSError:
            pass
    else:
        with open(games_path, 'w') as f:
            f.write(orig)


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
    with app.test_client() as client:
        # mark the test session as authenticated so routes are accessible
        with client.session_transaction() as sess:
            sess['authenticated'] = True
        yield client
