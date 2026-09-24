"""
Feature: Service Monitor — SendMetricgRPC Status Check
Description:
  Validate that service_mon correctly logs SendMetricgRPC's start, crash (SIGABRT),
  and stop (SIGTERM) events.

  Log tag ("SendMetricgRPC") is set to the service name itself — the user
  confirmed directly on the pod (2026-09-15) that FE's service_mon logs
  every service under its own supervisorctl service name (the same pattern
  already confirmed for the other 11 servicemonitor tests in this folder;
  see fleetedge_automation_exploration.md, SERVICEMONITOR TESTS).
"""

import time

LOG_DIR = "/home/ubuntu/.nddevice/log/service_mon"
SERVICE_NAME = "SendMetricgRPC"
LOG_TAG = "SendMetricgRPC"


def test_step1_verify_services_active(device):
    """STEP 1 — Verify service_mon and SendMetricgRPC are both RUNNING."""
    result = device.is_service_active("service_mon")
    assert result["status"] == "Pass", f"service_mon is not RUNNING: {result['state']}"
    result = device.is_service_active(SERVICE_NAME)
    assert result["status"] == "Pass", f"{SERVICE_NAME} is not RUNNING: {result['state']}"


def test_step2_restart_service(device):
    """STEP 2 — Restart SendMetricgRPC to trigger a start event."""
    device.variables["restart_start_ts"] = int(time.time()) * 1000
    result = device.restart_service(SERVICE_NAME)
    assert result["status"] == "Pass", f"Failed to restart {SERVICE_NAME}: {result['output']}"
    time.sleep(10)


def test_step3_verify_service_started_log(device):
    """STEP 3 — Verify 'Service started: SendMetricgRPC' in service_mon logs."""
    start_ts = device.variables.get("restart_start_ts")
    found = device.search_log(LOG_DIR, f"Service started: {LOG_TAG}", start_ts, timeout=60, interval=5)
    assert found is not None, f"'Service started: {LOG_TAG}' not found in service_mon logs."


def test_step4_get_pid_and_send_sigabrt(device):
    """STEP 4 — Get PID of SendMetricgRPC and send SIGABRT (kill -6)."""
    pid = device.run(f"pidof {SERVICE_NAME} | tr ' ' '\\n' | sort -n | head -n 1")
    assert pid and pid.strip(), f"Failed to get PID of {SERVICE_NAME}."
    device.variables["crash_start_ts"] = int(time.time()) * 1000
    device.run(f"kill -6 {pid.strip()}")
    device.variables["killed_pid"] = pid.strip()
    time.sleep(15)


def test_step5_verify_service_error_log(device):
    """STEP 5 — Verify 'Service error: SendMetricgRPC' in service_mon logs (crash detected)."""
    start_ts = device.variables.get("crash_start_ts")
    found = device.search_log(LOG_DIR, f"Service error: {LOG_TAG}", start_ts, timeout=60, interval=5)
    assert found is not None, f"'Service error: {LOG_TAG}' not found in service_mon logs after SIGABRT."


def test_step6_get_pid_and_send_sigterm(device):
    """STEP 6 — Get new PID of SendMetricgRPC (after crash recovery) and send SIGTERM."""
    pid = device.run(f"pidof {SERVICE_NAME} | tr ' ' '\\n' | sort -n | head -n 1")
    assert pid and pid.strip(), f"Failed to get new PID of {SERVICE_NAME} after crash recovery."
    device.variables["stop_start_ts"] = int(time.time()) * 1000
    device.run(f"kill -15 {pid.strip()}")
    time.sleep(10)


def test_step7_verify_service_stopped_log(device):
    """STEP 7 — Verify 'Service stopped: SendMetricgRPC' in service_mon logs (graceful stop)."""
    start_ts = device.variables.get("stop_start_ts")
    found = device.search_log(LOG_DIR, f"Service stopped: {LOG_TAG}", start_ts, timeout=60, interval=5)
    assert found is not None, f"'Service stopped: {LOG_TAG}' not found in service_mon logs after SIGTERM."


def test_step8_restart_and_verify_active(device):
    """STEP 8 — Restart SendMetricgRPC and verify both services are RUNNING again."""
    result = device.restart_service(SERVICE_NAME)
    assert result["status"] == "Pass", f"Failed to restart {SERVICE_NAME}: {result['output']}"
    time.sleep(10)
    result = device.is_service_active("service_mon")
    assert result["status"] == "Pass", "service_mon is not RUNNING after test."
    result = device.is_service_active(SERVICE_NAME)
    assert result["status"] == "Pass", f"{SERVICE_NAME} is not RUNNING after test."
