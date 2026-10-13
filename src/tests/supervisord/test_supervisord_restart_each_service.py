"""
Test case : Service restart using supervisorctl (manual)
Purpose   : Check that every service can be restarted with supervisorctl, and that
            the restart really replaces the process.

Precondition
  The ND pod is up and running.

Steps and expected result
  1. Take the list of ND services (the same list the sanity test
     test_expected_services_running_itn2429 uses) and check supervisorctl knows each one.
       -> No service is missing.
  2. For each service, one after the other, run `supervisorctl restart <service>`.
       -> supervisorctl prints "<service>: stopped" and "<service>: started".
       -> The old process is gone.
       -> A new process is running, with a different process number (pid).
       -> The new process is a child of pid 1 (supervisord).
     The test goes through all the services and reports every one that fails,
     instead of stopping at the first.

Things to know
  - `startup` is not restarted. It is a one-time script that starts the other
    services and then exits, so restarting it would not be a normal restart.
  - The service list is in services.py next to this test. It is a copy of the one in
    test_sanity_functions.py. If services are added or removed, update both.
  - The sheet checks the new process with `ps -ef | grep`. The test reads the pid
    from `supervisorctl status` instead (the same process) and then checks its
    parent with `ps -o ppid=`.
  - Restarting every service takes a few minutes.
"""

import re
import time

from src.tests.supervisord.services import EXPECTED_SERVICES

WAIT_FOR_RUNNING_SECONDS = 30


def _wait_for_pid(device, service):
    """Wait until the service is RUNNING again and return its pid (or None)."""
    deadline = time.time() + WAIT_FOR_RUNNING_SECONDS
    while True:
        result = device.get_service_pid(service)
        if result["pid"]:
            return result["pid"]
        if time.time() >= deadline:
            return None
        time.sleep(2)


def _parent_pid(device, pid):
    out = device.run(f"ps -o ppid= -p {pid}") or ""
    match = re.search(r"^\s*(\d+)\s*$", out, re.M)
    return match.group(1) if match else None


def _is_alive(device, pid):
    out = device.run(f"[ -d /proc/{pid} ] && printf 'PROCESS=%s\\n' alive || printf 'PROCESS=%s\\n' gone") or ""
    return "PROCESS=alive" in out


def test_step1_services_known_to_supervisorctl(device):
    """STEP 1 — Take the list of ND services and check supervisorctl knows every one of them."""
    out = device.run("supervisorctl status") or ""
    known = {line.split()[0] for line in out.splitlines() if line.split()}
    missing = [s for s in EXPECTED_SERVICES if s not in known]
    assert not missing, f"Services not listed by supervisorctl status: {missing}"
    print(f"Services to restart ({len(EXPECTED_SERVICES)}): {EXPECTED_SERVICES}")


def test_step2_restart_each_service(device):
    """STEP 2 — Run `supervisorctl restart <service>` for each service and check the old process is replaced by a new one under pid 1."""
    services = EXPECTED_SERVICES

    failures = []
    for service in services:
        old_pid = device.get_service_pid(service)["pid"]
        if not old_pid:
            failures.append(f"{service}: not RUNNING before the restart")
            continue

        restart = device.restart_service(service)
        if not ("stopped" in restart["output"].lower() and "started" in restart["output"].lower()):
            failures.append(f"{service}: supervisorctl did not print stopped and started: {restart['output']!r}")
            continue

        new_pid = _wait_for_pid(device, service)
        if not new_pid:
            failures.append(f"{service}: not RUNNING {WAIT_FOR_RUNNING_SECONDS}s after the restart")
        elif new_pid == old_pid:
            failures.append(f"{service}: same pid {old_pid} after the restart (process was not replaced)")
        elif _is_alive(device, old_pid):
            failures.append(f"{service}: old process {old_pid} is still running")
        elif _parent_pid(device, new_pid) != "1":
            failures.append(f"{service}: new process {new_pid} is not a child of pid 1 (parent is {_parent_pid(device, new_pid)})")
        else:
            print(f"[Restart] {service}: pid {old_pid} -> {new_pid}, parent 1")

    assert not failures, f"{len(failures)} of {len(services)} services failed the restart check:\n  " + "\n  ".join(failures)
