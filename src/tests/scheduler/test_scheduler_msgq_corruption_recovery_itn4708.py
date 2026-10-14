"""
Feature: Scheduler — Message Queue Corruption Recovery
Description:
  Verify the device recovers after the SCH message queue is corrupted.

  Ported from nd_test_bot's TC_1357_SCHEDULER_MSGQ_CURRUPTION_RECOVERY.
  STEP_4 (DeviceController_obj.reboot_device) is replaced with a
  scheduler_manager restart -- FE has no device-level reboot method. Unlike a
  reboot (which clears /dev/shm entirely), a restart only recovers the queue
  if scheduler_manager recreates /dev/shm/MSGQ/SCH on startup (UNVERIFIED --
  needs a live check before this test is trusted).
"""

import time

_SCH_QUEUE = "/dev/shm/MSGQ/SCH"


def test_step1_corrupt_sch_message_queue(device):
    """STEP_1 — Corrupt the SCH message queue."""
    output = device.run(f"bash -c 'echo \"corrupting data\" > {_SCH_QUEUE}'")
    assert not output, f"Failed to corrupt the SCH message queue: {output}"


def test_step2_verify_queue_corrupted(device):
    """STEP_2 — Verify the corrupted data is present in the SCH message queue."""
    corrupted_data = device.run(f"bash -c 'cat {_SCH_QUEUE}'") or ""
    assert "corrupting" in corrupted_data, f"Failed to find corrupted data in SCH message queue: {corrupted_data!r}"


def test_step3_wait(device):
    """STEP_3 — Wait 10s."""
    time.sleep(10)


def test_step4_restart_scheduler_manager(device):
    """STEP_4 — Restart scheduler_manager service (in place of the reference's device reboot)."""
    result = device.restart_service("scheduler_manager")
    assert result["status"] == "Pass", f"Failed to restart scheduler_manager: {result['details']}"


def test_step5_wait(device):
    """STEP_5 — Wait 15s."""
    time.sleep(15)


def test_step6_verify_queue_recovered(device):
    """STEP_6 — Verify the device recovered from the corrupted SCH message queue."""
    # The trailing echo puts an explicit RECOVERED / NOT RECOVERED verdict in the command log
    # (the queue is empty after recovery, so a bare `cat` would log no output at all).
    recovered_data = device.run(
        f"bash -c 'cat {_SCH_QUEUE}; grep -q corrupting {_SCH_QUEUE} && echo \"NOT RECOVERED\" || echo \"RECOVERED\"'"
    ) or ""
    assert "corrupting" not in recovered_data, f"Device did not recover from corrupted SCH message queue: {recovered_data!r}"
