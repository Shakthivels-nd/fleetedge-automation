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
    output = device.search_log("/home/ubuntu/.nddevice/log/ndcentral", "Trigger scheduler manager sent", timeout=80, interval=10)
    assert output, "Trigger scheduler manager not sent"
