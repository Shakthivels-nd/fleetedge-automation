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

    # ─── AWSIOT ───────────────────────────────────────────────────────
    # Each file under src/tests/awsiot/ uses the same test_stepN_... naming
    # scheme (see live_report.py's STEP_NAME_PATTERN grouping), so — same
    # reasoning as SERVICEMONITOR above — they're keyed individually by
    # file stem rather than a shared "awsiot" folder key.
    "test_awsiot_ping_keepalive_reboot": {
        "Ping & Reboot": ["test_step"],
    },
    "test_awsiot_ping_request_reboot_phone": {
        "Ping & Reboot": ["test_step"],
    },
    "test_awsiot_reboot_request_to_powermon": {
        "Ping & Reboot": ["test_step"],
    },
    "test_awsiot_api_call_versioncheck": {
        "Ping & Reboot": ["test_step"],
    },
    "test_awsiot_verify_connection_ignition_high": {
        "Connection & Server": ["test_step"],
    },
    "test_awsiot_verify_connection_no_network": {
        "Connection & Server": ["test_step"],
    },
    "test_awsiot_server_connected_or_not": {
        "Connection & Server": ["test_step"],
    },
    "test_awsiot_verify_server_address": {
        "Connection & Server": ["test_step"],
    },
    "test_awsiot_verify_logging": {
        "Connection & Server": ["test_step"],
    },
    "test_awsiot_check_private_key": {
        "Certificates & Keys": ["test_step"],
    },
    "test_awsiot_check_public_key": {
        "Certificates & Keys": ["test_step"],
    },
    "test_awsiot_check_certificates": {
        "Certificates & Keys": ["test_step"],
    },
    "test_awsiot_check_encryption_and_permission_of_private_keys": {
        "Certificates & Keys": ["test_step"],
    },
    "test_awsiot_verify_ka_certificate_check": {
        "Certificates & Keys": ["test_step"],
    },
    "test_awsiot_verify_iot_priv_key_decryption_before_connect": {
        "Certificates & Keys": ["test_step"],
    },
    # test_awsiot_verify_private_awsiot_key_encryption_on_regeneration,
    # test_awsiot_verify_private_jwt_key_encryption_on_regeneration,
    # test_awsiot_verify_backup_corruption_handling,
    # test_awsiot_service_exiting_when_bad_certificates_found,
    # test_awsiot_critical_info_certificates_corrupted, and
    # test_awsiot_jwt_registration_when_corrupted were removed -- cert/key
    # corruption tests leave the device degraded until self-heal, and FE
    # has a known issue that makes this category not applicable. See
    # PORT_TRACKER.csv for the skip reasons (known_issue_cert_corruption).
    "test_awsiot_eventdata_api_call": {
        "Event Data & Upload": ["test_step"],
    },
    "test_awsiot_eventdata_api_response": {
        "Event Data & Upload": ["test_step"],
    },
    "test_awsiot_receive_video_request": {
        "Event Data & Upload": ["test_step"],
    },
    "test_awsiot_send_request_to_uploader": {
        "Event Data & Upload": ["test_step"],
    },
    "test_awsiot_state_change_to_upload_state": {
        "Event Data & Upload": ["test_step"],
    },
    "test_awsiot_verify_payload": {
        "Shadow Payload": ["test_step"],
    },
    "test_awsiot_service_status_check": {
        "Service Health": ["test_step"],
    },
    "test_awsiot_service_stability": {
        "Service Health": ["test_step"],
    },
    "test_awsiot_msgq_creation": {
        "Service Health": ["test_step"],
    },
    "test_awsiot_check_binary_and_permissions": {
        "Service Health": ["test_step"],
    },
    "test_awsiot_override_parse_check": {
        "Configuration": ["test_step"],
    },
    "test_awsiot_verify_vehicle_class": {
        "Configuration": ["test_step"],
    },
    "test_awsiot_verify_publish_enabled": {
        "Configuration": ["test_step"],
    },
    "test_awsiot_verify_gps_publish_frequency": {
        "Configuration": ["test_step"],
    },
    "test_awsiot_all_cameras_enabled": {
        "Configuration": ["test_step"],
    },

    # ─── SCHEDULER ────────────────────────────────────────────────────
    "test_scheduler_msgq_creation_related_services": {
        "Msgq Creation": ["test_step"],
    },
    "test_scheduler_runs_wrapper_scheduler_every_min": {
        "Scheduling Cadence": ["test_step"],
    },
    "test_scheduler_file_pileup": {
        "Input/Output Handling": ["test_step"],
    },
    "test_scheduler_enters_file_valid_input_set": {
        "Input/Output Handling": ["test_step"],
    },
    "test_scheduler_deletes_file_invalid_input_set": {
        "Input/Output Handling": ["test_step"],
    },
    "test_scheduler_ndcentral_triggers_scheduler_manager": {
        "Triggering": ["test_step"],
    },
    "test_scheduler_manager_triggers_scheduler": {
        "Triggering": ["test_step"],
    },
    "test_scheduler_ndcentral_fails_to_trigger_scheduler": {
        "Triggering": ["test_step"],
    },
    "test_scheduler_file_state_not_dnd_no_alerts": {
        "Inertial Processing": ["test_step"],
    },
    "test_scheduler_complete_file_operation": {
        "Input/Output Handling": ["test_step"],
    },
    "test_scheduler_inertial_starts_processing_with_valid_parameters": {
        "Inertial Processing": ["test_step"],
    },
    "test_scheduler_completion_inertial_obs": {
        "Inertial Processing": ["test_step"],
    },
    "test_scheduler_detailed_copy_obs_generation": {
        "Inertial Processing": ["test_step"],
    },
    "test_scheduler_check_movement_of_hdfile_inertial_observation": {
        "Inertial Processing": ["test_step"],
    },
    "test_scheduler_inference_move_file_delete_state": {
        "Inference State Machine": ["test_step"],
    },
    "test_scheduler_inference_move_file_upload_state": {
        "Inference State Machine": ["test_step"],
    },
    "test_scheduler_inference_calls_deleter_delete_state": {
        "Inference State Machine": ["test_step"],
    },
    "test_scheduler_inference_calls_uploader_upload_state": {
        "Inference State Machine": ["test_step"],
    },
    "test_scheduler_state_modified_vision_running_state": {
        "Inference State Machine": ["test_step"],
    },
    "test_scheduler_inference_run_metadata_summary": {
        "Vision Inference": ["test_step"],
    },
    "test_scheduler_starts_outward_nrt_with_valid_parameters": {
        "Vision Inference": ["test_step"],
    },
    "test_scheduler_starts_inward_nrt_with_valid_parameters": {
        "Vision Inference": ["test_step"],
    },
    "test_scheduler_session_nrt_completion_status": {
        "Vision Inference": ["test_step"],
    },
    "test_scheduler_analysis_result_outward_inward_nrt": {
        "Vision Inference": ["test_step"],
    },
    "test_scheduler_inference_updates_collated_alerts": {
        "Inference State Machine": ["test_step"],
    },
    "test_scheduler_uploader_modifies_state_job_submit_state": {
        "Uploader Workflow": ["test_step"],
    },
    "test_scheduler_uploader_engine_workflow": {
        "Uploader Workflow": ["test_step"],
    },
    "test_scheduler_latency_check_without_alert": {
        "Latency": ["test_step"],
    },
    "test_scheduler_latency_check_incase_alert": {
        "Latency": ["test_step"],
    },
    "test_scheduler_deleter_checks_delete_state": {
        "Inference State Machine": ["test_step"],
    },
    "test_scheduler_deleters_deletes_nd_output_nd_input_files": {
        "Deleter": ["test_step"],
    },
    "test_scheduler_deletes_all_file_previous_session": {
        "Deleter": ["test_step"],
    },
    "test_scheduler_processed_file_written_to_disk": {
        "Input/Output Handling": ["test_step"],
    },
    "test_scheduler_file_locking_behaviour": {
        "Input/Output Handling": ["test_step"],
    },
    "test_scheduler_wrapper_otacheck_crontab": {
        "Crontab": ["test_step"],
    },
    "test_scheduler_wrapper_cleanupstate_crontab": {
        "Crontab": ["test_step"],
    },
    "test_scheduler_wrapper_scheduler_removed_from_user_crontab": {
        "Crontab": ["test_step"],
    },
    "test_scheduler_wrapper_otacheck_removed_user_crontab": {
        "Crontab": ["test_step"],
    },
    "test_scheduler_folder_permission_nd_output": {
        "Input/Output Handling": ["test_step"],
    },
    "test_scheduler_deletes_folder_root_permission_in_ndoutput": {
        "Deleter": ["test_step"],
    },
    "test_scheduler_state_files_new_session": {
        "Input/Output Handling": ["test_step"],
    },
    "test_scheduler_deletes_multiple_files": {
        "Deleter": ["test_step"],
    },
    "test_scheduler_healthstats_network_info": {
        "HealthStats": ["test_step"],
    },
    "test_scheduler_healthstats_signal_info": {
        "HealthStats": ["test_step"],
    },
    "test_scheduler_ndcentral_recording_start_end_to_hs": {
        "HealthStats": ["test_step"],
    },
    "test_scheduler_ndcentral_partial_file_recording_start_end_to_hs": {
        "HealthStats": ["test_step"],
    },
    "test_scheduler_fields_updated_each_session_in_hs": {
        "HealthStats": ["test_step"],
    },
    "test_scheduler_no_traceback": {
        "Reliability": ["test_step"],
    },
    "test_scheduler_logs_writing_and_logs_uploading": {
        "Logging": ["test_step"],
    },
    "test_scheduler_log_format_related_files": {
        "Logging": ["test_step"],
    },
    "test_scheduler_partial_file_process_linux_sign_crash": {
        "Reliability": ["test_step"],
    },
    "test_scheduler_queue_overflow_more_files_run_state": {
        "Queue Overflow": ["test_step"],
    },
    "test_scheduler_oldest_file_dropped_first_queue_overflow": {
        "Queue Overflow": ["test_step"],
    },
    "test_scheduler_queue_every_min": {
        "Queue Overflow": ["test_step"],
    },
    "test_scheduler_not_crashing_during_queue_overflow": {
        "Queue Overflow": ["test_step"],
    },
    "test_scheduler_no_attribute_error": {
        "Reliability": ["test_step"],
    },
    "test_scheduler_partial_file_process_backtoback_restart_bagheera": {
        "Reliability": ["test_step"],
    },
    "test_scheduler_no_pileup_deleter": {
        "Deleter": ["test_step"],
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
    "test_awsiot_ping_keepalive_reboot": "AWSIOT",
    "test_awsiot_ping_request_reboot_phone": "AWSIOT",
    "test_awsiot_reboot_request_to_powermon": "AWSIOT",
    "test_awsiot_api_call_versioncheck": "AWSIOT",
    "test_awsiot_verify_connection_ignition_high": "AWSIOT",
    "test_awsiot_verify_connection_no_network": "AWSIOT",
    "test_awsiot_server_connected_or_not": "AWSIOT",
    "test_awsiot_verify_server_address": "AWSIOT",
    "test_awsiot_verify_logging": "AWSIOT",
    "test_awsiot_check_private_key": "AWSIOT",
    "test_awsiot_check_public_key": "AWSIOT",
    "test_awsiot_check_certificates": "AWSIOT",
    "test_awsiot_check_encryption_and_permission_of_private_keys": "AWSIOT",
    "test_awsiot_verify_ka_certificate_check": "AWSIOT",
    "test_awsiot_verify_iot_priv_key_decryption_before_connect": "AWSIOT",
    "test_awsiot_eventdata_api_call": "AWSIOT",
    "test_awsiot_eventdata_api_response": "AWSIOT",
    "test_awsiot_receive_video_request": "AWSIOT",
    "test_awsiot_send_request_to_uploader": "AWSIOT",
    "test_awsiot_state_change_to_upload_state": "AWSIOT",
    "test_awsiot_verify_payload": "AWSIOT",
    "test_awsiot_service_status_check": "AWSIOT",
    "test_awsiot_service_stability": "AWSIOT",
    "test_awsiot_msgq_creation": "AWSIOT",
    "test_awsiot_check_binary_and_permissions": "AWSIOT",
    "test_awsiot_override_parse_check": "AWSIOT",
    "test_awsiot_verify_vehicle_class": "AWSIOT",
    "test_awsiot_verify_publish_enabled": "AWSIOT",
    "test_awsiot_verify_gps_publish_frequency": "AWSIOT",
    "test_awsiot_all_cameras_enabled": "AWSIOT",
    "test_scheduler_msgq_creation_related_services": "SCHEDULER",
    "test_scheduler_runs_wrapper_scheduler_every_min": "SCHEDULER",
    "test_scheduler_file_pileup": "SCHEDULER",
    "test_scheduler_enters_file_valid_input_set": "SCHEDULER",
    "test_scheduler_deletes_file_invalid_input_set": "SCHEDULER",
    "test_scheduler_ndcentral_triggers_scheduler_manager": "SCHEDULER",
    "test_scheduler_manager_triggers_scheduler": "SCHEDULER",
    "test_scheduler_ndcentral_fails_to_trigger_scheduler": "SCHEDULER",
    "test_scheduler_file_state_not_dnd_no_alerts": "SCHEDULER",
    "test_scheduler_complete_file_operation": "SCHEDULER",
    "test_scheduler_inertial_starts_processing_with_valid_parameters": "SCHEDULER",
    "test_scheduler_completion_inertial_obs": "SCHEDULER",
    "test_scheduler_detailed_copy_obs_generation": "SCHEDULER",
    "test_scheduler_check_movement_of_hdfile_inertial_observation": "SCHEDULER",
    "test_scheduler_inference_move_file_delete_state": "SCHEDULER",
    "test_scheduler_inference_move_file_upload_state": "SCHEDULER",
    "test_scheduler_inference_calls_deleter_delete_state": "SCHEDULER",
    "test_scheduler_inference_calls_uploader_upload_state": "SCHEDULER",
    "test_scheduler_state_modified_vision_running_state": "SCHEDULER",
    "test_scheduler_inference_run_metadata_summary": "SCHEDULER",
    "test_scheduler_starts_outward_nrt_with_valid_parameters": "SCHEDULER",
    "test_scheduler_starts_inward_nrt_with_valid_parameters": "SCHEDULER",
    "test_scheduler_session_nrt_completion_status": "SCHEDULER",
    "test_scheduler_analysis_result_outward_inward_nrt": "SCHEDULER",
    "test_scheduler_inference_updates_collated_alerts": "SCHEDULER",
    "test_scheduler_uploader_modifies_state_job_submit_state": "SCHEDULER",
    "test_scheduler_uploader_engine_workflow": "SCHEDULER",
    "test_scheduler_latency_check_without_alert": "SCHEDULER",
    "test_scheduler_latency_check_incase_alert": "SCHEDULER",
    "test_scheduler_deleter_checks_delete_state": "SCHEDULER",
    "test_scheduler_deleters_deletes_nd_output_nd_input_files": "SCHEDULER",
    "test_scheduler_deletes_all_file_previous_session": "SCHEDULER",
    "test_scheduler_processed_file_written_to_disk": "SCHEDULER",
    "test_scheduler_file_locking_behaviour": "SCHEDULER",
    "test_scheduler_wrapper_otacheck_crontab": "SCHEDULER",
    "test_scheduler_wrapper_cleanupstate_crontab": "SCHEDULER",
    "test_scheduler_wrapper_scheduler_removed_from_user_crontab": "SCHEDULER",
    "test_scheduler_wrapper_otacheck_removed_user_crontab": "SCHEDULER",
    "test_scheduler_folder_permission_nd_output": "SCHEDULER",
    "test_scheduler_deletes_folder_root_permission_in_ndoutput": "SCHEDULER",
    "test_scheduler_state_files_new_session": "SCHEDULER",
    "test_scheduler_deletes_multiple_files": "SCHEDULER",
    "test_scheduler_healthstats_network_info": "SCHEDULER",
    "test_scheduler_healthstats_signal_info": "SCHEDULER",
    "test_scheduler_ndcentral_recording_start_end_to_hs": "SCHEDULER",
    "test_scheduler_ndcentral_partial_file_recording_start_end_to_hs": "SCHEDULER",
    "test_scheduler_fields_updated_each_session_in_hs": "SCHEDULER",
    "test_scheduler_no_traceback": "SCHEDULER",
    "test_scheduler_logs_writing_and_logs_uploading": "SCHEDULER",
    "test_scheduler_log_format_related_files": "SCHEDULER",
    "test_scheduler_partial_file_process_linux_sign_crash": "SCHEDULER",
    "test_scheduler_queue_overflow_more_files_run_state": "SCHEDULER",
    "test_scheduler_oldest_file_dropped_first_queue_overflow": "SCHEDULER",
    "test_scheduler_queue_every_min": "SCHEDULER",
    "test_scheduler_not_crashing_during_queue_overflow": "SCHEDULER",
    "test_scheduler_no_attribute_error": "SCHEDULER",
    "test_scheduler_partial_file_process_backtoback_restart_bagheera": "SCHEDULER",
    "test_scheduler_no_pileup_deleter": "SCHEDULER",
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
