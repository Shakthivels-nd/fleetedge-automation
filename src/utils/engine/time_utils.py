import time
from datetime import datetime, timezone


def validate_size_range(min_size, size, max_size, inclusive=True):
    """Validate that numeric size lies within [min_size, max_size] (or (min,max) if inclusive=False).
    Returns a dict: {status, size, min_size, max_size, details} without using global state.
    Coerces inputs to float; fails gracefully if conversion invalid or bounds reversed.
    """
    details = []
    try:
        size_val = float(size)
        min_val = float(min_size)
        max_val = float(max_size)
    except (TypeError, ValueError) as e:
        return {
            'status': 'Fail',
            'size': size,
            'min_size': min_size,
            'max_size': max_size,
            'details': [f"Conversion error: {e}"]
        }
    if min_val > max_val:
        return {
            'status': 'Fail',
            'size': size_val,
            'min_size': min_val,
            'max_size': max_val,
            'details': ["Invalid bounds: min_size greater than max_size"]
        }

    if inclusive:
        in_range = (min_val <= size_val <= max_val)
        range_desc = f"[{min_val}, {max_val}]"
    else:
        in_range = (min_val < size_val < max_val)
        range_desc = f"({min_val}, {max_val})"

    if in_range:
        details.append(f"Size {size_val} within range {range_desc}")
        status = 'Pass'
    else:
        details.append(f"Size {size_val} outside range {range_desc}")
        status = 'Fail'
    return {
        'status': status,
        'size': size_val,
        'min_size': min_val,
        'max_size': max_val,
        'details': details
    }


def get_current_time_utc():
    """Return current UTC time string (YYYY-MM-DD HH:MM:SS) with status and details.
    Framework style: no self, structured dict output.
    """
    details = []
    try:
        current_utc_time = datetime.now(timezone.utc)
        ts_str = current_utc_time.strftime('%Y-%m-%d %H:%M:%S')
        details.append(f"UTC time: {ts_str}")
        return {
            'status': 'Pass',
            'utc_time': ts_str,
            'details': details
        }
    except Exception as e:
        details.append(f"Error retrieving UTC time: {e}")
        return {
            'status': 'Fail',
            'utc_time': None,
            'details': details
        }

def get_current_time_epoch():
    """Return current UTC epoch time with status and details.
    Framework style: returns dict (no globals).
    Provides both milliseconds and seconds since Unix epoch.
    Keys: status, epoch_ms, epoch_seconds, details.
    """
    details = []
    try:
        now_seconds = time.time()  # float seconds
        epoch_ms = int(now_seconds * 1000)
        epoch_seconds = int(now_seconds)
        details.append(f"Epoch ms: {epoch_ms}")
        details.append(f"Epoch seconds: {epoch_seconds}")
        return {
            'status': 'Pass',
            'epoch_ms': epoch_ms,
            'epoch_seconds': epoch_seconds,
            'details': details
        }
    except Exception as e:
        details.append(f"Error retrieving epoch time: {e}")
        return {
            'status': 'Fail',
            'epoch_ms': None,
            'epoch_seconds': None,
            'details': details
        }


def compare_time_difference_hms(timestamp1, expected_difference_minutes, timestamp2):
    """Compare two HH:MM:SS timestamps and evaluate if their difference (in minutes)
    is <= expected_difference_minutes. Framework style (returns dict, no globals).
    Args:
        timestamp1: earlier time as 'HH:MM:SS' (optionally with trailing ',ms'), datetime, or epoch ms/int seconds.
        expected_difference_minutes: threshold minutes (int/float).
        timestamp2: later time in same formats as timestamp1.
    Returns dict:
        status: Pass/Fail
        difference_minutes: computed float difference (or None on error)
        expected_difference_minutes: original threshold
        within_expected: bool or None
        details: list of messages
    """
    details = ["compare_time_difference_hms invoked"]

    def normalize(ts):
        if ts is None:
            return None
        # If numeric: treat as epoch seconds or ms
        if isinstance(ts, (int, float)):
            # Heuristic: 13-digit => ms, 10-digit => seconds
            val = int(ts)
            if len(str(val)) == 13:
                return datetime.utcfromtimestamp(val / 1000.0)
            elif len(str(val)) == 10:
                return datetime.utcfromtimestamp(val)
            else:
                # Fallback assume seconds
                return datetime.utcfromtimestamp(val)
        # If datetime already
        if hasattr(ts, 'year') and hasattr(ts, 'hour'):
            return ts
        if isinstance(ts, str):
            raw = ts.split(',')[0].strip()
            # Accept only HH:MM:SS format here
            try:
                return datetime.strptime(raw, '%H:%M:%S')
            except ValueError:
                details.append(f"Unsupported time string format: {ts}")
                return None
        details.append(f"Unrecognized timestamp type: {type(ts)}")
        return None

    dt1 = normalize(timestamp1)
    dt2 = normalize(timestamp2)

    if not dt1 or not dt2:
        return {
            'status': 'Fail',
            'difference_minutes': None,
            'expected_difference_minutes': expected_difference_minutes,
            'within_expected': None,
            'details': details + ["Failed to parse one or both timestamps"]
        }

    # If only time-of-day (no date), dt objects will default to same date (Jan 1 1900); allow negative -> swap
    diff_seconds = (dt2 - dt1).total_seconds()
    if diff_seconds < 0:
        # Swap if order reversed
        diff_seconds = (dt1 - dt2).total_seconds()
        details.append("Timestamps out of order; auto-swapped")

    diff_minutes = diff_seconds / 60.0
    within = diff_minutes <= float(expected_difference_minutes)
    if within:
        details.append(f"Difference {diff_minutes:.2f}m <= expected {expected_difference_minutes}m")
        status = 'Pass'
    else:
        details.append(f"Difference {diff_minutes:.2f}m > expected {expected_difference_minutes}m")
        status = 'Fail'

    return {
        'status': status,
        'difference_minutes': diff_minutes,
        'expected_difference_minutes': expected_difference_minutes,
        'within_expected': within,
        'details': details
    }
