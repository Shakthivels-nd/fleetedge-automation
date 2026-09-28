"""
Feature: AWSIOT — State Change to Upload State
Description:
  Verify AWSIOT state change. Push alert to device -> wait -> verify state
  changes to UPLOAD_STATE in inference logs.
"""

import time


def test_step1_check_datetime(device):
    """Verify AWSIOT state change.

    PreCondition_1 — Verify device datetime is in sync (non-blocking).
    """
    result = device.compare_datetime()
    if result["status"] != "Pass":
        print(f"datetime is incorrect: {result['details']}")


def test_step2_push_alert(device):
    """STEP_1 — Send push alert to trigger state change."""
    device.variables["search_start_ts"] = device.get_current_time_epoch()["epoch_ms"]
    output = device.run("./gen_ualert.sh", "/home/ubuntu/.nddevice/latest/service/bagheera")
    assert output and "User alert is generated..!!!" in output, f"Failed to generate user alert: {output}"


def test_step3_wait(device):
    """STEP_2 — Wait 180s for state change to propagate."""
    time.sleep(180)


def test_step4_verify_upload_state_log(device):
    """STEP_3 — Poll for 'modified to state:UPLOAD_STATE' in inference logs (300s, every 60s)."""
    ts = device.variables.get("search_start_ts")
    output = None
    for _ in range(5):  # 300s / 60s = 5 attempts
        output = device.search_log("/home/ubuntu/.nddevice/log/inference", "modified to state:UPLOAD_STATE", start_timestamp=ts, timeout=1, interval=1)
        if not output:
            output = device.search_log("/home/ubuntu/.nddevice/log/inference", "modified to  state:UPLOAD_STATE", start_timestamp=ts, timeout=1, interval=1)
        if output:
            break
        time.sleep(60)
    assert output, "State not changed to UPLOAD_STATE in inference logs within 300s"


def test_step5_verify_got_upload_state(device):
    """STEP_4 — Verify 'Got state UPLOAD_STATE' in inference logs (poll 300s, every 60s)."""
    output = None
    for _ in range(5):  # 300s / 60s = 5 attempts
        output = device.run("grep -inr \"Got state 'UPLOAD_STATE'\" /home/ubuntu/.nddevice/log/inference/*")
        if output and output.strip():
            break
        time.sleep(60)
    assert output and output.strip(), "Got state 'UPLOAD_STATE' not found in inference logs within 300s"
