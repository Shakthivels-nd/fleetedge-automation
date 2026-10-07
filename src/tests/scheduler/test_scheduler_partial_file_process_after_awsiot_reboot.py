"""
Feature: Scheduler — Partial File Process After AWSIOT Reboot
Description:
  Verify partial files are processed after the device reboots due to an
  AWSIOT reboot-phone request.

  Ported from nd_test_bot's TC_1432_SCHEDULER_PARTIAL_FILE_PROCESS_AFTER_AWSIOT_REBOOT.
  The reference's DeviceController_obj.track_reboot (STEP_4) is replaced with
  awsiot log checks, as in test_awsiot_ping_request_reboot_phone.py: the
  "Received command: reboot-phone" and "Rebooting..." lines logged after the
  reboot request. `systemctl is-active scheduler_manager` is replaced with
  device.is_service_active (supervisorctl).

  Log strings "Received command: reboot-phone", "Rebooting..." and "Inside
  filename /home/iriscli/ND_INPUT/<session>" (UNVERIFIED -- ported from
  reference / sibling test, not yet confirmed on FE for this flow) need a
  live check before this test is trusted.
"""

import time


def test_step1_wait(device):
    """PreCondition_1 — Wait 10s."""
    time.sleep(10)


def test_step2_verify_bagheera_active(device):
    """PreCondition_2 — Verify bagheera service is RUNNING."""
    result = device.is_service_active("bagheera")
    assert result["status"] == "Pass", f"bagheera is not RUNNING: {result['state']}"


def test_step3_get_new_session(device):
    """STEP_1 — Capture the next new session created."""
    result = device.get_new_session()
    assert result["status"] == "Pass", f"Session name not found: {result['details']}"
    device.variables["session_name"] = result["session_name"]


def test_step4_wait(device):
    """STEP_2 — Wait 10s."""
    time.sleep(10)


def test_step5_send_reboot(device):
    """STEP_3 — Send reboot-phone via cloud API."""
    device.variables["search_start_ts"] = device.get_current_time_epoch()["epoch_ms"]
    success, status_code = device.aws_reboot("8430")
    assert success, f"aws_reboot failed with status {status_code}"
    time.sleep(5)


def test_step6_verify_reboot_log(device):
    """STEP_4 — Verify 'Received command: reboot-phone' in awsiot logs."""
    ts = device.variables.get("search_start_ts")
    output = device.search_log("/home/ubuntu/.nddevice/log/awsiot", "Received command: reboot-phone", start_timestamp=ts)
    assert output, "reboot-phone command not received in awsiot logs"


def test_step7_verify_rebooting_log(device):
    """STEP_5 — Verify 'Rebooting...' in awsiot logs."""
    ts = device.variables.get("search_start_ts")
    output = device.search_log("/home/ubuntu/.nddevice/log/awsiot", "Rebooting...", start_timestamp=ts, timeout=300, interval=10)
    assert output, "'Rebooting...' not found in awsiot logs"


def test_step8_verify_scheduler_manager_active(device):
    """STEP_6 — Verify scheduler_manager service is RUNNING."""
    result = device.is_service_active("scheduler_manager")
    assert result["status"] == "Pass", f"Scheduler Manager service is not active: {result['state']}"


def test_step9_wait(device):
    """STEP_7 — Wait 70s."""
    time.sleep(70)


def test_step10_verify_partial_files_processed(device):
    """STEP_8 — Verify scheduler logs processing the session's partial files after the reboot."""
    session_name = device.variables.get("session_name")
    assert session_name, "Session name was not captured"
    result = device.run_command_iteratively(
        f"grep -rh 'Inside filename /home/iriscli/ND_INPUT/0{session_name}' /home/ubuntu/.nddevice/log/scheduler 2>/dev/null | tail -1",
        iteration=12, timeout=5, not_desired_output=[""],
    )
    assert result["status"] == "Pass", f"Partial files are not processed: {result['details']}"
    print(f"Processed: {result['output']}")
