import os
import sys
import tempfile

# ── Test environment setup ────────────────────────────────────────────────────
# Set required env vars BEFORE importing app so config.py doesn't raise.
os.environ.setdefault('FLOORBALL_PIN', 'testpin123')
os.environ.setdefault('FLASK_SECRET_KEY', 'test-secret-key-not-for-production')
os.environ.setdefault('SESSION_COOKIE_SECURE', 'False')

# Use a dedicated temp-file SQLite DB for the test session.
# A file DB is simpler than :memory: when multiple connections are involved.
_TEST_DB_FILE = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
_TEST_DB_FILE.close()
os.environ['DATABASE_URL'] = f'sqlite:///{_TEST_DB_FILE.name}'

# Ensure project root is on sys.path so tests can import app
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest  # noqa: E402
from app import app  # noqa: E402  – triggers create_app() and db.create_all()
from models.database import db  # noqa: E402


@pytest.fixture(autouse=True)
def app_ctx():
    """Push an application context for every test so DB calls work outside
    the request context (e.g. in test setup helpers)."""
    ctx = app.app_context()
    ctx.push()
    yield
    ctx.pop()


@pytest.fixture(autouse=True)
def clean_db(app_ctx):
    """Truncate all table data between tests so they run in isolation.
    Depends on app_ctx to ensure the app context is already pushed."""
    for table in reversed(db.metadata.sorted_tables):
        db.session.execute(table.delete())
    db.session.commit()
    yield


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
    with app.test_client() as client:
        # mark the test session as authenticated so routes are accessible
        with client.session_transaction() as sess:
            sess['authenticated'] = True
        yield client


# Ensure project root is on sys.path so tests can import app
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest  # noqa: E402
from app import app  # noqa: E402  – triggers create_app() and db.create_all()
from models.database import db  # noqa: E402


@pytest.fixture(autouse=True)
def clean_db():
    """Truncate all table data between tests so they run in isolation."""
    with app.app_context():
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()
    yield
    # post-test cleanup (nothing extra needed; next test does pre-test truncate)


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
    with app.test_client() as client:
        # mark the test session as authenticated so routes are accessible
        with client.session_transaction() as sess:
            sess['authenticated'] = True
        yield client
