"""
Feature: AWSIOT — Verify Server Address
Description:
  Verify awsiot logs the expected pingdata server address on restart.
"""

import time


def test_step1_check_datetime(device):
    """Verify awsiot logs the expected pingdata server address on restart.

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


def test_step4_verify_server_address(device):
    """STEP_3 — Verify server address in awsiot logs."""
    ts = device.variables.get("search_start_ts")
    output = device.search_log(
        "/home/ubuntu/.nddevice/log/awsiot",
        "server_address - https://idms-staging.netradyne.com/restserver/api/v1/upload/pingdata",
        start_timestamp=ts, timeout=60, interval=10,
    )
    assert output, "server address verification failed"
