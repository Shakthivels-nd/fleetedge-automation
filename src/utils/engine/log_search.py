import re
import shlex
import time
import calendar
from datetime import datetime

from ..logger import setup_logger
from .connection import run_command_on_pod

logger = setup_logger()

# Services whose logs are timestamped with UTC datetime strings at line start
# (e.g. "2026-09-08 10:00:00 - ...") rather than a leading epoch-ms token.
UTC_TIMESTAMP_SERVICES = {"otacheck", "keep_alive_manager", "scheduler_manager"}


def search_logs_in_pod(child, log_dir: str, search_term: str, start_timestamp: int = None, timeout: int = 60, interval: int = 5):
    """Periodically search for a term in all .log files inside a log directory within the pod,
    considering only logs after a given start timestamp.

    Enhancement: start_timestamp can now be provided as either epoch (ms/seconds) or UTC string
    in formats: 'YYYY-MM-DD HH:MM:SS' or 'YYYY:MM:DD HH:MM:SS'. Log lines may start with either
    an epoch (10/13 digits) or a UTC timestamp (optionally with ,mmm/.mmm milliseconds).

    If logs use epoch timestamps, current epoch ms is used when start_timestamp is None.
    If logs use UTC timestamps and a UTC start_timestamp string is provided, it will be parsed.
    (If None, current UTC time is converted to epoch ms.) Nothing else changed in behavior.
    """
    # Detect whether logs likely use UTC date-time format by sampling a few lines for search_term.
    detection_cmd = f"grep -Hn '{search_term}' {log_dir}/*.log 2>/dev/null | head -5 || true"
    detection_output = run_command_on_pod(child, detection_cmd) or ''
    utc_line_pattern = re.compile(r'^\d{4}[-:]\d{2}[-:]\d{2}\s+\d{2}:\d{2}:\d{2}')
    logs_use_utc = any(utc_line_pattern.search(line.split(':',2)[-1].strip()) for line in detection_output.splitlines())

    def _to_epoch_ms(ts):
        """Normalize start_timestamp value to epoch ms."""
        if ts is None:
            # Use current time (UTC basis) converted to epoch ms
            now = datetime.utcnow()
            return int(calendar.timegm(now.timetuple()) * 1000 + now.microsecond/1000.0)
        if isinstance(ts, (int, float)):
            val = int(ts)
            # 10-digit seconds -> ms
            if len(str(val)) == 10:
                val *= 1000
            return val
        if isinstance(ts, str):
            raw = ts.strip()
            if raw.isdigit():
                if len(raw) == 13:
                    return int(raw)
                if len(raw) == 10:
                    return int(raw) * 1000
                # Treat other lengths as seconds
                return int(raw) * 1000
            for fmt in ('%Y-%m-%d %H:%M:%S', '%Y:%m:%d %H:%M:%S'):
                try:
                    st = time.strptime(raw, fmt)
                    return int(calendar.timegm(st) * 1000)
                except ValueError:
                    continue
        # Fallback: current time
        now = datetime.utcnow()
        return int(calendar.timegm(now.timetuple()) * 1000 + now.microsecond/1000.0)

    start_epoch_ms = _to_epoch_ms(start_timestamp)

    logger.info(
        f"Searching for '{search_term}' in logs at {log_dir} after timestamp {start_epoch_ms} (UTC format detected={logs_use_utc}) with timeout {timeout}s..."
    )
    end_time = time.time() + timeout

    # Regex for UTC timestamp at start of content
    date_re = re.compile(r'^(\d{4}[-:]\d{2}[-:]\d{2})\s+(\d{2}:\d{2}:\d{2})(?:[,.](\d{1,3}))?')
    epoch_re = re.compile(r'^(\d{10}|\d{13})(?:\b|:)')

    def _extract_line_ts_ms(content):
        content = content.strip()
        # Try UTC date first
        m = date_re.match(content)
        if m:
            date_part, hms, ms_part = m.groups()
            for fmt in ('%Y-%m-%d %H:%M:%S', '%Y:%m:%d %H:%M:%S'):
                try:
                    st = time.strptime(f"{date_part} {hms}", fmt)
                    base_ms = int(calendar.timegm(st) * 1000)
                    if ms_part:
                        base_ms += int(ms_part.ljust(3, '0')[:3])
                    return base_ms
                except ValueError:
                    continue
        # Fallback epoch token at start
        m2 = epoch_re.match(content)
        if m2:
            token = m2.group(1)
            if len(token) == 13:
                return int(token)
            if len(token) == 10:
                return int(token) * 1000
        # Search inside content for a 13-digit epoch
        m3 = re.search(r'(\d{13})', content)
        if m3:
            return int(m3.group(1))
        return None

    while time.time() < end_time:
        cmd = f"grep -Hn '{search_term}' {log_dir}/*.log 2>/dev/null || true"
        output = run_command_on_pod(child, cmd)

        if output:
            filtered_lines = []
            for line in output.splitlines():
                parts = line.split(':', 2)
                if len(parts) < 3:
                    continue
                # parts[2] is remainder of line after filename + line number
                remainder = parts[2].strip()
                ts_val = _extract_line_ts_ms(remainder)
                if ts_val is not None and ts_val >= start_epoch_ms:
                    print(f"Matched line ts={ts_val}: {line}")
                    filtered_lines.append(line)
            if filtered_lines:
                result = "\n".join(filtered_lines)
                print(f"\nFound '{search_term}' in logs after {start_epoch_ms}:\n{result}\n")
                return result
        print(f"Log '{search_term}' not found yet after {start_epoch_ms}. Retrying in {interval}s...\n")
        time.sleep(interval)

    logger.warning(f"Timeout reached. '{search_term}' not found in logs after {start_epoch_ms}.")
    return None


def grep_logs(pod_connection, service, pattern, log_root="/home/ubuntu/.nddevice/log", since_ts=None):
    """
    Single-shot log search (no polling): grep a service's logs for a pattern,
    optionally restricted to lines after since_ts.

    Unlike search_logs_in_pod (which polls until found or timeout), this runs
    the grep exactly once and returns immediately, including the first/last
    5 lines of the log for context when the pattern is not found.

    Args:
        pod_connection: active pexpect spawn to the pod.
        service: service name (subdirectory under log_root).
        pattern: grep pattern (basic regex when since_ts is None, since the
            command line uses BRE there; extended-regex-looking patterns are
            still matched correctly via grep's own matching either way).
        log_root: root log directory on the device.
        since_ts: epoch-ms timestamp (int/str). Only lines after this are
            considered. If the service is UTC-timestamped (see
            UTC_TIMESTAMP_SERVICES), since_ts is converted to a UTC
            datetime string for comparison; otherwise lines are expected to
            start with "<epoch-ms>:" and are compared numerically.

    Returns dict: {status: 'Pass'/'Fail', output: str, details: [str, ...]}
    """
    details = []
    log_path = f"{log_root}/{service}"
    q_pattern = shlex.quote(pattern)
    q_log_path = shlex.quote(log_path)

    if since_ts:
        normalized_service = service.strip().lower()
        if normalized_service in UTC_TIMESTAMP_SERVICES:
            # otacheck/keep_alive_manager/scheduler_manager use UTC datetime logs
            epoch_sec = str(int(since_ts) // 1000)
            cmd = (
                f"grep -ihE {q_pattern} {q_log_path}/* 2>/dev/null | "
                f"awk -v ts=\"$(date -u -d @{epoch_sec} '+%Y-%m-%d %H:%M:%S')\" 'substr($0,1,19) >= ts'"
            )
        else:
            # All other services use epoch-ms at the start of the line
            cmd = f"awk -F: '$1+0 > {since_ts}' {q_log_path}/*.log* 2>/dev/null | grep -ai -- {q_pattern}"
    else:
        # BRE (not -E): literal parentheses in patterns like 'VOD req ACK (2) sent'
        # should match literally. Under -E, '(2)' is a regex group matching bare
        # '2', so it would never match a log line that actually contains '(2)'.
        cmd = f"grep -aih -- {q_pattern} {q_log_path}/*.log* 2>/dev/null"

    output = run_command_on_pod(pod_connection, cmd)
    stdout_lines = (output or "").strip().splitlines()

    # Trust grep/awk's own matching; just drop command echoes and blank lines.
    matched = [
        line for line in stdout_lines
        if line.strip() and "grep" not in line.lower() and "awk" not in line.lower()
    ]

    if matched:
        result = "\n".join(matched)
        details.append(f"Pattern '{pattern}' found in {service} logs ({len(matched)} line(s))")
        return {"status": "Pass", "output": result, "details": details}

    details.append(f"Pattern '{pattern}' NOT FOUND in {service} logs")

    # Provide first/last 5 lines of the log for context on failure.
    context_cmd = (
        f"for f in {q_log_path}/*.log*; do "
        f"echo \"--- $f (first 5) ---\"; head -n 5 \"$f\"; "
        f"echo \"--- $f (last 5) ---\"; tail -n 5 \"$f\"; "
        f"done 2>/dev/null"
    )
    context_output = run_command_on_pod(pod_connection, context_cmd)
    if context_output:
        details.append(f"Log context:\n{context_output}")

    return {"status": "Fail", "output": "", "details": details}


def search_log_interval(pod_connection, service_name, message, start_time_epoch=None):
    """Compute intervals between consecutive log lines matching a message in a service log directory.
    Supports both epoch (ms) and UTC date-time timestamps at line start.
    UTC formats supported at line start: 'YYYY-MM-DD HH:MM:SS' or with optional ',mmm' / '.mmm' milliseconds and optional trailing ' -'.
    start_time_epoch may be:
      - epoch ms (int/float or 13-digit string)
      - epoch seconds (10-digit -> auto *1000)
      - UTC string 'YYYY-MM-DD HH:MM:SS'
    Returns dict with: status, count, intervals_ms, stats, details.
    """
    details = []
    base_dir = f"/home/ubuntu/.nddevice/log/{service_name}"
    grep_cmd = f"grep -ria '{message}' {base_dir} 2>/dev/null || true"
    raw = run_command_on_pod(pod_connection, grep_cmd)
    if not raw:
        return {
            'status': 'Fail', 'count': 0, 'intervals_ms': [], 'stats': None,
            'details': [f"No matches for message '{message}' in {base_dir}"]
        }
    lines = [l for l in raw.splitlines() if l.strip()]

    # Normalize start_time_epoch param (support UTC string)
    if start_time_epoch is None:
        start_time_epoch = int((time.time() - 24*3600) * 1000)
        details.append(f"Default start_time (24h ago) ms: {start_time_epoch}")
    else:
        try:
            if isinstance(start_time_epoch, (int, float)):
                val = int(start_time_epoch)
                if len(str(val)) == 10:  # seconds -> ms
                    val *= 1000
                start_time_epoch = val
            elif isinstance(start_time_epoch, str):
                raw_ts = start_time_epoch.strip()
                if raw_ts.isdigit():
                    if len(raw_ts) == 13:
                        start_time_epoch = int(raw_ts)
                    elif len(raw_ts) == 10:
                        start_time_epoch = int(raw_ts) * 1000
                    else:
                        # treat as seconds
                        start_time_epoch = int(raw_ts) * 1000
                else:
                    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y:%m:%d %H:%M:%S'):
                        try:
                            st = time.strptime(raw_ts, fmt)
                            start_time_epoch = int(calendar.timegm(st) * 1000)
                            break
                        except ValueError:
                            continue
                    else:
                        raise ValueError('Unsupported start_time format')
            else:
                raise TypeError('Unsupported start_time type')
            details.append(f"Normalized start_time_epoch: {start_time_epoch}")
        except Exception as e:
            details.append(f"Failed to normalize start_time_epoch ({start_time_epoch}): {e}; using 24h default")
            start_time_epoch = int((time.time() - 24*3600) * 1000)

    ts_values = []
    # Regex for UTC date-time at beginning
    date_re = re.compile(r'^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})(?:[,.](\d{1,3}))?(?:\s+-)?')
    # Epoch tokens (prefer those followed by ':')
    ts_followed_colon = re.compile(r'(\d{13})(?=:)')
    ts_any = re.compile(r'(\d{13})')

    utc_parsed = 0
    epoch_parsed = 0

    for line in lines:
        # Strip filename prefix if present (keep remainder for timestamp detection)
        if ':' in line:
            parts = line.split(':', 1)
            if '/' in parts[0]:
                content = parts[1].strip()
            else:
                content = line.strip()
        else:
            content = line.strip()

        # Attempt UTC date-time at start
        m_date = date_re.match(content)
        ts_extracted = None
        if m_date:
            date_part, hms, ms_part = m_date.groups()
            try:
                st = time.strptime(f"{date_part} {hms}", '%Y-%m-%d %H:%M:%S')
                ts_extracted = int(calendar.timegm(st) * 1000)
                if ms_part:
                    ts_extracted += int(ms_part.ljust(3, '0')[:3])
                utc_parsed += 1
            except Exception as e:
                details.append(f"UTC parse error: {e} in line: {content[:80]}")
        if ts_extracted is None:
            # Fallback to epoch search inside content
            candidates = [int(m) for m in ts_followed_colon.findall(content)]
            if not candidates:
                candidates = [int(m) for m in ts_any.findall(content)]
            if candidates:
                newer = [c for c in candidates if c >= start_time_epoch]
                ts_extracted = max(newer) if newer else max(candidates)
                epoch_parsed += 1
        if ts_extracted is not None and ts_extracted >= start_time_epoch:
            ts_values.append(ts_extracted)

    ts_values.sort()
    count = len(ts_values)
    details.append(f"Collected {count} timestamps (UTC parsed: {utc_parsed}, epoch parsed: {epoch_parsed}) after start_time {start_time_epoch}")
    if count < 2:
        details.append("Need at least two occurrences to compute intervals")
        return {
            'status': 'Fail', 'count': count, 'intervals_ms': [], 'stats': None, 'details': details
        }
    intervals = [ts_values[i] - ts_values[i-1] for i in range(1, count)]
    min_i = min(intervals); max_i = max(intervals); avg_i = sum(intervals) / len(intervals)
    details.append(f"Intervals (ms): {intervals}")
    details.append(f"Min: {min_i} ms, Max: {max_i} ms, Avg: {avg_i:.2f} ms")
    return {
        'status': 'Pass', 'count': count, 'intervals_ms': intervals,
        'stats': {'min_ms': min_i, 'max_ms': max_i, 'avg_ms': avg_i}, 'details': details
    }


def frequency_based_calls(pod_connection, api_pattern, service_name, expected_interval_minutes, cloud_check=False, api_key=None, tolerance_minutes=1):
    """Check that an API call pattern appears twice within expected interval bounds.
    Args:
        pod_connection: active pexpect spawn to pod.
        api_pattern: suffix of URL path to search (already starts with '/').
        service_name: log subfolder name under /home/ubuntu/.nddevice/log
        expected_interval_minutes: target interval between two occurrences.
        cloud_check: whether to validate cloud propagation delay.
        api_key: key needed for cloud check (if any; placeholder).
        tolerance_minutes: +/- tolerance window.
    Returns:
        dict with keys: status (Pass/Fail), occurrences (list of epoch ms), diff_minutes (float or None), details (list of strings)
    """
    details = []
    occurrences = []
    status = 'Fail'
    target_min = expected_interval_minutes
    tol = tolerance_minutes
    end_deadline = time.time() + (target_min * 60) + 120  # grace window

    # Poll latest matching line
    grep_cmd = (
        "grep -ria 'https://idms-staging.netradyne.com/restserver" + api_pattern + "' "
        "/home/ubuntu/.nddevice/log/" + service_name + " | sort | tail -1"
    )

    ts_re_date = re.compile(r'^\d{4}-\d{2}-\d{2}')

    def parse_timestamp(line):
        line = line.strip()
        if not line:
            return None
        # Strip prefix before first ':' (filename)
        if ':' in line:
            line = line.split(':', 1)[1].strip()
        if ts_re_date.match(line):
            time_str = line.split(',')[0]
        else:
            time_str = line.split(':')[0]
        # Convert to epoch ms (support two formats)
        try:
            if ts_re_date.match(time_str):
                # Format: YYYY-MM-DD HH:MM:SS
                struct_time = time.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                return int(time.mktime(struct_time) * 1000)
            else:
                # Assume epoch ms already
                if time_str.isdigit():
                    return int(time_str)
        except Exception:
            return None
        return None

    details.append(f"Monitoring pattern {api_pattern} in {service_name} logs for two occurrences ~{target_min}m apart")

    while time.time() < end_deadline:
        line = run_command_on_pod(pod_connection, grep_cmd)
        if line:
            ts = parse_timestamp(line)
            if ts and (not occurrences or ts != occurrences[-1]):
                occurrences.append(ts)
                details.append(f"Observed occurrence at {ts}")
                if len(occurrences) == 1:
                    # Wait until near expected interval before second check
                    remaining = (target_min * 60) - (time.time() - (occurrences[0] / 1000)) + 40
                    if remaining > 0:
                        details.append(f"Sleeping {int(remaining)}s awaiting second occurrence")
                        time.sleep(min(remaining, 300))  # cap single sleep
                elif len(occurrences) >= 2:
                    diff_ms = abs(occurrences[1] - occurrences[0])
                    lower = (target_min - tol) * 60 * 1000
                    upper = (target_min + tol) * 60 * 1000
                    diff_minutes = diff_ms / 60000.0
                    if lower <= diff_ms <= upper:
                        status = 'Pass'
                        details.append(f"Interval OK: {diff_minutes:.2f}m within [{lower/60000:.2f},{upper/60000:.2f}]m")
                    else:
                        details.append(f"Interval OUT OF RANGE: {diff_minutes:.2f}m expected ~{target_min}±{tol}m")
                    break
        else:
            details.append("Pattern not found yet; retrying in 10s")
        time.sleep(10)

    if len(occurrences) < 2:
        details.append("Did not capture two occurrences in allotted time")
    elif cloud_check and api_key:
        # Placeholder cloud validation: require second occurrence within 50s of cloud echo
        details.append("Cloud check not implemented in this framework (skipped)")

    return {
        'status': status,
        'occurrences': occurrences,
        'diff_minutes': (abs(occurrences[1] - occurrences[0]) / 60000.0) if len(occurrences) >= 2 else None,
        'details': details
    }


def event_based_api_call(pod_connection, api_pattern, service_name, cloud_check=False, api_key=None, max_cloud_delay_ms=40000, cloud_retries=5):
    """Capture latest occurrence of an API call pattern in a service's logs (event-based).
    Args:
        pod_connection: active pexpect spawn.
        api_pattern: URL suffix or substring (e.g. '/api/v1/device/register').
        service_name: log subfolder under /home/ubuntu/.nddevice/log.
        cloud_check: whether to attempt cloud propagation delay validation (placeholder).
        api_key: identifier for cloud API (unused placeholder).
        max_cloud_delay_ms: acceptable max delay in ms for cloud echo (if implemented).
        cloud_retries: number of retries to attempt cloud check.
    Returns dict:
        status: Pass/Fail
        triggered_time_ms: epoch ms timestamp of latest matched log line (or None)
        cloud_delay_ms: measured cloud delay (or None)
        details: list of descriptive strings
    """
    details = []
    triggered_time = None
    cloud_delay = None
    # Build grep command similar to other helpers (search full staging domain + pattern if pattern starts with '/').
    if api_pattern.startswith('/'):
        search_term = f"https://idms-staging.netradyne.com/restserver{api_pattern}"
    else:
        search_term = api_pattern
    log_dir = f"/home/ubuntu/.nddevice/log/{service_name}"
    grep_cmd = f"grep -riwa '{search_term}' {log_dir} | sort | tail -1"
    line = run_command_on_pod(pod_connection, grep_cmd)
    if not line:
        details.append(f"Pattern '{search_term}' not found in {log_dir}")
        return {
            'status': 'Fail',
            'triggered_time_ms': None,
            'cloud_delay_ms': None,
            'details': details
        }

    # Parse timestamp from line content (after filename prefix if present)
    ts_re_date = re.compile(r'^\d{4}-\d{2}-\d{2}')
    content = line.strip()
    if ':' in content:
        parts = content.split(':', 1)
        # If first part looks like a path use second half
        if '/' in parts[0]:
            content = parts[1].strip()
    # Determine time string portion
    if ts_re_date.match(content):
        time_str = content.split(',')[0].strip() # YYYY-MM-DD HH:MM:SS
        try:
            struct_time = time.strptime(time_str, '%Y-%m-%d %H:%M:%S')
            triggered_time = int(time.mktime(struct_time) * 1000)
        except Exception as e:
            details.append(f"Failed to parse date-formatted timestamp: {e}")
    else:
        # Assume epoch ms appears before first ':' or space
        token = content.split(':')[0].split()[0]
        if token.isdigit():
            try:
                triggered_time = int(token)
                # Normalize 10-digit seconds to ms
                if len(token) == 10:
                    triggered_time *= 1000
            except Exception as e:
                details.append(f"Failed to parse numeric timestamp: {e}")
        else:
            details.append("No recognizable timestamp token at start of line")

    if not triggered_time:
        details.append("Could not extract triggered_time")
        return {
            'status': 'Fail',
            'triggered_time_ms': None,
            'cloud_delay_ms': None,
            'details': details
        }

    details.append(f"Latest occurrence timestamp (ms): {triggered_time}")

    if cloud_check and api_key:
        details.append("Cloud delay check placeholder (not implemented)")
        # Placeholder logic: simulate retries without real API
        for attempt in range(1, cloud_retries + 1):
            # In a real implementation replace with call retrieving cloud echo epoch ms
            simulated_cloud_ts = None  # Always None in placeholder
            if simulated_cloud_ts is None:
                details.append(f"Attempt {attempt}: cloud API timestamp unavailable")
                time.sleep(1)
                continue
            cloud_delay = abs(simulated_cloud_ts - triggered_time)
            details.append(f"Cloud delay ms: {cloud_delay}")
            if cloud_delay <= max_cloud_delay_ms:
                details.append("Cloud delay within threshold")
                break
        else:
            details.append("Cloud delay validation failed or not available")

    status = 'Pass' if triggered_time else 'Fail'
    return {
        'status': status,
        'triggered_time_ms': triggered_time,
        'cloud_delay_ms': cloud_delay,
        'details': details
    }
