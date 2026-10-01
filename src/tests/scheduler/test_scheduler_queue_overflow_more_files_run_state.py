"""
Feature: Scheduler — Queue Overflow (More Than 16 Files In RUN_STATE)
Description:
  Verify scheduler does not report a queue overflow error when more than 16
  fake RUN_STATE files are created in ND_INPUT.

  Ported from nd_test_bot's TC_1444_SCHEDULER_QUEUE_OVERFLOW_MORE_FILES_RUN_STATE.
  The reference's Calculator_obj.create_files_in_loop has no FE equivalent
  method -- ported its shell-command body directly (creates fake
  .chm/_ymetadata.txt/.STATE=RUN_STATE files with synthetic
  trip/part/timestamp names) via device.run() in a plain Python loop,
  rather than adding a new framework API, since this file-synthesis routine
  is specific to this and 2 sibling queue-overflow tests in this batch, not
  broadly reusable. `systemctl restart scheduler_manager` replaced with
  device.restart_service.

  Log string "ERROR - Queue OVERFLOW" (UNVERIFIED -- ported from reference,
  not yet confirmed on FE) needs a live check before this test is trusted.
"""

import time


def _create_files_in_loop(device, num_files, sleep_seconds):
    current_ts = int(time.time() * 1000)
    session_num = 3147
    for i in range(num_files):
        timestamp = current_ts + i * 60000
        part = f"{session_num + i}"
        cmd = (
            f"sh -c 'trip_num=$((RANDOM % 10000)); "
            f"touch /home/iriscli/ND_INPUT/0_trip${{trip_num}}_part{part}_91.0000_181.0000_0.0_{timestamp}_y.chm; "
            f"touch /home/iriscli/ND_INPUT/0_trip${{trip_num}}_part{part}_91.0000_181.0000_0.0_{timestamp}_ymetadata.txt; "
            f'echo "RUN_STATE" > /home/iriscli/ND_INPUT/0_trip${{trip_num}}_part{part}_91.0000_181.0000_0.0_{timestamp}_y.STATE\''
        )
        device.run(cmd)
        time.sleep(sleep_seconds)


def test_step1_wait(device):
    """PreCondition_1 — Wait 15s."""
    time.sleep(15)


def test_step2_clear_nd_input(device):
    """PreCondition_2 — Clear ND_INPUT directory."""
    device.run("rm -rf /home/iriscli/ND_INPUT/*")


def test_step3_clear_nd_output(device):
    """PreCondition_3 — Clear ND_OUTPUT directory."""
    device.run("rm -rf /home/iriscli/ND_OUTPUT/*")


def test_step4_create_25_fake_run_state_files(device):
    """STEP_1 — Create 25 fake RUN_STATE files in ND_INPUT, 0.5s apart."""
    _create_files_in_loop(device, num_files=25, sleep_seconds=0.5)


def test_step5_restart_scheduler_manager(device):
    """STEP_3 — Restart scheduler_manager service."""
    result = device.restart_service("scheduler_manager")
    assert result["status"] == "Pass", f"Failed to restart Scheduler Manager: {result['details']}"


def test_step6_wait(device):
    """STEP_3_1 — Wait 5s."""
    time.sleep(5)


def test_step7_verify_no_queue_overflow(device):
    """STEP_6 — Verify no queue overflow error, even with more than 16 files."""
    output = device.run("grep -inr 'ERROR - Queue OVERFLOW' /home/ubuntu/.nddevice/log/scheduler")
    assert not output, "Queue overflow found"


def test_step8_clear_nd_input(device):
    """PostCondition_1 — Clear ND_INPUT directory."""
    device.run("rm -rf /home/iriscli/ND_INPUT/*")


def test_step9_clear_nd_output(device):
    """PostCondition_2 — Clear ND_OUTPUT directory."""
    device.run("rm -rf /home/iriscli/ND_OUTPUT/*")
