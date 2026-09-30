"""
Feature: Scheduler — ndcentral Recording Start/End To HS
Description:
  Verify ndcentral sends recording start/end data to HealthStatsManager for
  every video session.

  Ported from nd_test_bot's TC_1404_SCHEDULER_NDCENTRAL_RECORDING_START_END_TO_HS.
  `systemctl restart bagheera` replaced with device.restart_service (FE
  uses supervisorctl, not systemctl).

  Log strings "sending recording data to HS", "Recording start time", "end
  time =", "recordingstart", "recordingend" (UNVERIFIED -- ported from
  reference, not yet confirmed on FE) need a live check before this test is
  trusted.
"""

import time


def test_step1_restart_bagheera(device):
    """STEP_1 — Restart bagheera service."""
    result = device.restart_service("bagheera")
    assert result["status"] == "Pass", f"Failed to restart bagheera service: {result['details']}"


def test_step2_wait(device):
    """STEP_2 — Wait 80s."""
    time.sleep(80)


def test_step3_verify_recording_data_sent_to_hs(device):
    """STEP_3 — Verify ndcentral logs sending recording data to HS."""
    output = device.search_log("/home/ubuntu/.nddevice/log/ndcentral", "sending recording data to HS", timeout=30, interval=5)
    assert output, "Recording data is not sent to HS"


def test_step4_verify_recording_start_end_fields(device):
    """STEP_4 — Verify ndcentral logs recording start/end time fields."""
    for message in ["Recording start time", "end time =", "recordingstart", "recordingend"]:
        output = device.search_log("/home/ubuntu/.nddevice/log/ndcentral", message, timeout=30, interval=5)
        assert output, f"'{message}' not found in ndcentral logs"
