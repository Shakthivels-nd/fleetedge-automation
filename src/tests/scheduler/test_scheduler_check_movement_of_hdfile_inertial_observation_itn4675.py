"""
Feature: Scheduler — Check Movement Of HD File / Inertial Observation
Description:
  Verify the HD zip file is copied to the internal buffer and inertial
  observations are copied to the internal path.

  Ported from nd_test_bot's
  TC_1297_SCHEDULER_CHECK_MOVEMENT_OF_HDFILE_INERTIAL_OBSERVATION.

  Uses device.run_command_iteratively with not_desired_output=[""] so an
  empty grep (no match yet) drives the retry, piped through `tail -1` to
  capture only the latest matching log line. Original
  search_log(timeout=200, interval=10) is preserved as
  (iteration=20, timeout=10).

  Log strings "copying hd zip to internal buffer" and "Copy of inertial
  observations successful to internal path" (UNVERIFIED -- ported from
  reference, not yet confirmed on FE) need a live check before this test is
  trusted.
"""

_LOG_DIR = "/home/ubuntu/.nddevice/log/inference_inertial"


def test_step1_verify_hdfile_and_inertial_obs_copied(device):
    """STEP_1 — Verify inference_inertial logs copying the HD zip and inertial observations."""
    for message in [
        "copying hd zip to internal buffer",
        "Copy of inertial observations successful to internal path",
    ]:
        result = device.run_command_iteratively(
            f"grep -h '{message}' {_LOG_DIR}/*.log 2>/dev/null | tail -1",
            iteration=20, timeout=10, not_desired_output=[""],
        )
        assert result["status"] == "Pass", f"'{message}' not found in inference_inertial logs: {result['details']}"
