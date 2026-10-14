"""
Feature: Scheduler — Fields Updated Each Session In HS
Description:
  Verify HealthStatsManager's cpu_info/gpu_info DB entries get a fresh
  timestamp roughly once a minute.

  Ported from nd_test_bot's TC_1407_SCHEDULER_FIELDS_UPDATED_EACH_SESSION_IN_HS.
  The reference's Calculator_obj.get_hs_db_latest_entry_ts is now ported as
  device.get_hs_db_latest_entry_ts (device_checks.get_hs_db_latest_entry_ts),
  matching the reference's retry semantics (up to 4 attempts, 10s apart, to
  ride out healthstats.db being transiently locked by a concurrent writer)
  instead of the earlier single-shot query, which had no such retry and
  could fail outright on a locked/not-yet-populated DB.

  Assumes /home/ubuntu/.nddevice/db/healthstats.db and its AH table/SESSION
  column (UNVERIFIED -- ported from reference, not yet confirmed on FE)
  match the reference's schema.
"""

import time


def _get_hs_db_latest_entry_ts(device, session):
    result = device.get_hs_db_latest_entry_ts(session)
    assert result["status"] == "Pass", f"healthstats.db query failed for session {session!r}: {result['details']}"
    return result["timestamp"]


def test_step0_wait(device):
    """PreCondition_1 — Wait 15s."""
    time.sleep(15)


def test_step1_restart_healthstatsmanager(device):
    """STEP_1 — Restart HealthStatsManager service."""
    result = device.restart_service("HealthStatsManager")
    assert result["status"] == "Pass", f"Failed to restart HealthStatsManager: {result['details']}"


def test_step2_wait(device):
    """STEP_1_1 — Wait 182s."""
    time.sleep(182)


def test_step3_get_first_timestamps(device):
    """STEP_2/STEP_2_1 — Capture the first cpu_info/gpu_info DB timestamps."""
    device.variables["timestamp1"] = _get_hs_db_latest_entry_ts(device, "health_info:cpu_info")
    device.variables["timestamp3"] = _get_hs_db_latest_entry_ts(device, "health_info:gpu_info")


def test_step4_wait(device):
    """STEP_3 — Wait 60s."""
    time.sleep(60)


def test_step5_get_second_timestamps(device):
    """STEP_4/STEP_4_1 — Capture the second cpu_info/gpu_info DB timestamps."""
    device.variables["timestamp2"] = _get_hs_db_latest_entry_ts(device, "health_info:cpu_info")
    device.variables["timestamp4"] = _get_hs_db_latest_entry_ts(device, "health_info:gpu_info")


def test_step6_verify_cpu_info_updated_around_one_minute(device):
    """STEP_5/STEP_6 — Verify the cpu_info DB entry timestamp advanced by ~1 minute."""
    time_diff_cpu = device.variables["timestamp2"] - device.variables["timestamp1"]
    assert 58000 <= time_diff_cpu <= 122000, f"HS cpu_info db entry time difference is not around 1 min: {time_diff_cpu}ms"


def test_step7_verify_gpu_info_updated_around_one_minute(device):
    """STEP_5_1/STEP_6_1 — Verify the gpu_info DB entry timestamp advanced by ~1 minute."""
    time_diff_gpu = device.variables["timestamp4"] - device.variables["timestamp3"]
    assert 58000 <= time_diff_gpu <= 122000, f"HS gpu_info db entry time difference is not around 1 min: {time_diff_gpu}ms"
