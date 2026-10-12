"""
Feature: Scheduler — File State NOT_DND (No Alerts)
Description:
  Verify inference_inertial extracts 0 alerts and moves the file to
  NOT_DND_STATE when no inertial alerts are found for a session.

  Ported from nd_test_bot's TC_1254_SCHEDULER_FILE_STATE_NOT_DND_NO_ALERTS.

  Uses device.run_command_iteratively with not_desired_output=[""] so an
  empty grep (no match yet) drives the retry, piped through `tail -1` to
  capture only the latest matching log line. Original
  search_log(timeout=200, interval=10) is preserved as
  (iteration=20, timeout=10).

  STEP_1 (the "Extracted 0 alerts" check, previously missing from this
  port) confirmed live at /home/ubuntu/.nddevice/log/inference -- the
  message appears there as "Extracted 0 alerts from 0 events", including
  across rotated log files (inference.log.<ts>), hence the `*.log*` glob.

  Log strings "Extracted 0 alerts" and "STATE is modified to  state:NOT_DND_STATE"
  need a live check on inference_inertial before this test is fully trusted.
"""

_INFERENCE_LOG_DIR = "/home/ubuntu/.nddevice/log/inference"
_INFERENCE_INERTIAL_LOG_DIR = "/home/ubuntu/.nddevice/log/inference_inertial"


def test_step1_verify_zero_alerts_extracted(device):
    """STEP_1 — Verify inference logs extracting 0 alerts from 0 events."""
    result = device.run_command_iteratively(
        f"grep -h 'Extracted 0 alerts' {_INFERENCE_LOG_DIR}/*.log* 2>/dev/null | tail -1",
        iteration=20, timeout=10, not_desired_output=[""],
    )
    assert result["status"] == "Pass", f"'Extracted 0 alerts' not found in inference logs: {result['details']}"


def test_step2_verify_not_dnd_state(device):
    """STEP_2 — Verify inference_inertial logs modifying state to NOT_DND_STATE."""
    result = device.run_command_iteratively(
        f"grep -h 'STATE is modified to  state:NOT_DND_STATE' {_INFERENCE_INERTIAL_LOG_DIR}/*.log 2>/dev/null | tail -1",
        iteration=20, timeout=10, not_desired_output=[""],
    )
    assert result["status"] == "Pass", f"State not modified to NOT_DND_STATE: {result['details']}"
