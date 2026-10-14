"""
Feature: AWSIOT — Verify Connection No Network
Description:
  Check whether AWSIOT connection is occuring or not when there is no
  network access to the cloud (API calls blocked).
"""

import time


def test_step1_check_datetime(device):
    """Check whether AWSIOT connection is occuring or not when there is no network.

    PreCondition_1 — Verify device datetime is in sync (non-blocking).
    """
    result = device.compare_datetime()
    if result["status"] != "Pass":
        print(f"datetime is incorrect: {result['details']}")


def test_step2_block_api_calls(device):
    """PreCondition_2 — Block device API calls to idms-staging.netradyne.com."""
    result = device.control_api_calls(True)
    assert result["status"] == "Pass", f"Failed to block api calls: {result['details']}"


def test_step3_restart_awsiot(device):
    """STEP_1 — Restart awsiot service."""
    device.variables["search_start_ts"] = device.get_current_time_epoch()["epoch_ms"]
    result = device.restart_service("awsiot")
    assert result["status"] == "Pass", f"Failed to restart awsiot service: {result['details']}"


def test_step4_wait(device):
    """STEP_2 — Wait 10s after restart."""
    time.sleep(10)


def test_step5_verify_connected(device):
    """STEP_3 — Verify awsiot connects to the AWS IOT server.
    """
    ts = device.variables.get("search_start_ts")
    output = device.search_log("/home/ubuntu/.nddevice/log/awsiot", "Connected successfully", start_timestamp=ts, timeout=60, interval=10)
    assert output, f"awsiot did not connect: {output}"


def test_step6_unblock_api_calls(device):
    """PostCondition_1 — Restore device API calls to idms-staging.netradyne.com."""
    result = device.control_api_calls(False)
    assert result["status"] == "Pass", f"Failed to unblock api calls: {result['details']}"


def test_step7_restart_awsiot(device):
    """PostCondition_2 — Restart awsiot service to restore normal connectivity."""
    device.restart_service("awsiot")
