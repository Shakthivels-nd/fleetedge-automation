"""
Test case : Unexpected service state
Purpose   : Every service is in one state at any moment, and a healthy service is
            RUNNING. Check that no service is stuck in a bad state such as BACKOFF,
            FATAL or UNKNOWN.

Precondition
  The ND pod is up and running.

Steps and expected result
  1. Run `supervisorctl status`
       -> Every service is RUNNING, or reaches RUNNING shortly after.
          The only exception is `startup`, which runs once at boot and then exits,
          so it is not checked.

Things to know
  - The services checked are the ND services in services.py, the same list the
    sanity test test_expected_services_running_itn2429 uses. A service from that list
    that supervisorctl does not show at all also fails the test.
  - A service that is still starting up (STARTING) or briefly in BACKOFF gets up to
    60 seconds to reach RUNNING. If it does not, the test fails and says which
    services are stuck and in what state.
  - BACKOFF, FATAL and UNKNOWN are called out in the failure message because they
    mean supervisord could not keep the service running.
"""

import time

from src.tests.supervisord.services import EXPECTED_SERVICES

STATES = {"RUNNING", "STOPPED", "STARTING", "BACKOFF", "STOPPING", "EXITED", "FATAL", "UNKNOWN"}
BAD_STATES = {"BACKOFF", "FATAL", "UNKNOWN"}
WAIT_FOR_RUNNING_SECONDS = 60


def _states(device):
    """{service: state} for each expected service; a service supervisorctl does not list gets state MISSING."""
    out = device.run("supervisorctl status") or ""
    states = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1] in STATES:
            states[parts[0]] = parts[1]
    return {s: states.get(s, "MISSING") for s in EXPECTED_SERVICES}


def test_step1_all_services_running_except_startup(device):
    """STEP 1 — Run `supervisorctl status` and check every service is RUNNING (startup is not in the list); give a starting service up to 60 seconds."""
    deadline = time.time() + WAIT_FOR_RUNNING_SECONDS
    states = _states(device)

    while True:
        not_running = {s: st for s, st in states.items() if st != "RUNNING"}
        if not not_running or time.time() >= deadline:
            break
        time.sleep(5)
        states = _states(device)

    bad = {s: st for s, st in not_running.items() if st in BAD_STATES}
    assert not not_running, (
        f"{len(not_running)} of {len(states)} services are not RUNNING: {not_running}"
        + (f". In a bad state (BACKOFF/FATAL/UNKNOWN): {bad}" if bad else "")
    )
