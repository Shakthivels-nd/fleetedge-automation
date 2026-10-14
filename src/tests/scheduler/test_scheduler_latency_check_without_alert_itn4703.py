"""
Feature: Scheduler — Latency Check (Without Alert)
Description:
  Verify scheduler_manager completes its process from scheduler start to
  deleter shutdown within one minute (no-alert path).

  Ported from nd_test_bot's TC_1332_SCHEDULER_LATENCY_CHECK_WITHOUT_ALERT.
  Uses device.compare_time_difference_hms (already an existing FE method,
  same name/signature as the reference's Calculator_obj method) to compare
  the two extracted HH:MM:SS timestamps.

  scheduler_manager log lines carry no timestamp of their own, e.g.
    ::====================::Wrapper_scheduler Starting::====================::
    Wrapper_scheduler with time = Tue Oct  6 08:51:23 GMT 2026
  so (same as the in-case-of-alert latency test) STEP_1 captures the device
  clock when the test starts and only accepts a "Wrapper_scheduler Starting"
  whose following "with time" date is at/after it. STEP_3 does the same for
  "Starting Delete Engine" / "Delete Engine with time = ...", accepting only a
  start at/after the scheduler start found in STEP_1 (60s, 10s interval).

  Log strings "Wrapper_scheduler Starting", "Wrapper_scheduler with time",
  "Starting Delete Engine", "Shutting down Delete Engine" (UNVERIFIED --
  ported from reference, not yet confirmed on FE) need a live check before
  this test is trusted.
"""

import calendar
import re
import time


_LOG_DIR = "/home/ubuntu/.nddevice/log/scheduler_manager"


def _latest_start_epoch(device, start_marker, time_label):
    """Epoch (s, UTC) of the latest "<start_marker>" entry, read from the "<time_label> with time = <date>"
    line that follows it (these logs carry no per-line timestamp), or None if there is none."""
    output = device.run(f"grep -h -A1 '{start_marker}' {_LOG_DIR}/* | tail -n 4") or ""
    times = re.findall(rf"{time_label} with time = \w+ (\w+)\s+(\d+) (\d{{2}}:\d{{2}}:\d{{2}}) GMT (\d{{4}})", output)
    if not times:
        return None
    mon, day, hms, year = times[-1]
    return calendar.timegm(time.strptime(f"{year} {mon} {day} {hms}", "%Y %b %d %H:%M:%S"))


def test_step1_verify_scheduler_starts(device):
    """STEP_1 — Verify scheduler_manager logs Wrapper_scheduler starting (after this test began)."""
    now_out = device.run("date -u +%s") or ""
    match = re.search(r"\b\d{10}\b", now_out)
    assert match, f"Could not read device time: {now_out!r}"
    test_start_epoch = int(match.group(0))
    device.variables["test_start_epoch"] = test_start_epoch
    end = time.time() + 90
    started_at = None
    while time.time() < end:
        started_at = _latest_start_epoch(device, "Wrapper_scheduler Starting", "Wrapper_scheduler")
        if started_at is not None and started_at >= test_start_epoch:
            device.variables["scheduler_started_epoch"] = started_at
            return
        time.sleep(10)
    assert False, f"Scheduler manager does not start its process (test start epoch {test_start_epoch}, latest start epoch {started_at})"


def test_step2_get_scheduler_start_time(device):
    """STEP_2 — Extract the wrapper_scheduler start time from scheduler_manager logs."""
    output = device.run("grep 'Wrapper_scheduler with time' /home/ubuntu/.nddevice/log/scheduler_manager/* | awk -F ' ' '{print $8}' | tail -n 1")
    scheduler_start_time = (output or "").strip()
    assert scheduler_start_time, "Wrapper_scheduler start time not found"
    device.variables["scheduler_start_time"] = scheduler_start_time


def test_step3_verify_deleter_starts(device):
    """STEP_3 — Verify scheduler_manager logs starting the Delete Engine (after the scheduler started)."""
    # Log shape (no per-line timestamp):
    #   ::====================::Starting Delete Engine ::====================::
    #   Delete Engine with time = Tue Oct  6 09:08:48 GMT 2026
    scheduler_started = device.variables.get("scheduler_started_epoch")
    assert scheduler_started, "scheduler_started_epoch was not captured in STEP_1"
    end = time.time() + 60
    started_at = None
    while time.time() < end:
        started_at = _latest_start_epoch(device, "Starting Delete Engine", "Delete Engine")
        if started_at is not None and started_at >= scheduler_started:
            return
        time.sleep(10)
    assert False, f"Delete Engine does not start its process (scheduler start epoch {scheduler_started}, latest Delete Engine start epoch {started_at})"


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
