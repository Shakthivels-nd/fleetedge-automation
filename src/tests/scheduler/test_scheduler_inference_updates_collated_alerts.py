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


def test_step1_verify_bagheera_active(device):
    """PreCondition_4 — Verify bagheera service is RUNNING."""
    result = device.is_service_active("bagheera")
    assert result["status"] == "Pass", f"bagheera is not RUNNING: {result['state']}"


def test_step2_capture_session_name(device):
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


def test_step3_push_alert(device):
    """STEP_3 — Push alert to device."""
    output = device.run("./gen_ualert.sh", "/home/ubuntu/.nddevice/latest/service/bagheera")
    assert device.user_alert_generated(output), f"Failed to generate user alert: {output}"


def test_step4_wait(device):
    """STEP_4 — Wait 50s."""
    time.sleep(50)


def test_step5_verify_alerts_written_and_collated(device):
    """STEP_5 — Verify inference logs writing alerts.json and updating collated_alerts_data."""
    for message in [
        "Writing alerts .* to /home/iriscli/ND_OUTPUT",
        "Successfully updated collated_alerts_data",
    ]:
        output = device.search_log("/home/ubuntu/.nddevice/log/inference", message, timeout=60, interval=10)
        assert output, f"'{message}' not found in inference logs"
