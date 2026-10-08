"""
Feature: Scheduler — ndcentral Triggers scheduler_manager
Description:
  Verify ndcentral sends a trigger to scheduler_manager at the end of a
  session.

  Ported from nd_test_bot's
  TC_1239_SCHEDULER_NDCENTRAL_TRIGGERS_SHEDULER_MANAGER. Restarts bagheera
  and scheduler_manager individually (FE's restart_service takes one
  service name at a time, unlike the reference's
  restart_service(["bagheera","scheduler_manager"]) list call).

  Log string "Trigger scheduler manager sent" (UNVERIFIED -- ported from
  reference, not yet confirmed on FE) needs a live check before this test
  is trusted.
"""


def test_step1_restart_bagheera(device):
    """STEP_1 — Restart bagheera service."""
    result = device.restart_service("bagheera")
    assert result["status"] == "Pass", f"Failed to restart bagheera service: {result['details']}"


def test_step1_1_restart_scheduler_manager(device):
    """STEP_1 (cont.) — Restart scheduler_manager service."""
    result = device.restart_service("scheduler_manager")
    assert result["status"] == "Pass", f"Failed to restart scheduler_manager service: {result['details']}"


def test_step2_verify_trigger_sent(device):
    """STEP_2 — Verify ndcentral logs sending the scheduler_manager trigger."""
    # ndcentral lines start with "<epoch-ms>: ...", so sort -n on that and tail -1 gives the latest occurrence.
    result = device.run_command_iteratively(
        "grep -h 'Trigger scheduler manager sent' /home/ubuntu/.nddevice/log/ndcentral/* 2>/dev/null | sort -n | tail -n 1",
        iteration=8, timeout=10, not_desired_output=[""],
    )
    assert result["status"] == "Pass", f"Trigger scheduler manager not sent: {result['details']}"
