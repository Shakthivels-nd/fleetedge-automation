"""
Feature: Scheduler — HealthStats Signal Info
Description:
  Verify cellular signal info (sinr/rsrp/rsrq/rssi, signal_strength) is
  populated in HealthStatsManager's health.log.

  Ported from nd_test_bot's TC_1386_SCHEDULER_HEALTHSTATS_SIGNAL_INFO.

  Log fields "sinr"/"rsrp"/"rsrq"/"rssi"/"signal_strength" (UNVERIFIED --
  ported from reference, not yet confirmed on FE) need a live check before
  this test is trusted.
"""


def test_step1_verify_signal_info_populated(device):
    """STEP_1 — Verify sinr/rsrp/rsrq/rssi fields are populated in health.log."""
    output = device.run("grep -E \"'sinr':|'rsrp':|'rsrq':|'rssi':\" /home/ubuntu/.nddevice/log/health/health.log")
    assert (output or "").strip(), "Failed to populate signal info"


def test_step2_verify_signal_strength_populated(device):
    """STEP_2 — Verify signal_strength field is populated in health.log."""
    output = device.run("grep -E \"'signal_strength':\" /home/ubuntu/.nddevice/log/health/health.log")
    assert (output or "").strip(), "Failed to populate signal strength"
