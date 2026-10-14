"""
Feature: AWSIOT — Service Stability
Description:
  Verify awsiot stays up and stable (uptime > 10 minutes) after a restart.
"""

import re
import time


def test_step1_check_datetime(device):
    """Verify awsiot stays up and stable (uptime > 10 minutes) after a restart.

    PreCondition_1 — Verify device datetime is in sync (non-blocking).
    """
    result = device.compare_datetime()
    if result["status"] != "Pass":
        print(f"datetime is incorrect: {result['details']}")


def test_step2_verify_service_status(device):
    """STEP_1 — Verify awsiot service status (non-blocking)."""
    result = device.is_service_active("awsiot")
    if result["status"] != "Pass":
        print(f"Service is inactive: {result['state']}")


def test_step3_restart_service(device):
    """STEP_2 — Restart awsiot service."""
    device.restart_service("awsiot")


def test_step4_wait(device):
    """STEP_3 — Wait 600s to observe stability."""
    time.sleep(600)


def test_step5_verify_uptime(device):
    """STEP_4 — Verify awsiot uptime is greater than 600s (non-blocking)."""
    output = device.run("supervisorctl status awsiot")
    uptime_seconds = None
    match = re.search(r"uptime\s+(\d+):(\d{2}):(\d{2})", output or "")
    if match:
        hours, minutes, seconds = (int(g) for g in match.groups())
        uptime_seconds = hours * 3600 + minutes * 60 + seconds
    if uptime_seconds is None or uptime_seconds <= 600:
        print(f"awsiot uptime is lesser than 10 minutes, thus service is unstable: uptime={uptime_seconds}")


def test_step6_verify_service_active(device):
    """STEP_5 — Verify awsiot service is active after the stability window (non-blocking)."""
    result = device.is_service_active("awsiot")
    if result["status"] != "Pass":
        print(f"Service is inactive: {result['state']}")
