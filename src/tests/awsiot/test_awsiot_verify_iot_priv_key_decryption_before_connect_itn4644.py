"""
Feature: AWSIOT — Verify IoT Priv Key Decryption Before Connect
Description:
  Verify decryption of JWT private key before establishing IoT channel
  connection. Success is decided based on the "Loading AwsIoT keys to
  buffer..." log.
"""

import time


def test_step1_check_datetime(device):
    """Verify decryption of JWT private key before establishing IoT channel connection.

    PreCondition_1 — Verify device datetime is in sync (non-blocking).
    """
    result = device.compare_datetime()
    if result["status"] != "Pass":
        print(f"datetime is incorrect: {result['details']}")


def test_step2_restart_awsiot(device):
    """STEP_1 — Restart awsiot service."""
    device.variables["search_start_ts"] = device.get_current_time_epoch()["epoch_ms"]
    result = device.restart_service("awsiot")
    assert result["status"] == "Pass", f"awsiot service restart failed: {result['details']}"


def test_step3_wait(device):
    """STEP_2 — Wait 10s after restart."""
    time.sleep(10)


def test_step4_verify_keys_loaded(device):
    """STEP_3 — Verify 'Loading AwsIoT keys to buffer' in awsiot logs."""
    ts = device.variables.get("search_start_ts")
    output = device.search_log("/home/ubuntu/.nddevice/log/awsiot", "Loading AwsIoT keys to buffer", start_timestamp=ts, timeout=60, interval=10)
    assert output, "Loading AwsIoT keys to buffer... log message not found"
