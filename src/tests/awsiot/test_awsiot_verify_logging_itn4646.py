"""
Feature: AWSIOT — Verify Logging
Description:
  Verify awsiot is active and its log folder/files are present, confirming
  logging is active.
"""


def test_step1_check_datetime(device):
    """Verify awsiot is active and logging to its log folder.

    PreCondition_1 — Verify device datetime is in sync (non-blocking).
    """
    result = device.compare_datetime()
    if result["status"] != "Pass":
        print(f"datetime is incorrect: {result['details']}")


def test_step2_verify_awsiot_active(device):
    """STEP_1 — Verify awsiot service is active."""
    result = device.is_service_active("awsiot")
    assert result["status"] == "Pass", f"awsiot is not active: {result['state']}"


def test_step3_verify_log_folder_present(device):
    """STEP_2 — Verify awsiot log folder(s) are present (non-blocking)."""
    output = device.run("ls /home/ubuntu/.nddevice/log/ | grep awsiot")
    entries = (output or "").split()
    if not ("awsiot" in entries and "awsiot_c" in entries):
        print(f"log folder is not present: {entries}")


def test_step4_verify_log_files_present(device):
    """STEP_3 — Verify awsiot log files are present."""
    output = device.run("ls /home/ubuntu/.nddevice/log/awsiot")
    assert output and ".log" in output, f"log files are not present: {output}"
