"""
Shared Flask extensions — imported by app.py (init_app) and route modules.
"""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Key function: limit by remote IP.
# In production behind a reverse proxy set RATELIMIT_HEADERS_ENABLED=1
# and configure RATELIMIT_KEY_PREFIX to avoid header-spoofing.
limiter = Limiter(key_func=get_remote_address)
