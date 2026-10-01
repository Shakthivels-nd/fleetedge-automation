"""
Feature: Scheduler — Session NRT Completion Status
Description:
  Verify NRT processing completes successfully (status 0) for a session.

  Ported from nd_test_bot's TC_1318_SCHEDULER_SESSION_NRT_COMPLETION_STATUS.
  Uses device.get_current_session_name (same as the reference's
  FileUtils_obj.get_current_session_name call here -- no substitution
  needed, this test doesn't push an alert so there's no before/after-alert
  ordering question).

  Log string "NRT processing finished for session_id .* with status 0"
  (regex, UNVERIFIED -- ported from reference, not yet confirmed on FE)
  needs a live check before this test is trusted.
"""

import time


def test_step1_verify_bagheera_active(device):
    """PreCondition_2 — Verify bagheera service is RUNNING."""
    result = device.is_service_active("bagheera")
    assert result["status"] == "Pass", f"bagheera is not RUNNING: {result['state']}"


def test_step2_get_current_session_name(device):
    """STEP_1 — Get the current session name."""
    result = device.get_current_session_name()
    assert result["status"] == "Pass", f"Session name not found: {result['details']}"
    device.variables["session_name"] = result["session_name"]


def test_step3_wait(device):
    """STEP_1_1 — Wait 60s."""
    time.sleep(60)


def test_step4_verify_nrt_completion(device):
    """STEP_2 — Verify inference logs NRT processing finishing with status 0."""
    output = device.search_log("/home/ubuntu/.nddevice/log/inference", "NRT processing finished for session_id .* with status 0", timeout=60, interval=10)
    session_name = device.variables.get("session_name")
    assert output, f"NRT processing not completed for session {session_name!r}"
