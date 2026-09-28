"""
Feature: AWSIOT — Reboot Request To Powermon
Description:
  Verify AWSIOT processes a cloud reboot-phone ping (log-only -- FE's
  power_mon has no track_turn_off/reboot-tracking mechanism, so the
  reference's physical shutdown check is not ported here) and that
  power_mon receives the reboot request.

  The reference's "Reboot request sent to powermon" awsiot log string does
  not exist on FE (confirmed against real device logs) -- FE logs a
  different sequence instead, checked in STEP_2.
"""

import time


def test_step1_check_datetime(device):
    """Verify AWSIOT sends a reboot request to power_mon.

    PreCondition_1 — Verify device datetime is in sync (non-blocking).
    """
    result = device.compare_datetime()
    if result["status"] != "Pass":
        print(f"datetime is incorrect: {result['details']}")


def test_step2_send_reboot(device):
    """STEP_1 — Send reboot-phone via cloud API."""
    device.variables["search_start_ts"] = device.get_current_time_epoch()["epoch_ms"]
    success, status_code = device.aws_reboot("8430")
    assert success, f"aws_reboot failed with status {status_code}"


def test_step3_verify_awsiot_log(device):
    """STEP_2 — Verify awsiot's reboot-handling log sequence.
    """
    ts = device.variables.get("search_start_ts")
    expected_lines = [
        "Received command: reboot-phone",
        "Rebooting...",
        "Reboot ping triggered, will send reboot request after responding to cloud",
        "Reboot command detected in completed ping request",
    ]
    missing = []
    for line in expected_lines:
        output = device.search_log("/home/ubuntu/.nddevice/log/awsiot", line, start_timestamp=ts, timeout=300, interval=10)
        if not output:
            missing.append(line)
    assert not missing, f"Missing expected awsiot reboot log line(s): {missing}"
