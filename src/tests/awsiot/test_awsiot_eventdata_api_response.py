"""
Feature: AWSIOT — Eventdata API Response
Description:
  Verify AWSIOT Event Data API Response.
"""

import time


def test_step1_check_datetime(device):
    """Verify AWSIOT Event Data API Response.

    PreCondition_1 — Verify device datetime is in sync (non-blocking).
    """
    result = device.compare_datetime()
    if result["status"] != "Pass":
        print(f"datetime is incorrect: {result['details']}")


def test_step2_verify_staging(device):
    """STEP_1 — Verify device is on staging server (non-blocking)."""
    device.variables["search_start_ts"] = device.get_current_time_epoch()["epoch_ms"]
    output = device.run("cat /home/ubuntu/.nddevice/latest/cloudconfig.ini | grep 'server = staging'")
    if not output or not output.strip():
        print("Device is not configured to staging server")


def test_step3_push_alert(device):
    """STEP_2 — Push alert to trigger event data (non-blocking)."""
    output = device.run("./gen_ualert.sh", "/home/ubuntu/.nddevice/latest/service/bagheera")
    if not device.user_alert_generated(output):
        print(f"Alert message is not sent to device: {output}")


def test_step4_start_uploader(device):
    """STEP_3 — Start uploader service (non-blocking)."""
    result = device.restart_service("uploader")
    if result["status"] != "Pass":
        print(f"Failed to start uploader service: {result['details']}")


def test_step5_wait(device):
    """STEP_4 — Wait 240s for event data processing."""
    time.sleep(240)


def test_step6_verify_event_processed(device):
    """STEP_5 — Verify 'Event data processed' in uploader logs."""
    ts = device.variables.get("search_start_ts")
    output = device.search_log("/home/ubuntu/.nddevice/log/unifieduploader", "Event data processed", start_timestamp=ts, timeout=60, interval=10)
    assert output, "Event data not processed — not found in uploader logs"
