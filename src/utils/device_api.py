"""
device_api.py — Single source of truth for the DeviceTest public API.

When you add a new method to DeviceTest (device_test.py), add it here too.
This registry exists so anything that needs to know the full DeviceTest
surface (docs, future tooling) has one place to read it from, instead of
re-deriving it from device_test.py by hand.
"""

from __future__ import annotations

# ── Registry ───────────────────────────────────────────────────────────
#
# Key   = method or property name on DeviceTest
# Value = dict with:
#   "signature"   — call signature shown to callers (omit for properties)
#   "returns"     — return type string
#   "description" — one-line description

DEVICE_API: dict[str, dict[str, str]] = {
    # ── Properties ─────────────────────────────────────────────────────
    "pod_connection": {
        "returns": "pexpect.spawn",
        "description": "The underlying connected pod session",
    },
    "ota_version": {
        "returns": "str | None",
        "description": "OTA package version detected at init (cached)",
    },
    "variables": {
        "returns": "dict",
        "description": "Shared state across steps within a test",
    },
    "command_log": {
        "returns": "List[dict]",
        "description": "Full log of operations executed through this DeviceTest",
    },

    # ── Core connection operations ───────────────────────────────────────
    "run": {
        "signature": "cmd, directory=None",
        "returns": "str | None",
        "description": "Run a command on the already-connected pod session",
    },
    "check_connected": {
        "signature": "",
        "returns": "bool",
        "description": "Check if the pod session is alive",
    },
    "close": {
        "signature": "",
        "returns": "None",
        "description": "Close the pod connection",
    },

    # ── Log search ─────────────────────────────────────────────────────
    "search_log": {
        "signature": "log_dir, search_term, start_timestamp=None, timeout=60, interval=5",
        "returns": "str | None",
        "description": "Poll device logs for a term after start_timestamp until found or timeout",
    },
    "grep_logs": {
        "signature": 'service, pattern, log_root="/home/ubuntu/.nddevice/log", since_ts=None',
        "returns": "dict",
        "description": "Single-shot (no polling) grep of a service's logs; {status, output, details}",
    },
    "search_log_interval": {
        "signature": "service_name, message, start_time_epoch=None",
        "returns": "dict",
        "description": "Compute intervals between consecutive matching log lines; {status, count, intervals_ms, stats, details}",
    },
    "frequency_based_calls": {
        "signature": "api_pattern, service_name, expected_interval_minutes, cloud_check=False, api_key=None, tolerance_minutes=1",
        "returns": "dict",
        "description": "Check an API call pattern recurs at the expected interval; {status, occurrences, diff_minutes, details}",
    },
    "event_based_api_call": {
        "signature": "api_pattern, service_name, cloud_check=False, api_key=None, max_cloud_delay_ms=40000, cloud_retries=5",
        "returns": "dict",
        "description": "Capture the latest occurrence of a one-shot API call pattern in logs; {status, triggered_time_ms, cloud_delay_ms, details}",
    },

    # ── Device / OTA checks ──────────────────────────────────────────────
    "verify_file_presence": {
        "signature": "directories, patterns",
        "returns": "List[dict]",
        "description": "Count files matching regex patterns per directory",
    },
    "check_file_availability": {
        "signature": "file_path",
        "returns": "dict",
        "description": "Check whether a file exists on the pod; {status, exists, file_name, file_path, details}",
    },
    "get_ota_version": {
        "signature": 'directory="/home/ubuntu/.nddevice"',
        "returns": "str | None",
        "description": "Re-detect the OTA version (use the .ota_version property for the cached value)",
    },
    "check_ota_md5sum": {
        "signature": 'ota_version, directory="/home/ubuntu/.nddevice"',
        "returns": "str",
        "description": "Return the md5sum of the given OTA package (raises AssertionError on parse failure)",
    },
    "check_no_legacy_package_exists": {
        "signature": 'ota_version, directory="/home/ubuntu/.nddevice"',
        "returns": "bool",
        "description": "Assert only the given OTA package exists in directory (raises AssertionError otherwise)",
    },
    "list_log_folder_contents": {
        "signature": 'directory="/data/nd_files/log"',
        "returns": "str | None",
        "description": "List the contents of a log folder on the pod",
    },
    "validate_services_uptime_diff": {
        "signature": 'directory="/home/ubuntu/.nddevice/latest/service", max_diff_seconds=5',
        "returns": "None",
        "description": "Assert all running services' uptimes are within max_diff_seconds of each other (raises AssertionError)",
    },
    "check_private_key_markers": {
        "signature": 'directory="/home/ubuntu/.nddevice/certificate"',
        "returns": "Dict[str, bool]",
        "description": "Check cert/key files contain the PRIVATE marker",
    },
    "is_service_active": {
        "signature": 'service_name, directory="/home/ubuntu/.nddevice/latest/service"',
        "returns": "dict",
        "description": "Check whether a supervisor-managed service is RUNNING; {status, service, state, details}",
    },
    "restart_service": {
        "signature": 'service_name, directory="/home/ubuntu/.nddevice/latest/service"',
        "returns": "dict",
        "description": "Restart a supervisor-managed service via supervisorctl; {status, service, output, details}",
    },
    "get_service_pid": {
        "signature": 'service_name, directory="/home/ubuntu/.nddevice/latest/service"',
        "returns": "dict",
        "description": "Get a service's PID directly from supervisorctl status (more reliable than pidof when the process name differs from the service name); {status, service, pid, details}",
    },
    "get_device_info": {
        "signature": 'deviceconfig_path="/home/ubuntu/config/deviceconfig.ini"',
        "returns": "dict",
        "description": "Retrieve device_type, device_id, ota_version from the pod; {status, device_type, device_id, ota_version, details}",
    },

    # ── Voyager host operations ──────────────────────────────────────────
    "reboot_voyager": {
        "signature": "",
        "returns": "None",
        "description": "Reboot the voyager host and wait for it to come back online",
    },
    "run_on_voyager": {
        "signature": 'cmd="ls -l", directory=None, ip_address=voyager_ip, username="voyager", password="voyager"',
        "returns": "str | None",
        "description": "Run a one-off command directly on the voyager host (not the pod)",
    },

    # ── Time / size helpers (pure utilities, no pod I/O) ──────────────────
    "get_current_time_utc": {
        "signature": "",
        "returns": "dict",
        "description": "Current UTC time; {status, utc_time, details}",
    },
    "get_current_time_epoch": {
        "signature": "",
        "returns": "dict",
        "description": "Current UTC epoch time; {status, epoch_ms, epoch_seconds, details}",
    },
    "compare_time_difference_hms": {
        "signature": "timestamp1, expected_difference_minutes, timestamp2",
        "returns": "dict",
        "description": "Compare two timestamps; {status, difference_minutes, within_expected, details}",
    },
    "validate_size_range": {
        "signature": "min_size, size, max_size, inclusive=True",
        "returns": "dict",
        "description": "Check size lies within [min_size, max_size]; {status, size, min_size, max_size, details}",
    },

    # ── Cloud API (IDMS) ─────────────────────────────────────────────────
    "aws_ping_command": {
        "signature": "user_id, ping_command",
        "returns": "tuple[str, bool]",
        "description": "Send an AWS IoT ping command (e.g. 'keep-alive', 'reboot-phone') to the device",
    },

    # ── Database (Postgres) ──────────────────────────────────────────────
    "wait_for_postgresql_result": {
        "signature": "query, params=(), timeout=300, interval=10",
        "returns": "list | None",
        "description": "Poll a Postgres query (DB_CONFIG) until it returns rows or times out",
    },
    "fetch_api_calls_window": {
        "signature": "device_id, msg_id, minutes_before=30, minutes_after=30, poll=False, timeout=120, interval=10",
        "returns": "dict",
        "description": "Fetch ndrequest_audit_log rows (DB_CONFIG_2) for a device/msg_id in a time window; {status, count, start_time, end_time, rows, details}",
    },
}
