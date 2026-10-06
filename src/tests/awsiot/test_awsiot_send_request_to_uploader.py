"""
Feature: AWSIOT — Send Request To Uploader
Description:
  Verify AWSIOT sends VOD upload requests (both cameras) to unifieduploader
  for the session created by a user alert (button press), and that
  unifieduploader receives both.

  Ported from nd_test_bot's true original TC_1109 starting from
  PreCondition_5/6 -- PreCondition_1-4 (download_config/change_mul_param_value/
  upload_config to disable privacy mode for all cameras) and PostCondition_1/2
  (reupload_config, final reboot) dropped: FE has no SCP/SFTP file-transfer
  capability and no device-level reboot method (only reboot_voyager for the
  host and aws_reboot via cloud ping), so there is no way to download-edit-
  upload a config file or reboot the device pod itself. Same "no FE
  equivalent" call already made for this config-download/change/upload group
  elsewhere in the port (see PORT_TRACKER.csv).

  Session-name capture matches the reference's order and mechanism exactly:
  PreCondition_6 blocks on `tail -F .../ndcentral/* | grep -m1 "creating
  folder for session"` (a single live tail, not a poll loop) BEFORE STEP_1
  pushes the alert. This captures whatever session is active/being created
  at that moment -- which is the session do_vod later references once the
  alert lands -- rather than racing to catch a session created after the
  alert (FE creates a new session roughly every 60s regardless of any
  alert, so polling forward after the alert risks grabbing an unrelated
  routine session instead of the alert's).

  STEP_2/STEP_2_1 port the reference's FileUtils_obj.get_current_session_name
  calls (device.get_current_session_name) for inward (cam_num=1) and
  outward (cam_num=0) -- a separate, standalone confirmation that the
  current session's per-camera filenames can be resolved, independent of
  the ndcentral-log-derived session name used for the VOD checks (same as
  the reference, which also never feeds session_name_inward/
  session_name_outward into the later VOD checks).

  STEP_6/STEP_7 (the reference's STEP_5/STEP_6) require BOTH the outward
  (0-prefixed) and inward (1-prefixed) VOD requests to be found -- the
  reference passes both patterns as one search_logs call, which requires
  all patterns matched, not just one of the two. Both searches use a
  single combined polling loop (not two independent full-length timeouts)
  so the step's total worst-case wait is still ~1 timeout window, not 2x.

  The reference's STEP_4/STEP_5_1/STEP_6_1 (krait/krait2-specific
  /data/nd_files/nd_sdcard/ video path) dropped -- FE's real video path is
  /media/SdCard/ for all devices (confirmed via live device grep), so the
  device-type branch never applies here.

  push_alert uses gen_ualert.sh (FE's real alert-trigger mechanism, no DTA
  agent on FE devices) instead of the reference's SendMsgServer-based
  push_alert. The reference's STEP_1_2/STEP_1_3 (svc/ndcentral button-press
  log confirmation) are dropped per user instruction.
"""

import time


def test_step1_check_datetime(device):
    """Verify AWSIOT sends VOD upload requests (both cameras) for a user-alert session.

    PreCondition_1 — Verify device datetime is in sync (non-blocking).
    """
    result = device.compare_datetime()
    if result["status"] != "Pass":
        print(f"datetime is incorrect: {result['details']}")


def test_step2_set_search_start(device):
    """Mark the search-start timestamp used by the log searches below."""
    device.variables["search_start_ts"] = device.get_current_time_epoch()["epoch_ms"]


def test_step2_1_capture_session_name(device):
    """PreCondition_6 — Capture the current session name from ndcentral's folder-creation log.

    Blocks on a live tail (matches the reference exactly) BEFORE the alert
    is pushed, so it captures whatever session is active at that moment --
    the session do_vod later references once the alert lands.
    """
    cmd = (
        "tail -F /home/ubuntu/.nddevice/log/ndcentral/* | "
        "grep --line-buffered -m 1 'creating folder for session' | "
        "awk -F'creating folder for session ' '{print $2}' | awk '{print $1}'"
    )
    output = device.run(cmd, timeout=125)
    session_name = (output or "").strip()
    assert session_name, f"Session name not found: {output!r}"
    device.variables["session_name"] = session_name


def test_step3_push_alert(device):
    """STEP_1 — Push alert to device."""
    output = device.run("./gen_ualert.sh", "/home/ubuntu/.nddevice/latest/service/bagheera")
    assert device.user_alert_generated(output), f"Failed to generate user alert: {output}"


def test_step4_get_inward_session_name(device):
    """STEP_2 — Get the current inward (cam_num=1) session filename (non-blocking)."""
    result = device.get_current_session_name(extension=".mp4", cam_num=1)
    if result["status"] != "Pass":
        print(f"Inward session name not found: {result['details']}")
    device.variables["session_name_inward"] = result.get("session_name")


def test_step4_1_get_outward_session_name(device):
    """STEP_2_1 — Get the current outward (cam_num=0) session filename (non-blocking)."""
    result = device.get_current_session_name(extension=".mp4", cam_num=0)
    if result["status"] != "Pass":
        print(f"Outward session name not found: {result['details']}")
    device.variables["session_name_outward"] = result.get("session_name")


def test_step5_wait_for_upload(device):
    """STEP_3 — Wait 120s for upload processing."""
    time.sleep(120)


def test_step6_restart_uploader(device):
    """STEP_4_1 — Restart uploader service."""
    result = device.restart_service("uploader")
    assert result["status"] == "Pass", f"Failed to restart uploader service: {result['details']}"


def _poll_both(device, log_dir, outward_pattern, inward_pattern, total_timeout, interval):
    """Poll for two patterns together, checking both each interval, so the
    combined wait is ~total_timeout, not total_timeout per pattern."""
    elapsed = 0
    outward_found = None
    inward_found = None
    while elapsed < total_timeout:
        if not outward_found:
            outward_found = device.search_log(log_dir, outward_pattern, start_timestamp=device.variables.get("search_start_ts"), timeout=1, interval=1)
        if not inward_found:
            inward_found = device.search_log(log_dir, inward_pattern, start_timestamp=device.variables.get("search_start_ts"), timeout=1, interval=1)
        if outward_found and inward_found:
            break
        time.sleep(interval)
        elapsed += interval
    return outward_found, inward_found


def test_step7_verify_vod_sent(device):
    """STEP_5 — Poll for VOD requests sent by awsiot for BOTH cameras of this session."""
    session_name = device.variables.get("session_name")
    assert session_name, "Session name was not captured in PreCondition_6"
    outward_found, inward_found = _poll_both(
        device,
        "/home/ubuntu/.nddevice/log/awsiot",
        f"do_vod: sending REQ_UPLOAD_VOD to uploader for file: /media/SdCard/0{session_name}.mp4",
        f"do_vod: sending REQ_UPLOAD_VOD to uploader for file: /media/SdCard/1{session_name}.mp4",
        total_timeout=1200, interval=30,
    )
    assert outward_found, f"Outward (0-prefixed) VOD request not sent by AWSIOT for session {session_name!r}"
    assert inward_found, f"Inward (1-prefixed) VOD request not sent by AWSIOT for session {session_name!r}"


def test_step8_verify_uploader_received(device):
    """STEP_6 — Verify unifieduploader received VOD requests for BOTH cameras of this session."""
    session_name = device.variables.get("session_name")
    assert session_name, "Session name was not captured in PreCondition_6"
    outward_found, inward_found = _poll_both(
        device,
        "/home/ubuntu/.nddevice/log/unifieduploader",
        f"VOD req received.* /media/SdCard/0{session_name}.mp4",
        f"VOD req received.* /media/SdCard/1{session_name}.mp4",
        total_timeout=600, interval=30,
    )
    assert outward_found, f"Outward (0-prefixed) VOD request not received by unifieduploader for session {session_name!r}"
    assert inward_found, f"Inward (1-prefixed) VOD request not received by unifieduploader for session {session_name!r}"


def test_step9_verify_awsiot_len(device):
    """STEP_6_2 — Verify 'Message Received: AWSIOT len' in uploader."""
    ts = device.variables.get("search_start_ts")
    output = device.search_log("/home/ubuntu/.nddevice/log/unifieduploader", "Message Received: AWSIOT len", start_timestamp=ts)
    assert output, "AWSIOT len not received by unifieduploader"
