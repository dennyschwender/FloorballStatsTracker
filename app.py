"""
FloorballStatsTracker - Main Application Entry Point
Refactored for clean modular architecture
"""
from flask import Flask, session, g, request, redirect, url_for
from flask_wtf.csrf import CSRFProtect
from urllib.parse import urlparse

# Import configuration
from config import FLASK_CONFIG, LANGUAGES, TRANSLATIONS

# Import utils
from utils.validators import format_date

# Import route blueprints
from routes import game_bp, roster_bp, stats_bp, api_bp


def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Apply configuration
    app.config.update(FLASK_CONFIG)
    
    # Initialize CSRF protection
    csrf = CSRFProtect(app)
    
    # Disable CSRF in testing mode for easier test execution
    if app.config.get('TESTING', False):
        app.config['WTF_CSRF_ENABLED'] = False
    
    # Register template helpers
    app.jinja_env.globals['format_date'] = format_date
    
    # Register before_request handlers
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
    
    @app.before_request
    def require_login():
        """Protect all routes except static and index/pin"""
        allowed_routes = ['game.index', 'static']
        if request.endpoint not in allowed_routes and not session.get('authenticated'):
            return redirect(url_for('game.index'))
    
    @app.after_request
    def set_security_headers(response):
        """Add security headers to all responses"""
        # Content Security Policy
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data:; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'DENY'
        # Prevent MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        # Enable XSS filter
        response.headers['X-XSS-Protection'] = '1; mode=block'
        # Referrer policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        # Permissions policy
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        return response
    
    # Language switching route
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
    
    # Register blueprints
    app.register_blueprint(game_bp)
    app.register_blueprint(roster_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(api_bp)
    
    return app


# Create the application instance
app = create_app()


if __name__ == '__main__':
    # Only enable debug mode if running directly with python app.py
    app.run(debug=True)
