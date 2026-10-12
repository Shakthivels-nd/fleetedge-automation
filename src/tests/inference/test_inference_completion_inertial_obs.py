"""
Feature: Scheduler — Completion Inertial Obs
Description:
  Verify inertial processing on an obsdata file completes successfully
  (inference process exits 0 and the engine reports completion).

  Ported from nd_test_bot's TC_1289_SCHEDULER_COMPLETION_INERTIAL_OBS.

  Uses device.run_command_iteratively with not_desired_output=[""] so an
  empty grep (no match yet) drives the retry, piped through `tail -1` to
  capture only the latest matching log line. Original
  search_log(timeout=200, interval=10) is preserved as
  (iteration=20, timeout=10).

  Log strings "accel_inference.main exited with code: 0", "Inertial
  Inference engine process completed", "Exiting inertial :::run_inference"
  (UNVERIFIED -- ported from reference, not yet confirmed on FE) need a
  live check before this test is trusted.
"""

_LOG_DIR = "/home/ubuntu/.nddevice/log/inference_inertial"


def test_step1_verify_inertial_processing_completed(device):
    """STEP_1 — Verify inference_inertial logs successful completion."""
    for message in [
        "accel_inference.main exited with code: 0",
        "Inertial Inference engine process completed",
        "Exiting inertial :::run_inference",
    ]:
        result = device.run_command_iteratively(
            f"grep -h '{message}' {_LOG_DIR}/*.log 2>/dev/null | tail -1",
            iteration=20, timeout=10, not_desired_output=[""],
        )
        assert result["status"] == "Pass", f"'{message}' not found in inference_inertial logs: {result['details']}"
