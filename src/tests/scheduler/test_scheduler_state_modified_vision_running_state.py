"""
Feature: Scheduler — State Modified To VISION_RUNNING_STATE
Description:
  Verify a file's state is modified to VISION_RUNNING_STATE.

  Ported from nd_test_bot's TC_1309_SCHEDULER_STATE_MODIFIED_VISION_RUNNING_STATE.

  Log string "STATE is modified to  state:VISION_RUNNING_STATE" (UNVERIFIED
  -- ported from reference, not yet confirmed on FE) needs a live check
  before this test is trusted.
"""


def test_step1_verify_vision_running_state(device):
    """STEP_1 — Verify inference logs modifying state to VISION_RUNNING_STATE."""
    output = device.search_log("/home/ubuntu/.nddevice/log/inference", "STATE is modified to  state:VISION_RUNNING_STATE", timeout=200, interval=10)
    assert output, "State is not modified to VISION_RUNNING_STATE"
