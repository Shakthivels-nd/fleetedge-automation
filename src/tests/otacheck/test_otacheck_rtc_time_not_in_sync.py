"""
Feature: otacheck — RTC Time Not In Sync
Description:
  Ported from the pytest_device_validator reference's TC_74
  (test_tc_74_otacheck_rtctime_not_insync.py), adapted to FE's API.

  NEGATIVE test: sets the pod's clock to next year, forces an OTA version
  check cycle, and verifies otacheck attempts the call but fails to
  connect (JWT/SSL certificate validation fails when the device's time is
  wrong) — then restores the clock and services regardless of pass/fail.

  ⚠️ This mutates the pod's system clock. The restore step always runs
  (each restore/cleanup step's own assertions are non-fatal by design —
  see test_step6/7 below) so the clock and time_sync are put back even if
  an earlier step fails, but this is still a disruptive action on shared
  hardware. Confirmed with the user before adding (2026-09-23).

  Deviates from the reference:
  - No wifi_mgr restart in the postcondition — FE has no such service.
  - Adds a time_sync restart after the clock restore (FE's own
    supervisorctl-managed time-sync service, confirmed present) so FE's
    own sync mechanism gets a chance to re-settle, in addition to the
    reference's ntpd/hwclock fix.
  - device_id comes from device.get_device_info() (FE's deviceconfig.ini),
    same as test_otacheck_sleep_based_on_device_id_modulo.py.
"""

import time

LOG_DIR = "/home/ubuntu/.nddevice/log/otacheck"
COUNTER_FILE = "/dev/shm/otacheck_count.txt"


def test_step1_get_device_id(device):
    """STEP 1 — Get the device's device_id (used to compute the pre-call sleep window)."""
    device.variables["test_start_ts"] = int(time.time()) * 1000
    info = device.get_device_info()
    device_id_str = info.get("device_id")
    assert device_id_str and str(device_id_str).isdigit(), f"device_id is not numeric: {device_id_str!r}"
    device.variables["device_id"] = int(device_id_str)


def test_step2_set_device_time_to_future(device):
    """STEP 2 — Set the pod's clock to one year in the future."""
    device.run('date -s "$(date -d \\"+1 year\\" +\\"%Y-%m-%d %H:%M:%S\\")"')
    time.sleep(5)


def test_step3_inject_otacheck_counter(device):
    """STEP 3 — Set otacheck's counter file to 10 to force a version check cycle."""
    device.run(f"echo 10 > {COUNTER_FILE}")
    time.sleep(30)


def test_step4_verify_ota_call_attempted(device):
    """STEP 4 — Verify 'OTACHECK COUNTER VALUE = 10' and 'callOta = True' both appear in otacheck logs."""
    start_ts = device.variables.get("test_start_ts")
    found_counter = device.search_log(LOG_DIR, "OTACHECK COUNTER VALUE = 10", start_ts, timeout=90, interval=10)
    found_call_ota = device.search_log(LOG_DIR, "callOta = True", start_ts, timeout=60, interval=10)
    assert found_counter is not None, "'OTACHECK COUNTER VALUE = 10' not found in otacheck logs."
    assert found_call_ota is not None, "'callOta = True' not found in otacheck logs."


def test_step5_verify_connection_failure_due_to_time_mismatch(device):
    """STEP 5 — Verify 'Failed to connect' in otacheck logs (auth fails due to wrong device time)."""
    device_id = device.variables.get("device_id") or 0
    time.sleep(device_id % 60)
    start_ts = device.variables.get("test_start_ts")
    found = device.search_log(LOG_DIR, "Failed to connect", start_ts, timeout=120, interval=10)
    assert found is not None, "'Failed to connect' not found in otacheck logs after setting device time to the future."


def test_step6_restore_device_time(device):
    """STEP 6 — Restore the pod's clock via NTP (falls back to hwclock)."""
    device.run("ntpd -q -p pool.ntp.org 2>/dev/null || hwclock -s")
    time.sleep(5)


def test_step7_restart_time_sync(device):
    """STEP 7 — Restart FE's time_sync service so it can re-settle after the clock restore."""
    result = device.restart_service("time_sync")
    assert result["status"] == "Pass", f"Failed to restart time_sync after clock restore: {result['output']}"
    time.sleep(10)
