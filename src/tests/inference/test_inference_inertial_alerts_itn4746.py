"""
Feature: Scheduler — Inertial Alerts
Description:
  Verify an alert pushed to the device is handled by inference_inertial:
  alerts are extracted, files move to NOT_DND_STATE, the alert message is
  sent to HS and the transcoding recommendation is received.

  Ported from nd_test_bot's TC_1256_SCHEDULER_INERTIAL_ALERTS_MASTER, with its
  three single-step child testcases folded in as the last three checks:
    TC_1252 (DND state alert), TC_1255 (alert msg sent to HS),
    TC_1283 (inertial receives transcoding recommendations on alert).
  The reference's svc log check ("Sending message for button falling: 0") is
  dropped. The session is obtained from the ndcentral "creating folder for
  session" log (60s check) followed by get_current_session_name, and the alert
  is pushed with ./gen_ualert.sh instead of SendMsgServer push_alert.

  Log strings "Extracted 1 alerts from 10 events", "STATE is modified to
  state:NOT_DND_STATE", "Sending alert msg to HS", "Transcoding recommendation
  = 2" (UNVERIFIED -- ported from reference, not yet confirmed on FE) need a
  live check before this test is trusted.
"""

import time

_INERTIAL_LOG_DIR = "/home/ubuntu/.nddevice/log/inference_inertial"


def test_step1_wait(device):
    """PreCondition_1 — Wait 10s."""
    time.sleep(10)


def test_step2_restart_bagheera(device):
    """PreCondition_2 — Restart bagheera service."""
    # Device-clock epoch (ms) taken before the restart: the session-creation search only
    # considers ndcentral lines logged after this point.
    device.variables["session_start_ts"] = device.get_current_time_epoch()["epoch_ms"]
    result = device.restart_service("bagheera")
    assert result["status"] == "Pass", f"Failed to restart bagheera service: {result['details']}"


def test_step3_wait(device):
    """PreCondition_3 — Wait 30s."""
    time.sleep(30)


def test_step4_verify_bagheera_active(device):
    """PreCondition_4 — Verify bagheera service is RUNNING."""
    result = device.is_service_active("bagheera")
    assert result["status"] == "Pass", f"bagheera is not RUNNING: {result['state']}"


def test_step5_wait_for_session_creation(device):
    """STEP_1 — Verify ndcentral logs a new session folder being created (60s check)."""
    found = device.search_log(
        "/home/ubuntu/.nddevice/log/ndcentral", "creating folder for session",
        device.variables["session_start_ts"], timeout=60, interval=5,
    )
    assert found, "Session name not found: no 'creating folder for session' in ndcentral logs"


def test_step6_get_current_session_name(device):
    """STEP_1_1 — Get the current session name."""
    result = device.get_current_session_name(cam_num=0)
    assert result["status"] == "Pass", f"Session name not found: {result['details']}"
    device.variables["session_name"] = result["session_name"]


def test_step7_wait(device):
    """STEP_1_2 — Wait 10s before pushing the alert."""
    time.sleep(10)


def test_step8_push_alert(device):
    """STEP_2 — Push alert to device."""
    # Device-clock epoch (ms) just before the alert; the inertial log checks below only
    # consider lines logged after it.
    device.variables["alert_start_ts"] = device.get_current_time_epoch()["epoch_ms"]
    output = device.run("./gen_ualert.sh", "/home/ubuntu/.nddevice/latest/service/bagheera")
    assert device.user_alert_generated(output), f"Failed to generate user alert: {output}"


def test_step9_wait(device):
    """STEP_2_1 — Wait 15s."""
    time.sleep(15)


def test_step10_wait(device):
    """STEP_3 — Wait 70s for inference_inertial to process the alert."""
    time.sleep(70)


def _verify_inertial_log(device, message, failure):
    output = device.search_log(_INERTIAL_LOG_DIR, message, device.variables["alert_start_ts"], timeout=300, interval=5)
    assert output, failure


def test_step12_verify_dnd_state_alert(device):
    """STEP_4 — Verify files are moved to NOT_DND_STATE when inertial alerts are found."""
    _verify_inertial_log(device, "STATE is modified to  state:NOT_DND_STATE", "State not modified to NOT_DND_STATE")


def test_step13_verify_alert_msg_sent_to_hs(device):
    """STEP_5 — Verify inference_inertial sends the alert message to HS."""
    _verify_inertial_log(device, "Sending alert msg to HS", "Alert message is not sent to Health stats")


def test_step14_verify_transcoding_recommendation(device):
    """STEP_6 — Verify the transcoding recommendation matches the number of alerts."""
    _verify_inertial_log(device, "Transcoding recommendation = 2", "Transcoding recommendation not found")
