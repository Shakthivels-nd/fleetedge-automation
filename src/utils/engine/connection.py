import pexpect
import sys
import re
import subprocess
import time

from ..logger import setup_logger

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
