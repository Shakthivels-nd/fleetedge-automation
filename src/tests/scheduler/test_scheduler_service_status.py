"""
Feature: Scheduler — Service Status
Description:
  Verify scheduler_manager is running and has been up for at least 1 second.

  Ported from nd_test_bot's TC_1233_SCHEDULER_SERVICE_STATUS_REBOOT, without
  the device reboot (STEP_1) and the post-reboot 60s wait (STEP_2), which FE
  has no mechanism for. `systemctl is-active` / `systemctl status` are
  replaced with supervisorctl (device.is_service_active and `supervisorctl
  status`, parsing "uptime H:MM:SS" instead of systemctl's "Active:" line).
"""

import re

_SERVICE = "scheduler_manager"
_SERVICE_DIR = "/home/ubuntu/.nddevice/latest/service"


def test_step1_verify_service_active(device):
    """STEP_1 — Verify scheduler_manager is active (RUNNING)."""
    result = device.is_service_active(_SERVICE)
    # The reference's fail_method for this step is action "continue": it logs the
    # message but does not stop the test, so this is deliberately non-fatal.
    if result["status"] != "Pass":
        print(f"Service is inactive: {result['state']}")


def test_step2_get_service_uptime(device):
    """STEP_2 — Get scheduler_manager's uptime in seconds from supervisorctl."""
    output = device.run(f"supervisorctl status {_SERVICE}", _SERVICE_DIR) or ""
    # e.g. "scheduler_manager   RUNNING   pid 209, uptime 0:38:12" (or "uptime 1 day, 2:03:04")
    match = re.search(r"uptime\s+(?:(\d+)\s+days?,\s+)?(\d+):(\d+):(\d+)", output)
    assert match, f"Could not parse uptime from supervisorctl status: {output!r}"
    days, hours, minutes, seconds = (int(g or 0) for g in match.groups())
    device.variables["service_uptime_sch"] = days * 86400 + hours * 3600 + minutes * 60 + seconds


def test_step3_verify_service_uptime(device):
    """STEP_3 — Verify scheduler_manager's uptime is at least 1 second."""
    uptime = device.variables["service_uptime_sch"]
    assert uptime >= 1, f"Service uptime is less than 1 sec: {uptime}"
