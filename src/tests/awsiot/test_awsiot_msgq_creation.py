"""
Feature: AWSIOT — MSGQ Creation
Description:
  Verify awsiot creates its message queue (AWSIOT and AWSIOT_PUB) on
  restart, both in logs and on disk under /dev/shm/MSGQ/.
"""

import time


def test_step1_check_datetime(device):
    """Verify awsiot creates its AWSIOT/AWSIOT_PUB message queues on restart.

    PreCondition_1 — Verify device datetime is in sync (non-blocking).
    """
    result = device.compare_datetime()
    if result["status"] != "Pass":
        print(f"datetime is incorrect: {result['details']}")


def test_step2_restart_awsiot(device):
    """STEP_1 — Restart awsiot service."""
    device.variables["search_start_ts"] = device.get_current_time_epoch()["epoch_ms"]
    result = device.restart_service("awsiot")
    assert result["status"] == "Pass", f"Failed to restart awsiot service: {result['details']}"


def test_step3_wait(device):
    """STEP_2 — Wait 20s after restart."""
    time.sleep(20)


def test_step4_verify_msgq_log(device):
    """STEP_3 — Verify message queue server creation log (non-blocking)."""
    ts = device.variables.get("search_start_ts")
    output = device.search_log("/home/ubuntu/.nddevice/log/awsiot", "Message queue server created AWSIOT", start_timestamp=ts, timeout=1, interval=1)
    if not output:
        output = device.search_log("/home/ubuntu/.nddevice/log/awsiot", "Message queue server created AWSIOT_PUB", start_timestamp=ts, timeout=1, interval=1)
    if not output:
        output = device.search_log("/home/ubuntu/.nddevice/log/awsiot", "Message queue created", start_timestamp=ts, timeout=1, interval=1)
    if not output:
        print("Awsiot Message queue server not created")


def test_step5_verify_msgq_on_disk(device):
    """STEP_4 — Verify AWSIOT and AWSIOT_PUB message queues exist under /dev/shm/MSGQ/."""
    output = device.run("ls /dev/shm/MSGQ/ | grep AWSIOT")
    entries = (output or "").split()
    assert "AWSIOT" in entries and "AWSIOT_PUB" in entries, f"awsiot MSGQ not created in respective path. MSGQ contains {entries}"
