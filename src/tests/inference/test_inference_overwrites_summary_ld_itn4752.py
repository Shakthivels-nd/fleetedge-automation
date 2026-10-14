"""
Feature: Scheduler — Inference Overwrites summary_LD.json
Description:
  Verify inference overwrites the summary_LD.json file created after inertial
  processing, and creates it again afterwards.

  Ported from nd_test_bot's TC_1317_SCHEDULER_INFERENCE_OVERWRITES_SUMMARY_LD,
  starting from its STEP_1. The reference's preconditions (disable hdmaps_mode
  via download/change/upload config, reboot the device, write keepalive_count)
  are not ported, so the device is assumed to already have hdmaps_mode
  disabled -- the minified-copy path only applies in that mode.

  Log strings "...summary_LD.json file exists. Overwriting" and "Created
  ...summary_LD.json" (UNVERIFIED -- ported from reference, not yet confirmed
  on FE) need a live check before this test is trusted.
"""

import time

_INFERENCE_LOG_DIR = "/home/ubuntu/.nddevice/log/inference"


def test_step1_get_current_session_name(device):
    """STEP_1 — Get the current session name."""
    result = device.get_current_session_name()
    assert result["status"] == "Pass", f"Session name not found: {result['details']}"
    device.variables["current_session"] = result["session_name"]


def test_step2_wait(device):
    """STEP_2 — Wait 90s."""
    time.sleep(90)


def test_step3_verify_summary_ld_overwritten(device):
    """STEP_3 — Verify inference starts overwriting summary_LD.json."""
    # Latest occurrence in the inference logs, ignoring the session name.
    result = device.run_command_iteratively(
        f"grep -h 'summary_LD.json file exists. Overwriting' {_INFERENCE_LOG_DIR}/*.log 2>/dev/null | tail -1",
        iteration=30, timeout=5, not_desired_output=[""],
    )
    assert result["status"] == "Pass", f"Inference has not started overwriting summary_LD.json file: {result['details']}"
    print(f"Latest overwrite line: {result['output']}")


def test_step4_verify_summary_ld_created(device):
    """STEP_4 — Verify inference creates summary_LD.json after overwriting."""
    # Latest occurrence in the inference logs, ignoring the session name.
    result = device.run_command_iteratively(
        f"grep -h 'Created /home/iriscli/ND_OUTPUT/.*summary_LD.json' {_INFERENCE_LOG_DIR}/*.log 2>/dev/null | tail -1",
        iteration=30, timeout=5, not_desired_output=[""]
    )
    assert result["status"] == "Pass", f"Inference has not created summary_LD.json file after overwriting: {result['details']}"
    print(f"Latest created line: {result['output']}")
    