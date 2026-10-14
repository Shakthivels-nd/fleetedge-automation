"""
Feature: Scheduler — wrapper_scheduler Removed From User Crontab
Description:
  Verify wrapper_scheduler is NOT present in the (non-root) user's crontab
  (it belongs in the root crontab, not the user one).

  Ported from nd_test_bot's TC_1365_SCHEDULER_WRAPPER_SCHEDULER_ REMOVED_FROM_USER_CRONTAB.py
  (note the stray space in the reference's own filename).
"""


def test_step1_verify_wrapper_scheduler_removed_from_user_crontab(device):
    """STEP_1 — Verify wrapper_scheduler is absent from the user crontab."""
    output = device.run('echo "$(crontab -l | grep -q "wrapper_scheduler" && echo false || echo true)"')
    assert (output or "").strip() == "true", "Failed to Remove wrapper_scheduler from User Crontab"
