"""
Feature: AWSIOT — Receive Video Request
Description:
  Verify AWSIOT receives VOD request.
"""

import time


def test_step1_check_datetime(device):
    """Verify AWSIOT receives VOD request.

    PreCondition_1 — Verify device datetime is in sync (non-blocking).
    """
    result = device.compare_datetime()
    if result["status"] != "Pass":
        print(f"datetime is incorrect: {result['details']}")


def test_step2_push_alert(device):
    """STEP_1 — Push alert to trigger VOD."""
    device.variables["search_start_ts"] = device.get_current_time_epoch()["epoch_ms"]
    output = device.run("./gen_ualert.sh", "/home/ubuntu/.nddevice/latest/service/bagheera")
    assert device.user_alert_generated(output), f"Failed to generate user alert: {output}"


def test_step3_wait(device):
    """STEP_2 — Wait 120s for VOD request."""
    time.sleep(120)


def test_step4_verify_vod_request(device):
    """STEP_3 — Poll for 'Received vod' or 'VOD REQUEST vod' in awsiot logs."""
    ts = device.variables.get("search_start_ts")
    timeout_s, interval_s = 600, 60
    elapsed = 0
    output = None
    while elapsed < timeout_s:
        output = device.search_log("/home/ubuntu/.nddevice/log/awsiot", "Received vod", start_timestamp=ts, timeout=1, interval=1)
        if output:
            break
        output = device.search_log("/home/ubuntu/.nddevice/log/awsiot", "VOD REQUEST vod", start_timestamp=ts, timeout=1, interval=1)
        if output:
            break
        time.sleep(interval_s)
        elapsed += interval_s
    assert output, "VOD request not received by awsiot"
