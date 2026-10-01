"""
Feature: Scheduler — Latency Check (Without Alert)
Description:
  Verify scheduler_manager completes its process from scheduler start to
  deleter shutdown within one minute (no-alert path).

  Ported from nd_test_bot's TC_1332_SCHEDULER_LATENCY_CHECK_WITHOUT_ALERT.
  Uses device.compare_time_difference_hms (already an existing FE method,
  same name/signature as the reference's Calculator_obj method) to compare
  the two extracted HH:MM:SS timestamps.

  Log strings "Wrapper_scheduler Starting", "Wrapper_scheduler with time",
  "Starting Delete Engine", "Shutting down Delete Engine" (UNVERIFIED --
  ported from reference, not yet confirmed on FE) need a live check before
  this test is trusted.
"""


def test_step1_verify_scheduler_starts(device):
    """STEP_1 — Verify scheduler_manager logs Wrapper_scheduler starting."""
    output = device.search_log("/home/ubuntu/.nddevice/log/scheduler_manager", "Wrapper_scheduler Starting", timeout=60, interval=10)
    assert output, "Scheduler manager does not start its process"


def test_step2_get_scheduler_start_time(device):
    """STEP_2 — Extract the wrapper_scheduler start time from scheduler_manager logs."""
    output = device.run("grep 'Wrapper_scheduler with time' /home/ubuntu/.nddevice/log/scheduler_manager/* | awk -F ' ' '{print $8}' | tail -n 1")
    scheduler_start_time = (output or "").strip()
    assert scheduler_start_time, "Wrapper_scheduler start time not found"
    device.variables["scheduler_start_time"] = scheduler_start_time


def test_step3_verify_deleter_starts(device):
    """STEP_3 — Verify scheduler_manager logs starting the Delete Engine."""
    output = device.search_log("/home/ubuntu/.nddevice/log/scheduler_manager", "Starting Delete Engine", timeout=60, interval=10)
    assert output, "Delete Engine does not start its process"


def test_step4_get_deleter_shutdown_time(device):
    """STEP_4 — Extract the Delete Engine shutdown time from deleter logs."""
    output = device.run("grep 'Shutting down Delete Engine' /home/ubuntu/.nddevice/log/deleter/deleter.log | awk -F ' ' '{print substr($2, 1, 8)}' | tail -n 1")
    deleter_shutdown_time = (output or "").strip()
    assert deleter_shutdown_time, "Delete Engine does not shut down"
    device.variables["deleter_shutdown_time"] = deleter_shutdown_time


def test_step5_verify_latency_within_one_minute(device):
    """STEP_5 — Verify scheduler-to-deleter latency is within 1 minute."""
    scheduler_start_time = device.variables.get("scheduler_start_time")
    deleter_shutdown_time = device.variables.get("deleter_shutdown_time")
    result = device.compare_time_difference_hms(scheduler_start_time, 1, deleter_shutdown_time)
    assert result["status"] == "Pass", (
        f"Scheduler manager does not complete its process from scheduler to deleter within one minute: {result['details']}"
    )
