"""
Feature: Scheduler — wrapper_cleanupstate In Root Crontab
Description:
  Verify wrapper_cleanupstate is present in the root crontab.

  Ported from nd_test_bot's TC_1359_SCHEDULER_WRAPPER_ CLEANUPSTATE.py
  (note the stray space before CLEANUPSTATE in the reference's own
  filename). No sudo: the pod session already runs as root.
"""


def test_step1_verify_wrapper_cleanupstate_in_crontab(device):
    """STEP_1 — Verify wrapper_cleanupstate is present in the root crontab."""
    output = device.run("crontab -l | grep '/home/ubuntu/bin/wrapper_cleanupstate'")
    assert output, "Failed to find wrapper_cleanupstate in Root Crontab"
