"""
Feature: otacheck — Override Configs Download
Description:
  Ported from the pytest_device_validator reference's TC_216
  (test_tc_216_otacheck_overrideconfigs_download.py), adapted to FE's paths
  and API. No config-download/upload helper is used by the reference test
  either — it edits nddevice.ini in place via a shell command, which is
  what this does too (device.run + sed), just against FE's fixed paths
  instead of the reference's krait/bagheera-device-type branching:
    nddevice.ini:         /home/ubuntu/.nddevice/nddevice.ini
    bagheera_override.ini: /home/ubuntu/config/bagheera_override.ini

  Clearing nddevice.ini's `version` field forces otacheck to treat the
  override config as out of date and re-download it on its next cycle
  (forced immediately here via the counter-file injection from
  test_otacheck_version_check_multiples_of_10.py).
"""

import time

LOG_DIR = "/home/ubuntu/.nddevice/log/otacheck"
COUNTER_FILE = "/dev/shm/otacheck_count.txt"
NDDEVICE_INI = "/home/ubuntu/.nddevice/nddevice.ini"
OVERRIDE_INI = "/home/ubuntu/config/bagheera_override.ini"


def test_step1_clear_override_config_version(device):
    """STEP 1 — Clear the `version` field in nddevice.ini to force a re-download."""
    device.variables["test_start_ts"] = int(time.time()) * 1000
    device.run(f'sed -i "s/^version.*=.*$/version = /" {NDDEVICE_INI}')
    time.sleep(5)


def test_step2_inject_otacheck_counter(device):
    """STEP 2 — Set otacheck's counter file to 10 to force a version check cycle."""
    device.run(f"echo 10 > {COUNTER_FILE}")
    time.sleep(30)


def test_step3_verify_file_sync_log(device):
    """STEP 3 — Verify 'File sync finished: .../bagheera_override.ini' in otacheck logs."""
    start_ts = device.variables.get("test_start_ts")
    found = device.search_log(
        LOG_DIR, f"File sync finished: {OVERRIDE_INI}", start_ts, timeout=210, interval=30
    )
    assert found is not None, f"'File sync finished: {OVERRIDE_INI}' not found in otacheck logs."


def test_step4_verify_nddevice_ini_updated_log(device):
    """STEP 4 — Verify 'Updated configuration in path .../nddevice.ini' in otacheck logs."""
    start_ts = device.variables.get("test_start_ts")
    found = device.search_log(
        LOG_DIR, f"Updated configuration in path {NDDEVICE_INI}", start_ts, timeout=60, interval=10
    )
    assert found is not None, f"'Updated configuration in path {NDDEVICE_INI}' not found in otacheck logs."


def test_step5_verify_override_file_exists(device):
    """STEP 5 — Verify bagheera_override.ini exists on the pod after the re-download."""
    output = device.run(f"ls {OVERRIDE_INI}")
    assert output and OVERRIDE_INI in output, f"{OVERRIDE_INI} not found after override config re-download."
