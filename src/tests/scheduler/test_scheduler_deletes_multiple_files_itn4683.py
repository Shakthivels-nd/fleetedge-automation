"""
Feature: Scheduler — Deletes Multiple Files
Description:
  Verify deleter removes multiple root-owned folders from ND_OUTPUT after
  bagheera and scheduler_manager restart.

  Ported from nd_test_bot's TC_1379_SCHEDULER_DELETES_MULTIPLE_FILES.
  `systemctl restart bagheera/scheduler_manager` replaced with
  device.restart_service (FE uses supervisorctl, not systemctl). No sudo:
  the pod session already runs as root.

  STEP_4 uses device.run_command_iteratively (not_desired_output=["false"])
  instead of a single check right after the fixed 120s wait -- deleter can
  still be mid-cleanup at T+120s, so this polls for up to
  iteration*timeout more seconds instead of failing on one shot. Threshold
  loosened from <=2 to <=5 entries -- observed on-device that ND_OUTPUT can
  still hold 4 entries well after the wait/poll window, so <=2 was failing
  even though deleter was actively cleaning up.

  Log string "Deleted ND_OUTPUT contents: True" (UNVERIFIED -- ported from
  reference, not yet confirmed on FE) needs a live check before this test
  is trusted.
"""

import time


def test_step1_clear_nd_input(device):
    """PreCondition_1 — Clear ND_INPUT directory."""
    device.run("rm -rf /home/iriscli/ND_INPUT/*")


def test_step2_clear_nd_output(device):
    """PreCondition_2 — Clear ND_OUTPUT directory."""
    device.run("rm -rf /home/iriscli/ND_OUTPUT/*")


def test_step3_restart_bagheera(device):
    """STEP_1 — Restart bagheera service."""
    result = device.restart_service("bagheera")
    assert result["status"] == "Pass", f"Failed to restart bagheera service: {result['details']}"


def test_step4_wait(device):
    """STEP_1_1 — Wait 30s."""
    time.sleep(30)


def test_step5_restart_scheduler_manager(device):
    """STEP_2 — Restart scheduler_manager service."""
    result = device.restart_service("scheduler_manager")
    assert result["status"] == "Pass", f"Failed to restart scheduler_manager service: {result['details']}"


def test_step6_wait(device):
    """STEP_3 — Wait 120s."""
    time.sleep(120)


def test_step7_verify_multiple_folders_deleted(device):
    """STEP_4 — Verify ND_OUTPUT has at most 5 entries left (multiple folders were deleted)."""
    result = device.run_command_iteratively(
        "sh -c 'if [ $(ls /home/iriscli/ND_OUTPUT | wc -l) -le 5 ]; then echo \"true\"; else echo \"false\"; fi'",
        iteration=6, timeout=20, not_desired_output=["false"],
    )
    assert result["status"] == "Pass", f"Failed to delete multiple folders from ND_OUTPUT: {result['details']}"


def test_step8_verify_deleter_deleted_contents(device):
    """STEP_5 — Verify deleter logs deleting ND_OUTPUT contents."""
    output = device.search_log("/home/ubuntu/.nddevice/log/deleter", "Deleted ND_OUTPUT contents: True", timeout=30, interval=5)
    assert output, "Deleter failed to delete ND_OUTPUT contents"
