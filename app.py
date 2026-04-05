"""
FloorballStatsTracker - Main Application Entry Point
Refactored for clean modular architecture
"""
import os
import secrets
from flask import Flask, session, g, request, redirect, url_for, render_template
from flask_wtf.csrf import CSRFProtect
from urllib.parse import urlparse

# Import configuration
from config import FLASK_CONFIG, LANGUAGES, TRANSLATIONS

# Import utils
from utils.validators import format_date

# Import database + models (models must be imported before db.create_all)
from models.database import db
import models  # noqa: F401 — registers GameRecord, RosterPlayer, User, TeamPermission, TeamSettings

# Import route blueprints
from routes import game_bp, roster_bp, stats_bp, api_bp, admin_bp

# Import shared extensions
from extensions import limiter


_NEW_TEXT_COLUMNS = {
    'games': ['block_shots', 'stolen_balls'],
    'users': None,         # whole table — handled by create_all
    'team_permissions': None,
    'team_settings': None,
}


def _migrate_db(database):
    """Add newly introduced columns to existing SQLite tables.

    SQLAlchemy's create_all only creates *new* tables; it never alters
    existing ones.  We therefore inspect the live DB and issue
    ALTER TABLE … ADD COLUMN for any column that is missing.
    """
    from sqlalchemy import inspect, text
    inspector = inspect(database.engine)
    existing_tables = inspector.get_table_names()

    for table, new_cols in _NEW_TEXT_COLUMNS.items():
        if new_cols is None or table not in existing_tables:
            continue
        existing_cols = {c['name'] for c in inspector.get_columns(table)}
        for col in new_cols:
            if col not in existing_cols:
                with database.engine.connect() as conn:
                    conn.execute(text(
                        f"ALTER TABLE {table} ADD COLUMN {col} TEXT NOT NULL DEFAULT '{{}}'"
                    ))
                    conn.commit()


def create_app():
    """Application factory pattern"""
    app = Flask(__name__)

    # Apply configuration
    app.config.update(FLASK_CONFIG)

    # Initialise SQLAlchemy
    db.init_app(app)

    # Initialise rate limiter
    limiter.init_app(app)

    # Ensure the gamesFiles directory exists, then create DB tables
    db_dir = os.path.dirname(
        app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
    )
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    with app.app_context():
        db.create_all()
        # Migrate: add any new columns that don't yet exist in the DB
        _migrate_db(db)

    # Initialize CSRF protection
    csrf = CSRFProtect(app)

    # Disable CSRF in testing mode for easier test execution
    if app.config.get('TESTING', False):
        app.config['WTF_CSRF_ENABLED'] = False

    # Register template helpers
    app.jinja_env.globals['format_date'] = format_date

    # ── Before-request handlers ───────────────────────────────────────────────

    @app.before_request
    def set_language():
        """Set language for each request"""
        default = app.config.get('DEFAULT_LANG', 'en')
        lang = session.get('lang', default)
        if lang not in LANGUAGES:
            lang = default
        g.lang = lang
        g.t = TRANSLATIONS[lang]
        # Expose current game id (if any) to templates in a stable way
        try:
            vid = request.view_args.get('game_id') if request.view_args else None
        except Exception:
            vid = None
        g.current_game_id = vid
        # Expose current user object to templates (None for PIN-sessions/tests)
        from models.auth_models import User as _User
        uid = session.get('user_id')
        g.current_user = db.session.get(_User, uid) if uid else None
        # Only sessions explicitly flagged at login (admin PIN or admin user flow)
        g.is_admin_session = bool(session.get('is_admin_session'))

    @app.before_request
    def generate_csp_nonce():
        """Generate a unique nonce per request for Content-Security-Policy."""
        g.csp_nonce = secrets.token_urlsafe(16)

    @app.before_request
    def require_login():
        """Protect all routes except static, pin page and user login."""
        allowed_routes = ['game.index', 'game.user_login', 'stats.stats', 'static']
        if request.endpoint not in allowed_routes and not session.get('authenticated'):
            return redirect(url_for('game.index'))

    # ── After-request handlers ────────────────────────────────────────────────

    @app.after_request
    def set_security_headers(response):
        """Add security headers to all responses"""
        nonce = getattr(g, 'csp_nonce', '')
        # Content Security Policy — nonce replaces unsafe-inline for scripts
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            f"script-src 'self' 'nonce-{nonce}' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: blob:; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "connect-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "frame-ancestors 'none';"
        )
        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'DENY'
        # Prevent MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        # Enable XSS filter (legacy browsers)
        response.headers['X-XSS-Protection'] = '1; mode=block'
        # Referrer policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        # Permissions policy
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'

        return response

    # ── Language switching route ──────────────────────────────────────────────

    @app.route('/set_language', methods=['POST'])
    def set_language_route():
        """Change application language"""
        default = app.config.get('DEFAULT_LANG', 'en')
        lang = request.form.get('lang', default)
        # Security: Validate language input
        if lang not in LANGUAGES:
            lang = default
        session['lang'] = lang
        session.permanent = True  # Maintain session timeout
        # Redirect back to previous page or home safely
        ref = request.referrer or url_for('game.index')
        # Remove backslashes which some browsers accept
        safe_ref = ref.replace('\\', '')
        parsed = urlparse(safe_ref)
        if not parsed.netloc and not parsed.scheme:
            return redirect(safe_ref)
        return redirect(url_for('game.index'))

    # ── Custom error handlers ─────────────────────────────────────────────────

    @app.errorhandler(404)
    def not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('403.html'), 403

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return render_template('500.html'), 500

    # ── Register blueprints ───────────────────────────────────────────────────

    app.register_blueprint(game_bp)
    app.register_blueprint(roster_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)

    return app


# Create the application instance
app = create_app()


if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(debug=debug)
