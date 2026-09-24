"""
Feature: otacheck — Sleep Based on Device ID Modulo
Description:
  Ported from the pytest_device_validator reference's TC_30
  (test_tc_30_otacheck_sleep_based_on_deviceid_mod.py), adapted to FE's API.

  otacheck sleeps (device_id % 60) seconds before connecting to the cloud
  for a version check, to stagger the fleet's calls. This forces a version
  check cycle (counter injection) and verifies otacheck logs the expected
  sleep duration computed from the device's own device_id.

  device_id comes from device.get_device_info() (reads FE's
  deviceconfig.ini), the FE equivalent of the reference's device.device_id
  CLI-arg accessor.
"""

import time

LOG_DIR = "/home/ubuntu/.nddevice/log/otacheck"
COUNTER_FILE = "/dev/shm/otacheck_count.txt"


def test_step1_get_device_id(device):
    """STEP 1 — Get the device's device_id."""
    device.variables["test_start_ts"] = int(time.time()) * 1000
    info = device.get_device_info()
    device_id_str = info.get("device_id")
    assert device_id_str and str(device_id_str).isdigit(), f"device_id is not numeric: {device_id_str!r}"
    device.variables["device_id"] = int(device_id_str)


def test_step2_calculate_expected_sleep_time(device):
    """STEP 2 — Compute device_id % 60 to get the expected sleep duration in seconds."""
    device_id = device.variables.get("device_id")
    assert device_id is not None, "device_id not found in device.variables."
    device.variables["expected_sleep"] = device_id % 60


def test_step3_inject_otacheck_counter(device):
    """STEP 3 — Set otacheck's counter file to 10 to force a version check cycle."""
    device.run(f"echo 10 > {COUNTER_FILE}")
    time.sleep(30)


def test_step4_verify_ota_call_triggered(device):
    """STEP 4 — Verify 'callOta = True' in otacheck logs."""
    start_ts = device.variables.get("test_start_ts")
    found = device.search_log(LOG_DIR, "callOta = True", start_ts, timeout=240, interval=30)
    assert found is not None, "'callOta = True' not found in otacheck logs."


def test_step5_verify_sleep_message_matches_device_id_modulo(device):
    """STEP 5 — Verify 'Sleeping for <device_id % 60>' in otacheck logs."""
    expected_sleep = device.variables.get("expected_sleep")
    start_ts = device.variables.get("test_start_ts")
    assert expected_sleep is not None, "expected_sleep not set from STEP 2."
    found = device.search_log(LOG_DIR, f"Sleeping for {expected_sleep}", start_ts, timeout=60, interval=10)
    assert found is not None, f"'Sleeping for {expected_sleep}' not found in otacheck logs."
