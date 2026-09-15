"""Mapping of test functions to functionality groups per test module/folder.

Each module key (matched against the test's file path, see
get_functionality_group_from_nodeid below) maps to a dict of
{functionality_group: [test function name suffixes]}. Suffixes are matched
against the trailing part of the test function name — usually the itnNNNN
ticket id, e.g. "itn2446" from "test_ini_fields_present_itn2446" — so this
map stays valid even if the descriptive part of a test name changes.

Scaled down from the pytest_device_validator reference's functionality_map.py
(thousands of TC IDs across many services) to this repo's actual size: ~26
tests across test_sanity_functions.py plus one-test-per-folder service checks
(src/tests/btfv/, src/tests/power_monitor/). Extend this by hand as new tests
are added — nothing enforces it automatically, same convention as
device_api.py (see fleetedge_automation_exploration.md — DEVICETEST FACADE).
"""

FUNCTIONALITY_MAP = {
    "test_sanity_functions": {
        "Connectivity & Config": [
            "itn2426",  # test_connection_success
            "itn2427",  # test_data_disk_usage
            "itn2446",  # test_ini_fields_present
        ],
        "Service Status": [
            "itn2429",  # test_expected_services_running
            "itn2470",  # test_service_uptime
        ],
        "User Alert & Video Upload": [
            "itn2432",  # test_gen_useralert_and_video_upload
            "itn2630",  # test_size_of_outward_mp4_file_after_alert_is_greter_than_44MB
            "itn2631",  # test_size_of_inward_mp4_file_after_alert_is_with_14MB_and_15MB
        ],
        "Video File Checks": [
            "itn2469",  # test_inward_video_file_encryption
            "itn2637",  # test_outward_video_file_encryption
            "itn2455",  # test_size_of_outward_mp4_file_before_alert_is_8bytes
            "itn2629",  # test_size_of_inward_mp4_file_before_alert_is_8bytes
            "itn2468",  # test_video_encryption_config
            "itn2428",  # test_mp4_files_present
            "itn2454",  # test_gps_mp4_file_metadata
            "itn2617",  # test_partial_files_uploaded_to_cloud
        ],
        "OTA & Logs": [
            "itn2430",  # test_ota_md5sum_and_check_no_legacy_package_exists
            "itn2459",  # test_list_log_folder_contents
            "itn2457",  # test_summary_json_files_generated
        ],
        "Cloud API Calls": [
            "itn2642",  # test_api_call_upload_device_status
            "itn2639",  # test_api_call_upload_keep_alive
            "itn2633",  # test_api_call_version_check
            "itn2638",  # test_api_call_upload_observation
            "itn2634",  # test_api_call_upload_videolist
            "itn2640",  # test_api_call_upload_logs
            "itn2660",  # test_aws_ping_keepalive_command
            "itn2661",  # test_aws_ping_reboot_command
        ],
    },

    "btfv": {
        "Service Status": [
            "test_btfv_service_status",
        ],
    },

    "power_monitor": {
        "Service Status": [
            "test_power_monitor_service_status",
        ],
    },
}


def get_functionality_group(module_key: str, test_id: str) -> str:
    """Return the functionality group for a given module and test id.

    module_key: the test module's stem, e.g. "test_sanity_functions", "btfv".
    test_id: full test function name, e.g. "test_ini_fields_present_itn2446".
    Returns "Other" if no mapping is found.
    """
    module_map = FUNCTIONALITY_MAP.get(module_key, {})
    for group, suffixes in module_map.items():
        for suffix in suffixes:
            if test_id.endswith(suffix) or test_id == suffix:
                return group
    return "Other"


def get_functionality_group_from_nodeid(nodeid: str, test_id: str) -> str:
    """Extract the module key from a pytest nodeid and return its functionality group.

    Tries the parent folder name first (e.g. "btfv" for
    "src/tests/btfv/test_btfv_service_status.py") since that's how
    per-service subfolders are keyed in FUNCTIONALITY_MAP, then falls back
    to the file stem (e.g. "test_sanity_functions") for test files that
    live directly under src/tests/ with no dedicated subfolder.

    nodeid: e.g. "src/tests/btfv/test_btfv_service_status.py::test_btfv_service_status".
    test_id: e.g. "test_btfv_service_status".
    """
    path_part = nodeid.split("::")[0].replace("\\", "/")
    segments = path_part.split("/")
    file_stem = segments[-1].removesuffix(".py")
    parent_folder = segments[-2] if len(segments) >= 2 else None

    if parent_folder and parent_folder in FUNCTIONALITY_MAP:
        group = get_functionality_group(parent_folder, test_id)
        if group != "Other":
            return group

    return get_functionality_group(file_stem, test_id)
