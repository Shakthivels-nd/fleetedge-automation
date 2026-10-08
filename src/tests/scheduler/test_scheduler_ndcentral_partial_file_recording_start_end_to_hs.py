"""
Feature: Scheduler — ndcentral Partial File Recording Start/End To HS
Description:
  Verify ndcentral sends recording start/end data to HealthStatsManager for
  a PARTIAL video session (created by restarting bagheera twice back to
  back, interrupting the recording).

  Ported from nd_test_bot's
  TC_1405_SCHEDULER_NDCENTRAL_PARTIAL_FILE_RECORDING_START_END_TO_HS.
  `systemctl restart bagheera` replaced with device.restart_service (FE
  uses supervisorctl, not systemctl).

  Log strings "Partial - rec start", "rec end", "sending msg to hs",
  "recordingstart", "recordingend" (UNVERIFIED -- ported from reference,
  not yet confirmed on FE) need a live check before this test is trusted.
"""

import time


def test_step1_restart_bagheera_first(device):
    """STEP_1 — Restart bagheera service."""
    result = device.restart_service("bagheera")
    assert result["status"] == "Pass", f"Failed to restart bagheera service: {result['details']}"


def test_step2_wait(device):
    """STEP_1_1 — Wait 10s."""
    time.sleep(10)


def test_step3_restart_bagheera_second(device):
    """STEP_2 — Restart bagheera service again (interrupts the recording, creating a partial session)."""
    device.variables["restart_start_ts"] = int(time.time()) * 1000  # epoch ms, just before the restart
    result = device.restart_service("bagheera")
    assert result["status"] == "Pass", f"Failed to restart bagheera service: {result['details']}"


def test_step4_wait(device):
    """STEP_3 — Wait 80s."""
    time.sleep(80)


def test_step5_verify_partial_recording_logged(device):
    """STEP_4 — Verify ndcentral logs partial recording start/end."""
    # The partial-recording line is logged while bagheera/ndcentral restart, i.e. well before this
    # check runs, so no start-time filter here: show only the latest occurrence
    # (ndcentral lines start with "<epoch-ms>: ...", so sort -n on that and tail -1).
    for message in ["Partial - rec start", "rec end"]:
        result = device.run_command_iteratively(
            f"grep -h '{message}' /home/ubuntu/.nddevice/log/ndcentral/* 2>/dev/null | sort -n | tail -n 1",
            iteration=12, timeout=5, not_desired_output=[""],
        )
        assert result["status"] == "Pass", f"'{message}' not found in ndcentral logs: {result['details']}"


def test_step6_verify_recording_data_sent_to_hs(device):
    """STEP_5 — Verify ndcentral logs sending recording data to HS with start/end fields."""
    restart_start_ts = device.variables.get("restart_start_ts")
    assert restart_start_ts, "restart_start_ts was not captured before the second restart"
    for message in ["sending msg to hs", "recordingstart", "recordingend"]:
        output = device.search_log("/home/ubuntu/.nddevice/log/ndcentral", message, restart_start_ts, timeout=60, interval=5)
        assert output, f"'{message}' not found in ndcentral logs"
