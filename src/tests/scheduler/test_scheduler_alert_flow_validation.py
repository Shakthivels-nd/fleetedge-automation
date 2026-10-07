"""
Feature: Scheduler — Alert Flow Validation
Description:
  End-to-end validation of a session with an alert, from its creation to its
  deletion: the alert is pushed and detected, the session is processed by
  inference_inertial and inference, uploaded (UPLOAD_STATE -> JOB_SUBMIT_STATE)
  and then deleted.

  Ported from nd_test_bot's TC_2105_SCHEDULER_ALERT_FLOW_VALIDATION, mapped the
  same way as test_scheduler_flow_validation.py (TC_2098): the hdmaps_mode
  config precondition and device reboot are not ported (device assumed to
  already have hdmaps_mode disabled), sd_card_path -> /media/SdCard, log checks look up the
  latest occurrence ignoring the session name (current AND rotated logs, no
  timestamp filter), the file-existence steps just check for any file, and the
  reference's "continue"-on-fail steps are separate asserting tests.
  Alert-specific mappings:
    - SendMsgServer push_alert -> ./gen_ualert.sh (FE's alert trigger)
    - the svc log check ("Sending message for button falling: 0") is dropped --
      gen_ualert.sh doesn't go through svc
    - the reference's STEP_15 reads an unset variable (session_name_alert); like
      the other steps it now ignores the session name
    - NRT result line uses FE's wording "... = 0 and inAnalyseRunResult = 0"
  The uploader/deleter steps poll for up to 300s (they lag a session by minutes).

  All log strings (UNVERIFIED -- ported from reference, not yet confirmed on
  FE) need a live check before this test is trusted.
"""

import time

_LOG = "/home/ubuntu/.nddevice/log"
_SD_CARD_PATH = "/media/SdCard"


def _latest(device, service, message, iteration=12, interval=5):
    """Latest occurrence of `message` (a grep regex; the session name is replaced by `.*`) anywhere in a
    service's logs, current and rotated; the lines start with a timestamp, so a plain sort puts the
    latest last. Retried up to `iteration` times; returns the line ("" if never found)."""
    result = device.run_command_iteratively(
        f'grep -rh "{message}" {_LOG}/{service} 2>/dev/null | sort | tail -n 1',
        iteration=iteration, timeout=interval, not_desired_output=[""],
    )
    return result["output"] if result["status"] == "Pass" else ""


def _verify_latest(device, service, message, failure, iteration=12, interval=5):
    output = _latest(device, service, message, iteration, interval)
    print(f"Latest: {output}")
    assert output, failure


def _verify_any_file(device, listing_cmd, failure):
    result = device.run_command_iteratively(listing_cmd, iteration=3, timeout=1, not_desired_output=[""])
    assert result["status"] == "Pass", f"{failure}: {result['details']}"
    print(f"Found: {result['output']}")


def test_step1_set_keepalive_count(device):
    """PreCondition_1 — Set keepalive_count to 11."""
    device.run(""" bash -c "echo 11 > /home/ubuntu/.nddevice/log/keepalive_count.txt" """)


def test_step2_verify_services_active(device):
    """PreCondition_2 — Verify bagheera and scheduler_manager services are RUNNING."""
    for service in ["bagheera", "scheduler_manager"]:
        result = device.is_service_active(service)
        assert result["status"] == "Pass", f"{service} service is not active: {result['state']}"


def test_step3_capture_session_name(device):
    """STEP_1 — Session creation: capture the session name."""
    cmd = (
        "( timeout 170 tail -F /home/ubuntu/.nddevice/log/ndcentral/* 2>/dev/null | "
        "grep --line-buffered -m 1 'creating folder for session' | "
        "awk -F'creating folder for session ' '{print $2}' | awk '{print $1}' ) 2>/dev/null"
    )
    output = device.run(cmd, timeout=180)
    session_name = (output or "").strip()
    assert session_name, f"Session name not found: {output!r}"
    device.variables["session_name"] = session_name


def test_step4_wait(device):
    """STEP_2 — Wait 10s."""
    time.sleep(10)


def test_step5_push_alert(device):
    """STEP_3 — Trigger alert for the session."""
    output = device.run("./gen_ualert.sh", "/home/ubuntu/.nddevice/latest/service/bagheera")
    assert device.user_alert_generated(output), f"Failed to generate user alert: {output}"


def test_step6_wait(device):
    """STEP_4 — Wait 80s."""
    time.sleep(80)


def test_step7_set_keepalive_count(device):
    """STEP_5 — Set keepalive_count to 11."""
    device.run("chmod 777 /home/ubuntu/.nddevice/log/keepalive_count.txt ; echo 11  > /home/ubuntu/.nddevice/log/keepalive_count.txt")


def test_step8_verify_chm_file_written(device):
    """STEP_6 — Ndcentral writes the chm file to ND_INPUT."""
    _verify_latest(device, "ndcentral", "FINAL CS FILE /home/iriscli/ND_INPUT/", "Chm file not found", iteration=10, interval=10)


def test_step9_verify_trigger_scheduler_manager_sent(device):
    """STEP_7 — Ndcentral sends the request to scheduler manager for the NRT process."""
    _verify_latest(device, "ndcentral", "Trigger scheduler manager sent", "Trigger scheduler manager not sent")


def test_step10_verify_scheduler_read_new_state(device):
    """STEP_8 — Scheduler reads the state of the file and identifies it as NEW_STATE."""
    for message in ["Inside filename /home/iriscli/ND_INPUT/", "We have files in NEW_STATE"]:
        _verify_latest(device, "scheduler", message, f"'{message}' not found in scheduler logs")


def test_step11_verify_run_state(device):
    """STEP_9 — In inference_inertial, the selected session is in RUN_STATE."""
    _verify_latest(device, "inference_inertial", "Got state 'RUN_STATE'in file: /home/iriscli/ND_INPUT/.*STATE", "RUN_STATE count not found")


def test_step12_verify_inertial_operating(device):
    """STEP_10 — Inference inertial starts operating on the obsdata, metadata and output folder."""
    _verify_latest(device, "inference_inertial", "We are going to operate on the obsdata file /home/iriscli/ND_OUTPUT/.*/inertial_obs.obsdata metadata file /home/iriscli/ND_INPUT/.*metadata.txt and output folder /home/iriscli/ND_OUTPUT/", "Inference Inertial Engine not started operating")


def test_step13_verify_running_state(device):
    """STEP_11 — The session state is modified to RUNNING_STATE."""
    _verify_latest(device, "inference_inertial", "File: /home/iriscli/ND_INPUT/.*STATE is modified to  state:RUNNING_STATE", "RUNNING_STATE count not found")


def test_step14_verify_transcoding_recommendation(device):
    """STEP_12 — Inference inertial sets the transcoding recommendation to 2."""
    _verify_latest(device, "inference_inertial", "Transcoding recommendation = 2", "Transcoding recommendation not found")


def test_step15_verify_summary_ld_created(device):
    """STEP_13 — Inference inertial creates summary_LD.json under ND_OUTPUT."""
    _verify_latest(device, "inference_inertial", "Created /home/iriscli/ND_OUTPUT/.*/summary_LD.json", "summary_ld.json file not created")


def test_step16_verify_hd_zip_moved_to_sdcard(device):
    """STEP_14 — Inference inertial moves the hd zip file to the SD card."""
    _verify_latest(device, "inference", f"File sync finished: {_SD_CARD_PATH}/.*zip, time taken", "File sync not finished")


def test_step17_verify_inertial_obs_kept_with_md5sum(device):
    """STEP_15 — Inference inertial keeps the processed file under inertial_obs with the md5sum in the zip name."""
    _verify_latest(device, "inference_inertial", "File sync finished: /home/ubuntu/.nddevice/inertial_obs/.*zip, time taken", "File sync not finished")


def test_step18_verify_ib_alert_true(device):
    """STEP_16 — Inference inertial sets is_ib_alert True."""
    _verify_latest(device, "inference", "is_ib_alert True$", "is_ib_alert True not found", iteration=10, interval=10)


def test_step19_verify_vision_running_state(device):
    """STEP_17 — Inference changes the session state to VISION_RUNNING_STATE."""
    _verify_latest(device, "inference", "File: /home/iriscli/ND_INPUT/.*STATE is modified to  state:VISION_RUNNING_STATE", "VISION_RUNNING_STATE count not found")


def test_step20_verify_nrt_status_success(device):
    """STEP_18 — Outward NRT and Inward NRT status are success."""
    _verify_latest(device, "inference", "outAnalyseRunResult = 0 and inAnalyseRunResult = 0", "NRT status not success")


def test_step21_verify_final_observation_written(device):
    """STEP_19 — Inference writes the session's final observation into the observations directory."""
    _verify_latest(device, "inference", "File sync finished: /home/ubuntu/.nddevice/observations/.*zip, time taken", "File sync not finished")


def test_step22_verify_alert_session_identified(device):
    """STEP_20 — Inference identifies the session with the alert."""
    _verify_latest(device, "inference", "video:.*mp4, compression:2 is_ib_alert True", "Alert session not identified")


def test_step23_verify_upload_state(device):
    """STEP_21 — Inference marks the session state to UPLOAD_STATE."""
    _verify_latest(device, "inference", "File: /home/iriscli/ND_INPUT/.*STATE is modified to  state:UPLOAD_STATE", "UPLOAD_STATE not found", iteration=30, interval=10)


def test_step24_verify_uploader_engine_started(device):
    """STEP_22 — Inference triggers the Uploader Engine."""
    _verify_latest(device, "inference", "Uploader Engine is not running. Starting Now", "Uploader Engine not started", iteration=30, interval=10)


def test_step25_verify_session_added_to_uploader_db(device):
    """STEP_23 — Unified uploader adds the session to the uploader db."""
    _verify_latest(device, "unifieduploader", "Updated status 1  to upload req /home/iriscli/ND_OUTPUT/.* to table", "Session not added to uploader db", iteration=30, interval=10)


def test_step26_verify_uploader_checks_upload_state(device):
    """STEP_24 — Uploader checks the file in UPLOAD_STATE."""
    _verify_latest(device, "uploader", "Checking UPLOAD_STATE in file: /home/iriscli/ND_INPUT/", "UPLOAD_STATE not checked by uploader", iteration=30, interval=10)


def test_step27_verify_job_submit_state(device):
    """STEP_25 — Uploader operates on the session and modifies the state to JOB_SUBMIT_STATE."""
    _verify_latest(device, "uploader", "File: /home/iriscli/ND_INPUT/.*STATE is modified to  state:JOB_SUBMIT_STATE", "JOB_SUBMIT_STATE not found", iteration=30, interval=10)


def test_step28_verify_deleter_checks_delete_state(device):
    """STEP_26 — Deleter checks the delete state of the files received."""
    _verify_latest(device, "deleter", "Checking DELETE_STATE in file: /home/iriscli/ND_INPUT/.*STATE", "DELETE_STATE not checked by deleter", iteration=30, interval=15)


def test_step29_verify_deleter_selected_session(device):
    """STEP_27 — Deleter selects the session for deletion."""
    _verify_latest(device, "deleter", "We are going to delete video file /home/iriscli/ND_INPUT/.*mp4 metadata file /home/iriscli/ND_INPUT/.*metadata.txt and output folder /home/iriscli/ND_OUTPUT/", "Deleter Engine not started operating", iteration=30, interval=10)


def test_step30_verify_deletion_successful(device):
    """STEP_28 — Deletion is successful."""
    _verify_latest(device, "deleter", "Files with names /home/iriscli/ND_INPUT/.*\\* are deleted", "Files not deleted", iteration=30, interval=10)


def test_step31_verify_nd_input_files_exist(device):
    """STEP_29 — Files exist in ND_INPUT."""
    _verify_any_file(device, "ls -1 /home/iriscli/ND_INPUT 2>/dev/null | tail -n 1", "No files in ND_INPUT")


def test_step32_verify_observation_available(device):
    """STEP_30 — Files exist in the observations directory."""
    _verify_any_file(device, "ls -1 /home/ubuntu/.nddevice/observations 2>/dev/null | tail -n 1", "No files in the observations directory")


def test_step33_verify_circular_buffer_file(device):
    """STEP_31 — Files exist in the circular buffer space (SD card)."""
    _verify_any_file(device, f"ls -1 {_SD_CARD_PATH}/*.zip 2>/dev/null | tail -n 1", "No zip files on the SD card")


def test_step34_restore_keepalive_count(device):
    """PostCondition_1 — Set keepalive_count to 10."""
    device.run("chmod 777 /home/ubuntu/.nddevice/log/keepalive_count.txt ; echo 10  > /home/ubuntu/.nddevice/log/keepalive_count.txt")


def test_step35_wait(device):
    """PostCondition_2 — Wait 60s."""
    time.sleep(60)
