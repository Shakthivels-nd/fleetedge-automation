"""
Feature: Scheduler — No Traceback
Description:
  Verify no tracebacks appear in the scheduler or scheduler_manager logs.

  Ported from nd_test_bot's TC_1411_SCHEDULER_NO_TRACEBACK. Note the
  reference's grep pattern is lowercase "traceback" (case-sensitive) --
  kept exactly as written.
"""


def test_step1_verify_no_traceback_in_scheduler(device):
    """STEP_1 — Verify no traceback in scheduler logs."""
    output = device.run('bash -c \'if grep -q "traceback" /home/ubuntu/.nddevice/log/scheduler/*.log; then echo true; else echo false; fi\'')
    assert (output or "").strip() == "false", "Tracebacks found in the scheduler logs"


def test_step2_verify_no_traceback_in_scheduler_manager(device):
    """STEP_2 — Verify no traceback in scheduler_manager logs."""
    output = device.run('bash -c \'if grep -q "traceback" /home/ubuntu/.nddevice/log/scheduler_manager/*.log; then echo true; else echo false; fi\'')
    assert (output or "").strip() == "false", "Tracebacks found in the scheduler_manager logs"
