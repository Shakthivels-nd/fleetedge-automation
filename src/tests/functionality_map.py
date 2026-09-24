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

    "unifiedAnalyticsClient": {
        "Startup & Thread Liveness": ["test_step"],
    },

    # ─── OTACHECK ─────────────────────────────────────────────────────
    # Keyed by file stem (like SERVICEMONITOR below), not the "otacheck"
    # folder, since more otacheck test files are expected here with their
    # own test_stepN_... naming — a shared folder key would collide the
    # same way servicemonitor's files would.
    "test_otacheck_version_check_multiples_of_10": {
        "Version Check API": ["test_step"],
    },
    "test_otacheck_counter_increment": {
        "Counter Behavior": ["test_step"],
    },
    "test_otacheck_override_configs_download": {
        "Configuration": ["test_step"],
    },
    "test_otacheck_current_version_logged": {
        "Version Check API": ["test_step"],
    },
    "test_otacheck_sleep_based_on_device_id_modulo": {
        "Scheduling & Timing": ["test_step"],
    },
    "test_otacheck_rtc_time_not_in_sync": {
        "Scheduling & Timing": ["test_step"],
    },

    # ─── SERVICEMONITOR ───────────────────────────────────────────────
    # Each file under src/tests/servicemonitor/ uses the same step names
    # (test_step1_..., test_step2_..., etc.) across every service, so they
    # can't be told apart by test name alone within a shared "servicemonitor"
    # key — _resolve_module_key() falls back to the file stem in that case,
    # so each service gets its own entry here keyed by its file's stem.
    "test_bagheera_status_check": {
        "Service Monitor — bagheera": ["test_step"],
    },
    "test_svc_status_check": {
        "Service Monitor — svc": ["test_step"],
    },
    "test_awsiot_status_check": {
        "Service Monitor — awsiot": ["test_step"],
    },
    "test_circular_buffer_status_check": {
        "Service Monitor — circular_buffer": ["test_step"],
    },
    "test_power_monitor_status_check": {
        "Service Monitor — power_monitor": ["test_step"],
    },
    "test_scheduler_manager_status_check": {
        "Service Monitor — scheduler_manager": ["test_step"],
    },
    "test_speed_status_check": {
        "Service Monitor — speed": ["test_step"],
    },
    "test_time_sync_status_check": {
        "Service Monitor — time_sync": ["test_step"],
    },
    "test_uploader_status_check": {
        "Service Monitor — uploader": ["test_step"],
    },
    "test_outward_analytics_client_status_check": {
        "Service Monitor — outwardAnalyticsClient": ["test_step"],
    },
    "test_analytics_service_status_check": {
        "Service Monitor — analyticsService": ["test_step"],
    },
    "test_healthstatsmanager_status_check": {
        "Service Monitor — HealthStatsManager": ["test_step"],
    },
    "test_sendmetricgrpc_status_check": {
        "Service Monitor — SendMetricgRPC": ["test_step"],
    },
    "test_audio_playback_status_check": {
        "Service Monitor — audioPlayback": ["test_step"],
    },
    "test_inward_analytics_client_status_check": {
        "Service Monitor — inwardAnalyticsClient": ["test_step"],
    },
    "test_nd_fe_alerts_status_check": {
        "Service Monitor — nd_fe_alerts": ["test_step"],
    },
    "test_nd_suspendresume_status_check": {
        "Service Monitor — nd_suspendresume": ["test_step"],
    },
    "test_nd_system_status_status_check": {
        "Service Monitor — nd_system_status": ["test_step"],
    },
    "test_podlogger_status_check": {
        "Service Monitor — podlogger": ["test_step"],
    },
    "test_unified_analytics_client_status_check": {
        "Service Monitor — unifiedAnalyticsClient": ["test_step"],
    },
}


# Display name for each module key used above — shown as the "Service"
# column in the Coverage tab. Keep in sync with FUNCTIONALITY_MAP's keys.
SERVICE_DISPLAY_NAMES = {
    "test_sanity_functions": "Sanity",
    "btfv": "BTFV",
    "power_monitor": "Power Monitor",
    "unifiedAnalyticsClient": "unifiedAnalyticsClient",
    "test_otacheck_version_check_multiples_of_10": "otacheck",
    "test_otacheck_counter_increment": "otacheck",
    "test_otacheck_override_configs_download": "otacheck",
    "test_otacheck_current_version_logged": "otacheck",
    "test_otacheck_sleep_based_on_device_id_modulo": "otacheck",
    "test_otacheck_rtc_time_not_in_sync": "otacheck",
    "test_bagheera_status_check": "Service Monitor",
    "test_svc_status_check": "Service Monitor",
    "test_awsiot_status_check": "Service Monitor",
    "test_circular_buffer_status_check": "Service Monitor",
    "test_power_monitor_status_check": "Service Monitor",
    "test_scheduler_manager_status_check": "Service Monitor",
    "test_speed_status_check": "Service Monitor",
    "test_time_sync_status_check": "Service Monitor",
    "test_uploader_status_check": "Service Monitor",
    "test_outward_analytics_client_status_check": "Service Monitor",
    "test_analytics_service_status_check": "Service Monitor",
    "test_healthstatsmanager_status_check": "Service Monitor",
    "test_sendmetricgrpc_status_check": "Service Monitor",
    "test_audio_playback_status_check": "Service Monitor",
    "test_inward_analytics_client_status_check": "Service Monitor",
    "test_nd_fe_alerts_status_check": "Service Monitor",
    "test_nd_suspendresume_status_check": "Service Monitor",
    "test_nd_system_status_status_check": "Service Monitor",
    "test_podlogger_status_check": "Service Monitor",
    "test_unified_analytics_client_status_check": "Service Monitor",
}


def get_functionality_group(module_key: str, test_id: str) -> str:
    """Return the functionality group for a given module and test id.

    module_key: the test module's stem, e.g. "test_sanity_functions", "btfv".
    test_id: full test function name, e.g. "test_ini_fields_present_itn2446".
    A suffix is usually an itnNNNN ticket id (matched via endswith), but a
    plain prefix like "test_step" also works (matched via startswith) for
    modules where every test shares the same step-numbered naming, e.g.
    src/tests/servicemonitor/*_status_check.py.
    Returns "Other" if no mapping is found.
    """
    module_map = FUNCTIONALITY_MAP.get(module_key, {})
    for group, suffixes in module_map.items():
        for suffix in suffixes:
            if test_id.endswith(suffix) or test_id.startswith(suffix) or test_id == suffix:
                return group
    return "Other"


def _resolve_module_key(nodeid: str, test_id: str) -> str:
    """Return the FUNCTIONALITY_MAP key that actually matches this test.

    Tries the parent folder name first (e.g. "btfv" for
    "src/tests/btfv/test_btfv_service_status.py") since that's how
    per-service subfolders are keyed in FUNCTIONALITY_MAP, then falls back
    to the file stem (e.g. "test_sanity_functions") for test files that
    live directly under src/tests/ with no dedicated subfolder. Returns
    the file stem if neither maps a group for this test (i.e. it'll show
    up as "Other" downstream), so there's always a stable module key.
    """
    path_part = nodeid.split("::")[0].replace("\\", "/")
    segments = path_part.split("/")
    file_stem = segments[-1].removesuffix(".py")
    parent_folder = segments[-2] if len(segments) >= 2 else None

    if parent_folder and parent_folder in FUNCTIONALITY_MAP:
        if get_functionality_group(parent_folder, test_id) != "Other":
            return parent_folder

    return file_stem


def get_functionality_group_from_nodeid(nodeid: str, test_id: str) -> str:
    """Extract the module key from a pytest nodeid and return its functionality group.

    nodeid: e.g. "src/tests/btfv/test_btfv_service_status.py::test_btfv_service_status".
    test_id: e.g. "test_btfv_service_status".
    """
    module_key = _resolve_module_key(nodeid, test_id)
    return get_functionality_group(module_key, test_id)


def get_service_from_nodeid(nodeid: str, test_id: str) -> str:
    """Return the display-friendly service name for a test (Coverage tab's Service column).

    Falls back to the raw module key (e.g. an unmapped file stem) if no
    display name is registered for it in SERVICE_DISPLAY_NAMES.
    """
    module_key = _resolve_module_key(nodeid, test_id)
    return SERVICE_DISPLAY_NAMES.get(module_key, module_key)
