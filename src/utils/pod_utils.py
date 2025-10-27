import pexpect
import sys
import re
import time
import subprocess
import os
from .logger import setup_logger
from datetime import datetime
import calendar


logger = setup_logger()
voyager_ip = "172.16.22.119"
def connect_to_pod(ip_address: str = voyager_ip, username: str = "voyager", password: str = "voyager", pod: str = "netra"):
    """
    Establish a persistent SSH session into a pod using pexpect.
    Returns the pexpect.spawn object for later command execution.
    """
    remote_cmd = (
        f"/opt/k3s/kubectl exec -it "
        f"$(/opt/k3s/kubectl get pods | grep {pod} | awk \"{{print $1}}\") "
        "-- bash"
    )
    ssh_cmd = f"ssh {username}@{ip_address} -tt '{remote_cmd}'"
    logger.info(f"Connecting to pod at {ip_address} as {username}...")

    child = pexpect.spawn(f"sshpass -p {password} {ssh_cmd}", encoding="utf-8", timeout=30)
    child.sendline("stty -echo")
    child.expect([r'[#\$] '])
    child.logfile = sys.stdout  # optional: print interaction to stdout


    child.expect([r'[#\$] ', pexpect.EOF, pexpect.TIMEOUT])  # wait for pod bash prompt
    logger.info(f"Connected to pod at {ip_address} as {username}")
    return child

def run_command_on_voyager(ip_address: str = voyager_ip, username: str = "voyager", password: str = "voyager", cmd: str = "ls -l", directory: str = None):
    """
    Run a single command on the pod via SSH and return its output.
    This is a one-off command, not a persistent session.
    """
    remote_cmd = f"ssh {username}@{ip_address} -tt '{cmd}'"
    full_cmd = f"sshpass -p {password} {remote_cmd}"
    if directory:
        full_cmd = f"sshpass -p {password} ssh {username}@{ip_address} -tt 'cd {directory} && {cmd}'"

    logger.info(f"Running command on pod at {ip_address}: {cmd}")
    child = pexpect.spawn(full_cmd, encoding="utf-8", timeout=30)
    child.expect([r'[#\$] ', pexpect.EOF, pexpect.TIMEOUT], timeout=30)
    output = child.before.strip()
    output = clean_output(output)
    logger.info(f"Command output:\n{output}")
    return output if output else None
    

def run_command_on_pod(child, cmd: str, directory: str = None):
    """
    Run a command inside the already connected pod session.
    Returns only the output of the current command, excluding the command itself.
    """
    full_cmd = f"cd {directory} && {cmd}" if directory else cmd
    child.sendline(full_cmd)
    try:
        child.expect([r'[#\$] ', pexpect.EOF, pexpect.TIMEOUT], timeout=30)
    except pexpect.TIMEOUT:
        logger.error(f"Command timed out: {full_cmd}")
        return ""
    output_lines = child.before.splitlines()

    # remove echoed command line
    if output_lines and output_lines[0].strip() == full_cmd.strip():
        output_lines = output_lines[1:]

    # remove leading empty lines
    while output_lines and not output_lines[0].strip():
        output_lines.pop(0)

    output = "\n".join(output_lines).strip()
    output = clean_output(output)
    logger.info(f"Command: {full_cmd}")
    logger.info(f"Output:\n{output}")  
    return output if output else None

def reboot_voyager():
    """Reboot the pod before tests in this module."""
    print("\n[Setup] Rebooting pod before tests...")
    run_command_on_voyager(cmd="sudo reboot")
    # wait for voyager to come back up
    wait_for_ping(timeout=180, interval=5)
    
    # wait until the pod is initialized
    time.sleep(240)
    print("[Setup] Pod reboot complete.")


def wait_for_ping(ip: str=voyager_ip, timeout: int = 180, interval: int = 5):
    """
    Wait until the given IP responds to ping.
    Returns True if reachable, False if timeout expires.
    """
    print(f"[Wait] Waiting for {ip} to respond to ping...")

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # For Linux/macOS
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "1", ip],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if result.returncode == 0:
                print(f"[Wait] {ip} is reachable.")
                return True
        except Exception as e:
            print(f"[Wait] Ping check failed: {e}")

        time.sleep(interval)

    print(f"[Wait] Timeout: {ip} did not respond within {timeout} seconds.")
    return False

def close_pod_connection(child):
    child.sendline("exit")
    child.close()

def clean_output(output: str) -> str:
    """
    Clean command output by removing:
      - ANSI escape sequences
      - Shell prompts like 'root@host:/path#' or '$'
      - Duplicate blank lines
    """
    # Remove ANSI escape sequences (colors, cursor moves, etc.)
    ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
    output = ansi_escape.sub('', output)

    # Remove shell prompt lines (root@..., ubuntu@..oot., etc.)
    prompt_pattern = re.compile(r'\b(?:oot@|netradyne-|homeroot|root@)[^\n]*', re.IGNORECASE)    
    output = prompt_pattern.sub('', output)

    # Remove trailing/leading whitespace and compress multiple blank lines
    output = re.sub(r'\n+', '\n', output).strip()

    return output


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


def verify_file_presence(child, directories, patterns):
    """
    Checks for files matching patterns in given directories using the pod connection.
    Returns a list of dicts with directory, pattern, and count info.
    """
    results = []

    for directory in directories:
        for pattern in patterns:
            cmd = f"ls {directory} | grep -E '{pattern}' | wc -l"
            output = run_command_on_pod(child, cmd).strip()
            
            # Extract first number from output
            match = re.search(r'\d+', output)
            count = int(match.group()) if match else 0

            results.append({
                "directory": directory,
                "pattern": pattern,
                "count": count
            })

            logger.info(f"Directory: {directory}, Pattern: {pattern}, Count: {count}")

    return results
def check_ota_md5sum(pod_connection, ota_version, directory="/home/ubuntu/.nddevice"):
    """
    Check the md5sum of a given OTA in the specified directory.
    """
    print("Check the md5sum of a given OTA in the specified directory")
    print(f"Checking md5sum for OTA: {ota_version} in {directory}")

    cmd = f"cd {directory} && md5sum {ota_version}"
    output = run_command_on_pod(pod_connection, cmd).strip()

    # Split into lines to find the one that contains the md5 hash
    lines = [line.strip() for line in output.splitlines()]
    md5_line = None
    for line in lines:
        if re.match(r"^[a-fA-F0-9]{32}\s+", line):
            md5_line = line
            break

    if not md5_line:
        raise AssertionError(f"Failed to parse md5sum output:\n{output}")

    md5_hash = md5_line.split()[0]
    print(f" MD5 checksum for {ota_version}: {md5_hash}")
    return md5_hash

def check_no_legacy_package_exists(pod_connection, ota_version, directory="/home/ubuntu/.nddevice"):
    """
    Ensure that only the specified OTA file exists in the directory.
    """
    print("Ensure no legacy OTA packages exist except the specified one")
    print(f"Verifying only OTA present: {ota_version} in {directory}")

    # Use `find` instead of `ls` to avoid shell prompt noise
    cmd = f"cd {directory} && find . -maxdepth 1 -type f -name '*.tar.gz' -printf '%f\n'"
    output = run_command_on_pod(pod_connection, cmd).strip()

    # Split and clean lines
    lines = [line.strip() for line in output.splitlines() if line.strip()]

    # Filter valid `.tar.gz` files
    ota_files = [
    f.lstrip("> ").strip()
    for f in lines
    if f.strip().endswith(".tar.gz")
]

    if not ota_files:
        raise AssertionError(
            f"No OTA *.tar.gz files found in {directory}. Raw output:\n{output}"
        )

    other_otas = [f for f in ota_files if f != ota_version]

    if ota_version not in ota_files:
        raise AssertionError(
            f"Requested OTA '{ota_version}' not found. Found: {ota_files}"
        )

    if other_otas:
        raise AssertionError(f"Unexpected OTA files present: {other_otas}")

    print(f"Only the specified OTA '{ota_version}' exists in {directory}")
    return True

def list_log_folder_contents(pod_connection, directory="/data/nd_files/log"):
    """
    List the contents of the log folder on the pod.
    Just runs `ls -lh` and prints/returns the output.
    """
    print(f"Listing contents of: {directory}")

    cmd = f"cd {directory} && ls -lh"
    output = run_command_on_pod(pod_connection, cmd)

    print(":::::::::::: LOG DIRECTORY CONTENTS ::::::::::::")
    print(output)
    print("::::::::::::::::::::::::::::::::::::::::::::::::")

    return output


def validate_services_uptime_diff(pod_connection, directory="/home/ubuntu/.nddevice/latest/service", max_diff_seconds=5):
    """
    Print all running services with uptime and check if the maximum difference
    between uptimes is within max_diff_seconds.
    """
    cmd = f"cd {directory} && supervisorctl status *"
    output = run_command_on_pod(pod_connection, cmd)

    uptime_pattern = re.compile(r'^(.*?)\s+RUNNING\s+pid\s+\d+,\s+uptime\s+(\d+:\d+:\d+)', re.MULTILINE)

    services = []
    uptimes_in_seconds = []

    for line in output.splitlines():
        match = uptime_pattern.search(line)
        if match:
            service_name = match.group(1).strip()
            uptime_str = match.group(2)
            h, m, s = map(int, uptime_str.split(':'))
            total_seconds = h * 3600 + m * 60 + s

            services.append((service_name, uptime_str, total_seconds))
            uptimes_in_seconds.append(total_seconds)

    if not services:
        print("No running services found in the directory.")
        return

    # Print each service and its uptime
    print("\nService Uptime List:")
    for svc, uptime_str, seconds in services:
        print(f"{svc}: {uptime_str} ({seconds} seconds)")

    # Calculate max difference
    min_uptime = min(uptimes_in_seconds)
    max_uptime = max(uptimes_in_seconds)
    diff = max_uptime - min_uptime

    print(f"\nEarliest uptime: {min_uptime} seconds")
    print(f"Latest uptime:   {max_uptime} seconds")
    print(f"Difference:       {diff} seconds")

    # Enforce threshold
    if diff > max_diff_seconds:
        raise AssertionError(
            f"Uptime difference ({diff}s) exceeds allowed {max_diff_seconds}s"
        )
    else:
        print(f"\n All services are within {max_diff_seconds} seconds difference.")

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
                    remaining = (target_min * 60) - ((time.time()) - (occurrences[0] / 1000)) + 40
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
    grep_cmd = f"grep -riwa '{search_term}' {log_dir} 2>/dev/null | sort | tail -1"
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
def check_private_key_markers(pod_connection, directory="/home/ubuntu/.nddevice/certificate"):
    """Check if key files contain the 'PRIVATE' marker.
    Returns dict mapping filename to boolean.
    """
    files_cmds = {
        "private.pem.key": "grep -q 'PRIVATE' private.pem.key && echo 'true' || echo 'false'",
        "ed25519key.pem": "grep -q 'PRIVATE' ed25519key.pem && echo 'true' || echo 'false'",
    }
    results = {}
    for fname, cmd in files_cmds.items():
        output = run_command_on_pod(pod_connection, f"cd {directory} && {cmd}")
        val = (output or '').strip().lower() == 'true'
        print(f"[CertCheck] {fname}: {'FOUND' if val else 'NOT FOUND'}")
        results[fname] = val
    return results


def get_ota_version(pod_connection, directory="/home/ubuntu/.nddevice"):
    """Detect current OTA version by listing directory for version folder or *.tar.gz.
    Returns version string or None. (No nddevice.ini fallback)"""
    list_cmd = f"cd {directory} && ls -1"
    output = run_command_on_pod(pod_connection, list_cmd)
    if not output:
        return None
    candidates = []
    version_re = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+\.rc\.[0-9]+$")
    for line in output.splitlines():
        name = line.strip()
        if version_re.match(name):
            candidates.append(name)
        elif name.endswith('.tar.gz'):
            base = name[:-7]
            if version_re.match(base):
                candidates.append(base)
    if not candidates:
        return None
    seen = []
    for c in candidates:
        if c not in seen:
            seen.append(c)
    return seen[0]

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

def get_current_time_utc():
    """Return current UTC time string (YYYY-MM-DD HH:MM:SS) with status and details.
    Framework style: no self, structured dict output.
    """
    details = []
    try:
        from datetime import datetime, timezone
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
    

def check_file_availability(pod_connection, file_path):
    """Check if a file exists on the pod.
    Args:
        pod_connection: active pexpect spawn.
        file_path: absolute path to file.
    Returns dict:
        status: Pass/Fail
        exists: bool
        file_name: basename
        file_path: original path
        details: list messages
    """
    details = ["file_availability check invoked"]
    file_name = os.path.basename(file_path)
    # Use bash test to avoid parsing ls errors
    cmd = f"bash -c '[ -f {file_path} ] && echo FOUND || echo MISSING'"
    result = run_command_on_pod(pod_connection, cmd)
    outcome = (result or '').strip()
    if outcome == 'FOUND':
        details.append(f"File present: {file_path}")
        status = 'Pass'
        exists = True
    else:
        details.append(f"File missing: {file_path}")
        status = 'Fail'
        exists = False
    return {
        'status': status,
        'exists': exists,
        'file_name': file_name,
        'file_path': file_path,
        'details': details
    }

def get_device_info(pod_connection, deviceconfig_path="/home/ubuntu/config/deviceconfig.ini"):
    """Retrieve device_type, device_id, ota_version.
    Args:
        pod_connection: active pexpect spawn.
        deviceconfig_path: path to deviceconfig.ini file.
    Returns dict:
        status: Pass/Fail
        device_type: extracted devicetype or None
        device_id: extracted deviceid or None
        ota_version: current OTA version or None
        details: list of messages
    """
    details = ["get_device_info invoked"]
    device_type = None
    device_id = None
    ota_version = None
    status = 'Pass'

    # OTA version via existing helper
    try:
        ota_version = get_ota_version(pod_connection)
        if ota_version:
            details.append(f"OTA version: {ota_version}")
        else:
            details.append("OTA version not detected")
    except Exception as e:
        details.append(f"Error retrieving OTA version: {e}")
        status = 'Fail'

    # Parse deviceconfig.ini for deviceid/devicetype
    try:
        cfg_content = run_command_on_pod(pod_connection, f"cat {deviceconfig_path} 2>/dev/null || true")
        if cfg_content:
            for line in cfg_content.splitlines():
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                k = k.strip().lower()
                v = v.strip()
                if k == 'deviceid' and not device_id:
                    device_id = v
                elif k == 'devicetype' and not device_type:
                    device_type = v
        else:
            details.append(f"deviceconfig.ini content empty or not readable at {deviceconfig_path}")
        if device_id:
            details.append(f"device_id: {device_id}")
        else:
            details.append("device_id not found in deviceconfig.ini")
        if device_type:
            details.append(f"device_type: {device_type}")
        else:
            details.append("device_type not found in deviceconfig.ini")
    except Exception as e:
        details.append(f"Error parsing deviceconfig.ini: {e}")
        status = 'Fail'

    # Fallback to environment variables if missing
    if not device_id or not device_type:
        try:
            env_out = run_command_on_pod(pod_connection, "env | grep -Ei '^(deviceid|devicetype)=' || true")
            if env_out:
                for line in env_out.splitlines():
                    if '=' in line:
                        ek, ev = line.split('=', 1)
                        lk = ek.lower().strip()
                        ev = ev.strip()
                        if lk == 'deviceid' and not device_id:
                            device_id = ev
                        elif lk == 'devicetype' and not device_type:
                            device_type = ev
                details.append("Applied environment variable fallback for missing fields")
        except Exception as e:
            details.append(f"Env fallback error: {e}")
            status = 'Fail'

    if not (device_id or device_type or ota_version):
        status = 'Fail'
        details.append("No metadata values retrieved")

    return {
        'status': status,
        'device_type': device_type,
        'device_id': device_id,
        'ota_version': ota_version,
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
    from datetime import datetime
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

if __name__ == "__main__":
    # Connect to pod
    child = connect_to_pod("172.16.22.119")

    #  Run multiple commands
    run_command_on_pod(child, "./gen_ualert.sh", "/home/ubuntu/.nddevice/latest/service/bagheera")

    # disk usage
    run_command_on_pod(child, "du -sh /data")

    # Close connection
    close_pod_connection(child)


