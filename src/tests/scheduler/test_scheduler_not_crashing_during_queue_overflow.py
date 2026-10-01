"""
Feature: Scheduler — Not Crashing During Queue Overflow
Description:
  Verify scheduler does not crash during a queue-overflow scenario, and
  keeps completing file operations (syncing observations to disk).

  Ported from nd_test_bot's TC_1453_SCHEDULER_NOT_CRASHING_DURING_QUEUE_OVERFLOW.
  Uses the same fake-file-creation loop as the sibling queue-overflow tests
  in this batch (24 files, 1s apart -- matches this TC's own trigger loop
  count/interval, which differs slightly from TC_1444/1445's 25 files/0.5s).

  Log strings "RUN_STATE count =", "ERROR - Queue OVERFLOW",
  "nd_file_operate_device: file operation complete", "syncing content to
  disk /home/ubuntu/.nddevice/observations" (UNVERIFIED -- ported from
  reference, not yet confirmed on FE) need a live check before this test is
  trusted.
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


def test_step1_create_24_fake_run_state_files(device):
    """trigger — Create 24 fake RUN_STATE files in ND_INPUT, 1s apart."""
    _create_files_in_loop(device, num_files=24, sleep_seconds=1)


def test_step2_clear_nd_input(device):
    """PreCondition_1 — Clear ND_INPUT directory."""
    device.run("rm -rf /home/iriscli/ND_INPUT/*")


def test_step3_clear_nd_output(device):
    """PreCondition_2 — Clear ND_OUTPUT directory."""
    device.run("rm -rf /home/iriscli/ND_OUTPUT/*")


def test_step4_wait(device):
    """STEP_1 — Wait 40s."""
    time.sleep(40)


def test_step5_restart_scheduler_manager(device):
    """STEP_3 — Restart scheduler_manager service."""
    result = device.restart_service("scheduler_manager")
    assert result["status"] == "Pass", f"Failed to restart scheduler_manager: {result['details']}"


def test_step6_wait(device):
    """STEP_4 — Wait 20s."""
    time.sleep(20)


def test_step7_get_run_state_count(device):
    """STEP_5 — Get the latest RUN_STATE count."""
    output = device.run("grep -inr 'RUN_STATE count =' /home/ubuntu/.nddevice/log/scheduler | tail -n 1 | awk -F'=' '{print $3}' | xargs")
    run_state_count = (output or "").strip()
    assert run_state_count, "RUN_STATE count not found"
    device.variables["run_state_count"] = run_state_count


def test_step8_verify_run_state_count_greater_than_15(device):
    """STEP_6 — Verify RUN_STATE count is greater than 15 (queue was fed >16 files)."""
    run_state_count = device.variables.get("run_state_count")
    assert run_state_count and int(run_state_count) > 15, f"RUN_STATE count is less than 16: {run_state_count!r}"


def test_step9_verify_no_queue_overflow(device):
    """STEP_7 — Verify no queue overflow error was logged."""
    output = device.run("grep -inr 'ERROR - Queue OVERFLOW' /home/ubuntu/.nddevice/log/scheduler")
    assert not output, "Queue Overflow found"


def test_step10_verify_scheduler_not_crashing(device):
    """STEP_8 — Verify scheduler keeps completing file operations after copying observations (not crashing)."""
    for message in [
        "nd_file_operate_device: file operation complete",
        "syncing content to disk /home/ubuntu/.nddevice/observations",
    ]:
        output = device.search_log("/home/ubuntu/.nddevice/log/scheduler_manager", message, timeout=180, interval=10)
        assert output, f"'{message}' not found -- scheduler may be crashing during queue overflow"


def test_step11_clear_nd_input(device):
    """PostCondition_1 — Clear ND_INPUT directory."""
    device.run("rm -rf /home/iriscli/ND_INPUT/*")


def test_step12_clear_nd_output(device):
    """PostCondition_2 — Clear ND_OUTPUT directory."""
    device.run("rm -rf /home/iriscli/ND_OUTPUT/*")
