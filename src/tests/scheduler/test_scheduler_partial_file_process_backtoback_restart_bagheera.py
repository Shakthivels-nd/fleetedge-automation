"""
Feature: Scheduler — Partial File Process After Back-To-Back Bagheera Restarts
Description:
  Verify partial files from two sessions are processed after bagheera is
  restarted back to back immediately (twice), each restart creating a
  partial recording.

  Ported from nd_test_bot's
  TC_1459_SCHEDULER_PARTIAL_FILE_PROCESS_BACKTOBACK_RESTART_BAGHEERA.
  `systemctl restart bagheera/scheduler_manager` replaced with
  device.restart_service.

  Log strings "Partial - rec start", "rec end", "Inside filename
  /home/iriscli/ND_INPUT/<session>" (UNVERIFIED -- ported from reference,
  not yet confirmed on FE) need a live check before this test is trusted.
"""

import time


def test_step1_wait(device):
    """PreCondition_1 — Wait 10s."""
    time.sleep(10)


def test_step2_restart_bagheera_first(device):
    """STEP_1 — Restart bagheera service."""
    result = device.restart_service("bagheera")
    assert result["status"] == "Pass", f"Failed to restart bagheera service: {result['details']}"


def test_step3_wait(device):
    """STEP_1_1 — Wait 15s."""
    time.sleep(15)


def test_step4_get_first_session_name(device):
    """STEP_1_2 — Get the current session name (non-blocking)."""
    result = device.get_current_session_name(cam_num=0)
    if result["status"] != "Pass":
        print(f"First session name not found: {result['details']}")
    device.variables["session_name_first"] = result.get("session_name")


def test_step5_restart_bagheera_second(device):
    """STEP_2 — Restart bagheera service again."""
    result = device.restart_service("bagheera")
    assert result["status"] == "Pass", f"Failed to restart bagheera service: {result['details']}"


def test_step6_wait(device):
    """STEP_2_1 — Wait 15s."""
    time.sleep(15)


def test_step7_get_second_session_name(device):
    """STEP_2_2 — Get the current session name (non-blocking)."""
    result = device.get_current_session_name(cam_num=0)
    if result["status"] != "Pass":
        print(f"Second session name not found: {result['details']}")
    device.variables["session_name_second"] = result.get("session_name")


def test_step8_restart_bagheera_third(device):
    """STEP_3 — Restart bagheera service a third time."""
    result = device.restart_service("bagheera")
    assert result["status"] == "Pass", f"Failed to restart bagheera service: {result['details']}"


def test_step9_wait(device):
    """STEP_3_1 — Wait 10s."""
    time.sleep(10)


def test_step10_restart_scheduler_manager(device):
    """STEP_3_2 — Restart scheduler_manager service."""
    result = device.restart_service("scheduler_manager")
    assert result["status"] == "Pass", f"Failed to restart scheduler_manager service: {result['details']}"


def test_step11_wait(device):
    """STEP_3_3 — Wait 90s."""
    time.sleep(90)


def test_step12_verify_partial_recording_data(device):
    """STEP_4 — Verify ndcentral logs partial recording start/end."""
    for message in ["Partial - rec start", "rec end"]:
        output = device.search_log("/home/ubuntu/.nddevice/log/ndcentral", message, timeout=30, interval=5)
        assert output, f"'{message}' not found in ndcentral logs"


def test_step13_verify_both_sessions_processed(device):
    """STEP_5 — Verify scheduler logs processing both partial sessions."""
    session_name_first = device.variables.get("session_name_first")
    session_name_second = device.variables.get("session_name_second")
    for session_name in [session_name_first, session_name_second]:
        assert session_name, "Session name was not captured"
        output = device.search_log("/home/ubuntu/.nddevice/log/scheduler", f"Inside filename /home/iriscli/ND_INPUT/{session_name}", timeout=30, interval=5)
        assert output, f"Partial files for session {session_name!r} are not processed"
