from datetime import datetime


def parse_timestamp(timestamp: str) -> int|None:
    """Helper function to automatically parse a timestamp string into a
        Unix epoch timestamp. Returns None if the timestamp is invalid.
        Supports:
        - Unix epoch as integer string (e.g., "1234567890")
        - Unix epoch as float string (e.g., "1234567890.123")
        - ISO 8601 format strings (e.g., "2023-01-01T00:00:00Z")
        - Other datetime formats parseable by datetime.fromisoformat() or datetime.strptime()
    """
    if type(timestamp) is not str:
        raise ValueError('timestamp must be a string')

    if not timestamp:
        return 0

    # try parsing result of str(time())
    try:
        return int(float(timestamp))
    except (ValueError, TypeError):
        pass

    # try ISO 8601 format
    try:
        if 'T' in timestamp or '+' in timestamp or timestamp.endswith('Z'):
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        else:
            # Try parsing without timezone
            dt = datetime.fromisoformat(timestamp)
        return int(dt.timestamp())
    except (ValueError, TypeError):
        pass

    # try some other common formats
    common_formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M:%S.%f',
        '%Y/%m/%d %H:%M:%S',
        '%d/%m/%Y %H:%M:%S',
        '%m/%d/%Y %H:%M:%S',
    ]
    for fmt in common_formats:
        try:
            dt = datetime.strptime(timestamp, fmt)
            return int(dt.timestamp())
        except (ValueError, TypeError):
            continue

    return None
