"""
Test case : Kill the service using the kill command
Purpose   : Check that when a service is killed, supervisord starts a new one by
            itself and the old one is gone.

Precondition
  The service is running. The test uses bagheera, as in the sheet.

Steps and expected result
  1. Find the process id (pid) of bagheera.
  2. Kill it with `kill -6`.
  3. Check bagheera again.
       -> A new bagheera process comes up on its own, with a different pid.
       -> The old process is gone.

Things to know
  - The new process gets up to 30 seconds to appear.
  - To run this for a different service, change SERVICE below.
"""

import time

SERVICE = "bagheera"
WAIT_FOR_NEW_PROCESS_SECONDS = 30


def test_step1_find_service_pid(device):
    """STEP 1 — Find the process id of bagheera."""
    pid = device.get_service_pid(SERVICE)["pid"]
    assert pid, f"{SERVICE} is not RUNNING"
    device.variables["pid_before_kill"] = pid


def test_step2_kill_service(device):
    """STEP 2 — Kill bagheera with `kill -6`."""
    device.run(f"kill -6 {device.variables['pid_before_kill']}")


def test_step3_service_recovers(device):
    """STEP 3 — Check a new bagheera process comes up with a different pid and the old one is gone."""
    old_pid = device.variables["pid_before_kill"]
    deadline = time.time() + WAIT_FOR_NEW_PROCESS_SECONDS
    new_pid = None
    while time.time() < deadline:
        pid = device.get_service_pid(SERVICE)["pid"]
        if pid and pid != old_pid:
            new_pid = pid
            break
        time.sleep(2)
    assert new_pid, f"{SERVICE} did not come back with a new pid within {WAIT_FOR_NEW_PROCESS_SECONDS}s of killing {old_pid}"

    old = device.run(f"[ -d /proc/{old_pid} ] && printf 'PROCESS=%s\\n' alive || printf 'PROCESS=%s\\n' gone") or ""
    assert "PROCESS=gone" in old, f"The old {SERVICE} process {old_pid} is still running"
