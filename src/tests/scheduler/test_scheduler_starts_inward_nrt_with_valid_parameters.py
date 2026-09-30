"""
Feature: Scheduler — Starts Inward NRT With Valid Parameters
Description:
  Verify Inward Non-Real-Time (NRT) processing starts correctly, using the
  expected obsdata/metadata/outdir, and proceeds to start the vision engine.

  Ported from nd_test_bot's
  TC_1315_SCHEDULER_STARTS_INWARD_NRT_WITH_VALID_PARAMETERS. Regex patterns
  (".*") pass through FE's search_log to plain `grep` (basic regex)
  unchanged, same as the other regex-pattern ports in this batch. Note the
  reference's own log message text says "Outward NRT" even in this
  INWARD-named test case (matches the reference exactly, likely a copy-paste
  in the source device logging, not a porting error).

  Log strings (UNVERIFIED -- ported from reference, not yet confirmed on FE)
  need a live check before this test is trusted.
"""


def test_step1_verify_inward_nrt_starts(device):
    """STEP_1 — Verify inference logs starting Inward NRT with valid parameters."""
    for message in [
        "Starting Outward NRT",
        "obsdata: /home/iriscli/ND_OUTPUT/.*/inward_vis_obs.obsdata",
        "metadata: /home/iriscli/ND_OUTPUT/.*/isummary.json",
        "outdir: /home/iriscli/ND_OUTPUT/",
        "running processNRT",
        "Starting vision engine processing",
    ]:
        output = device.search_log("/home/ubuntu/.nddevice/log/inference", message, timeout=125, interval=10)
        assert output, f"'{message}' not found in inference logs"
