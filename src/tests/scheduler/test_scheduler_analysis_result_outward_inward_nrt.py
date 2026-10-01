"""
Feature: Scheduler — Analysis Result Outward/Inward NRT
Description:
  Verify both outward and inward NRT analysis runs report a successful
  (0) result.

  Ported from nd_test_bot's TC_1319_SCHEDULER_ANALYSIS_RESULT_OUTWARD_INWARD_NRT.

  Uses device.run_command_iteratively with not_desired_output=[""] so an
  empty grep (no match yet) drives the retry, piped through `tail -1` to
  capture only the latest matching log line. Original
  search_log(timeout=200, interval=10) is preserved as
  (iteration=20, timeout=10).

  Log strings "outAnalyseRunResult = 0" and "inAnalyseRunResult = 0"
  (UNVERIFIED -- ported from reference, not yet confirmed on FE) need a
  live check before this test is trusted.
"""

_LOG_DIR = "/home/ubuntu/.nddevice/log/inference"


def test_step1_verify_outward_inward_analysis_results(device):
    """STEP_1 — Verify inference logs both outward and inward analysis results as 0."""
    for message in ["outAnalyseRunResult = 0 and inAnalyseRunResult = 0"]:
        result = device.run_command_iteratively(
            f"grep -h '{message}' {_LOG_DIR}/*.log 2>/dev/null | tail -1",
            iteration=20, timeout=10, not_desired_output=[""],
        )
        assert result["status"] == "Pass", f"'{message}' not found in inference logs: {result['details']}"
