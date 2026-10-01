"""
Feature: Scheduler — Deletes File Invalid Input Set
Description:
  Verify scheduler deletes a checksum file from ND_INPUT that no longer has
  a matching metadata file (an invalid/incomplete input set).

  Ported from nd_test_bot's TC_1228_SCHEDULER_DELETES_FILE_INVALID_INPUT_SET.
  The reference stops/restarts scheduler_manager via `systemctl`, which FE
  doesn't use (FE manages services via supervisorctl). Uses
  device.stop_service (supervisorctl stop) rather than grabbing the PID
  via `pidof` and sending it SIGTERM directly -- confirmed on-device that
  `kill -15` on the PID left the service RUNNING (supervisor's own
  autorestart wins the race), while `supervisorctl stop` reliably reports
  it stopped, since supervisor itself owns the running/stopped state.

  Path /home/iriscli/ND_INPUT and the log string "Deleting files as there
  is not matching pair (metadata, checksum)" (UNVERIFIED -- ported from
  reference, not yet confirmed on FE) need a live check before this test is
  trusted.
"""

import time


def test_step1_stop_scheduler_manager(device):
    """STEP_1 — Stop scheduler_manager service."""
    result = device.stop_service("scheduler_manager")
    assert result["status"] == "Pass", f"Failed to stop scheduler_manager service: {result['details']}"


def test_step2_wait(device):
    """STEP_2 — Wait 60s."""
    time.sleep(60)


def test_step3_delete_metadata_file(device):
    """STEP_3 — Delete the *metadata.txt file from ND_INPUT."""
    output = device.run("rm /home/iriscli/ND_INPUT/*metadata.txt && echo DELETED")
    assert output and "DELETED" in output, f"Failed to delete metadata.txt file: {output}"


def test_step4_restart_scheduler_manager(device):
    """STEP_4 — Restart scheduler_manager service."""
    result = device.restart_service("scheduler_manager")
    assert result["status"] == "Pass", f"Failed to start scheduler_manager service: {result['details']}"


def test_step5_wait(device):
    """STEP_5 — Wait 10s."""
    time.sleep(10)


def test_step6_verify_invalid_input_set_deleted(device):
    """STEP_6 — Verify scheduler logs deleting the file for a non-matching (metadata, checksum) pair."""
    output = device.search_log("/home/ubuntu/.nddevice/log/scheduler", "Deleting files as there is not matching pair (metadata, checksum)", timeout=30, interval=5)
    assert output, "Scheduler did not delete the file upon invalid input set from ND_INPUT"


def test_step7_restore_scheduler_manager(device):
    """PostCondition_1 — Restart scheduler_manager service to restore normal state."""
    result = device.restart_service("scheduler_manager")
    assert result["status"] == "Pass", f"Failed to restart scheduler_manager service: {result['details']}"
