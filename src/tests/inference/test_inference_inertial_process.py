"""
Feature: Inference — Inertial Process
Description:
  Verify metadata is written under the GI path (/home/iriscli/ND_INPUT) and
  processed by the inertial module once the scheduler changes the state file
  to RUN_STATE.

  Ported from nd_test_bot's TC_811_BAGHEERA_INERTIAL_PROCESS. Log strings
  (UNVERIFIED -- ported from reference, not yet confirmed on FE) need a live
  check before this test is trusted.
"""

import time

_INERTIAL_LOG_DIR = "/home/ubuntu/.nddevice/log/inference_inertial"


def test_step1_verify_run_state_in_input(device):
    """STEP_1 — Verify inference_inertial logs "Got state 'RUN_STATE'" for a file in ND_INPUT."""
    result = device.run_command_iteratively(
        f"grep -ahn \"Got state 'RUN_STATE'in file: /home/iriscli/ND_INPUT/\" {_INERTIAL_LOG_DIR}/* | tail -1",
        iteration=6, timeout=20, not_desired_output=[""],
    )
    assert result["status"] == "Pass", f"State not changed to RUN_STATE: {result['details']}"


def test_step2_verify_scheduler_changes_state_to_run_state(device):
    """STEP_2 — Verify the scheduler changes the state file to RUN_STATE (inertial module)."""
    start_ts = device.get_current_time_epoch()["epoch_ms"] - 120000
    found = device.search_log(
        _INERTIAL_LOG_DIR, "Found 1 files in run state(s): RUN_STATE in inertial module",
        start_ts, timeout=120, interval=20,
    )
    assert found, "Scheduler does not change the state file to RUN_STATE"


def test_step3_verify_metadata_under_gi_path(device):
    """STEP_3 — Verify metadata is being written under the GI path (ND_INPUT *ymetadata.txt)."""
    output = device.run(
        f"grep -a -E 'metadata: /home/iriscli/ND_INPUT/.*ymetadata\\.txt' {_INERTIAL_LOG_DIR}/inference_inertial.log "
        f"> /dev/null && echo true || echo false"
    )
    assert output and output.strip().endswith("true"), "Metadata is not being written under the GI path"
