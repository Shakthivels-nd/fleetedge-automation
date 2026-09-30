"""
Feature: Scheduler — ndcentral Fails To Trigger Scheduler
Description:
  Verify ndcentral logs a send_msg failure when scheduler_manager's message
  queue is removed out from under it (simulating a broken IPC channel).

  Ported from nd_test_bot's
  TC_1244_SCHEDULER_NDCENTRAL_FAILS_TO_TRIGGER_SCHEDULER. Stops
  scheduler_manager via device.stop_service (supervisorctl stop) --
  confirmed on-device that `kill -15` on the PID from `pidof` left the
  service RUNNING (supervisor's own autorestart wins the race), while
  `supervisorctl stop` reliably reports it stopped.

  Log strings "Message queue server created SCH" and "send_msg failed"
  (UNVERIFIED -- ported from reference, not yet confirmed on FE) need a
  live check before this test is trusted.
"""

import time


def test_step1_restart_scheduler_manager(device):
    """STEP_1 — Restart scheduler_manager service."""
    result = device.restart_service("scheduler_manager")
    assert result["status"] == "Pass", f"Failed to restart scheduler_manager service: {result['details']}"


def test_step2_wait(device):
    """STEP_2_1 — Wait 30s."""
    time.sleep(30)


def test_step3_capture_msgq_id(device):
    """STEP_3 — Capture scheduler_manager's message queue id from its logs."""
    output = device.run(
        "grep -inr 'Message queue server created SCH' /home/ubuntu/.nddevice/log/scheduler_manager/* | "
        "awk -F'SCH ' '{print $2}' | awk '{print $1}' | tail -n 1"
    )
    msgq_id = (output or "").strip()
    assert msgq_id, "Failed to get message queue id"
    device.variables["msgq_id"] = msgq_id


def test_step4_stop_scheduler_manager(device):
    """STEP_4 — Stop scheduler_manager service."""
    result = device.stop_service("scheduler_manager")
    assert result["status"] == "Pass", f"Failed to stop scheduler_manager service: {result['details']}"


def test_step4_1_wait(device):
    """STEP_4_1 — Wait 10s."""
    time.sleep(10)


def test_step5_remove_msgq(device):
    """STEP_5/STEP_6 — Remove scheduler_manager's message queue via ipcrm."""
    msgq_id = device.variables.get("msgq_id")
    assert msgq_id, "msgq_id was not captured in STEP_3"
    output = device.run(f"ipcrm -q {msgq_id} && echo REMOVED")
    assert output and "REMOVED" in output, f"msgq_id not found: {output}"


def test_step5_1_wait(device):
    """STEP_6_1 — Wait 10s."""
    time.sleep(10)


def test_step6_restart_bagheera(device):
    """STEP_6_2 — Restart bagheera service."""
    result = device.restart_service("bagheera")
    assert result["status"] == "Pass", f"Failed to restart bagheera service: {result['details']}"


def test_step7_verify_send_msg_failed(device):
    """STEP_7 — Verify ndcentral logs a send_msg failure."""
    output = device.search_log("/home/ubuntu/.nddevice/log/ndcentral", "send_msg failed", timeout=300, interval=40)
    assert output, "send_msg failed not found"


def test_step8_restore_scheduler_manager(device):
    """PostCondition_1 — Restart scheduler_manager service to restore normal state."""
    result = device.restart_service("scheduler_manager")
    assert result["status"] == "Pass", f"Failed to restart scheduler_manager service: {result['details']}"
