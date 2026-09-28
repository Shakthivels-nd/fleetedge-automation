"""
Feature: AWSIOT — Ping Request Reboot Phone
Description:
  Validate AWSIOT Ping Request: Reboot-phone.
"""

import time


def test_step1_check_datetime(device):
    """Validate AWSIOT Ping Request: Reboot-phone.

    PreCondition_1 — Verify device datetime is in sync (non-blocking).
    """
    result = device.compare_datetime()
    if result["status"] != "Pass":
        print(f"datetime is incorrect: {result['details']}")


def test_step2_send_reboot(device):
    """PreCondition_1 — Send reboot-phone via cloud API."""
    device.variables["search_start_ts"] = device.get_current_time_epoch()["epoch_ms"]
    success, status_code = device.aws_reboot("8430")
    assert success, f"aws_reboot failed with status {status_code}"
    time.sleep(5)


def test_step3_verify_reboot_log(device):
    """STEP_1 — Verify 'Received command: reboot-phone' in logs."""
    ts = device.variables.get("search_start_ts")
    output = device.search_log("/home/ubuntu/.nddevice/log/awsiot", "Received command: reboot-phone", start_timestamp=ts)
    assert output, "reboot-phone command not received in awsiot logs"


def test_step4_verify_rebooting_log(device):
    """STEP_2 — Verify 'Rebooting...' in awsiot logs."""
    ts = device.variables.get("search_start_ts")
    output = device.search_log("/home/ubuntu/.nddevice/log/awsiot", "Rebooting...", start_timestamp=ts, timeout=300, interval=10)
    assert output, "'Rebooting...' not found in awsiot logs"
