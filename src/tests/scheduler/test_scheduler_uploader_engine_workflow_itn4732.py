"""
Feature: Scheduler — Uploader Engine Workflow
Description:
  Verify the complete uploader engine workflow: initialization, state
  checking, event triggering, file state modification, file sync
  completion, and engine shutdown.

  Ported from nd_test_bot's TC_1327_SCHEDULER_UPLOADER_ENGINE_WORKFLOW.
  Session name is captured (matching the reference's STEP_1) but, same as
  the reference, never consumed by the later log checks -- kept for
  parity/debug visibility. Every log check greps all uploader logs
  (rotated ones included) on the device and shows only the latest
  occurrence; regex patterns (".*") are passed to `grep` (basic regex)
  unchanged.

  push_alert uses gen_ualert.sh (FE's real alert-trigger mechanism, no DTA
  agent on FE devices) instead of the reference's SendMsgServer-based
  push_alert.

  Log strings (UNVERIFIED -- ported from reference, not yet confirmed on FE)
  need a live check before this test is trusted.
"""

import time


_LOG_DIR = "/home/ubuntu/.nddevice/log/uploader"


def _grep_latest(device, message, error):
    """Grep every uploader log (rotated ones included) for `message` (basic regex) and show only the
    latest occurrence: lines start with "YYYY-MM-DD HH:MM:SS,mmm", so sort + tail -1 gives the newest.
    Retries up to 30s (6 x 5s) until something is found."""
    result = device.run_command_iteratively(
        f"grep -h '{message}' {_LOG_DIR}/* 2>/dev/null | sort | tail -n 1",
        iteration=6, timeout=5, not_desired_output=[""],
    )
    assert result["status"] == "Pass", f"{error}: {result['details']}"


def test_step1_verify_bagheera_active(device):
    """PreCondition_2 — Verify bagheera service is RUNNING."""
    result = device.is_service_active("bagheera")
    assert result["status"] == "Pass", f"bagheera is not RUNNING: {result['state']}"


def test_step2_get_current_session_name(device):
    """STEP_1 — Get the current session name (before pushing the alert)."""
    result = device.get_current_session_name()
    assert result["status"] == "Pass", f"Session name not found: {result['details']}"
    device.variables["session_name"] = result["session_name"]


def test_step3_push_alert(device):
    """STEP_3 — Push alert to device."""
    output = device.run("./gen_ualert.sh", "/home/ubuntu/.nddevice/latest/service/bagheera")
    assert device.user_alert_generated(output), f"Failed to generate user alert: {output}"


def test_step4_wait(device):
    """STEP_4 — Wait 100s."""
    time.sleep(100)


def test_step5_verify_uploader_engine_started(device):
    """STEP_5 — Verify uploader logs starting the Uploader Engine."""
    _grep_latest(device, "Starting Uploader Engine", "Uploader Engine not started")


def test_step6_verify_upload_state_checked(device):
    """STEP_6 — Verify uploader logs checking UPLOAD_STATE in ND_INPUT."""
    _grep_latest(device, "Checking UPLOAD_STATE in file: /home/iriscli/ND_INPUT", "UPLOAD_STATE not checked")


def test_step7_verify_event_data_message_sent(device):
    """STEP_7 — Verify uploader logs sending a MSG_TYPE_EVENTDATA message."""
    _grep_latest(device, "sending message <newUploadMetaData.MSG_TYPE_EVENTDATA object at .* to uploader", "Uploader did not detect the alert and send msgtype to uploader")


def test_step8_verify_event_codes_and_ib_alert(device):
    """STEP_8 — Verify uploader logs commn_set/event_codes/ibAlert True."""
    for message in ["commn_set", "event_codes", "ibAlert True"]:
        _grep_latest(device, message, f"'{message}' not detected in uploader logs")


def test_step9_verify_state_modified_to_job_submit_state(device):
    """STEP_9 — Verify uploader logs modifying state to JOB_SUBMIT_STATE."""
    _grep_latest(device, "STATE is modified to  state:JOB_SUBMIT_STATE", "Uploader did not modify state to JOB_SUBMIT_STATE")


def test_step10_verify_file_sync_finished(device):
    """STEP_10 — Verify uploader logs finishing the file sync."""
    _grep_latest(device, "File sync finished: /home/iriscli/ND_INPUT", "File sync not finished")


def test_step11_verify_uploader_engine_shutdown(device):
    """STEP_11 — Verify uploader logs shutting down the Uploader Engine."""
    _grep_latest(device, "Shutting down Uploader Engine", "Uploader Engine not shutdown")
