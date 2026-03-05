"""
DEPRECATED — GameCache was used by the legacy JSON file backend.

The application now uses SQLite (via Flask-SQLAlchemy) which handles
caching and concurrency natively. This module is retained only to avoid
breaking any third-party scripts that may import it; it will be removed
in a future release.
"""


class GameCache:
    """No-op stub retained for backward compatibility. Do not use."""

    def get(self, filepath):  # noqa: ARG002
        return None

    def set(self, filepath, games):  # noqa: ARG002
        pass

    def invalidate(self):
        pass
