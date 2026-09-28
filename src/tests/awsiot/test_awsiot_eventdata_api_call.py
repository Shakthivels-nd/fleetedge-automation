"""
Feature: AWSIOT — Eventdata API Call
Description:
  Verify AWSIOT Event Data API call.
"""

import time


def test_step1_check_datetime(device):
    """Verify AWSIOT Event Data API call.

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
    """STEP_2 — Push alert to trigger event data API call (non-blocking)."""
    output = device.run("./gen_ualert.sh", "/home/ubuntu/.nddevice/latest/service/bagheera")
    if not output or "User alert is generated..!!!" not in output:
        print(f"Alert message is not sent to device: {output}")


def test_step4_start_uploader(device):
    """STEP_3 — Start uploader service (non-blocking)."""
    result = device.restart_service("uploader")
    if result["status"] != "Pass":
        print(f"Failed to start uploader service: {result['details']}")


def test_step5_wait(device):
    """STEP_4 — Wait 120s for event data processing."""
    time.sleep(120)


def test_step6_verify_eventdata_call(device):
    """STEP_5 — Verify eventdata upload API call in uploader logs."""
    ts = device.variables.get("search_start_ts")
    output = device.search_log(
        "/home/ubuntu/.nddevice/log/unifieduploader",
        "Calling service: https://idms-staging.netradyne.com/restserver/api/v1/upload/eventdata",
        start_timestamp=ts, timeout=360, interval=10,
    )
    assert output, "Event data call not found"
