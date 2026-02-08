"""
Security utilities for input sanitization and validation
"""
import os
import re


def sanitize_filename(filename):
    """Sanitize filename to prevent path traversal and other attacks."""
    if not filename:
        return None
    # Remove any directory separators and parent directory references
    filename = os.path.basename(filename)
    # Allow only alphanumeric, underscore, hyphen, and dot
    filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
    # Prevent hidden files
    if filename.startswith('.'):
        filename = '_' + filename[1:]
    return filename


def validate_category(category):
    """Validate category input to prevent injection attacks."""
    if not category:
        return False
    # Only allow alphanumeric and specific allowed characters
    return bool(re.match(r'^[a-zA-Z0-9_-]+$', category))


def validate_season(season):
    """Validate season input (e.g., 2024-25)."""
    if not season:
        return True  # Empty season is allowed for backward compatibility
    # Allow format like 2024-25 or just 2024
    return bool(re.match(r'^\d{4}(-\d{2})?$', season))
