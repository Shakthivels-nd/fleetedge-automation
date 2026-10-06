"""
Feature: Scheduler — Latency Check (In Case Of Alert)
Description:
  Verify scheduler_manager completes its process from scheduler start to
  uploader shutdown within 1.5 minutes (alert path).

  Ported from nd_test_bot's TC_1334_SCHEDULER_LATENCY_CHECK_INCASE_ALERT.
  Session-name capture uses the same live-tail-before-alert mechanism as
  TC_1304/TC_1323 (matches the reference's own step order: capture session
  BEFORE push_alert). session_name is captured but, same as the reference,
  never consumed by the later checks -- kept for parity/debug visibility.

  push_alert uses gen_ualert.sh (FE's real alert-trigger mechanism, no DTA
  agent on FE devices) instead of the reference's SendMsgServer-based
  push_alert.

  Log strings "Wrapper_scheduler Starting", "Wrapper_scheduler with time",
  "Shutting down Uploader Engine" (UNVERIFIED -- ported from reference, not
  yet confirmed on FE) need a live check before this test is trusted.
"""

import calendar
import re
import time


def test_step1_wait_before_start(device):
    """PreCondition_1 — Wait 10s."""
    time.sleep(10)


def test_step2_verify_bagheera_active(device):
    """PreCondition_2 — Verify bagheera service is RUNNING."""
    result = device.is_service_active("bagheera")
    assert result["status"] == "Pass", f"bagheera is not RUNNING: {result['state']}"


def test_step3_capture_session_name(device):
    """STEP_1 — Capture the current session name (before pushing the alert)."""
    cmd = (
        "( timeout 170 tail -F /home/ubuntu/.nddevice/log/ndcentral/* 2>/dev/null | "
        "grep --line-buffered -m 1 'creating folder for session' | "
        "awk -F'creating folder for session ' '{print $2}' | awk '{print $1}' ) 2>/dev/null"
    )
    output = device.run(cmd, timeout=180)
    session_name = (output or "").strip()
    assert session_name, f"Session name not found: {output!r}"
    device.variables["session_name"] = session_name


def test_step4_wait_before_alert(device):
    """STEP_2 — Wait 10s before pushing the alert."""
    time.sleep(10)


def test_step5_push_alert(device):
    """STEP_3 — Push alert to device."""
    # Device-clock epoch (s) just before the alert; scheduler_manager lines carry no timestamp
    # of their own, so step 7 compares the date inside "Wrapper_scheduler with time = ..." to it.
    now_out = device.run("date -u +%s") or ""
    match = re.search(r"\b\d{10}\b", now_out)
    assert match, f"Could not read device time: {now_out!r}"
    device.variables["alert_start_epoch"] = int(match.group(0))
    output = device.run("./gen_ualert.sh", "/home/ubuntu/.nddevice/latest/service/bagheera")
    assert device.user_alert_generated(output), f"Failed to generate user alert: {output}"


def test_step6_wait(device):
    """STEP_3_1 — Wait 50s."""
    time.sleep(50)


def test_step7_verify_scheduler_starts(device):
    """STEP_4 — Verify scheduler_manager logs Wrapper_scheduler starting (after the alert was pushed)."""
    # Log shape (no per-line timestamp), one pair per minute:
    #   ::====================::Wrapper_scheduler Starting::====================::
    #   Wrapper_scheduler with time = Tue Oct  6 08:51:23 GMT 2026
    # so take the latest "Starting" + following "with time" pair and compare that date to the alert.
    alert_epoch = device.variables.get("alert_start_epoch")
    assert alert_epoch, "alert_start_epoch was not captured in the push-alert step"
    end = time.time() + 90
    started_at = None
    while time.time() < end:
        output = device.run("grep -h -A1 'Wrapper_scheduler Starting' /home/ubuntu/.nddevice/log/scheduler_manager/* | tail -n 4") or ""
        times = re.findall(r"Wrapper_scheduler with time = \w+ (\w+)\s+(\d+) (\d{2}:\d{2}:\d{2}) GMT (\d{4})", output)
        if times:
            mon, day, hms, year = times[-1]
            started_at = calendar.timegm(time.strptime(f"{year} {mon} {day} {hms}", "%Y %b %d %H:%M:%S"))
            if started_at >= alert_epoch:
                return
        time.sleep(10)
    assert False, f"Scheduler manager does not start its process after the alert (alert epoch {alert_epoch}, latest start epoch {started_at})"


def test_step8_get_scheduler_start_time(device):
    """STEP_5 — Extract the wrapper_scheduler start time from scheduler_manager logs."""
    output = device.run("grep 'Wrapper_scheduler with time' /home/ubuntu/.nddevice/log/scheduler_manager/* | awk -F ' ' '{print $8}' | tail -n 1")
    scheduler_start_time = (output or "").strip()
    assert scheduler_start_time, "Wrapper_scheduler start time not found"
    device.variables["scheduler_start_time"] = scheduler_start_time


def test_step9_wait(device):
    """STEP_6 — Wait 50s."""
    time.sleep(50)


def test_step10_get_uploader_shutdown_time(device):
    """STEP_7 — Extract the Uploader Engine shutdown time from uploader logs."""
    output = device.run("grep 'Shutting down Uploader Engine' /home/ubuntu/.nddevice/log/uploader/uploader.log | awk -F ' ' '{print substr($2, 1, 8)}' | tail -n 1")
    uploader_shutdown_time = (output or "").strip()
    assert uploader_shutdown_time, "Uploader Engine does not shut down"
    device.variables["uploader_shutdown_time"] = uploader_shutdown_time


def test_step11_verify_latency_within_expected(device):
    """STEP_8 — Verify scheduler-to-uploader latency is within 1.5 minutes."""
    scheduler_start_time = device.variables.get("scheduler_start_time")
    uploader_shutdown_time = device.variables.get("uploader_shutdown_time")
    result = device.compare_time_difference_hms(scheduler_start_time, 1.5, uploader_shutdown_time)
    assert result["status"] == "Pass", (
        f"Scheduler manager does not complete its process from scheduler to uploader within expected time: {result['details']}"
    )
