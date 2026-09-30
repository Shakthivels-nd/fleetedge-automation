"""
Feature: Scheduler — scheduler_manager Triggers Scheduler
Description:
  Verify scheduler_manager starts the scheduler process when it detects
  scheduler is not already running.

  Ported from nd_test_bot's TC_1240_SCHEDULER_MANAGER_TRIGGERS_SCHEDULER.

  Log string "scheduler is not running. Starting Now" (UNVERIFIED -- ported
  from reference, not yet confirmed on FE) needs a live check before this
  test is trusted.
"""


def test_step1_verify_scheduler_manager_starts_scheduler(device):
    """STEP_1 — Verify scheduler_manager logs starting scheduler when it's not running."""
    output = device.search_log("/home/ubuntu/.nddevice/log/scheduler_manager", "scheduler is not running. Starting Now", timeout=80, interval=10)
    assert output, "Scheduler manager does not trigger scheduler"
