"""
Feature: Scheduler — Inference Moves File To Upload State
Description:
  Verify a file's state is modified to UPLOAD_STATE when inference
  processing completes and an alert IS detected for the session.

  Ported from nd_test_bot's TC_1302_SCHEDULER_INFERENCE_MOVE_FILE_UPLOAD_STATE.
  Uses device.get_new_session (ported from nd_test_bot's
  FileUtils_obj.get_new_session, per user instruction -- see device_checks.py
  for the forward-poll caveat noted there) to capture the alert's session,
  matching the reference's own mechanism and step order (capture BEFORE
  push_alert) exactly.

  push_alert uses gen_ualert.sh (FE's real alert-trigger mechanism, no DTA
  agent on FE devices) instead of the reference's SendMsgServer-based
  push_alert.
  Log strings "is_ib_alert True", "STATE is modified to  state:UPLOAD_STATE",
  "STATE to UPLOAD_STATE   alerts found, exit code 0" (double space
  preserved exactly as in the reference; UNVERIFIED -- ported from
  reference, not yet confirmed on FE) need a live check before this test is
  trusted.
"""

import time


def test_step1_wait_before_start(device):
    """PreCondition_1 — Wait 15s."""
    time.sleep(15)


def test_step2_verify_bagheera_active(device):
    """PreCondition_2 — Verify bagheera service is RUNNING."""
    result = device.is_service_active("bagheera")
    assert result["status"] == "Pass", f"bagheera is not RUNNING: {result['state']}"


def test_step3_wait_before_alert(device):
    """STEP_1 — Wait 10s."""
    time.sleep(10)


def test_step4_get_new_session(device):
    """STEP_1_1 — Capture the next new session created (before pushing the alert)."""
    result = device.get_new_session()
    assert result["status"] == "Pass", f"Failed to get new session: {result['details']}"
    device.variables["session_name_alert"] = result["session_name"]


def test_step5_push_alert(device):
    """STEP_2 — Push alert to device."""
    device.variables["alert_start_ts"] = int(time.time()) * 1000  # epoch ms, just before the alert
    output = device.run("./gen_ualert.sh", "/home/ubuntu/.nddevice/latest/service/bagheera")
    assert device.user_alert_generated(output), f"Failed to generate user alert: {output}"


def test_step6_wait(device):
    """STEP_2_2 — Wait 80s."""
    time.sleep(80)


def test_step7_verify_alert_identified_for_session(device):
    """STEP_5 — Verify inference identifies the alert for this session."""
    session_name_alert = device.variables.get("session_name_alert")
    assert session_name_alert, "session_name_alert was not captured in STEP_1_1"
    result = device.run_command_iteratively(
        f"grep -inr -E '0{session_name_alert}.*is_ib_alert True$' /home/ubuntu/.nddevice/log/inference",
        iteration=13, timeout=10, not_desired_output=[""],
    )
    assert result["status"] == "Pass", f"Alert not identified for session {session_name_alert!r}: {result['details']}"


def test_step8_verify_state_modified_to_upload_state(device):
    """STEP_6 — Verify inference logs modifying the file's state to UPLOAD_STATE."""
    alert_start_ts = device.variables.get("alert_start_ts")
    assert alert_start_ts, "alert_start_ts was not captured in the push-alert step"
    for message in [
        "is_ib_alert True",
        "STATE is modified to  state:UPLOAD_STATE",
        "STATE to UPLOAD_STATE   alerts found, exit code 0",
    ]:
        output = device.search_log("/home/ubuntu/.nddevice/log/inference", message, alert_start_ts, timeout=60, interval=10)
        assert output, f"'{message}' not found in inference logs"
