"""
Feature: AWSIOT — Verify Connection Ignition High
Description:
  Check whether AWSIOT connects to AWS IOT server successfully 
"""

import time


def test_step1_check_datetime(device):
    """Check whether AWSIOT connects to AWS IOT server successfully.

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
    """STEP_2 — Wait 10s after restart."""
    time.sleep(10)


def test_step4_verify_connected(device):
    """STEP_3 — Verify 'Connected successfully' in awsiot logs."""
    ts = device.variables.get("search_start_ts")
    output = device.search_log("/home/ubuntu/.nddevice/log/awsiot", "Connected successfully", start_timestamp=ts, timeout=60, interval=10)
    assert output, "Not connected to AWS IOT server"
