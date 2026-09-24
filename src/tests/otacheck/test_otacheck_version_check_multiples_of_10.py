"""
Feature: otacheck — Version Check API at Multiples of 10
Description:
  Ported from the pytest_device_validator reference's TC_29
  (test_tc_29_otacheck_versioncheckapi_multiples_of_10.py), adapted to FE's
  DeviceTest API (device.run/search_log/variables instead of the
  reference's device.get_timestamp()/CommandResult-based API).

  Forces otacheck's version-check cycle by writing 10 to its counter file
  (confirmed present on FE at /dev/shm/otacheck_count.txt, no
  krait/bagheera-device-type branching needed — FE has a single device
  type/path), then verifies otacheck's own logs show the counter value,
  the OTA call being triggered, and countFromFile being used.
"""

import time

LOG_DIR = "/home/ubuntu/.nddevice/log/otacheck"
COUNTER_FILE = "/dev/shm/otacheck_count.txt"


def test_step1_inject_otacheck_counter(device):
    """STEP 1 — Set otacheck's counter file to 10 to force a version check cycle."""
    device.variables["test_start_ts"] = int(time.time()) * 1000
    device.run(f"echo 10 > {COUNTER_FILE}")
    time.sleep(30)


def test_step2_verify_counter_value_logged(device):
    """STEP 2 — Verify 'OTACHECK COUNTER VALUE = 10' in otacheck logs."""
    start_ts = device.variables.get("test_start_ts")
    found = device.search_log(LOG_DIR, "OTACHECK COUNTER VALUE = 10", start_ts, timeout=210, interval=30)
    assert found is not None, "'OTACHECK COUNTER VALUE = 10' not found in otacheck logs."


def test_step3_verify_ota_call_triggered(device):
    """STEP 3 — Verify 'callOta = True' in otacheck logs."""
    start_ts = device.variables.get("test_start_ts")
    found = device.search_log(LOG_DIR, "callOta = True", start_ts, timeout=60, interval=10)
    assert found is not None, "'callOta = True' not found in otacheck logs."


def test_step4_verify_countfromfile_flag(device):
    """STEP 4 — Verify 'countFromFile:True' in otacheck logs."""
    start_ts = device.variables.get("test_start_ts")
    found = device.search_log(LOG_DIR, "countFromFile:True", start_ts, timeout=60, interval=10)
    assert found is not None, "'countFromFile:True' not found in otacheck logs."
