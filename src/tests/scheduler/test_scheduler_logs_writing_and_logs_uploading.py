"""
Feature: Scheduler — Logs Writing And Logs Uploading
Description:
  Verify scheduler_manager writes logs under its own log folder, and that
  those logs get picked up (compressed, then their local copy deleted) by
  the log-upload flow.

  Ported from nd_test_bot's TC_1420_SCHEDULER_LOGS_WRITING_AND_LOGS_UPLOADING.

  Log strings "FILE: .*scheduler/scheduler.log.*compressed.*retVal: 0" and
  "INFO - Deleted bagheera device logs: /home/ubuntu/.nddevice/log/scheduler/scheduler"
  (UNVERIFIED -- ported from reference, not yet confirmed on FE) need a
  live check before this test is trusted.
"""


def test_step1_verify_log_files_present(device):
    """STEP_1 — Verify log files are present under scheduler_manager."""
    output = device.run("ls -l /home/ubuntu/.nddevice/log/scheduler_manager")
    assert output, "Log files are not present under scheduler_manager"


def test_step2_verify_logs_being_written(device):
    """STEP_2 — Verify scheduler_manager is actively writing logs."""
    output = device.run("grep -inr 'Wrapper_scheduler Starting' /home/ubuntu/.nddevice/log/scheduler_manager")
    assert output, "Log files are not present under scheduler_manager"


def test_step3_verify_logs_picked_for_upload(device):
    """STEP_3 — Verify scheduler logs were picked up and compressed for upload by keep_alive_manager."""
    output = device.run("grep -inr 'FILE: .*scheduler/scheduler.log.*compressed.*retVal: 0' /home/ubuntu/.nddevice/log/keep_alive_manager/")
    assert output, "Scheduler logs not picked while uploading logs"


def test_step4_verify_uploaded_logs_deleted_locally(device):
    """STEP_4 — Verify scheduler logs were deleted locally after being uploaded."""
    output = device.run("grep -inr 'INFO - Deleted bagheera device logs: /home/ubuntu/.nddevice/log/scheduler/scheduler' /home/ubuntu/.nddevice/log/keep_alive_manager/")
    assert output, "Scheduler logs not picked while uploading logs"
