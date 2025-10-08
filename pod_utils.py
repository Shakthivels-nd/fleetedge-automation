import pexpect,sys,re

def connect_to_pod(ip_address: str, username: str = "voyager", password: str = "voyager", pod: str = "netra"):
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
    print(f"Connecting to {ip_address} as {username}...\n")

    child = pexpect.spawn(f"sshpass -p {password} {ssh_cmd}", encoding="utf-8", timeout=30)
    child.logfile = sys.stdout  # optional: print interaction to stdout


    child.expect([r'[#\$] ', pexpect.EOF, pexpect.TIMEOUT])  # wait for pod bash prompt
    print(f"Connected to pod '{pod}'!\n")
    return child

def run_command_on_pod(child, cmd: str, directory: str = None):
    """
    Run a command inside the already connected pod session.
    """
    full_cmd = f"cd {directory} && {cmd}" if directory else cmd
    child.sendline(full_cmd)
    child.expect([r'[#\$] ', pexpect.EOF, pexpect.TIMEOUT])
    # child.before contains everything before the prompt (including the command)
    output_lines = child.before.splitlines()
    if len(output_lines) > 1:
        # skip the first line (the echoed command)
        output = "\n".join(output_lines[1:]).strip()
    else:
        output = child.before.strip()
    
    print(output)
    return output

def close_pod_connection(child):
    child.sendline("exit")
    child.close()

def clean_output(output: str) -> str:
    # Remove ANSI escape sequences
    ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', output).strip()

import time
import re

import time
import re

def search_logs_in_pod(child, log_dir: str, search_term: str, timeout: int = 60, interval: int = 5):
    """
    Periodically search for a term in all .log files inside a log directory within the pod.
    
    Args:
        child: pexpect session object connected to the pod.
        log_dir: Path to the directory containing log files.
        search_term: Text or regex pattern to search for.
        timeout: Max time (seconds) to search before giving up.
        interval: Delay (seconds) between each search attempt.

    Returns:
        str: Matching log line(s) if found, else None.
    """
    print(f"Searching for '{search_term}' inside {log_dir}/*.log for up to {timeout}s...\n")
    end_time = time.time() + timeout

    while time.time() < end_time:
        # Use grep to recursively search all .log files, suppress errors
        cmd = f"grep -Hn '{search_term}' {log_dir}/*.log 2>/dev/null || true"
        output = run_command_on_pod(child, cmd)

        # If grep finds something, output contains file names and lines
        if re.search(search_term, output, re.IGNORECASE):
            print(f"\nFound '{search_term}' in logs:\n{output}\n")
            return output
        else:
            print(f"⏳ '{search_term}' not found yet. Retrying in {interval}s...\n")
            time.sleep(interval)

    print(f"\nTimeout reached ({timeout}s). '{search_term}' not found in {log_dir}.\n")
    return None



if __name__ == "__main__":
    # Connect to pod
    child = connect_to_pod("172.16.22.119")

    # # Run multiple commands
    # #user Alert
    # run_command_on_pod(child, "./gen_ualert.sh", "/home/ubuntu/.nddevice/latest/service/bagheera")

    # #disk usage
    run_command_on_pod(child, "du -sh /data")
    # run_command_on_pod(child, "lsblk")
    # run_command_on_pod(child, "free -h")

    # search_logs_in_pod(child, "/home/ubuntu/.nddevice/latest/logs", "Alert sent to user")

    # Close connection
    # close_pod_connection(child)

