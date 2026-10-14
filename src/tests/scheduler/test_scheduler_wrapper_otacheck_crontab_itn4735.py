"""
Feature: Scheduler — wrapper_otacheck In Root Crontab
Description:
  Verify wrapper_otacheck is present in the root crontab.

  Ported from nd_test_bot's TC_1358_SCHEDULER_WRAPPER_OTACHECK_ CRONTAB.py
  (note the stray space before CRONTAB in the reference's own filename).
  No sudo: the pod session already runs as root.
"""


def test_step1_verify_wrapper_otacheck_in_crontab(device):
    """STEP_1 — Verify wrapper_otacheck is present in the root crontab."""
    output = device.run("crontab -l | grep '/home/ubuntu/bin/wrapper_otacheck'")
    assert output, "Failed to find wrapper_otacheck in Root Crontab"
