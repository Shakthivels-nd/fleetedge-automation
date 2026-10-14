"""
Feature: Scheduler — Minified Obs Generation (Inertial)
Description:
  Verify a minified copy of the obs (summary_LD.json) is generated once
  inertial processing is completed.

  Ported from nd_test_bot's TC_1295_SCHEDULER_MIINIFIED_OBS_GENERATION_INERTIAL,
  starting from its PreCondition_4. The reference's earlier preconditions
  (disable hdmaps_mode via download/change/upload config, reboot the device,
  write keepalive_count) are not ported, so the device is assumed to already
  have hdmaps_mode disabled -- the minified-copy path only applies in that mode.

  Log strings "calling ndlib.generate_ld_metadata" and "Created
  /home/iriscli/ND_OUTPUT/<session>/summary_LD.json" (UNVERIFIED -- ported
  from reference, not yet confirmed on FE) need a live check before this test
  is trusted.
"""

import time

_INERTIAL_LOG_DIR = "/home/ubuntu/.nddevice/log/inference_inertial"


def test_step1_wait(device):
    """PreCondition_1 — Wait 10s."""
    # Device-clock epoch (ms) taken before the session starts: the log checks below only
    # consider lines logged after this point.
    device.variables["search_start_ts"] = device.get_current_time_epoch()["epoch_ms"]
    time.sleep(10)


def test_step2_verify_bagheera_active(device):
    """PreCondition_2 — Verify bagheera service is RUNNING."""
    result = device.is_service_active("bagheera")
    assert result["status"] == "Pass", f"bagheera is not RUNNING: {result['state']}"


def test_step3_get_current_session_name(device):
    """STEP_1 — Get the current session name."""
    result = device.get_current_session_name(cam_num=0)
    assert result["status"] == "Pass", f"Session name not found: {result['details']}"
    device.variables["session_name"] = result["session_name"]


def test_step4_wait(device):
    """STEP_2 — Wait 120s."""
    time.sleep(120)


def test_step5_verify_generate_ld_metadata_called(device):
    """STEP_3 — Verify inference_inertial calls ndlib.generate_ld_metadata."""
    output = device.search_log(_INERTIAL_LOG_DIR, "calling ndlib.generate_ld_metadata", device.variables["search_start_ts"], timeout=120, interval=5)
    assert output, "calling ndlib.generate_ld_metadata not found"


def test_step6_verify_minified_obs_generated(device):
    """STEP_4 — Verify the minified copy of the obs (summary_LD.json) is generated for the session."""
    session_name = device.variables["session_name"]
    output = device.search_log(
        _INERTIAL_LOG_DIR, f"Created /home/iriscli/ND_OUTPUT/{session_name}/summary_LD.json",
        device.variables["search_start_ts"], timeout=150, interval=5,
    )
    assert output, "Minified copy of obs is not generated"
