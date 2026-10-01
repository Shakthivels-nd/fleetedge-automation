"""
Feature: Scheduler — No AttributeError
Description:
  Verify no "AttributeError" appears in the scheduler or scheduler_manager
  logs (e.g. the reference's specific known failure mode:
  AttributeError: 'NoneType' object has no attribute 'send').

  Ported from nd_test_bot's TC_1454_SCHEDULER_NO_ATTRIBUTE_ERROR.
"""


def test_step1_verify_no_attribute_error_in_scheduler(device):
    """STEP_1 — Verify no AttributeError in scheduler logs."""
    output = device.run("grep -inr 'AttributeError' /home/ubuntu/.nddevice/log/scheduler && echo True || echo False")
    assert (output or "").strip() == "False", "AttributeError found in the scheduler logs"


def test_step2_verify_no_attribute_error_in_scheduler_manager(device):
    """STEP_2 — Verify no AttributeError in scheduler_manager logs."""
    output = device.run("grep -inr 'AttributeError' /home/ubuntu/.nddevice/log/scheduler_manager && echo True || echo False")
    assert (output or "").strip() == "False", "AttributeError found in the scheduler_manager logs"
