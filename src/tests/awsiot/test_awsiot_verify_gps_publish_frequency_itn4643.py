"""
Feature: AWSIOT — Verify GPS Publish Frequency
Description:
  Verify awsiot logs that its GPS data publish frequency is 10 secs after
  a restart.

  Ported skipping the reference's config read/write steps (STEP_1-5:
  check_config_value / download_config / change_param_value / upload_config)
  -- no FE equivalent for the config download/change/upload APIs, and the
  frequency's effective value is confirmed via a log line
  ("AWS IOT gps data publish frequency is 10 secs") anyway, not a config
  file read, so this assumes publish_freq_in_secs is already 10 on the
  device (not toggled by this test) and verifies that state the same way
  the reference's own PostCondition_2 does.
"""

import time


def test_step1_check_datetime(device):
    """Verify awsiot logs its GPS data publish frequency is 10 secs.

    PreCondition_1 — Verify device datetime is in sync (non-blocking).
    """
    result = device.compare_datetime()
    if result["status"] != "Pass":
        print(f"datetime is incorrect: {result['details']}")


def test_step2_restart_awsiot(device):
    """ Restart awsiot service."""
    device.variables["search_start_ts"] = device.get_current_time_epoch()["epoch_ms"]
    result = device.restart_service("awsiot")
    assert result["status"] == "Pass", f"Failed to restart awsiot service: {result['details']}"


def test_step3_wait(device):
    """Wait 10s after restart."""
    time.sleep(10)


def test_step4_verify_gps_publish_frequency(device):
    """Verify 'AWS IOT gps data publish frequency is 10 secs' in awsiot logs."""
    ts = device.variables.get("search_start_ts")
    output = device.search_log("/home/ubuntu/.nddevice/log/awsiot", "AWS IOT gps data publish frequency is 10 secs", start_timestamp=ts, timeout=60, interval=10)
    assert output, "Awsiot gps data publish frequency is 10 secs not found in logs"
