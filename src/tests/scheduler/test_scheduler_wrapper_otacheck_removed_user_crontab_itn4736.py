"""
Feature: Scheduler — wrapper_otacheck Removed From User Crontab
Description:
  Verify wrapper_otacheck is NOT present in the (non-root) user's crontab.

  Ported from nd_test_bot's TC_1368_SCHEDULER_WRAPPER_OTACHECK_REMOVED_USER_CRONTAB.
  The reference's STEP_1 device-type gate only runs STEP_2 for non-krait
  (bagheera-type) devices, exiting early otherwise -- dropped the gate
  entirely since FE devices are always bagheera-type.
"""


def test_step1_verify_wrapper_otacheck_removed_from_user_crontab(device):
    """STEP_2 — Verify wrapper_otacheck is absent from the user crontab."""
    output = device.run('echo "$(crontab -l | grep -q "wrapper_otacheck" && echo false || echo true)"')
    assert (output or "").strip() == "true", "Failed to Remove wrapper_otacheck from User Crontab"
