"""
Feature: Scheduler — Starts Outward NRT With Valid Parameters
Description:
  Verify Outward Non-Real-Time (NRT) processing starts correctly, using the
  expected obsdata/metadata/outdir, and proceeds to start the vision engine.

  Ported from nd_test_bot's
  TC_1314_SCHEDULER_STARTS_OUTWARD_NRT_WITH_VALID_PARAMETERS. Regex patterns
  (".*") pass through FE's search_log to plain `grep` (basic regex)
  unchanged, same as the other regex-pattern ports in this batch.

  Log strings (UNVERIFIED -- ported from reference, not yet confirmed on FE)
  need a live check before this test is trusted.
"""


def test_step1_verify_outward_nrt_starts(device):
    """STEP_1 — Verify inference logs starting Outward NRT with valid parameters."""
    for message in [
        "Starting Outward NRT",
        "obsdata: /home/iriscli/ND_OUTPUT/.*/outward_vis_obs.obsdata",
        "metadata: /home/iriscli/ND_OUTPUT/.*/isummary.json",
        "outdir: /home/iriscli/ND_OUTPUT/",
        "running processNRT",
        "Starting vision engine processing",
    ]:
        output = device.search_log("/home/ubuntu/.nddevice/log/inference", message, timeout=125, interval=10)
        assert output, f"'{message}' not found in inference logs"
