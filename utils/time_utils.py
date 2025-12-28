from datetime import datetime, timezone, timedelta
import config

def get_current_time():
    """Returns basic datetime.utcnow() + offset."""
    # Use timezone-aware UTC then apply offset
    utc_now = datetime.now(timezone.utc)
    # Apply offset
    local_time = utc_now + timedelta(hours=config.TIMEZONE_OFFSET)
    # Return naive or aware? The prompt implies "Match current minute using UTC + TIMEZONE_OFFSET (3)".
    # Usually easier to work with naive if comparing to simple strings, but let's keep it clean.
    # We'll return a naive datetime representing that wall time.
    return local_time.replace(tzinfo=None) # Make naive for easy string formatting/comparison

def parse_sheet_time(date_str: str, time_str: str) -> datetime:
    """
    Parses date (YYYY-MM-DD or similar) and time (H:MM or HH:MM).
    Returns a naive datetime object.
    """
    # Normalize inputs
    if not date_str or not time_str:
        return None

    # Handle some variations if needed, but standard strptime is usually enough if format is consistent.
    # User said "Support YYYY-MM-DD and H:MM vs HH:MM"
    # date_str might be "2025-12-28"
    # time_str might be "8:05" or "08:05"
    
    full_str = f"{date_str.strip()} {time_str.strip()}"
    try:
        # Try primary format
        return datetime.strptime(full_str, "%Y-%m-%d %H:%M")
    except ValueError:
        try:
            # Maybe time uses seconds? Or date uses slashes?
            # Re-try with flexible handling if strictly needed, but %H:%M handles 8:05 and 08:05.
            # Maybe date uses / ?
            return datetime.strptime(full_str, "%Y/%m/%d %H:%M")
        except ValueError:
            return None
