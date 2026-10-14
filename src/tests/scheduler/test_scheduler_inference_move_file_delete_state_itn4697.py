"""
Feature: Scheduler — Inference Moves File To Delete State
Description:
  Verify a file's state is modified to DELETE_STATE when inference
  processing completes and no alert is detected.

  Ported from nd_test_bot's TC_1301_SCHEDULER_INFERENCE_MOVE_FILE_DELETE_STATE.

  Uses device.run_command_iteratively with not_desired_output=[""] so an
  empty grep (no match yet) drives the retry, piped through `tail -1` to
  capture only the latest matching log line. Original
  search_log(timeout=125, interval=10) is preserved as
  (iteration=13, timeout=10).

  Log strings "is_ib_alert False", "STATE is modified to  state:DELETE_STATE",
  "STATE to DELETE_STATE no alerts found, exit code 0" (UNVERIFIED -- ported
  from reference, not yet confirmed on FE) need a live check before this
  test is trusted.
"""

_LOG_DIR = "/home/ubuntu/.nddevice/log/inference"


def test_step1_verify_file_moved_to_delete_state(device):
    """STEP_1 — Verify inference logs moving the file to DELETE_STATE (no alert)."""
    for message in [
        "is_ib_alert False",
        "STATE is modified to  state:DELETE_STATE",
        "STATE to DELETE_STATE no alerts found, exit code 0",
    ]:
        result = device.run_command_iteratively(
            f"grep -h '{message}' {_LOG_DIR}/*.log 2>/dev/null | tail -1",
            iteration=13, timeout=10, not_desired_output=[""],
        )
        assert result["status"] == "Pass", f"'{message}' not found in inference logs: {result['details']}"
