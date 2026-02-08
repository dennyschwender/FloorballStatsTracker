"""
Performance optimization: In-memory cache for games.json
"""
import os
import threading


class GameCache:
    """In-memory cache for games.json with file modification time-based invalidation"""
    
    def __init__(self):
        self._cache = None
        self._mtime = None
        self._lock = threading.Lock()
    
    def get(self, filepath):
        """Get cached games if valid, otherwise return None"""
        with self._lock:
            if self._cache is None:
                return None
            
            # Check if file has been modified
            try:
                current_mtime = os.path.getmtime(filepath)
                if self._mtime != current_mtime:
                    # File has been modified, invalidate cache
                    self._cache = None
                    self._mtime = None
                    return None
            except OSError:
                # File doesn't exist or can't be accessed
                return None
            
            return self._cache
    
    def set(self, filepath, games):
        """Store games in cache with current file modification time"""
        with self._lock:
            try:
                self._mtime = os.path.getmtime(filepath)
                self._cache = games
            except OSError:
                # If we can't get mtime, don't cache
                self._cache = None
                self._mtime = None
    
    def invalidate(self):
        """Invalidate the cache (call after writes)"""
        with self._lock:
            self._cache = None
            self._mtime = None
