"""
Backwards-compatible re-export shim.

pod_utils.py used to contain every helper in this framework (connection,
log search, device/OTA checks, time/size helpers, cloud API, DB queries) in
one ~1400-line file. It has been split into focused modules under
src/utils/engine/ (connection.py, log_search.py, device_checks.py,
time_utils.py, cloud_api.py, db_utils.py). This module re-exports everything
from those so any `from src.utils.engine.pod_utils import X` import keeps
working unchanged.

Prefer importing from the specific module directly in new code (e.g.
`from src.utils.engine.connection import run_command_on_pod`), or better
yet, calling through the DeviceTest facade (src/utils/device_test.py).
"""

from dotenv import load_dotenv

load_dotenv()

from .connection import (
    voyager_ip,
    connect_to_pod,
    run_command_on_voyager,
    run_command_on_pod,
    reboot_voyager,
    wait_for_ping,
    close_pod_connection,
    clean_output,
)
from .log_search import (
    UTC_TIMESTAMP_SERVICES,
    search_logs_in_pod,
    grep_logs,
    search_log_interval,
    frequency_based_calls,
    event_based_api_call,
)
from .device_checks import (
    verify_file_presence,
    check_ota_md5sum,
    check_no_legacy_package_exists,
    list_log_folder_contents,
    validate_services_uptime_diff,
    check_private_key_markers,
    get_ota_version,
    check_file_availability,
    get_device_info,
)
from .time_utils import (
    validate_size_range,
    get_current_time_utc,
    get_current_time_epoch,
    compare_time_difference_hms,
)
from .cloud_api import (
    login_api,
    aws_ping_command,
)
from .db_utils import (
    DB_CONFIG,
    DB_CONFIG_2,
    run_postgresql_query,
    wait_for_postgresql_result,
    fetch_api_calls_window,
)

__all__ = [
    "voyager_ip",
    "connect_to_pod",
    "run_command_on_voyager",
    "run_command_on_pod",
    "reboot_voyager",
    "wait_for_ping",
    "close_pod_connection",
    "clean_output",
    "UTC_TIMESTAMP_SERVICES",
    "search_logs_in_pod",
    "grep_logs",
    "search_log_interval",
    "frequency_based_calls",
    "event_based_api_call",
    "verify_file_presence",
    "check_ota_md5sum",
    "check_no_legacy_package_exists",
    "list_log_folder_contents",
    "validate_services_uptime_diff",
    "check_private_key_markers",
    "get_ota_version",
    "check_file_availability",
    "get_device_info",
    "validate_size_range",
    "get_current_time_utc",
    "get_current_time_epoch",
    "compare_time_difference_hms",
    "login_api",
    "aws_ping_command",
    "DB_CONFIG",
    "DB_CONFIG_2",
    "run_postgresql_query",
    "wait_for_postgresql_result",
    "fetch_api_calls_window",
]


if __name__ == "__main__":
    # Connect to pod
    # child = connect_to_pod("172.16.22.119")

    # #  Run multiple commands
    # run_command_on_pod(child, "./gen_ualert.sh", "/home/ubuntu/.nddevice/latest/service/bagheera")

    # # disk usage
    # run_command_on_pod(child, "du -sh /data")

    # # Close connection
    # close_pod_connection(child)
    aws_ping_command("8430", "reboot-phone")
