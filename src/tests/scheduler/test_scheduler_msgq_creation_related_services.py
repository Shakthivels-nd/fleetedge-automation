"""
Feature: Scheduler — Msgq Creation Related Services
Description:
  Verify message queues are created for scheduler_manager and its related
  services (uploader, HealthStatsManager, ndcentral).

  Ported from nd_test_bot's TC_1155_SCHEDULER_MSGQ_CREATION_RELATED_SERVICES.
  PreCondition_1 (DeviceController_obj.reboot_device) dropped -- FE has no
  device-level reboot method (skip_reason=reboot_required elsewhere in the
  port). Instead of relying on a reboot (or on stale/pre-existing log
  lines), each relevant service is explicitly restarted right before its
  own message-queue-creation log check, so the "Message queue ... created"
  lines are freshly generated within this test run.
"""


def test_step1_verify_scheduler_manager_msgq(device):
    """STEP_2 — Restart scheduler_manager and verify its own message queues were created."""
    device.variables["search_start_ts"] = device.get_current_time_epoch()["epoch_ms"]
    result = device.restart_service("scheduler_manager")
    assert result["status"] == "Pass", f"Failed to restart scheduler_manager: {result['details']}"
    ts = device.variables["search_start_ts"]
    for message in [
        "Message queue created",
        "Message queue server created SCH",
    ]:
        output = device.search_log("/home/ubuntu/.nddevice/log/scheduler_manager", message, start_timestamp=ts, timeout=30, interval=5)
        assert output, f"'{message}' not found in scheduler_manager logs"

    output = device.run("grep -h 'Message queue client created SM' /home/ubuntu/.nddevice/log/scheduler_manager/* | tail -1")
    assert output, "'Message queue client created SM' not found in scheduler_manager logs"


def test_step2_verify_uploader_msgq(device):
    """STEP_3 — Restart unifieduploader (uploader) and verify its message queue was created."""
    ts = device.get_current_time_epoch()["epoch_ms"]
    result = device.restart_service("uploader")
    assert result["status"] == "Pass", f"Failed to restart uploader: {result['details']}"
    output = device.search_log("/home/ubuntu/.nddevice/log/unifieduploader", "Message queue server created UniUpload", start_timestamp=ts, timeout=30, interval=5)
    assert output, "'Message queue server created UniUpload' not found in unifieduploader logs"


def test_step3_verify_healthstatsmanager_msgq(device):
    """STEP_4 — Verify scheduler_manager's message queue client for HealthStatsManager was created (scheduler_manager already restarted in STEP_2)."""
    output = device.run("grep -h 'Message queue client created HS' /home/ubuntu/.nddevice/log/scheduler_manager/* | tail -1")
    assert output, "'Message queue client created HS' not found in scheduler_manager logs"


def test_step4_verify_ndcentral_msgq(device):
    """STEP_5 — Restart bagheera (ndcentral's supervisor group) and verify ndcentral's message queue was created."""
    ts = device.get_current_time_epoch()["epoch_ms"]
    result = device.restart_service("bagheera")
    assert result["status"] == "Pass", f"Failed to restart bagheera: {result['details']}"
    output = device.search_log("/home/ubuntu/.nddevice/log/ndcentral", "Message queue server created q_nd_central", start_timestamp=ts, timeout=30, interval=5)
    assert output, "'Message queue server created q_nd_central' not found in ndcentral logs"
