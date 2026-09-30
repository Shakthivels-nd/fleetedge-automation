"""
Feature: Scheduler — Deleter Checks Delete State
Description:
  Verify deleter checks the DELETE_STATE of files it receives from ND_INPUT.

  Ported from nd_test_bot's TC_1336_SCHEDULER_DELETER_CHECKS_DELETE_SATE.
  Session name is captured (matching the reference's STEP_1) but, same as
  the reference, never consumed by the later log check -- kept for
  parity/debug visibility.

  Log strings "Entering into ::check_delete_state" and "Checking
  DELETE_STATE in file: /home/iriscli/ND_INPUT/0_trip" (UNVERIFIED --
  ported from reference, not yet confirmed on FE) need a live check before
  this test is trusted.
"""


def test_step1_verify_bagheera_active(device):
    """PreCondition_2 — Verify bagheera service is RUNNING."""
    result = device.is_service_active("bagheera")
    assert result["status"] == "Pass", f"bagheera is not RUNNING: {result['state']}"


def test_step2_get_current_session_name(device):
    """STEP_1 — Get the current session name."""
    result = device.get_current_session_name(cam_num=0)
    assert result["status"] == "Pass", f"Session name not found: {result['details']}"
    device.variables["session_name"] = result["session_name"]


def test_step3_verify_deleter_checks_delete_state(device):
    """STEP_3 — Verify deleter logs entering and checking DELETE_STATE for files in ND_INPUT."""
    for message in [
        "Entering into ::check_delete_state",
        "Checking DELETE_STATE in file: /home/iriscli/ND_INPUT/0_trip",
    ]:
        output = device.search_log("/home/ubuntu/.nddevice/log/deleter", message, timeout=120, interval=20)
        assert output, f"'{message}' not found in deleter logs"
