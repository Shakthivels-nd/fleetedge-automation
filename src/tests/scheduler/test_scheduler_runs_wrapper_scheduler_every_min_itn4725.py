"""
Feature: Scheduler — Runs wrapper_scheduler Every Minute
Description:
  Verify scheduler_manager calls wrapper_scheduler once per minute, by
  comparing the last two "Wrapper_scheduler with time=" log timestamps.

  Ported from nd_test_bot's TC_1156_SCHEDULER_RUNS_WRAPPER_SCHEDULER_EVERY_MIN.
  The reference's FileUtils_obj.scheduler_call_check has no FE equivalent
  method -- ported its exact grep/awk/cut extraction pipeline inline via
  device.run() rather than adding a new device_test.py method, since the
  logic (handle the ":59 -> :00" minute-rollover edge case) is specific to
  this one check and not reusable elsewhere.

  Log string "Wrapper_scheduler with time" (UNVERIFIED -- ported from
  reference, not yet confirmed on FE) needs a live grep pass before this
  test is trusted.
"""

import time


def test_step1_verify_scheduler_manager_active(device):
    """PreCondition_1 — Verify scheduler_manager service is RUNNING."""
    result = device.is_service_active("scheduler_manager")
    assert result["status"] == "Pass", f"scheduler_manager is not RUNNING: {result['state']}"


def test_step2_wait(device):
    """STEP_1 — Wait 60s so at least two wrapper_scheduler calls are logged."""
    time.sleep(60)


def test_step3_verify_wrapper_scheduler_runs_every_minute(device):
    """STEP_2 — Verify consecutive wrapper_scheduler log timestamps are exactly 1 minute apart."""
    cmd = (
        'grep "Wrapper_scheduler with time" /home/ubuntu/.nddevice/log/scheduler_manager/log_*.log | '
        "awk -F'=' '{print $2}' | "
        "awk '{print $4}' | "
        "cut -d':' -f2"
    )
    output = device.run(cmd)
    assert output, "Failed to retrieve scheduler timestamps from logs"
    timestamps = output.strip().splitlines()
    assert len(timestamps) >= 2, f"Not enough wrapper_scheduler timestamps to compare: {timestamps}"

    # Minute-rollover edge case: if the second-to-last entry is minute 59,
    # compare it against the one before it instead of the last entry, since
    # 59 -> 00 would otherwise look like a -59 minute jump.
    if int(timestamps[-2]) == 59:
        current_time = int(timestamps[-2])
        previous_time = int(timestamps[-3])
    else:
        current_time = int(timestamps[-1])
        previous_time = int(timestamps[-2])

    assert current_time - previous_time == 1, (
        f"Scheduler does not run wrapper_scheduler every one minute "
        f"(previous={previous_time}, current={current_time})"
    )
