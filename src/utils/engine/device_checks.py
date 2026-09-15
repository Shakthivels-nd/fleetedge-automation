import os
import re

from ..logger import setup_logger
from .connection import run_command_on_pod

logger = setup_logger()


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
