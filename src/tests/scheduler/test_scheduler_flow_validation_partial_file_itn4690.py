"""
Feature: Scheduler — Flow Validation (Partial File)
Description:
  End-to-end validation of the scheduler-to-uploader workflow for a partial
  file: a recording interrupted mid-session is processed as a partial file
  (inertial and vision NRT), its isummary.json is flagged partial/leftover, and
  the session is deleted.

  Ported from nd_test_bot's TC_2110_SCHEDULER_FLOW_VALIDATION_PARTIAL_FILE,
  mapped the same way as test_scheduler_flow_validation.py (TC_2098): the
  hdmaps_mode config precondition is not ported (device assumed to already have
  hdmaps_mode disabled), sd_card_path -> /media/SdCard, log checks look up the
  latest occurrence ignoring the session name (current AND rotated logs, no
  timestamp filter), the file-existence steps just check for any file, and the
  reference's "continue"-on-fail steps are separate asserting tests.
  Partial-file mappings:
    - the reference's mid-test device reboot (STEP_2), which interrupts the
      recording, is replaced with a bagheera restart (STEP_4), which also leaves
      a partial recording; the "Starting scheduler at reboot" check on the
      reboot service log (STEP_4 there) is dropped as reboot-specific
    - NOTE: the unifieduploader "Sending obs archive pass to HS" check (STEP_32)
      is described by the reference as happening "upon reboot" -- UNVERIFIED
      whether a bagheera restart triggers it
  The deletion steps poll for up to 300s (the deleter lags a session by minutes).

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
    """STEP_2 — Wait 15s."""
    time.sleep(15)


def test_step5_set_keepalive_count(device):
    """STEP_3 — Set keepalive_count to 11."""
    device.run("chmod 777 /home/ubuntu/.nddevice/log/keepalive_count.txt ; echo 11  > /home/ubuntu/.nddevice/log/keepalive_count.txt")


def test_step6_restart_bagheera(device):
    """STEP_4 — Restart bagheera to interrupt the recording (in place of the reference's device reboot)."""
    result = device.restart_service("bagheera")
    assert result["status"] == "Pass", f"Failed to restart bagheera service: {result['details']}"


def test_step7_verify_partial_chm_file_written(device):
    """STEP_5 — Ndcentral writes the final CS file for the partial file."""
    _verify_latest(device, "ndcentral", "FINAL CS FILE for partial file /home/iriscli/ND_INPUT/", "Partial chm file not found", iteration=10, interval=10)


def test_step8_wait(device):
    """STEP_6 — Wait 60s."""
    time.sleep(60)


def test_step9_verify_scheduler_manager_started_scheduler(device):
    """STEP_7 — Scheduler manager starts the scheduler if it is not running."""
    for message in ["scheduler is not running. Starting Now", "Started scheduler: 1"]:
        _verify_latest(device, "scheduler_manager", message, f"Scheduler manager not started: '{message}' not found")


def test_step10_verify_scheduler_started(device):
    """STEP_8 — Scheduler started."""
    _verify_latest(device, "scheduler", "Starting Scheduler", "Scheduler not started")


def test_step11_verify_scheduler_read_file_state(device):
    """STEP_9 — Scheduler reads the state of the file."""
    _verify_latest(device, "scheduler", "Name of the file: /home/iriscli/ND_INPUT/.*STATE", "Scheduler not read the state of the file")


def test_step12_verify_new_state(device):
    """STEP_10 — Scheduler identifies the state as NEW_STATE for the partial session."""
    _verify_latest(device, "scheduler", "We have files in NEW_STATE", "Scheduler not identify the state as NEW_STATE")


def test_step13_wait(device):
    """STEP_11 — Wait 60s."""
    time.sleep(60)


def test_step14_verify_inertial_engine_started(device):
    """STEP_12 — Inference inertial engine is started if it is not running."""
    _verify_latest(device, "scheduler_manager", "Inertial Inference Engine is not running. Starting Now", "Unable to start Inference Inertial Engine")


def test_step15_verify_run_state(device):
    """STEP_13 — The selected session is in RUN_STATE."""
    _verify_latest(device, "scheduler", "Got state 'RUN_STATE'in file: /home/iriscli/ND_INPUT/.*STATE", "RUN_STATE count not found")


def test_step16_verify_inertial_operating(device):
    """STEP_14 — Inference inertial starts operating (no obsdata file for a partial session)."""
    _verify_latest(device, "inference_inertial", "We are going to operate on the obsdata file  metadata file /home/iriscli/ND_INPUT/.*metadata.txt and output folder /home/iriscli/ND_OUTPUT/", "Inference Inertial Engine not started operating")


def test_step17_verify_running_state(device):
    """STEP_15 — The session state is modified to RUNNING_STATE."""
    _verify_latest(device, "inference_inertial", "File: /home/iriscli/ND_INPUT/.*STATE is modified to  state:RUNNING_STATE", "RUNNING_STATE count not found")


def test_step18_verify_summary_ld_created(device):
    """STEP_16 — Inference inertial creates summary_LD.json under ND_OUTPUT."""
    _verify_latest(device, "inference_inertial", "Created /home/iriscli/ND_OUTPUT/.*/summary_LD.json", "summary_ld.json file not created")


def test_step19_verify_hd_zip_moved_to_sdcard(device):
    """STEP_17 — Inference inertial moves the hd zip file to the SD card."""
    _verify_latest(device, "inference", f"File sync finished: {_SD_CARD_PATH}/.*zip, time taken", "File sync not finished")


def test_step20_verify_inertial_obs_kept_with_md5sum(device):
    """STEP_18 — Inference inertial keeps the processed file under inertial_obs with the md5sum in the zip name."""
    _verify_latest(device, "inference_inertial", "File sync finished: /home/ubuntu/.nddevice/inertial_obs/.*zip, time taken", "File sync not finished")


def test_step21_verify_inference_engine_started(device):
    """STEP_19 — Inference engine is started if it is not running."""
    _verify_latest(device, "inference_inertial", "Inference Engine is not running. Starting Now", "Inference Engine not started")


def test_step22_verify_not_dnd_state(device):
    """STEP_20 — Inference inertial marks the session NOT_DND_STATE."""
    _verify_latest(device, "inference_inertial", " Moving /home/iriscli/ND_INPUT/.*STATE to NOT_DND_STATE", "NOT_DND_STATE count not found")


def test_step23_verify_vision_nrt_started(device):
    """STEP_21 — Inference starts ViSION NRT on the selected session."""
    _verify_latest(device, "inference", "We are going to operate on the video file /home/iriscli/ND_INPUT/.*mp4, metadata file /home/iriscli/ND_OUTPUT/.*/isummary.json, outObsdata File /home/iriscli/ND_OUTPUT/.*/outward_vis_obs.obsdata, inObsdata File /home/iriscli/ND_OUTPUT/.*/inward_vis_obs.obsdata, and output folder /home/iriscli/ND_OUTPUT/", "Inference ViSION NRT not started")


def test_step24_verify_vision_running_state(device):
    """STEP_22 — Inference changes the session state to VISION_RUNNING_STATE."""
    _verify_latest(device, "inference", "File: /home/iriscli/ND_INPUT/.*STATE is modified to  state:VISION_RUNNING_STATE", "VISION_RUNNING_STATE count not found")


def test_step25_verify_isummary_partial(device):
    """STEP_23 — Inference creates isummary.json and flags it as partial/leftover."""
    _verify_latest(device, "inference", "/home/iriscli/ND_OUTPUT/.*/isummary.json is Partial or leftover metadata file", "isummary.json not flagged as partial")


def test_step26_verify_final_observation_written(device):
    """STEP_24 — Inference writes the session's final observation into the observations directory."""
    _verify_latest(device, "inference", "File sync finished: /home/ubuntu/.nddevice/observations/.*zip, time taken", "File sync not finished")


def test_step27_verify_no_alert(device):
    """STEP_25 — Inference detects no alert from this session."""
    _verify_latest(device, "inference", "video:.*mp4, compression:0 is_ib_alert False", "Alert found")


def test_step28_verify_delete_state(device):
    """STEP_26 — Inference marks the session state to DELETE_STATE."""
    _verify_latest(device, "inference", "File: /home/iriscli/ND_INPUT/.*STATE is modified to  state:DELETE_STATE", "DELETE_STATE count not found", iteration=30, interval=10)


def test_step29_verify_deleter_engine_started(device):
    """STEP_27 — Inference starts the deleter."""
    _verify_latest(device, "inference", "Deleter Engine is not running. Starting Now", "Deleter Engine not started", iteration=30, interval=10)


def test_step30_verify_deleter_selected_session(device):
    """STEP_28 — Deleter selects the session for deletion."""
    _verify_latest(device, "deleter", "We are going to delete video file /home/iriscli/ND_INPUT/.*mp4 metadata file /home/iriscli/ND_INPUT/.*metadata.txt and output folder /home/iriscli/ND_OUTPUT/", "Deleter Engine not started operating", iteration=30, interval=10)


def test_step31_verify_deletion_successful(device):
    """STEP_29 — Deletion is successful."""
    _verify_latest(device, "deleter", "Files with names /home/iriscli/ND_INPUT/.*\\* are deleted", "Files not deleted", iteration=30, interval=10)


def test_step32_verify_nd_input_files_exist(device):
    """STEP_30 — Files exist in ND_INPUT."""
    _verify_any_file(device, "ls -1 /home/iriscli/ND_INPUT 2>/dev/null | tail -n 1", "No files in ND_INPUT")


def test_step33_verify_observation_available(device):
    """STEP_31 — Files exist in the observations directory."""
    _verify_any_file(device, "ls -1 /home/ubuntu/.nddevice/observations 2>/dev/null | tail -n 1", "No files in the observations directory")


def test_step34_verify_obs_archive_sent_to_hs(device):
    """STEP_32 — Unified uploader sends the observation archive to HS."""
    _verify_latest(device, "unifieduploader", "Sending obs archive pass to HS: /home/ubuntu/.nddevice/unoperated_obs/.*json", "Obs archive not sent to HS", iteration=10, interval=10)


def test_step35_verify_circular_buffer_file(device):
    """STEP_33 — Files exist in the circular buffer space (SD card)."""
    _verify_any_file(device, f"ls -1 {_SD_CARD_PATH}/*.zip 2>/dev/null | tail -n 1", "No zip files on the SD card")