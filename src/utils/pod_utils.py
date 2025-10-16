import pexpect
import sys
import re
import time
import subprocess
from .logger import setup_logger


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
    """
    Periodically search for a term in all .log files inside a log directory within the pod,
    considering only logs after a given start time
    
    stamp.

    Args:
        child: pexpect session object connected to the pod.
        log_dir: Path to the directory containing log files.
        search_term: Text or regex pattern to search for.
        start_timestamp: Epoch timestamp marking the start of the test.
        timeout: Max time (seconds) to search before giving up.
        interval: Delay (seconds) between each search attempt.

    Returns:
        str: Matching log line(s) if found, else None.
    """
    if start_timestamp is None:
        start_timestamp = int(time.time())*1000  # current time in ms
    
    logger.info(f"Searching for '{search_term}' in logs at {log_dir} after timestamp {start_timestamp} with timeout {timeout}s...")
    end_time = time.time() + timeout

    while time.time() < end_time:
        # Use grep to search all .log files, suppress errors
        cmd = f"grep -Hn '{search_term}' {log_dir}/*.log 2>/dev/null || true"
        output = run_command_on_pod(child, cmd)

        if output:
            # Filter lines based on timestamp
            filtered_lines = []
            for line in output.splitlines():
                parts = line.split(':')

                # Example structure:
                # parts[0] -> /home/.../log_1760594776000.log
                # parts[1] -> 118        (line number)
                # parts[2] -> 1760594844089 (timestamp)
                if len(parts) > 2 and parts[2].isdigit():
                    timestamp = int(parts[2])
                    if timestamp >= start_timestamp:
                        print(f"Matched line with timestamp {timestamp}: {line}")
                        filtered_lines.append(line)

            if filtered_lines:
                result = "\n".join(filtered_lines)
                print(f"\nFound '{search_term}' in logs after {start_timestamp}:\n{result}\n")
                return result

        print(f"Log '{search_term}' not found yet after {start_timestamp}. Retrying in {interval}s...\n")
        time.sleep(interval)

    logger.warning(f"Timeout reached. '{search_term}' not found in logs after {start_timestamp}.")
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
    print(f"✅ MD5 checksum for {ota_version}: {md5_hash}")
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



if __name__ == "__main__":
    # Connect to pod
    child = connect_to_pod("172.16.22.119")

    #  Run multiple commands
    run_command_on_pod(child, "./gen_ualert.sh", "/home/ubuntu/.nddevice/latest/service/bagheera")

    # disk usage
    run_command_on_pod(child, "du -sh /data")

    # Close connection
    close_pod_connection(child)

