"""
Feature: otacheck — Current Version Logged
Description:
  Ported from the pytest_device_validator reference's TC_40
  (test_tc_40_otacheck_devicenotifies_cloud_newversion.py), scoped down to
  what FE can actually verify.

  The reference primarily queries a cloud IDMS "ops-data" API
  (device.ops_data_api(), full auth/product-id/HTTP integration we don't
  have) to get the version the cloud believes the device is on, falling
  back to device-side sources (nddevice.ini / otacheck logs) only if the
  API call fails. Building the ops-data API integration for one test isn't
  worth it, so this test uses FE's existing device.get_ota_version()
  (already used elsewhere, e.g. test_ota_md5sum_and_check_no_legacy_package_exists_itn2430
  in test_sanity_functions.py) as the version source instead — the same
  fallback mechanism the reference falls back to, just via an
  already-proven FE method rather than a new cloud API client.

  This verifies otacheck logs the version it detected locally (device-side
  confirmation), not that the cloud dashboard was notified (which would
  need the ops-data API to confirm end-to-end).
"""

import time

LOG_DIR = "/home/ubuntu/.nddevice/log/otacheck"


def test_step1_get_current_ota_version(device):
    """STEP 1 — Get the device's current OTA version."""
    device.variables["test_start_ts"] = int(time.time()) * 1000
    version = device.get_ota_version()
    assert version, "OTA version not detected on the pod."
    device.variables["ota_version"] = version


def test_step2_verify_otacheck_logs_current_version(device):
    """STEP 2 — Verify 'CurrentVersion <version>' in otacheck logs."""
    version = device.variables.get("ota_version")
    start_ts = device.variables.get("test_start_ts")
    assert version, "ota_version not set from STEP 1."
    found = device.search_log(LOG_DIR, f"CurrentVersion {version}", start_ts, timeout=240, interval=30)
    assert found is not None, f"'CurrentVersion {version}' not found in otacheck logs."
