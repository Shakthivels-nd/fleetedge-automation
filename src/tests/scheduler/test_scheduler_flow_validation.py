"""
Feature: Scheduler — Flow Validation
Description:
  End-to-end validation of a session from its creation to its deletion:
  ndcentral writes the chm file, scheduler_manager starts the scheduler, the
  scheduler moves the session through NEW/RUN/RUNNING states, inference_inertial
  and inference process it, and the deleter removes its files.

  Ported from nd_test_bot's TC_2098_SCHEDULER_FLOW_VALIDATION, 1:1 except for
  what FE doesn't support: the reference's hdmaps_mode precondition (config
  download/change/upload) and device reboot are not ported, so the device is
  assumed to already have hdmaps_mode disabled. Other mappings:
    - sd_card_path (command_dict_obj.get_remote_filepath) -> /media/SdCard
    - `tail -f` session capture -> timeout-wrapped `tail -F`
    - search_logs steps filter to lines after the session capture (device-clock
      timestamp) and, like the reference's greps, read current AND rotated logs;
      session-specific greps need no timestamp
    - the deletion-related steps poll for up to 300s (the deleter lags a session
      by ~3-4 min)
    - the reference's "continue"-on-fail steps are separate asserting tests, so
      the later steps still run when one fails
  Differences from the reference text: STEP_23 searches "outAnalyseRunResult = 0
  and inAnalyseRunResult = 0" (the wording FE actually logs), the failing log
  steps look up the latest occurrence ignoring the session name, and STEP_30-32
  just check that files exist in ND_INPUT, the observations directory and the
  SD card (any file, not this session's).

  All log strings (UNVERIFIED -- ported from reference, not yet confirmed on
  FE) need a live check before this test is trusted.
"""

import time

_LOG = "/home/ubuntu/.nddevice/log"
_SD_CARD_PATH = "/media/SdCard"


def _grep(device, pattern, service, iteration=1, interval=10):
    """The reference's `grep -inr "<pattern>" <service log dir>/*` (current and rotated logs);
    retried up to `iteration` times, returns the output ("" if never found)."""
    result = device.run_command_iteratively(
        f'grep -inr "{pattern}" {_LOG}/{service}/* 2>/dev/null',
        iteration=iteration, timeout=interval, not_desired_output=[""],
    )
    return result["output"] if result["status"] == "Pass" else ""


def _search(device, service, message, iteration=12, interval=5):
    """Poll a service's logs (current AND rotated -- the shared search_log only reads `*.log`) for the
    latest line with message logged since the session capture; returns the line ("" if never found).
    ndcentral lines start with an epoch-ms, every other service's with a UTC datetime."""
    start_ms = int(device.variables["search_start_ts"])
    if service == "ndcentral":
        since = f"awk -F: '$1+0 >= {start_ms}'"
    else:
        since = f"awk -v ts=\"$(date -u -d @{start_ms // 1000} '+%Y-%m-%d %H:%M:%S')\" 'substr($0,1,19) >= ts'"
    result = device.run_command_iteratively(
        f"grep -rh '{message}' {_LOG}/{service} 2>/dev/null | {since} | tail -n 1",
        iteration=iteration, timeout=interval, not_desired_output=[""],
    )
    return result["output"] if result["status"] == "Pass" else ""


def _latest(device, service, message, iteration=12, interval=5):
    """Latest occurrence of `message` (a grep regex; the session name is replaced by `.*`) anywhere in a
    service's logs, current and rotated; the lines start with a timestamp, so a plain sort puts the
    latest last. Retried up to `iteration` times; returns the line ("" if never found)."""
    result = device.run_command_iteratively(
        f'grep -rh "{message}" {_LOG}/{service} 2>/dev/null | sort | tail -n 1',
        iteration=iteration, timeout=interval, not_desired_output=[""],
    )
    return result["output"] if result["status"] == "Pass" else ""


def _session(device):
    return device.variables["session_name"]


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
    # Device-clock epoch (ms): the non-session-specific log searches below only consider
    # lines logged after this point.
    device.variables["search_start_ts"] = device.get_current_time_epoch()["epoch_ms"]
    cmd = (
        "( timeout 170 tail -F /home/ubuntu/.nddevice/log/ndcentral/* 2>/dev/null | "
        "grep --line-buffered -m 1 'creating folder for session' | "
        "awk -F'creating folder for session ' '{print $2}' | awk '{print $1}' ) 2>/dev/null"
    )
    output = device.run(cmd, timeout=180)
    session_name = (output or "").strip()
    assert session_name, f"Session name not found: {output!r}"
    # Paths below add the "0" (outward camera) prefix themselves, as the reference does.
    device.variables["session_name"] = session_name[1:] if session_name.startswith("0_trip") else session_name


def test_step4_wait(device):
    """STEP_2 — Wait 30s."""
    time.sleep(30)


def test_step5_verify_chm_file_written(device):
    """STEP_3 — Ndcentral writes the chm file to ND_INPUT."""
    result = device.run_command_iteratively(
        f'grep -inr "FINAL CS FILE /home/iriscli/ND_INPUT/0{_session(device)}" {_LOG}/ndcentral/* 2>/dev/null',
        iteration=10, timeout=10, not_desired_output=[""],
    )
    assert result["status"] == "Pass", f"Chm file not found: {result['details']}"


def test_step6_set_keepalive_count(device):
    """STEP_4 — Set keepalive_count to 11."""
    device.run("chmod 777 /home/ubuntu/.nddevice/log/keepalive_count.txt ; echo 11  > /home/ubuntu/.nddevice/log/keepalive_count.txt")


def test_step7_wait(device):
    """STEP_5 — Wait 60s."""
    time.sleep(60)


def test_step8_verify_trigger_scheduler_manager_sent(device):
    """STEP_6 — Ndcentral sends the request to scheduler manager for the NRT process."""
    assert _search(device, "ndcentral", "Trigger scheduler manager sent"), "Trigger scheduler manager not sent"


def test_step9_verify_scheduler_manager_started_scheduler(device):
    """STEP_7 — Scheduler manager starts the scheduler if it is not running."""
    for message in ["scheduler is not running. Starting Now", "Started scheduler: 1"]:
        output = _latest(device, "scheduler_manager", message)
        print(f"Latest '{message}': {output}")
        assert output, f"Scheduler manager not started: '{message}' not found"


def test_step10_verify_scheduler_started(device):
    """STEP_8 — Scheduler started."""
    assert _search(device, "scheduler", "Starting Scheduler"), "Scheduler not started"


def test_step11_verify_scheduler_read_file_state(device):
    """STEP_9 — Scheduler reads the state of the file."""
    message = f"Name of the file: /home/iriscli/ND_INPUT/0{_session(device)}.STATE"
    assert _search(device, "scheduler", message), "Scheduler not read the state of the file"


def test_step12_verify_new_state(device):
    """STEP_10 — Scheduler identifies the state as NEW_STATE."""
    assert _search(device, "scheduler", "We have files in NEW_STATE"), "Scheduler not identify the state as NEW_STATE"


def test_step13_wait(device):
    """STEP_11 — Wait 60s."""
    time.sleep(60)


def test_step14_verify_inertial_engine_started(device):
    """STEP_12 — Inference inertial engine is started if it is not running."""
    output = _latest(device, "scheduler_manager", "Inertial Inference Engine is not running. Starting Now")
    print(f"Latest: {output}")
    assert output, "Unable to start Inference Inertial Engine"


def test_step15_verify_run_state(device):
    """STEP_13 — The selected session is in RUN_STATE."""
    output = _grep(device, f"Got state 'RUN_STATE'in file: /home/iriscli/ND_INPUT/0{_session(device)}.STATE", "scheduler")
    assert output, "RUN_STATE count not found"


def test_step16_verify_inertial_operating(device):
    """STEP_14 — Inference inertial starts operating on the obsdata, metadata and output folder."""
    output = _latest(device, "inference_inertial", "We are going to operate on the obsdata file /home/iriscli/ND_OUTPUT/.*/inertial_obs.obsdata metadata file /home/iriscli/ND_INPUT/.*metadata.txt and output folder /home/iriscli/ND_OUTPUT/")
    print(f"Latest: {output}")
    assert output, "Inference Inertial Engine not started operating"


def test_step17_verify_running_state(device):
    """STEP_15 — The session state is modified to RUNNING_STATE."""
    output = _latest(device, "inference_inertial", "File: /home/iriscli/ND_INPUT/.*STATE is modified to  state:RUNNING_STATE")
    print(f"Latest: {output}")
    assert output, "RUNNING_STATE count not found"


def test_step18_verify_summary_ld_created(device):
    """STEP_16 — Inference inertial creates summary_LD.json under ND_OUTPUT."""
    output = _latest(device, "inference_inertial", "Created /home/iriscli/ND_OUTPUT/.*/summary_LD.json")
    print(f"Latest: {output}")
    assert output, "summary_ld.json file not created"


def test_step19_verify_hd_zip_moved_to_sdcard(device):
    """STEP_17 — Inference inertial moves the hd zip file to the SD card."""
    output = _latest(device, "inference", f"File sync finished: {_SD_CARD_PATH}/.*zip, time taken")
    print(f"Latest: {output}")
    assert output, "File sync not finished"


def test_step20_verify_inertial_obs_kept_with_md5sum(device):
    """STEP_18 — Inference inertial keeps the processed file under inertial_obs with the md5sum in the zip name."""
    output = _latest(device, "inference_inertial", "File sync finished: /home/ubuntu/.nddevice/inertial_obs/.*zip, time taken")
    print(f"Latest: {output}")
    assert output, "File sync not finished"


def test_step21_verify_inference_engine_started(device):
    """STEP_19 — Inference engine is started if it is not running."""
    assert _search(device, "inference_inertial", "Inference Engine is not running. Starting Now"), "Inference Engine not started"


def test_step22_verify_not_dnd_state(device):
    """STEP_20 — Inference inertial marks the session NOT_DND_STATE."""
    output = _latest(device, "inference_inertial", " Moving /home/iriscli/ND_INPUT/.*STATE to NOT_DND_STATE")
    print(f"Latest: {output}")
    assert output, "NOT_DND_STATE count not found"


def test_step23_verify_vision_nrt_started(device):
    """STEP_21 — Inference starts ViSION NRT on the selected session."""
    output = _latest(device, "inference", "We are going to operate on the video file /home/iriscli/ND_INPUT/.*mp4, metadata file /home/iriscli/ND_OUTPUT/.*/isummary.json, outObsdata File /home/iriscli/ND_OUTPUT/.*/outward_vis_obs.obsdata, inObsdata File /home/iriscli/ND_OUTPUT/.*/inward_vis_obs.obsdata, and output folder /home/iriscli/ND_OUTPUT/")
    print(f"Latest: {output}")
    assert output, "Inference ViSION NRT not started"


def test_step24_verify_vision_running_state(device):
    """STEP_22 — Inference changes the session state to VISION_RUNNING_STATE."""
    output = _latest(device, "inference", "File: /home/iriscli/ND_INPUT/.*STATE is modified to  state:VISION_RUNNING_STATE")
    print(f"Latest: {output}")
    assert output, "VISION_RUNNING_STATE count not found"


def test_step25_verify_nrt_status_success(device):
    """STEP_23 — Outward NRT and Inward NRT status are success."""
    assert _search(device, "inference", "outAnalyseRunResult = 0 and inAnalyseRunResult = 0"), "NRT status not success"


def test_step26_verify_final_observation_written(device):
    """STEP_24 — Inference writes the session's final observation into the observations directory."""
    output = _latest(device, "inference", "File sync finished: /home/ubuntu/.nddevice/observations/.*zip, time taken")
    print(f"Latest: {output}")
    assert output, "File sync not finished"


def test_step27_verify_no_alert(device):
    """STEP_25 — Inference detects no alert from this session."""
    output = _latest(device, "inference", "video:.*mp4, compression:0 is_ib_alert False")
    print(f"Latest: {output}")
    assert output, "Alert found"


def test_step28_verify_delete_state(device):
    """STEP_26 — Inference marks the session state to DELETE_STATE."""
    output = _latest(device, "inference", "File: /home/iriscli/ND_INPUT/.*STATE is modified to  state:DELETE_STATE")
    print(f"Latest: {output}")
    assert output, "DELETE_STATE count not found"


def test_step29_verify_deleter_engine_started(device):
    """STEP_27 — Inference starts the deleter."""
    assert _search(device, "inference", "Deleter Engine is not running. Starting Now", iteration=30, interval=10), "Deleter Engine not started"


def test_step30_verify_deleter_selected_session(device):
    """STEP_28 — Deleter selects the session for deletion."""
    output = _latest(device, "deleter", "We are going to delete video file /home/iriscli/ND_INPUT/.*mp4 metadata file /home/iriscli/ND_INPUT/.*metadata.txt and output folder /home/iriscli/ND_OUTPUT/")
    print(f"Latest: {output}")
    assert output, "Deleter Engine not started operating"


def test_step31_verify_deletion_successful(device):
    """STEP_29 — Deletion is successful."""
    output = _latest(device, "deleter", "Files with names /home/iriscli/ND_INPUT/.*\\* are deleted")
    print(f"Latest: {output}")
    assert output, "Files not deleted"


def _verify_any_file(device, listing_cmd, failure):
    result = device.run_command_iteratively(listing_cmd, iteration=3, timeout=1, not_desired_output=[""])
    assert result["status"] == "Pass", f"{failure}: {result['details']}"
    print(f"Found: {result['output']}")


def test_step32_verify_nd_input_files_exist(device):
    """STEP_30 — Files exist in ND_INPUT."""
    _verify_any_file(device, "ls -1 /home/iriscli/ND_INPUT 2>/dev/null | tail -n 1", "No files in ND_INPUT")


def test_step33_verify_observation_available(device):
    """STEP_31 — Files exist in the observations directory."""
    _verify_any_file(device, "ls -1 /home/ubuntu/.nddevice/observations 2>/dev/null | tail -n 1", "No files in the observations directory")


def test_step34_verify_circular_buffer_file(device):
    """STEP_32 — Files exist in the circular buffer space (SD card)."""
    _verify_any_file(device, f"ls -1 {_SD_CARD_PATH}/*.zip 2>/dev/null | tail -n 1", "No zip files on the SD card")
