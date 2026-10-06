"""
Feature: Scheduler — Inference Calls Uploader (Upload State)
Description:
  Verify inference starts the Uploader Engine when a file is moved to
  UPLOAD_STATE (alert case).

  Ported from nd_test_bot's TC_1304_SCHEDULER_INFERENCE_CALLS_UPLOADER_UPLOAD_STATE.
  Session-name capture uses device.get_current_session_name AFTER push_alert
  (the reference's own STEP_3_1 already captures via
  FileUtils_obj.get_current_session_name in this test, unlike TC_1302 which
  used get_new_session -- so no substitution needed here, this already
  matches the pattern used elsewhere in this repo).

  push_alert uses gen_ualert.sh (FE's real alert-trigger mechanism, no DTA
  agent on FE devices) instead of the reference's SendMsgServer-based
  push_alert.

  Log strings (UNVERIFIED -- ported from reference, not yet confirmed on FE)
  need a live check before this test is trusted.
"""

import time


def test_step1_restart_bagheera(device):
    """PreCondition_1 — Restart bagheera service."""
    result = device.restart_service("bagheera")
    assert result["status"] == "Pass", f"Failed to restart bagheera service: {result['details']}"


def test_step2_verify_bagheera_active(device):
    """PreCondition_2 — Verify bagheera service is RUNNING."""
    result = device.is_service_active("bagheera")
    assert result["status"] == "Pass", f"bagheera is not RUNNING: {result['state']}"


def test_step3_capture_session_name(device):
    """STEP_1 — Capture the current session name (before pushing the alert)."""
    cmd = (
        "( timeout 170 tail -F /home/ubuntu/.nddevice/log/ndcentral/* 2>/dev/null | "
        "grep --line-buffered -m 1 'creating folder for session' | "
        "awk -F'creating folder for session ' '{print $2}' | awk '{print $1}' ) 2>/dev/null"
    )
    output = device.run(cmd, timeout=180)
    session_name = (output or "").strip()
    assert session_name, f"Session name not found: {output!r}"
    device.variables["session_name"] = session_name


def test_step4_push_alert(device):
    """STEP_3 — Push alert to device."""
    output = device.run("./gen_ualert.sh", "/home/ubuntu/.nddevice/latest/service/bagheera")
    assert device.user_alert_generated(output), f"Failed to generate user alert: {output}"


def test_step5_get_current_session_name(device):
    """STEP_3_1 — Get the current session name after the alert (used for the inference log check)."""
    result = device.get_current_session_name()
    assert result["status"] == "Pass", f"Failed to get current session name: {result['details']}"
    device.variables["session_name_alert"] = result["session_name"]


def test_step6_wait(device):
    """STEP_4 — Wait 80s."""
    time.sleep(80)


def test_step7_verify_svc_button_press(device):
    """STEP_5 — Verify svc detects the button press."""
    output = device.search_log("/home/ubuntu/.nddevice/log/svc", "Sending message for button falling: 0", timeout=30, interval=5)
    assert output, "Log message not found in svc logs"


def test_step8_verify_ndcentral_alert_received(device):
    """STEP_5_1 — Verify ndcentral receives the user alert message."""
    output = device.search_log("/home/ubuntu/.nddevice/log/ndcentral", "User alert msg received", timeout=30, interval=5)
    assert output, "ndcentral does not receive user alert message"


def test_step9_verify_alert_identified_for_session(device):
    """STEP_6 — Verify inference identifies the alert for this session."""
    session_name_alert = device.variables.get("session_name_alert")
    assert session_name_alert, "session_name_alert was not captured in STEP_3_1"
    result = device.run_command_iteratively(
        f"grep -inr -E '0{session_name_alert}.*is_ib_alert True$' /home/ubuntu/.nddevice/log/inference",
        iteration=6, timeout=10,
    )
    assert result["status"] == "Pass", f"Alert not identified for session {session_name_alert!r}: {result['details']}"


def test_step10_verify_state_modified_to_upload_state(device):
    """STEP_7 — Verify inference logs modifying the file's state to UPLOAD_STATE and starting the Uploader Engine."""
    for message in [
        "STATE is modified to  state:UPLOAD_STATE",
        "Uploader Engine is not running. Starting Now",
    ]:
        output = device.search_log("/home/ubuntu/.nddevice/log/inference", message, timeout=60, interval=10)
        assert output, f"'{message}' not found in inference logs"


def test_step11_verify_uploader_started(device):
    """STEP_8 — Verify uploader logs starting the Uploader Engine."""
    output = device.search_log("/home/ubuntu/.nddevice/log/uploader", "Starting Uploader Engine", timeout=30, interval=5)
    assert output, "Uploader Engine is not running"
