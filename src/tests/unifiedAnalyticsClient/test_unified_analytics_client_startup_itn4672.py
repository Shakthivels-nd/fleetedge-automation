"""
Feature: unifiedAnalyticsClient — Startup & Thread Liveness Check
Description:
  Validate that unifiedAnalyticsClient's own log (not service_mon's) shows a
  clean startup followed by both worker threads reporting alive, after a
  restart.

  Log format observed directly on the pod (2026-09-23):
    unifiedAnalyticsClient.log.2026-09-23_06-00:18:2026-09-23 06:09:22,986 - CRITICAL - root                      - Starting Unified Analytics Client
    unifiedAnalyticsClient.log.2026-09-23_06-40:20:2026-09-23 06:50:12,899 - INFO    - root                      - Thread inertial_client_thread is alive
    ...                                                                                                            - Thread gps_client_thread is alive
"""

import time

LOG_DIR = "/home/ubuntu/.nddevice/log/unifiedAnalyticsClient"
SERVICE_NAME = "unifiedAnalyticsClient"


def test_step1_verify_service_active(device):
    """STEP 1 — Verify unifiedAnalyticsClient is RUNNING."""
    result = device.is_service_active(SERVICE_NAME)
    assert result["status"] == "Pass", f"{SERVICE_NAME} is not RUNNING: {result['state']}"


def test_step2_restart_service(device):
    """STEP 2 — Restart unifiedAnalyticsClient."""
    device.variables["restart_start_ts"] = int(time.time()) * 1000
    result = device.restart_service(SERVICE_NAME)
    assert result["status"] == "Pass", f"Failed to restart {SERVICE_NAME}: {result['output']}"
    time.sleep(10)


def test_step3_verify_starting_log(device):
    """STEP 3 — Verify 'Starting Unified Analytics Client' in unifiedAnalyticsClient's own logs."""
    start_ts = device.variables.get("restart_start_ts")
    found = device.search_log(LOG_DIR, "Starting Unified Analytics Client", start_ts, timeout=60, interval=5)
    assert found is not None, "'Starting Unified Analytics Client' not found in unifiedAnalyticsClient logs."


def test_step4_verify_inertial_client_thread_alive(device):
    """STEP 4 — Verify 'Thread inertial_client_thread is alive' in unifiedAnalyticsClient's own logs."""
    start_ts = device.variables.get("restart_start_ts")
    found = device.search_log(LOG_DIR, "Thread inertial_client_thread is alive", start_ts, timeout=60, interval=5)
    assert found is not None, "'Thread inertial_client_thread is alive' not found in unifiedAnalyticsClient logs."


def test_step5_verify_gps_client_thread_alive(device):
    """STEP 5 — Verify 'Thread gps_client_thread is alive' in unifiedAnalyticsClient's own logs."""
    start_ts = device.variables.get("restart_start_ts")
    found = device.search_log(LOG_DIR, "Thread gps_client_thread is alive", start_ts, timeout=60, interval=5)
    assert found is not None, "'Thread gps_client_thread is alive' not found in unifiedAnalyticsClient logs."
