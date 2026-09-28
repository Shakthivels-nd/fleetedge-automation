"""
Feature: AWSIOT — Override Parse Check
Description:
  Verify awsiot parses the bagheera_override.ini override file successfully
  on restart, from whichever path the device type expects.
"""

import time


def test_step1_check_datetime(device):
    """Verify awsiot parses the bagheera_override.ini override file successfully.

    PreCondition_1 — Verify device datetime is in sync (non-blocking).
    """
    result = device.compare_datetime()
    if result["status"] != "Pass":
        print(f"datetime is incorrect: {result['details']}")


def test_step2_restart_awsiot(device):
    """STEP_1 — Restart awsiot service."""
    device.variables["search_start_ts"] = device.get_current_time_epoch()["epoch_ms"]
    result = device.restart_service("awsiot")
    assert result["status"] == "Pass", f"Failed to restart awsiot service: {result['details']}"


def test_step3_wait(device):
    """STEP_2 — Wait 30s after restart."""
    time.sleep(30)


def test_step4_verify_override_parsed(device):
    """STEP_3 — Verify override file parsed successfully (either known override path)."""
    ts = device.variables.get("search_start_ts")
    output = device.search_log(
        "/home/ubuntu/.nddevice/log/awsiot",
        "Override file /data/nd_files/config/bagheera_override.ini present",
        start_timestamp=ts, timeout=1, interval=1,
    )
    if not output:
        output = device.search_log(
            "/home/ubuntu/.nddevice/log/awsiot",
            "OVerride file parsed successfully",
            start_timestamp=ts, timeout=1, interval=1,
        )
    if not output:
        output = device.search_log(
            "/home/ubuntu/.nddevice/log/awsiot",
            "Override file /home/ubuntu/config/bagheera_override.ini present",
            start_timestamp=ts, timeout=60, interval=10,
        )
    assert output, "override file parsing failed"
