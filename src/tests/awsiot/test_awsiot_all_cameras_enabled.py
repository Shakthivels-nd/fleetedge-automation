"""
Feature: AWSIOT — All Cameras Enabled
Description:
  Verify awsiot logs "response sent for cameras:15 request" after a
  restart, confirming all cameras are enabled (bagheera-type camera
  bitmask: left+right+front+back = 0b1111 = 15; the reference's krait-type
  ":3" variant is not applicable here -- FE's real log line confirmed via
  device grep to be "response sent for cameras:15 request", i.e. FE is
  bagheera-type).

  Ported skipping the reference's config read/write steps (STEP_1,
  STEP_3/3_1/4/4_1, STEP_5: download_config / change_param_value (per
  camera) / upload_config) -- no FE equivalent for the config
  download/change/upload APIs, and the enabled state is confirmed via a
  log line anyway, not a config file read, so this assumes all cameras
  are already enabled on the device (not toggled by this test) and
  verifies that state the same way the reference's own STEP_7_1 does.
"""

import time


def test_step1_check_datetime(device):
    """Verify awsiot logs that all cameras are enabled.

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


def test_step4_verify_all_cameras_enabled(device):
    """Verify 'response sent for cameras:15 request' in awsiot logs."""
    ts = device.variables.get("search_start_ts")
    output = device.search_log("/home/ubuntu/.nddevice/log/awsiot", "response sent for cameras:15 request", start_timestamp=ts, timeout=60, interval=10)
    assert output, "All cameras not enabled"
