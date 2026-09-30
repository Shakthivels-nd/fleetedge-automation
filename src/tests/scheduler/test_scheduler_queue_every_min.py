"""
Feature: Scheduler — Queue Overflow Checked Every Minute
Description:
  Verify the scheduler checks the queue-overflow scenario roughly once per
  minute.

  Ported from nd_test_bot's TC_1452_SCHEDULER_QUEUE_EVERY_MIN. Uses
  device.compare_time_difference_hms (existing FE method, same name/
  signature as the reference's Calculator_obj method).

  Log string "Entering:::manage_queue" (UNVERIFIED -- ported from
  reference, not yet confirmed on FE) needs a live check before this test
  is trusted.
"""

import time


def test_step1_wait(device):
    """PreCondition_1 — Wait 15s."""
    time.sleep(15)


def test_step2_get_first_queue_check_time(device):
    """STEP_1 — Get the second-to-last queue-check timestamp."""
    output = device.run("grep -inr 'Entering:::manage_queue' /home/ubuntu/.nddevice/log/scheduler/ | awk '{print $2}' | tail -n 2 | head -n 1")
    queue_time_first = (output or "").strip()
    assert queue_time_first, "Queue overflow scenario is not checked"
    device.variables["queue_time_first"] = queue_time_first


def test_step3_get_second_queue_check_time(device):
    """STEP_2 — Get the last queue-check timestamp."""
    output = device.run("grep -inr 'Entering:::manage_queue' /home/ubuntu/.nddevice/log/scheduler/ | awk '{print $2}' | tail -n 1")
    queue_time_second = (output or "").strip()
    assert queue_time_second, "Queue overflow scenario is not checked"
    device.variables["queue_time_second"] = queue_time_second


def test_step4_verify_checked_once_per_minute(device):
    """STEP_3 — Verify the two queue-check timestamps are ~1 minute apart."""
    queue_time_first = device.variables.get("queue_time_first")
    queue_time_second = device.variables.get("queue_time_second")
    result = device.compare_time_difference_hms(queue_time_first, 1.7, queue_time_second)
    assert result["status"] == "Pass", f"Queue overflow scenario is not checked once for every min: {result['details']}"
