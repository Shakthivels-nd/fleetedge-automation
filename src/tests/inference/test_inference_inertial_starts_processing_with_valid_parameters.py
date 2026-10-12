"""
Feature: Scheduler — Inertial Starts Processing With Valid Parameters
Description:
  Verify inference_inertial starts processing an obsdata file with the
  expected obsdata/metadata/outdir parameters.

  Ported from nd_test_bot's
  TC_1281_SCHEDULER_INERTIAL_STARTS_PROCESSING_WITH_VALID_PARAMETERS. The
  reference's patterns are regex (obsdata/metadata lines use ".*" to match
  the session-specific path segment) -- grep's basic regex already supports
  "." and "*" the same way, so no special regex flag/handling is needed here.

  Uses device.run_command_iteratively with not_desired_output=[""] so an
  empty grep (no match yet) drives the retry, piped through `tail -1` to
  capture only the latest matching log line. Original
  search_log(timeout=200, interval=10) is preserved as
  (iteration=20, timeout=10).

  Log strings (UNVERIFIED -- ported from reference, not yet confirmed on FE)
  need a live check before this test is trusted.
"""

_LOG_DIR = "/home/ubuntu/.nddevice/log/inference_inertial"


def test_step1_verify_inertial_processing_started(device):
    """STEP_1 — Verify inference_inertial logs starting processing with valid obsdata/metadata/outdir."""
    for message in [
        "Started inertial processing",
        "obsdata:",
        "metadata: /home/iriscli/ND_INPUT/.*_ymetadata.txt",
        "outdir: /home/iriscli/ND_OUTPUT/",
    ]:
        result = device.run_command_iteratively(
            f"grep -h '{message}' {_LOG_DIR}/*.log 2>/dev/null | tail -1",
            iteration=20, timeout=10, not_desired_output=[""],
        )
        assert result["status"] == "Pass", f"'{message}' not found in inference_inertial logs: {result['details']}"
