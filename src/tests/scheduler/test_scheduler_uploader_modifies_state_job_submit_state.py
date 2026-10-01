"""
Feature: Scheduler — Uploader Modifies State To JOB_SUBMIT_STATE
Description:
  Verify uploader modifies a file's state to JOB_SUBMIT_STATE after an
  alert is pushed.

  Ported from nd_test_bot's
  TC_1326_SCHEDULER_UPLOADER_MODIFIES_STATE_JOB_SUBMIT_STATE. Session name
  is captured (matching the reference's STEP_1) but, same as the
  reference, never consumed by the later log check -- kept for parity/debug
  visibility.

  push_alert uses gen_ualert.sh (FE's real alert-trigger mechanism, no DTA
  agent on FE devices) instead of the reference's SendMsgServer-based
  push_alert.

  Log string "STATE is modified to  state:JOB_SUBMIT_STATE" (UNVERIFIED --
  ported from reference, not yet confirmed on FE) needs a live check before
  this test is trusted.
"""

import time


def test_step1_get_current_session_name(device):
    """STEP_1 — Get the current session name (before pushing the alert)."""
    result = device.get_current_session_name()
    assert result["status"] == "Pass", f"Session name not found: {result['details']}"
    device.variables["session_name"] = result["session_name"]


def test_step2_push_alert(device):
    """STEP_3 — Push alert to device."""
    output = device.run("./gen_ualert.sh", "/home/ubuntu/.nddevice/latest/service/bagheera")
    assert output and "User alert is generated..!!!" in output, f"Failed to generate user alert: {output}"


def test_step3_wait(device):
    """STEP_4 — Wait 50s."""
    time.sleep(50)


def test_step4_verify_state_modified_to_job_submit_state(device):
    """STEP_5 — Verify uploader logs modifying state to JOB_SUBMIT_STATE."""
    output = device.search_log("/home/ubuntu/.nddevice/log/uploader", "STATE is modified to  state:JOB_SUBMIT_STATE", timeout=60, interval=10)
    assert output, "Uploader did not modify state to JOB_SUBMIT_STATE"
