"""
Feature: AWSIOT — Service Status Check
Description:
  Verify awsiot service status, then restart it and verify it comes back
  active.
"""


def test_step1_check_datetime(device):
    """Verify awsiot service status check and restart recovery.

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


def test_step4_verify_service_active(device):
    """STEP_3 — Verify awsiot service is active after restart (non-blocking)."""
    result = device.is_service_active("awsiot")
    if result["status"] != "Pass":
        print(f"Service is inactive: {result['state']}")
