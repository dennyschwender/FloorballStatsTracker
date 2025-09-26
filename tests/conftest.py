import sys
import os

# ensure project root is on sys.path so tests can import app
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest  # noqa: E402
from app import app  # noqa: E402


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        # mark the test session as authenticated so routes are accessible
        with client.session_transaction() as sess:
            sess['authenticated'] = True
        yield client
