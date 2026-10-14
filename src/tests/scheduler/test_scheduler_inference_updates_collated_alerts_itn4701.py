"""
Feature: Scheduler — Inference Updates Collated Alerts
Description:
  Verify inference writes alerts to alerts.json and updates
  collated_alerts_data after an alert is pushed.

  Ported from nd_test_bot's TC_1323_SCHEDULER_INFERENCE_UPDATES_COLLATED_ALERTS.
  Session-name capture uses the same live-tail-before-alert mechanism as
  TC_1304 (matches the reference's own step order: capture session BEFORE
  push_alert). push_alert uses gen_ualert.sh (FE's real alert-trigger
  mechanism, no DTA agent on FE devices) instead of the reference's
  SendMsgServer-based push_alert. session_name is captured but (same as the
  reference) never consumed by the later log check -- kept for parity/debug
  visibility.

  Log strings "Writing alerts .* to /home/iriscli/ND_OUTPUT" (regex) and
  "Successfully updated collated_alerts_data" (UNVERIFIED -- ported from
  reference, not yet confirmed on FE) need a live check before this test is
  trusted.
"""

import time
import re


def test_step1_restart_bagheera(device):
    """PreCondition_1 — Restart bagheera service."""
    result = device.restart_service("bagheera")
    assert result["status"] == "Pass", f"Failed to restart bagheera service: {result['details']}"


def test_step2_verify_bagheera_active(device):
    """PreCondition_2 — Verify bagheera service is RUNNING."""
    device.variables["session_start_ts"] = int(time.time()) * 1000
    result = device.is_service_active("bagheera")
    assert result["status"] == "Pass", f"bagheera is not RUNNING: {result['state']}"


def test_step3_wait_before_alert(device):
    """STEP_3 — Wait 10s before pushing the alert."""
    time.sleep(10)

def test_step4_push_alert(device):
    """STEP_4 — Push alert to device."""
    # Device-clock (UTC) time just before the alert, used to ignore stale inference log lines.
    now_out = device.run("date -u '+%Y-%m-%d %H:%M:%S'") or ""
    match = re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", now_out)
    assert match, f"Could not read device time: {now_out!r}"
    device.variables["alert_start_utc"] = match.group(0)
    output = device.run("./gen_ualert.sh", "/home/ubuntu/.nddevice/latest/service/bagheera")
    assert device.user_alert_generated(output), f"Failed to generate user alert: {output}"

def test_step5_wait(device):
    """STEP_5 — Wait 50s."""
    time.sleep(50)


def test_step6_verify_alerts_written_and_collated(device):
    """STEP_6 — Verify inference logs writing alerts.json and updating collated_alerts_data."""
    # Grep all inference logs (incl. rotated ones) oldest -> newest by mtime, keep lines stamped
    # at/after the alert (lines start with "YYYY-MM-DD HH:MM:SS", UTC, so a string compare
    # works), and take the latest (tail -1). Messages are basic regexes.
    alert_start_utc = device.variables.get("alert_start_utc")
    assert alert_start_utc, "alert_start_utc was not captured in the push-alert step"
    logs = "$(ls -tr /home/ubuntu/.nddevice/log/inference/* 2>/dev/null)"
    for message in [
        "Writing alerts .* to /home/iriscli/ND_OUTPUT",
        "Successfully updated collated_alerts_data",
    ]:
        result = device.run_command_iteratively(
            f"grep -h '{message}' {logs} 2>/dev/null | "
            f"awk -v ts='{alert_start_utc}' 'substr($0,1,19) >= ts' | tail -1",
            iteration=12, timeout=10, not_desired_output=[""],
        )
        assert result["status"] == "Pass", f"'{message}' not found in inference logs after {alert_start_utc}: {result['details']}"
