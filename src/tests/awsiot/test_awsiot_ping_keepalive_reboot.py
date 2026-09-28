"""
Feature: AWSIOT — Ping Keep Alive and Reboot Phone
Description:
  Check whether ping keep alive is occuring or not, then validate AWSIOT
  Ping Request: Reboot-phone.
"""

import time


def test_step1_check_datetime(device):
    """Check whether ping keep alive is occuring or not; validate reboot-phone.

    PreCondition — Verify device datetime is in sync.
    """
    result = device.compare_datetime()
    assert result["status"] == "Pass", f"Device datetime is out of sync: {result['details']}"


def test_step2_send_keepalive_ping(device):
    """STEP_1 — Send AWS keep-alive ping command."""
    device.variables["search_start_ts"] = device.get_current_time_epoch()["epoch_ms"]
    test_status, response_status = device.aws_ping_command("8430", "keep-alive")
    assert test_status == "Pass" and response_status, f"Failed to send keep-alive ping: {test_status}"


def test_step3_1_wait_after_keepalive(device):
    """STEP_1_1 — Wait 35 seconds after keep-alive."""
    time.sleep(35)


def test_step4_check_keepalive_received(device):
    """STEP_2 — Verify 'Received command: keep-alive' in awsiot logs."""
    ts = device.variables.get("search_start_ts")
    output = device.search_log("/home/ubuntu/.nddevice/log/awsiot", "Received command: keep-alive", start_timestamp=ts, timeout=60, interval=10)
    assert output, "awsiot logs missing 'Received command: keep-alive'"


def test_step5_1_wait_before_reboot(device):
    """STEP_2_1 — Wait 2 seconds before sending reboot."""
    time.sleep(2)


def test_step6_send_reboot_phone(device):
    """STEP_3 — Send AWS reboot-phone command."""
    success, status_code = device.aws_reboot("8430")
    assert success, f"Failed to send reboot-phone: status={status_code}"


def test_step7_wait_after_reboot_cmd(device):
    """STEP_4 — Wait 5 seconds after reboot command."""
    time.sleep(5)


def test_step8_check_reboot_received(device):
    """STEP_5 — Verify 'Received command: reboot-phone' in awsiot logs."""
    ts = device.variables.get("search_start_ts")
    output = device.search_log("/home/ubuntu/.nddevice/log/awsiot", "Received command: reboot-phone", start_timestamp=ts, timeout=60, interval=10)
    assert output, "awsiot logs missing 'Received command: reboot-phone'"


def test_step9_verify_rebooting_log(device):
    """STEP_6 — Verify 'Rebooting...' in awsiot logs after reboot-phone command."""
    ts = device.variables.get("search_start_ts")
    output = device.search_log("/home/ubuntu/.nddevice/log/awsiot", "Rebooting...", start_timestamp=ts, timeout=250, interval=10)
    assert output, "awsiot logs missing 'Rebooting...' after reboot-phone command"
