"""
Input validation and formatting utilities
"""


def format_date(date_str):
    """Format date from YYYY-MM-DD to DD.MM.YYYY for display"""
    try:
        if not date_str:
            return date_str
        parts = str(date_str).split('-')
        if len(parts) == 3:
            return f"{parts[2]}.{parts[1]}.{parts[0]}"
    except Exception:
        pass
    return date_str
