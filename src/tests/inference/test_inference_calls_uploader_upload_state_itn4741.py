"""
Feature: Scheduler — Inference Calls Uploader (Upload State)
Description:
  Verify inference starts the Uploader Engine when a file is moved to
  UPLOAD_STATE (alert case).

  Ported from nd_test_bot's TC_1304_SCHEDULER_INFERENCE_CALLS_UPLOADER_UPLOAD_STATE.
  Session-name capture uses device.get_current_session_name AFTER push_alert
  (the reference's own STEP_3_1 already captures via
  FileUtils_obj.get_current_session_name in this test, unlike TC_1302 which
  used get_new_session -- so no substitution needed here, this already
  matches the pattern used elsewhere in this repo).

  push_alert uses gen_ualert.sh (FE's real alert-trigger mechanism, no DTA
  agent on FE devices) instead of the reference's SendMsgServer-based
  push_alert.

  Reference STEP_5 (svc "button falling" log) and STEP_5_1 (ndcentral "User
  alert msg received" log) are intentionally NOT ported (they depend on the
  DTA push_alert path; FE uses gen_ualert.sh).

  Log strings (UNVERIFIED -- ported from reference, not yet confirmed on FE)
  need a live check before this test is trusted.
"""

import re
import time


def test_step1_restart_bagheera(device):
    """PreCondition_1 — Restart bagheera service."""
    result = device.restart_service("bagheera")
    assert result["status"] == "Pass", f"Failed to restart bagheera service: {result['details']}"


def test_step2_verify_bagheera_active(device):
    """PreCondition_2 — Verify bagheera service is RUNNING."""
    device.variables["session_start_ts"] = int(time.time()) * 1000
    result = device.is_service_active("bagheera")
    assert result["status"] == "Pass", f"bagheera is not RUNNING: {result['state']}"


def test_step3_capture_session_name(device):
    """STEP_1 — Capture the next session name ndcentral creates (before pushing the alert)."""
    start_ts = device.variables.get("session_start_ts")
    # Without a start timestamp search_log only accepts lines logged after the search begins.
    found = device.search_log(
        "/home/ubuntu/.nddevice/log/ndcentral", "creating folder for session",
        start_ts, timeout=60, interval=5,
    )
    assert found, "Session name not found: no 'creating folder for session' in ndcentral logs"
    names = re.findall(r"creating folder for session\s+(\S+)", found)
    assert names, f"Could not parse session name from: {found!r}"
    device.variables["session_name"] = names[0]


def test_step4_wait_before_alert(device):
    """STEP_2 — Wait 10s before pushing the alert."""
    time.sleep(10)


def test_step5_push_alert(device):
    """STEP_3 — Push alert to device."""
    # Device-clock (UTC) time just before the alert, used to ignore stale uploader log lines.
    now_out = device.run("date -u '+%Y-%m-%d %H:%M:%S'") or ""
    match = re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", now_out)
    assert match, f"Could not read device time: {now_out!r}"
    device.variables["alert_start_utc"] = match.group(0)
    output = device.run("./gen_ualert.sh", "/home/ubuntu/.nddevice/latest/service/bagheera")
    assert device.user_alert_generated(output), f"Failed to generate user alert: {output}"


def test_step6_get_current_session_name(device):
    """STEP_3_1 — Get the current session name after the alert (used for the inference log check)."""
    result = device.get_current_session_name()
    assert result["status"] == "Pass", f"Failed to get current session name: {result['details']}"
    device.variables["session_name_alert"] = result["session_name"]


def test_step7_wait(device):
    """STEP_4 — Wait 80s."""
    time.sleep(80)


def test_step8_verify_alert_identified_for_session(device):
    """STEP_6 — Verify inference identifies the alert for this session."""
    session_name_alert = device.variables.get("session_name_alert")
    assert session_name_alert, "session_name_alert was not captured in STEP_3_1"
    result = device.run_command_iteratively(
        f"grep -inr -E '0{session_name_alert}.*is_ib_alert True$' /home/ubuntu/.nddevice/log/inference",
        iteration=13, timeout=10, not_desired_output=[""],
    )
    assert result["status"] == "Pass", f"Alert not identified for session {session_name_alert!r}: {result['details']}"


def test_step9_verify_state_modified_to_upload_state(device):
    """STEP_7 — Verify inference logs modifying the file's state to UPLOAD_STATE and starting the Uploader Engine."""
    # device.search_log with no start timestamp only accepts lines logged AFTER the
    # search begins, so it misses lines written during the earlier waits. Grep the
    # logs directly (oldest -> newest by mtime, tail -1 = latest) instead.
    session_name_alert = device.variables.get("session_name_alert")
    assert session_name_alert, "session_name_alert was not captured in STEP_3_1"
    logs = "$(ls -tr /home/ubuntu/.nddevice/log/inference/* 2>/dev/null)"
    for message, session_filter in [
        ("STATE is modified to  state:UPLOAD_STATE", f" | grep -F '{session_name_alert}'"),
        ("Uploader Engine is not running. Starting Now", ""),
    ]:
        result = device.run_command_iteratively(
            f"grep -h '{message}' {logs} 2>/dev/null{session_filter} | tail -1",
            iteration=6, timeout=10, not_desired_output=[""],
        )
        assert result["status"] == "Pass", f"'{message}' not found in inference logs: {result['details']}"


def test_step10_verify_uploader_started(device):
    """STEP_8 — Verify uploader logs starting the Uploader Engine (after the alert was pushed)."""
    alert_start = device.variables.get("alert_start_utc")
    assert alert_start, "alert_start_utc was not captured in the push-alert step"
    # Files oldest -> newest by mtime; keep only lines stamped at/after the alert
    # (lines start with "YYYY-MM-DD HH:MM:SS", UTC, so a string compare works); tail -1 = latest.
    result = device.run_command_iteratively(
        "grep -h 'Starting Uploader Engine' $(ls -tr /home/ubuntu/.nddevice/log/uploader/* 2>/dev/null) 2>/dev/null | "
        f"awk -v ts='{alert_start}' 'substr($0,1,19) >= ts' | tail -1",
        iteration=6, timeout=10, not_desired_output=[""],
    )
    assert result["status"] == "Pass", f"Uploader Engine did not start after {alert_start}: {result['details']}"
