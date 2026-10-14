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

    # ─── SUPERVISORD ──────────────────────────────────────────────────
    # Keyed by file stem (like OTACHECK/SERVICEMONITOR) since every file
    # under src/tests/supervisord/ uses the shared test_stepN_... naming.
    "test_supervisord_start_up_nd_is_binary": {
        "Startup & PID 1": ["test_step"],
    },
    "test_supervisord_startup_sequence": {
        "Startup & PID 1": ["test_step"],
    },
    "test_supervisord_logs_availability": {
        "Logging & Rotation": ["test_step"],
    },
    "test_supervisord_restart_each_service": {
        "supervisorctl Commands": ["test_step"],
    },
    "test_supervisord_unexpected_service_state": {
        "Startup & PID 1": ["test_step"],
    },
    "test_supervisord_kill_service_and_recover": {
        "Process Group": ["test_step"],
    },
    "test_supervisord_valid_process_group": {
        "Process Group": ["test_step"],
    },
    "test_supervisord_intentional_service_crash": {
        "Auto-restart & Failure": ["test_step"],
    },

    # ─── SERVICEMONITOR ───────────────────────────────────────────────
    # Each file under src/tests/servicemonitor/ uses the same step names
    # (test_step1_..., test_step2_..., etc.) across every service, so they
    # can't be told apart by test name alone within a shared "servicemonitor"
    # key — _resolve_module_key() falls back to the file stem in that case,
    # so each service gets its own entry here keyed by its file's stem.
    "test_bagheera_status_check_itn4654": {
        "Service Monitor — bagheera": ["test_step"],
    },
    "test_svc_status_check_itn4666": {
        "Service Monitor — svc": ["test_step"],
    },
    "test_awsiot_status_check_itn4653": {
        "Service Monitor — awsiot": ["test_step"],
    },
    "test_circular_buffer_status_check_itn4655": {
        "Service Monitor — circular_buffer": ["test_step"],
    },
    "test_power_monitor_status_check_itn4662": {
        "Service Monitor — power_monitor": ["test_step"],
    },
    "test_scheduler_manager_status_check_itn4663": {
        "Service Monitor — scheduler_manager": ["test_step"],
    },
    "test_speed_status_check_itn4665": {
        "Service Monitor — speed": ["test_step"],
    },
    "test_time_sync_status_check_itn4667": {
        "Service Monitor — time_sync": ["test_step"],
    },
    "test_uploader_status_check_itn4669": {
        "Service Monitor — uploader": ["test_step"],
    },
    "test_outward_analytics_client_status_check_itn4660": {
        "Service Monitor — outwardAnalyticsClient": ["test_step"],
    },
    "test_analytics_service_status_check_itn4651": {
        "Service Monitor — analyticsService": ["test_step"],
    },
    "test_healthstatsmanager_status_check_itn4656": {
        "Service Monitor — HealthStatsManager": ["test_step"],
    },
    "test_sendmetricgrpc_status_check_itn4664": {
        "Service Monitor — SendMetricgRPC": ["test_step"],
    },
    "test_audio_playback_status_check_itn4652": {
        "Service Monitor — audioPlayback": ["test_step"],
    },
    "test_inward_analytics_client_status_check_itn4657": {
        "Service Monitor — inwardAnalyticsClient": ["test_step"],
    },
    "test_nd_fe_alerts_status_check_itn4658": {
        "Service Monitor — nd_fe_alerts": ["test_step"],
    },
    "test_nd_suspendresume_status_check": {
        "Service Monitor — nd_suspendresume": ["test_step"],
    },
    "test_nd_system_status_status_check_itn4659": {
        "Service Monitor — nd_system_status": ["test_step"],
    },
    "test_podlogger_status_check_itn4661": {
        "Service Monitor — podlogger": ["test_step"],
    },
    "test_unified_analytics_client_status_check_itn4668": {
        "Service Monitor — unifiedAnalyticsClient": ["test_step"],
    },

    # ─── AWSIOT ───────────────────────────────────────────────────────
    # Each file under src/tests/awsiot/ uses the same test_stepN_... naming
    # scheme (see live_report.py's STEP_NAME_PATTERN grouping), so — same
    # reasoning as SERVICEMONITOR above — they're keyed individually by
    # file stem rather than a shared "awsiot" folder key.
    "test_awsiot_ping_keepalive_reboot_itn4633": {
        "Ping & Reboot": ["test_step"],
    },
    "test_awsiot_ping_request_reboot_phone_itn4634": {
        "Ping & Reboot": ["test_step"],
    },
    "test_awsiot_reboot_request_to_powermon_itn4635": {
        "Ping & Reboot": ["test_step"],
    },
    "test_awsiot_api_call_versioncheck_itn4623": {
        "Ping & Reboot": ["test_step"],
    },
    "test_awsiot_verify_connection_ignition_high_itn4641": {
        "Connection & Server": ["test_step"],
    },
    "test_awsiot_verify_connection_no_network_itn4642": {
        "Connection & Server": ["test_step"],
    },
    "test_awsiot_server_connected_or_not_itn4637": {
        "Connection & Server": ["test_step"],
    },
    "test_awsiot_verify_server_address_itn4621": {
        "Connection & Server": ["test_step"],
    },
    "test_awsiot_verify_logging_itn4646": {
        "Connection & Server": ["test_step"],
    },
    "test_awsiot_check_private_key_itn4627": {
        "Certificates & Keys": ["test_step"],
    },
    "test_awsiot_check_public_key_itn4628": {
        "Certificates & Keys": ["test_step"],
    },
    "test_awsiot_check_certificates_itn4625": {
        "Certificates & Keys": ["test_step"],
    },
    "test_awsiot_check_encryption_and_permission_of_private_keys_itn4626": {
        "Certificates & Keys": ["test_step"],
    },
    "test_awsiot_verify_ka_certificate_check_itn4645": {
        "Certificates & Keys": ["test_step"],
    },
    "test_awsiot_verify_iot_priv_key_decryption_before_connect_itn4644": {
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
    "test_awsiot_eventdata_api_call_itn4629": {
        "Event Data & Upload": ["test_step"],
    },
    "test_awsiot_eventdata_api_response_itn4630": {
        "Event Data & Upload": ["test_step"],
    },
    "test_awsiot_receive_video_request_itn4650": {
        "Event Data & Upload": ["test_step"],
    },
    "test_awsiot_send_request_to_uploader_itn4636": {
        "Event Data & Upload": ["test_step"],
    },
    "test_awsiot_state_change_to_upload_state_itn4640": {
        "Event Data & Upload": ["test_step"],
    },
    "test_awsiot_verify_payload_itn4647": {
        "Shadow Payload": ["test_step"],
    },
    "test_awsiot_service_status_check_itn4639": {
        "Service Health": ["test_step"],
    },
    "test_awsiot_service_stability_itn4638": {
        "Service Health": ["test_step"],
    },
    "test_awsiot_msgq_creation_itn4631": {
        "Service Health": ["test_step"],
    },
    "test_awsiot_check_binary_and_permissions_itn4624": {
        "Service Health": ["test_step"],
    },
    "test_awsiot_override_parse_check_itn4632": {
        "Configuration": ["test_step"],
    },
    "test_awsiot_verify_vehicle_class_itn4649": {
        "Configuration": ["test_step"],
    },
    "test_awsiot_verify_publish_enabled_itn4648": {
        "Configuration": ["test_step"],
    },
    "test_awsiot_verify_gps_publish_frequency_itn4643": {
        "Configuration": ["test_step"],
    },
    "test_awsiot_all_cameras_enabled_itn4622": {
        "Configuration": ["test_step"],
    },

    # ─── SCHEDULER ────────────────────────────────────────────────────
    "test_scheduler_msgq_creation_related_services_itn4709": {
        "Msgq Creation": ["test_step"],
    },
    "test_scheduler_runs_wrapper_scheduler_every_min_itn4725": {
        "Scheduling Cadence": ["test_step"],
    },
    "test_scheduler_file_pileup_itn4688": {
        "Input/Output Handling": ["test_step"],
    },
    "test_scheduler_enters_file_valid_input_set_itn4685": {
        "Input/Output Handling": ["test_step"],
    },
    "test_scheduler_deletes_file_invalid_input_set_itn4681": {
        "Input/Output Handling": ["test_step"],
    },
    "test_scheduler_ndcentral_triggers_scheduler_manager_itn4713": {
        "Triggering": ["test_step"],
    },
    "test_scheduler_manager_triggers_scheduler_itn4706": {
        "Triggering": ["test_step"],
    },
    "test_scheduler_ndcentral_fails_to_trigger_scheduler_itn4710": {
        "Triggering": ["test_step"],
    },
    "test_scheduler_file_state_not_dnd_no_alerts_itn4689": {
        "Inertial Processing": ["test_step"],
    },
    "test_scheduler_complete_file_operation_itn4676": {
        "Input/Output Handling": ["test_step"],
    },
    "test_scheduler_inertial_starts_processing_with_valid_parameters_itn4694": {
        "Inertial Processing": ["test_step"],
    },
    "test_scheduler_completion_inertial_obs_itn4677": {
        "Inertial Processing": ["test_step"],
    },
    "test_scheduler_detailed_copy_obs_generation_itn4684": {
        "Inertial Processing": ["test_step"],
    },
    "test_scheduler_check_movement_of_hdfile_inertial_observation_itn4675": {
        "Inertial Processing": ["test_step"],
    },
    "test_scheduler_inference_move_file_delete_state_itn4697": {
        "Inference State Machine": ["test_step"],
    },
    "test_scheduler_inference_move_file_upload_state_itn4698": {
        "Inference State Machine": ["test_step"],
    },
    "test_scheduler_inference_calls_deleter_delete_state_itn4695": {
        "Inference State Machine": ["test_step"],
    },
    "test_scheduler_inference_calls_uploader_upload_state_itn4696": {
        "Inference State Machine": ["test_step"],
    },
    "test_scheduler_state_modified_vision_running_state_itn4731": {
        "Inference State Machine": ["test_step"],
    },
    "test_scheduler_inference_run_metadata_summary_itn4700": {
        "Vision Inference": ["test_step"],
    },
    "test_scheduler_starts_outward_nrt_with_valid_parameters_itn4729": {
        "Vision Inference": ["test_step"],
    },
    "test_scheduler_starts_inward_nrt_with_valid_parameters_itn4728": {
        "Vision Inference": ["test_step"],
    },
    "test_scheduler_session_nrt_completion_status_itn4727": {
        "Vision Inference": ["test_step"],
    },
    "test_scheduler_analysis_result_outward_inward_nrt_itn4674": {
        "Vision Inference": ["test_step"],
    },
    "test_scheduler_inference_updates_collated_alerts_itn4701": {
        "Inference State Machine": ["test_step"],
    },
    "test_scheduler_uploader_modifies_state_job_submit_state_itn4733": {
        "Uploader Workflow": ["test_step"],
    },
    "test_scheduler_uploader_engine_workflow_itn4732": {
        "Uploader Workflow": ["test_step"],
    },
    "test_scheduler_latency_check_without_alert_itn4703": {
        "Latency": ["test_step"],
    },
    "test_scheduler_latency_check_incase_alert_itn4702": {
        "Latency": ["test_step"],
    },
    "test_scheduler_deleter_checks_delete_state_itn4678": {
        "Inference State Machine": ["test_step"],
    },
    "test_scheduler_deleters_deletes_nd_output_nd_input_files_itn4679": {
        "Deleter": ["test_step"],
    },
    "test_scheduler_deletes_all_file_previous_session_itn4680": {
        "Deleter": ["test_step"],
    },
    "test_scheduler_processed_file_written_to_disk_itn4722": {
        "Input/Output Handling": ["test_step"],
    },
    "test_scheduler_file_locking_behaviour_itn4687": {
        "Input/Output Handling": ["test_step"],
    },
    "test_scheduler_wrapper_otacheck_crontab_itn4735": {
        "Crontab": ["test_step"],
    },
    "test_scheduler_wrapper_cleanupstate_crontab_itn4734": {
        "Crontab": ["test_step"],
    },
    "test_scheduler_wrapper_scheduler_removed_from_user_crontab_itn4737": {
        "Crontab": ["test_step"],
    },
    "test_scheduler_wrapper_otacheck_removed_user_crontab_itn4736": {
        "Crontab": ["test_step"],
    },
    "test_scheduler_folder_permission_nd_output_itn4692": {
        "Input/Output Handling": ["test_step"],
    },
    "test_scheduler_deletes_folder_root_permission_in_ndoutput_itn4682": {
        "Deleter": ["test_step"],
    },
    "test_scheduler_state_files_new_session_itn4730": {
        "Input/Output Handling": ["test_step"],
    },
    "test_scheduler_deletes_multiple_files_itn4683": {
        "Deleter": ["test_step"],
    },
    "test_scheduler_healthstats_network_info": {
        "HealthStats": ["test_step"],
    },
    "test_scheduler_healthstats_signal_info": {
        "HealthStats": ["test_step"],
    },
    "test_scheduler_ndcentral_recording_start_end_to_hs_itn4712": {
        "HealthStats": ["test_step"],
    },
    "test_scheduler_ndcentral_partial_file_recording_start_end_to_hs_itn4711": {
        "HealthStats": ["test_step"],
    },
    "test_scheduler_fields_updated_each_session_in_hs_itn4686": {
        "HealthStats": ["test_step"],
    },
    "test_scheduler_no_traceback_itn4717": {
        "Reliability": ["test_step"],
    },
    "test_scheduler_logs_writing_and_logs_uploading_itn4705": {
        "Logging": ["test_step"],
    },
    "test_scheduler_log_format_related_files_itn4704": {
        "Logging": ["test_step"],
    },
    "test_scheduler_partial_file_process_linux_sign_crash_itn4721": {
        "Reliability": ["test_step"],
    },
    "test_scheduler_queue_overflow_more_files_run_state_itn4724": {
        "Queue Overflow": ["test_step"],
    },
    "test_scheduler_oldest_file_dropped_first_queue_overflow_itn4718": {
        "Queue Overflow": ["test_step"],
    },
    "test_scheduler_queue_every_min_itn4723": {
        "Queue Overflow": ["test_step"],
    },
    "test_scheduler_not_crashing_during_queue_overflow_itn4716": {
        "Queue Overflow": ["test_step"],
    },
    "test_scheduler_no_attribute_error_itn4714": {
        "Reliability": ["test_step"],
    },
    "test_scheduler_partial_file_process_backtoback_restart_bagheera_itn4720": {
        "Reliability": ["test_step"],
    },
    "test_scheduler_no_pileup_deleter_itn4715": {
        "Deleter": ["test_step"],
    },

    # ─── INFERENCE ────────────────────────────────────────────────────
    "test_inference_file_state_not_dnd_no_alerts_itn4745": {
        "Inertial Processing": ["test_step"],
    },
    "test_inference_inertial_starts_processing_with_valid_parameters_itn4748": {
        "Inertial Processing": ["test_step"],
    },
    "test_inference_completion_inertial_obs_itn4743": {
        "Inertial Processing": ["test_step"],
    },
    "test_inference_minified_obs_generation_inertial_itn4749": {
        "Inertial Processing": ["test_step"],
    },
    "test_inference_detailed_copy_obs_generation_itn4744": {
        "Inertial Processing": ["test_step"],
    },
    "test_inference_check_movement_of_hdfile_inertial_observation_itn4742": {
        "Inertial Processing": ["test_step"],
    },
    "test_inference_move_file_delete_state_itn4750": {
        "Inference State Machine": ["test_step"],
    },
    "test_inference_move_file_upload_state_itn4751": {
        "Inference State Machine": ["test_step"],
    },
    "test_inference_calls_deleter_delete_state_itn4740": {
        "Inference State Machine": ["test_step"],
    },
    "test_inference_calls_uploader_upload_state_itn4741": {
        "Inference State Machine": ["test_step"],
    },
    "test_inference_state_modified_vision_running_state_itn4757": {
        "Inference State Machine": ["test_step"],
    },
    "test_inference_run_metadata_summary_itn4753": {
        "Vision Inference": ["test_step"],
    },
    "test_inference_overwrites_summary_ld_itn4752": {
        "Inertial Processing": ["test_step"],
    },
    "test_inference_updates_collated_alerts_itn4758": {
        "Inference State Machine": ["test_step"],
    },
    "test_inference_starts_outward_nrt_with_valid_parameters_itn4756": {
        "Vision Inference": ["test_step"],
    },
    "test_inference_starts_inward_nrt_with_valid_parameters_itn4755": {
        "Vision Inference": ["test_step"],
    },
    "test_inference_session_nrt_completion_status_itn4754": {
        "Vision Inference": ["test_step"],
    },
    "test_inference_analysis_result_outward_inward_nrt_itn4739": {
        "Vision Inference": ["test_step"],
    },
    "test_inference_alert_flow_validation_itn4738": {
        "Inference State Machine": ["test_step"],
    },
    "test_inference_inertial_alerts_itn4746": {
        "DND & Alert Management": ["test_step"],
    },
    "test_inference_uploader_modifies_state_job_submit_state": {
        "Uploader Workflow": ["test_step"],
    },
    "test_inference_uploader_engine_workflow": {
        "Uploader Workflow": ["test_step"],
    },
    "test_inference_latency_check_incase_alert": {
        "Latency": ["test_step"],
    },
    "test_inference_latency_check_without_alert": {
        "Latency": ["test_step"],
    },
    "test_inference_deleter_checks_delete_state": {
        "Inference State Machine": ["test_step"],
    },
    "test_inference_deleters_deletes_nd_output_nd_input_files": {
        "Deleter": ["test_step"],
    },
    "test_inference_deletes_all_file_previous_session": {
        "Deleter": ["test_step"],
    },
    "test_inference_deletes_folder_root_permission_in_ndoutput": {
        "Deleter": ["test_step"],
    },
    "test_inference_deletes_multiple_files": {
        "Deleter": ["test_step"],
    },
    "test_inference_no_pileup_deleter": {
        "Deleter": ["test_step"],
    },
    "test_inference_ndcentral_recording_start_end_to_hs": {
        "HealthStats": ["test_step"],
    },
    "test_inference_ndcentral_partial_file_recording_start_end_to_hs": {
        "HealthStats": ["test_step"],
    },
    "test_inference_ndcentral_triggers_scheduler_manager": {
        "Triggering": ["test_step"],
    },
    "test_inference_ndcentral_fails_to_trigger_scheduler": {
        "Triggering": ["test_step"],
    },
    "test_inference_state_files_new_session": {
        "Input/Output Handling": ["test_step"],
    },
    "test_inference_partial_file_process_backtoback_restart_bagheera": {
        "Reliability": ["test_step"],
    },
    "test_inference_partial_file_process_linux_sign_crash": {
        "Reliability": ["test_step"],
    },
    "test_inference_fields_updated_each_session_in_hs": {
        "HealthStats": ["test_step"],
    },
    "test_inference_inertial_process_itn4747": {
        "Inertial Processing": ["test_step"],
    },
    "test_inference_obs_file_gen": {
        "Inertial Processing": ["test_step"],
    },
    "test_inference_obs_file_deletion": {
        "Inertial Processing": ["test_step"],
    },
    "test_inference_file_pileup_inertialobs": {
        "Inertial Processing": ["test_step"],
    },
    "test_inference_metadata_user_alert": {
        "DND & Alert Management": ["test_step"],
    },
    "test_inference_xattr_metadata_alert_session": {
        "DND & Alert Management": ["test_step"],
    },
    "test_inference_alert_copied_to_sdcard": {
        "Inference State Machine": ["test_step"],
    },
    "test_inference_summary_json_file_size": {
        "Inference State Machine": ["test_step"],
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
    "test_bagheera_status_check_itn4654": "Service Monitor",
    "test_svc_status_check_itn4666": "Service Monitor",
    "test_awsiot_status_check_itn4653": "Service Monitor",
    "test_circular_buffer_status_check_itn4655": "Service Monitor",
    "test_power_monitor_status_check_itn4662": "Service Monitor",
    "test_scheduler_manager_status_check_itn4663": "Service Monitor",
    "test_speed_status_check_itn4665": "Service Monitor",
    "test_time_sync_status_check_itn4667": "Service Monitor",
    "test_uploader_status_check_itn4669": "Service Monitor",
    "test_outward_analytics_client_status_check_itn4660": "Service Monitor",
    "test_analytics_service_status_check_itn4651": "Service Monitor",
    "test_healthstatsmanager_status_check_itn4656": "Service Monitor",
    "test_sendmetricgrpc_status_check_itn4664": "Service Monitor",
    "test_audio_playback_status_check_itn4652": "Service Monitor",
    "test_inward_analytics_client_status_check_itn4657": "Service Monitor",
    "test_nd_fe_alerts_status_check_itn4658": "Service Monitor",
    "test_nd_suspendresume_status_check": "Service Monitor",
    "test_nd_system_status_status_check_itn4659": "Service Monitor",
    "test_podlogger_status_check_itn4661": "Service Monitor",
    "test_unified_analytics_client_status_check_itn4668": "Service Monitor",
    "test_awsiot_ping_keepalive_reboot_itn4633": "AWSIOT",
    "test_awsiot_ping_request_reboot_phone_itn4634": "AWSIOT",
    "test_awsiot_reboot_request_to_powermon_itn4635": "AWSIOT",
    "test_awsiot_api_call_versioncheck_itn4623": "AWSIOT",
    "test_awsiot_verify_connection_ignition_high_itn4641": "AWSIOT",
    "test_awsiot_verify_connection_no_network_itn4642": "AWSIOT",
    "test_awsiot_server_connected_or_not_itn4637": "AWSIOT",
    "test_awsiot_verify_server_address_itn4621": "AWSIOT",
    "test_awsiot_verify_logging_itn4646": "AWSIOT",
    "test_awsiot_check_private_key_itn4627": "AWSIOT",
    "test_awsiot_check_public_key_itn4628": "AWSIOT",
    "test_awsiot_check_certificates_itn4625": "AWSIOT",
    "test_awsiot_check_encryption_and_permission_of_private_keys_itn4626": "AWSIOT",
    "test_awsiot_verify_ka_certificate_check_itn4645": "AWSIOT",
    "test_awsiot_verify_iot_priv_key_decryption_before_connect_itn4644": "AWSIOT",
    "test_awsiot_eventdata_api_call_itn4629": "AWSIOT",
    "test_awsiot_eventdata_api_response_itn4630": "AWSIOT",
    "test_awsiot_receive_video_request_itn4650": "AWSIOT",
    "test_awsiot_send_request_to_uploader_itn4636": "AWSIOT",
    "test_awsiot_state_change_to_upload_state_itn4640": "AWSIOT",
    "test_awsiot_verify_payload_itn4647": "AWSIOT",
    "test_awsiot_service_status_check_itn4639": "AWSIOT",
    "test_awsiot_service_stability_itn4638": "AWSIOT",
    "test_awsiot_msgq_creation_itn4631": "AWSIOT",
    "test_awsiot_check_binary_and_permissions_itn4624": "AWSIOT",
    "test_awsiot_override_parse_check_itn4632": "AWSIOT",
    "test_awsiot_verify_vehicle_class_itn4649": "AWSIOT",
    "test_awsiot_verify_publish_enabled_itn4648": "AWSIOT",
    "test_awsiot_verify_gps_publish_frequency_itn4643": "AWSIOT",
    "test_awsiot_all_cameras_enabled_itn4622": "AWSIOT",
    "test_scheduler_msgq_creation_related_services_itn4709": "SCHEDULER",
    "test_scheduler_runs_wrapper_scheduler_every_min_itn4725": "SCHEDULER",
    "test_scheduler_file_pileup_itn4688": "SCHEDULER",
    "test_scheduler_enters_file_valid_input_set_itn4685": "SCHEDULER",
    "test_scheduler_deletes_file_invalid_input_set_itn4681": "SCHEDULER",
    "test_scheduler_ndcentral_triggers_scheduler_manager_itn4713": "SCHEDULER",
    "test_scheduler_manager_triggers_scheduler_itn4706": "SCHEDULER",
    "test_scheduler_ndcentral_fails_to_trigger_scheduler_itn4710": "SCHEDULER",
    "test_scheduler_file_state_not_dnd_no_alerts_itn4689": "SCHEDULER",
    "test_scheduler_complete_file_operation_itn4676": "SCHEDULER",
    "test_scheduler_inertial_starts_processing_with_valid_parameters_itn4694": "SCHEDULER",
    "test_scheduler_completion_inertial_obs_itn4677": "SCHEDULER",
    "test_scheduler_detailed_copy_obs_generation_itn4684": "SCHEDULER",
    "test_scheduler_check_movement_of_hdfile_inertial_observation_itn4675": "SCHEDULER",
    "test_scheduler_inference_move_file_delete_state_itn4697": "SCHEDULER",
    "test_scheduler_inference_move_file_upload_state_itn4698": "SCHEDULER",
    "test_scheduler_inference_calls_deleter_delete_state_itn4695": "SCHEDULER",
    "test_scheduler_inference_calls_uploader_upload_state_itn4696": "SCHEDULER",
    "test_scheduler_state_modified_vision_running_state_itn4731": "SCHEDULER",
    "test_scheduler_inference_run_metadata_summary_itn4700": "SCHEDULER",
    "test_scheduler_starts_outward_nrt_with_valid_parameters_itn4729": "SCHEDULER",
    "test_scheduler_starts_inward_nrt_with_valid_parameters_itn4728": "SCHEDULER",
    "test_scheduler_session_nrt_completion_status_itn4727": "SCHEDULER",
    "test_scheduler_analysis_result_outward_inward_nrt_itn4674": "SCHEDULER",
    "test_scheduler_inference_updates_collated_alerts_itn4701": "SCHEDULER",
    "test_scheduler_uploader_modifies_state_job_submit_state_itn4733": "SCHEDULER",
    "test_scheduler_uploader_engine_workflow_itn4732": "SCHEDULER",
    "test_scheduler_latency_check_without_alert_itn4703": "SCHEDULER",
    "test_scheduler_latency_check_incase_alert_itn4702": "SCHEDULER",
    "test_scheduler_deleter_checks_delete_state_itn4678": "SCHEDULER",
    "test_scheduler_deleters_deletes_nd_output_nd_input_files_itn4679": "SCHEDULER",
    "test_scheduler_deletes_all_file_previous_session_itn4680": "SCHEDULER",
    "test_scheduler_processed_file_written_to_disk_itn4722": "SCHEDULER",
    "test_scheduler_file_locking_behaviour_itn4687": "SCHEDULER",
    "test_scheduler_wrapper_otacheck_crontab_itn4735": "SCHEDULER",
    "test_scheduler_wrapper_cleanupstate_crontab_itn4734": "SCHEDULER",
    "test_scheduler_wrapper_scheduler_removed_from_user_crontab_itn4737": "SCHEDULER",
    "test_scheduler_wrapper_otacheck_removed_user_crontab_itn4736": "SCHEDULER",
    "test_scheduler_folder_permission_nd_output_itn4692": "SCHEDULER",
    "test_scheduler_deletes_folder_root_permission_in_ndoutput_itn4682": "SCHEDULER",
    "test_scheduler_state_files_new_session_itn4730": "SCHEDULER",
    "test_scheduler_deletes_multiple_files_itn4683": "SCHEDULER",
    "test_scheduler_healthstats_network_info": "SCHEDULER",
    "test_scheduler_healthstats_signal_info": "SCHEDULER",
    "test_scheduler_ndcentral_recording_start_end_to_hs_itn4712": "SCHEDULER",
    "test_scheduler_ndcentral_partial_file_recording_start_end_to_hs_itn4711": "SCHEDULER",
    "test_scheduler_fields_updated_each_session_in_hs_itn4686": "SCHEDULER",
    "test_scheduler_no_traceback_itn4717": "SCHEDULER",
    "test_scheduler_logs_writing_and_logs_uploading_itn4705": "SCHEDULER",
    "test_scheduler_log_format_related_files_itn4704": "SCHEDULER",
    "test_scheduler_partial_file_process_linux_sign_crash_itn4721": "SCHEDULER",
    "test_scheduler_queue_overflow_more_files_run_state_itn4724": "SCHEDULER",
    "test_scheduler_oldest_file_dropped_first_queue_overflow_itn4718": "SCHEDULER",
    "test_scheduler_queue_every_min_itn4723": "SCHEDULER",
    "test_scheduler_not_crashing_during_queue_overflow_itn4716": "SCHEDULER",
    "test_scheduler_no_attribute_error_itn4714": "SCHEDULER",
    "test_scheduler_partial_file_process_backtoback_restart_bagheera_itn4720": "SCHEDULER",
    "test_scheduler_no_pileup_deleter_itn4715": "SCHEDULER",
    "test_inference_file_state_not_dnd_no_alerts_itn4745": "INFERENCE",
    "test_inference_inertial_starts_processing_with_valid_parameters_itn4748": "INFERENCE",
    "test_inference_completion_inertial_obs_itn4743": "INFERENCE",
    "test_inference_minified_obs_generation_inertial_itn4749": "INFERENCE",
    "test_inference_detailed_copy_obs_generation_itn4744": "INFERENCE",
    "test_inference_check_movement_of_hdfile_inertial_observation_itn4742": "INFERENCE",
    "test_inference_move_file_delete_state_itn4750": "INFERENCE",
    "test_inference_move_file_upload_state_itn4751": "INFERENCE",
    "test_inference_calls_deleter_delete_state_itn4740": "INFERENCE",
    "test_inference_calls_uploader_upload_state_itn4741": "INFERENCE",
    "test_inference_state_modified_vision_running_state_itn4757": "INFERENCE",
    "test_inference_run_metadata_summary_itn4753": "INFERENCE",
    "test_inference_overwrites_summary_ld_itn4752": "INFERENCE",
    "test_inference_updates_collated_alerts_itn4758": "INFERENCE",
    "test_inference_starts_outward_nrt_with_valid_parameters_itn4756": "INFERENCE",
    "test_inference_starts_inward_nrt_with_valid_parameters_itn4755": "INFERENCE",
    "test_inference_session_nrt_completion_status_itn4754": "INFERENCE",
    "test_inference_analysis_result_outward_inward_nrt_itn4739": "INFERENCE",
    "test_inference_alert_flow_validation_itn4738": "INFERENCE",
    "test_inference_inertial_alerts_itn4746": "INFERENCE",
    "test_inference_uploader_modifies_state_job_submit_state": "INFERENCE",
    "test_inference_uploader_engine_workflow": "INFERENCE",
    "test_inference_latency_check_incase_alert": "INFERENCE",
    "test_inference_latency_check_without_alert": "INFERENCE",
    "test_inference_deleter_checks_delete_state": "INFERENCE",
    "test_inference_deleters_deletes_nd_output_nd_input_files": "INFERENCE",
    "test_inference_deletes_all_file_previous_session": "INFERENCE",
    "test_inference_deletes_folder_root_permission_in_ndoutput": "INFERENCE",
    "test_inference_deletes_multiple_files": "INFERENCE",
    "test_inference_no_pileup_deleter": "INFERENCE",
    "test_inference_ndcentral_recording_start_end_to_hs": "INFERENCE",
    "test_inference_ndcentral_partial_file_recording_start_end_to_hs": "INFERENCE",
    "test_inference_ndcentral_triggers_scheduler_manager": "INFERENCE",
    "test_inference_ndcentral_fails_to_trigger_scheduler": "INFERENCE",
    "test_inference_state_files_new_session": "INFERENCE",
    "test_inference_partial_file_process_backtoback_restart_bagheera": "INFERENCE",
    "test_inference_partial_file_process_linux_sign_crash": "INFERENCE",
    "test_inference_fields_updated_each_session_in_hs": "INFERENCE",
    "test_inference_inertial_process_itn4747": "INFERENCE",
    "test_inference_obs_file_gen": "INFERENCE",
    "test_inference_obs_file_deletion": "INFERENCE",
    "test_inference_file_pileup_inertialobs": "INFERENCE",
    "test_inference_metadata_user_alert": "INFERENCE",
    "test_inference_xattr_metadata_alert_session": "INFERENCE",
    "test_inference_alert_copied_to_sdcard": "INFERENCE",
    "test_inference_summary_json_file_size": "INFERENCE",
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
