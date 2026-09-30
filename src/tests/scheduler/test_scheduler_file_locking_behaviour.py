"""
Feature: Scheduler — File Locking Behaviour
Description:
  Verify scheduler_manager locks the bagheera_override config file before
  processing a new session.

  Ported from nd_test_bot's TC_1350_SCHEDULER_FILE_LOCKING_BEHAVIOUR. The
  reference branches on device_type (krait path /data/nd_files/config/ vs
  bagheera path /home/ubuntu/config/) -- dropped the krait branch and the
  device-type check, using the bagheera path directly (matches FE's
  confirmed /home/ubuntu/config/ convention, same as
  get_device_info's default deviceconfig_path).

  Log strings "Trying to lock file /home/ubuntu/config/bagheera_override.ini"
  and "Locked file /home/ubuntu/config/bagheera_override.ini" (UNVERIFIED --
  ported from reference, not yet confirmed on FE) need a live check before
  this test is trusted.
"""


def test_step1_restart_scheduler_manager(device):
    """PreCondition_1 — Restart scheduler_manager service."""
    result = device.restart_service("scheduler_manager")
    assert result["status"] == "Pass", f"Failed to restart scheduler_manager service: {result['details']}"


def test_step2_verify_config_file_locked(device):
    """STEP_3 — Verify scheduler_manager locks the bagheera_override config file."""
    for message in [
        "Trying to lock file /home/ubuntu/config/bagheera_override.ini",
        "Locked file /home/ubuntu/config/bagheera_override.ini",
    ]:
        output = device.search_log("/home/ubuntu/.nddevice/log/scheduler_manager", message, timeout=120, interval=15)
        assert output, f"'{message}' not found in scheduler_manager logs"
