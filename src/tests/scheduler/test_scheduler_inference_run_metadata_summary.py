"""
Feature: Scheduler — Inference Runs Metadata Summary
Description:
  Verify vision inference starts processing on the isummary.json metadata
  file.

  Ported from nd_test_bot's TC_1310_SCHEDULER_INFERENCE_RUN_METADATA_SUMMARY.
  The reference's pattern is regex (".*" for the session-specific path
  segment) -- FE's search_log passes patterns to plain `grep` (basic
  regex), which already supports "." and "*" the same way, so no special
  regex flag/handling is needed here.

  Log string "Entering vision :::run_inference::: /home/iriscli/ND_OUTPUT/.*/isummary.json"
  (UNVERIFIED -- ported from reference, not yet confirmed on FE) needs a
  live check before this test is trusted.
"""


def test_step1_verify_vision_inference_starts_on_isummary(device):
    """STEP_1 — Verify inference logs entering vision inference on isummary.json."""
    output = device.search_log("/home/ubuntu/.nddevice/log/inference", "Entering vision :::run_inference::: /home/iriscli/ND_OUTPUT/.*/isummary.json", timeout=125, interval=10)
    assert output, "Vision inference did not start on isummary.json"
