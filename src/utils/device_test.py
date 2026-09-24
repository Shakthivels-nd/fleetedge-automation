"""
device_test.py — Unified DEVICE TEST interface for fleetedge-automation.

Wraps the existing util modules (connection, log_search, device_checks,
time_utils, cloud_api, db_utils) behind a single object so tests call
device.run(...), device.search_log(...), etc. instead of importing and
calling a dozen separate functions directly.

This does not replace those util modules -- DeviceTest is a thin facade
over them, matching the pattern documented in
fleetedge_automation_exploration.md. See device_api.py for the single
source of truth listing every method this class exposes.

Usage:
    device = DeviceTest(pod_connection)
    result = device.run("supervisorctl status")
    device.search_log("awsiot", "Connected successfully")
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from .engine import connection
from .engine import log_search
from .engine import device_checks
from .engine import time_utils
from .engine import cloud_api
from .engine import db_utils


class DeviceTest:
    """Facade over the pod-connection util modules.

    Takes an already-connected pexpect session (as produced by the
    `pod_connection` fixture) -- it does not open its own connection.
    """

    def __init__(self, pod_connection):
        self._pod_connection = pod_connection
        self._variables: Dict[str, Any] = {}
        self._command_log: List[Dict[str, Any]] = []

        self._ota_version = device_checks.get_ota_version(self._pod_connection)
        self._variables["ota_version"] = self._ota_version

    # ── Properties ─────────────────────────────────────────────────────

    @property
    def pod_connection(self):
        """The underlying pexpect.spawn session."""
        return self._pod_connection

    @property
    def ota_version(self) -> Optional[str]:
        """OTA package version detected at init (cached)."""
        return self._ota_version

    @property
    def variables(self) -> Dict[str, Any]:
        """Shared state across steps within a test."""
        return self._variables

    @property
    def command_log(self) -> List[Dict[str, Any]]:
        """Full log of operations executed through this DeviceTest."""
        return self._command_log

    def _log(self, cmd: str, output: Any) -> None:
        self._command_log.append({
            "cmd": cmd,
            "output": output,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        })

    # ── Core connection operations ───────────────────────────────────────

    def run(self, cmd: str, directory: Optional[str] = None) -> Optional[str]:
        """Run a command on the already-connected pod session."""
        output = connection.run_command_on_pod(self._pod_connection, cmd, directory)
        self._log(f"run({cmd})", output)
        return output

    def check_connected(self) -> bool:
        """Check if the pod session is alive."""
        return bool(self._pod_connection and self._pod_connection.isalive())

    def close(self) -> None:
        """Close the pod connection."""
        connection.close_pod_connection(self._pod_connection)

    # ── Log search ─────────────────────────────────────────────────────

    def search_log(self, log_dir: str, search_term: str, start_timestamp=None,
                    timeout: int = 60, interval: int = 5) -> Optional[str]:
        """Poll device logs for a term after start_timestamp until found or timeout."""
        result = log_search.search_logs_in_pod(
            self._pod_connection, log_dir, search_term, start_timestamp, timeout, interval
        )
        self._log(f"search_log({log_dir}, {search_term})", result)
        return result

    def grep_logs(self, service: str, pattern: str,
                   log_root: str = "/home/ubuntu/.nddevice/log", since_ts=None) -> Dict[str, Any]:
        """Single-shot (no polling) grep of a service's logs."""
        result = log_search.grep_logs(self._pod_connection, service, pattern, log_root, since_ts)
        self._log(f"grep_logs({service}, {pattern})", result)
        return result

    def search_log_interval(self, service_name: str, message: str, start_time_epoch=None) -> Dict[str, Any]:
        """Compute intervals between consecutive matching log lines."""
        result = log_search.search_log_interval(self._pod_connection, service_name, message, start_time_epoch)
        self._log(f"search_log_interval({service_name}, {message})", result)
        return result

    def frequency_based_calls(self, api_pattern: str, service_name: str, expected_interval_minutes: float,
                               cloud_check: bool = False, api_key: Optional[str] = None,
                               tolerance_minutes: float = 1) -> Dict[str, Any]:
        """Check an API call pattern recurs at the expected interval."""
        result = log_search.frequency_based_calls(
            self._pod_connection, api_pattern, service_name, expected_interval_minutes,
            cloud_check, api_key, tolerance_minutes,
        )
        self._log(f"frequency_based_calls({api_pattern}, {service_name})", result)
        return result

    def event_based_api_call(self, api_pattern: str, service_name: str,
                              cloud_check: bool = False, api_key: Optional[str] = None,
                              max_cloud_delay_ms: int = 40000, cloud_retries: int = 5) -> Dict[str, Any]:
        """Capture the latest occurrence of a one-shot API call pattern in logs."""
        result = log_search.event_based_api_call(
            self._pod_connection, api_pattern, service_name,
            cloud_check, api_key, max_cloud_delay_ms, cloud_retries,
        )
        self._log(f"event_based_api_call({api_pattern}, {service_name})", result)
        return result

    # ── Device / OTA checks ──────────────────────────────────────────────

    def verify_file_presence(self, directories: List[str], patterns: List[str]) -> List[Dict[str, Any]]:
        """Count files matching patterns per directory."""
        result = device_checks.verify_file_presence(self._pod_connection, directories, patterns)
        self._log(f"verify_file_presence({directories}, {patterns})", result)
        return result

    def check_file_availability(self, file_path: str) -> Dict[str, Any]:
        """Check whether a file exists on the pod."""
        result = device_checks.check_file_availability(self._pod_connection, file_path)
        self._log(f"check_file_availability({file_path})", result)
        return result

    def get_ota_version(self, directory: str = "/home/ubuntu/.nddevice") -> Optional[str]:
        """Re-detect the OTA version (use the .ota_version property for the cached value)."""
        result = device_checks.get_ota_version(self._pod_connection, directory)
        self._log(f"get_ota_version({directory})", result)
        return result

    def check_ota_md5sum(self, ota_version: str, directory: str = "/home/ubuntu/.nddevice") -> str:
        """Return the md5sum of the given OTA package."""
        result = device_checks.check_ota_md5sum(self._pod_connection, ota_version, directory)
        self._log(f"check_ota_md5sum({ota_version})", result)
        return result

    def check_no_legacy_package_exists(self, ota_version: str, directory: str = "/home/ubuntu/.nddevice") -> bool:
        """Assert only the given OTA package exists in directory."""
        result = device_checks.check_no_legacy_package_exists(self._pod_connection, ota_version, directory)
        self._log(f"check_no_legacy_package_exists({ota_version})", result)
        return result

    def list_log_folder_contents(self, directory: str = "/data/nd_files/log") -> Optional[str]:
        """List the contents of a log folder on the pod."""
        result = device_checks.list_log_folder_contents(self._pod_connection, directory)
        self._log(f"list_log_folder_contents({directory})", result)
        return result

    def validate_services_uptime_diff(self, directory: str = "/home/ubuntu/.nddevice/latest/service",
                                       max_diff_seconds: int = 5) -> None:
        """Assert all running services' uptimes are within max_diff_seconds of each other."""
        result = device_checks.validate_services_uptime_diff(self._pod_connection, directory, max_diff_seconds)
        self._log(f"validate_services_uptime_diff({directory})", result)
        return result

    def check_private_key_markers(self, directory: str = "/home/ubuntu/.nddevice/certificate") -> Dict[str, bool]:
        """Check cert/key files contain the PRIVATE marker."""
        result = device_checks.check_private_key_markers(self._pod_connection, directory)
        self._log(f"check_private_key_markers({directory})", result)
        return result

    def is_service_active(self, service_name: str, directory: str = "/home/ubuntu/.nddevice/latest/service") -> Dict[str, Any]:
        """Check whether a supervisor-managed service is RUNNING."""
        result = device_checks.is_service_active(self._pod_connection, service_name, directory)
        self._log(f"is_service_active({service_name})", result)
        return result

    def restart_service(self, service_name: str, directory: str = "/home/ubuntu/.nddevice/latest/service") -> Dict[str, Any]:
        """Restart a supervisor-managed service via supervisorctl."""
        result = device_checks.restart_service(self._pod_connection, service_name, directory)
        self._log(f"restart_service({service_name})", result)
        return result

    def get_service_pid(self, service_name: str, directory: str = "/home/ubuntu/.nddevice/latest/service") -> Dict[str, Any]:
        """Get a supervisor-managed service's PID directly from supervisorctl status."""
        result = device_checks.get_service_pid(self._pod_connection, service_name, directory)
        self._log(f"get_service_pid({service_name})", result)
        return result

    def get_device_info(self, deviceconfig_path: str = "/home/ubuntu/config/deviceconfig.ini") -> Dict[str, Any]:
        """Retrieve device_type, device_id, ota_version from the pod."""
        result = device_checks.get_device_info(self._pod_connection, deviceconfig_path)
        self._log(f"get_device_info({deviceconfig_path})", result)
        return result

    # ── Voyager host operations ──────────────────────────────────────────

    def reboot_voyager(self) -> None:
        """Reboot the voyager host and wait for it to come back online."""
        connection.reboot_voyager()
        self._log("reboot_voyager()", None)

    def run_on_voyager(self, cmd: str = "ls -l", directory: Optional[str] = None,
                        ip_address: str = connection.voyager_ip,
                        username: str = "voyager", password: str = "voyager") -> Optional[str]:
        """Run a one-off command directly on the voyager host (not the pod)."""
        result = connection.run_command_on_voyager(ip_address, username, password, cmd, directory)
        self._log(f"run_on_voyager({cmd})", result)
        return result

    # ── Time / size helpers (pure utilities, no pod I/O) ──────────────────

    def get_current_time_utc(self) -> Dict[str, Any]:
        return time_utils.get_current_time_utc()

    def get_current_time_epoch(self) -> Dict[str, Any]:
        return time_utils.get_current_time_epoch()

    def compare_time_difference_hms(self, timestamp1, expected_difference_minutes, timestamp2) -> Dict[str, Any]:
        return time_utils.compare_time_difference_hms(timestamp1, expected_difference_minutes, timestamp2)

    def validate_size_range(self, min_size, size, max_size, inclusive: bool = True) -> Dict[str, Any]:
        return time_utils.validate_size_range(min_size, size, max_size, inclusive)

    # ── Cloud API (IDMS) ─────────────────────────────────────────────────

    def aws_ping_command(self, user_id: str, ping_command: str):
        """Send an AWS IoT ping command (e.g. 'keep-alive', 'reboot-phone') to the device."""
        result = cloud_api.aws_ping_command(user_id, ping_command)
        self._log(f"aws_ping_command({user_id}, {ping_command})", result)
        return result

    # ── Database (Postgres) ──────────────────────────────────────────────

    def wait_for_postgresql_result(self, query: str, params: tuple = (),
                                    timeout: int = 300, interval: int = 10):
        """Poll a Postgres query (DB_CONFIG) until it returns rows or times out."""
        result = db_utils.wait_for_postgresql_result(query, params, timeout, interval)
        self._log("wait_for_postgresql_result(...)", result)
        return result

    def fetch_api_calls_window(self, device_id: str, msg_id: int, minutes_before: int = 30,
                                minutes_after: int = 30, poll: bool = False,
                                timeout: int = 120, interval: int = 10) -> Dict[str, Any]:
        """Fetch ndrequest_audit_log rows (DB_CONFIG_2) for a device/msg_id in a time window."""
        result = db_utils.fetch_api_calls_window(
            device_id, msg_id, minutes_before, minutes_after, poll, timeout, interval
        )
        self._log(f"fetch_api_calls_window({device_id}, msg_id={msg_id})", result)
        return result
