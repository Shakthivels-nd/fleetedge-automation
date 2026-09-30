"""
Feature: Scheduler — Inference Calls Deleter (Delete State)
Description:
  Verify inference starts the Deleter Engine when a file is moved to
  DELETE_STATE (no alert case).

  Ported from nd_test_bot's TC_1303_SCHEDULER_INFERENCE_CALLS_DELETER_DELETE_STATE.

  Uses device.run_command_iteratively with not_desired_output=[""] so an
  empty grep (no match yet) drives the retry, piped through `tail -1` to
  capture only the latest matching log line. Original
  search_log(timeout, interval) pairs are preserved as
  (iteration=timeout/interval, timeout=interval).

  Log strings "is_ib_alert False", "STATE is modified to  state:DELETE_STATE",
  "STATE to DELETE_STATE no alerts found, exit code 0",
  "Deleter Engine is not running. Starting Now", "Starting Delete Engine"
  (UNVERIFIED -- ported from reference, not yet confirmed on FE) need a
  live check before this test is trusted.
"""

_INFERENCE_LOG_DIR = "/home/ubuntu/.nddevice/log/inference"
_DELETER_LOG_DIR = "/home/ubuntu/.nddevice/log/deleter"


def test_step1_verify_file_moved_to_delete_state(device):
    """STEP_1 — Verify inference logs moving the file to DELETE_STATE and starting the Deleter Engine."""
    for message in [
        "is_ib_alert False",
        "STATE is modified to  state:DELETE_STATE",
        "STATE to DELETE_STATE no alerts found, exit code 0",
        "Deleter Engine is not running. Starting Now",
    ]:
        result = device.run_command_iteratively(
            f"grep -h '{message}' {_INFERENCE_LOG_DIR}/*.log 2>/dev/null | tail -1",
            iteration=13, timeout=10, not_desired_output=[""],
        )
        assert result["status"] == "Pass", f"'{message}' not found in inference logs: {result['details']}"


def test_step2_verify_deleter_started(device):
    """STEP_2 — Verify deleter logs starting the Delete Engine."""
    result = device.run_command_iteratively(
        f"grep -h 'Starting Delete Engine' {_DELETER_LOG_DIR}/*.log 2>/dev/null | tail -1",
        iteration=6, timeout=5, not_desired_output=[""],
    )
    assert result["status"] == "Pass", f"Deleter did not start the Delete Engine: {result['details']}"
