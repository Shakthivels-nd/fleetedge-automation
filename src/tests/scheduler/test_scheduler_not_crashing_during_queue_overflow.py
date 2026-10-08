"""
Feature: Scheduler — Not Crashing During Queue Overflow
Description:
  Verify scheduler does not crash during a queue-overflow scenario, and
  keeps completing file operations (syncing observations to disk).

  Ported from nd_test_bot's TC_1453_SCHEDULER_NOT_CRASHING_DURING_QUEUE_OVERFLOW.
  As in the reference, the file-creation "trigger" (24 files, 1s apart) runs
  in a background thread during STEP_1's 40s wait, after the ND_INPUT /
  ND_OUTPUT clears. The main thread only sleeps meanwhile, so the shared pod
  session is never used by two threads at once. The trigger command is the
  reference's own (fixed part03147a, device-clock timestamp), not the
  create_files_in_loop variant used by TC_1444/1445.

  Log strings "RUN_STATE count =", "ERROR - Queue OVERFLOW",
  "nd_file_operate_device: file operation complete", "syncing content to
  disk /home/ubuntu/.nddevice/observations" (UNVERIFIED -- ported from
  reference, not yet confirmed on FE) need a live check before this test is
  trusted.
"""

import threading
import time

_SCHEDULER_LOG_DIR = "/home/ubuntu/.nddevice/log/scheduler"
_SCHEDULER_MANAGER_LOG_DIR = "/home/ubuntu/.nddevice/log/scheduler_manager"

TRIGGER_CMD = (
    "sh -c 'trip_num=$((RANDOM % 10000)); timestamp=$(date +%s%N | cut -b1-13); "
    "touch /home/iriscli/ND_INPUT/0_trip${trip_num}_part03147a_91.0000_181.0000_0.0_${timestamp}_y.chm; "
    "touch /home/iriscli/ND_INPUT/0_trip${trip_num}_part03147a_91.0000_181.0000_0.0_${timestamp}_ymetadata.txt; "
    "echo \"RUN_STATE\" > /home/iriscli/ND_INPUT/0_trip${trip_num}_part03147a_91.0000_181.0000_0.0_${timestamp}_y.STATE'"
)


def test_step1_clear_nd_input(device):
    """PreCondition_1 — Clear ND_INPUT directory."""
    device.run("rm -rf /home/iriscli/ND_INPUT/*")


def test_step2_clear_nd_output(device):
    """PreCondition_2 — Clear ND_OUTPUT directory."""
    device.run("rm -rf /home/iriscli/ND_OUTPUT/*")


def test_step3_wait_while_creating_fake_run_state_files(device):
    """STEP_1 — Wait 40s while 24 fake RUN_STATE files are created, 1s apart, in the background."""
    # Device-clock epoch (ms) taken before any file is created: the log checks below only
    # consider lines logged after this point, never ones left over from earlier runs.
    device.variables["search_start_ts"] = device.get_current_time_epoch()["epoch_ms"]
    errors = []

    def _trigger():
        try:
            for _ in range(24):
                device.run(TRIGGER_CMD)
                time.sleep(1)
        except Exception as e:  # surfaced after the wait; thread exceptions are otherwise lost
            errors.append(e)

    thread = threading.Thread(target=_trigger, daemon=True)
    thread.start()
    time.sleep(40)
    thread.join(timeout=30)
    assert not thread.is_alive(), "File-creation trigger did not finish"
    assert not errors, f"File-creation trigger failed: {errors[0]!r}"


def test_step4_restart_scheduler_manager(device):
    """STEP_2 — Restart scheduler_manager service."""
    result = device.restart_service("scheduler_manager")
    assert result["status"] == "Pass", f"Failed to restart scheduler_manager: {result['details']}"


def test_step5_wait(device):
    """STEP_3 — Wait 20s."""
    time.sleep(20)


def _since_start(device, pattern):
    """grep the scheduler logs (current + rotated) for pattern, keeping only lines logged since
    the test started. Scheduler lines start with a UTC datetime ('2026-10-06 13:17:02,244 - ...')."""
    start_sec = int(device.variables["search_start_ts"]) // 1000
    return (
        f"grep -rh '{pattern}' {_SCHEDULER_LOG_DIR} 2>/dev/null | "
        f"awk -v ts=\"$(date -u -d @{start_sec} '+%Y-%m-%d %H:%M:%S')\" 'substr($0,1,19) >= ts' | sort"
    )


def test_step6_get_run_state_count(device):
    """STEP_4 — Get the latest RUN_STATE count logged since the test started."""
    cmd = _since_start(device, "RUN_STATE count =") + " | tail -n 1 | awk -F'=' '{print $3}' | xargs"
    run_state_count = (device.run(cmd) or "").strip()
    assert run_state_count, "RUN_STATE count not found"
    device.variables["run_state_count"] = run_state_count


def test_step7_verify_run_state_count_greater_than_15(device):
    """STEP_5 — Verify RUN_STATE count is greater than 15 (queue was fed >16 files)."""
    run_state_count = device.variables.get("run_state_count")
    print(f"RUN_STATE count = {run_state_count!r}")
    assert run_state_count and int(run_state_count) > 15, f"RUN_STATE count is less than 16: {run_state_count!r}"


def test_step8_verify_queue_overflow_logged(device):
    """STEP_6 — Verify the queue overflow error was logged since the test started."""
    # In the reference this step passes when the grep FINDS the overflow line (its status
    # condition is `!= "Fail"`, and grep exits non-zero only when nothing matches); the
    # RUN_STATE count in step 4 is itself taken from that overflow line.
    output = device.run(_since_start(device, "ERROR - Queue OVERFLOW") + " | tail -n 1")
    print(f"Queue overflow: {output}")
    assert output, "Queue Overflow not found"


def test_step9_verify_scheduler_not_crashing(device):
    """STEP_7 — Verify scheduler keeps completing file operations after copying observations (not crashing)."""
    for message in [
        "nd_file_operate_device: file operation complete",
        "syncing content to disk /home/ubuntu/.nddevice/observations",
    ]:
        result = device.run_command_iteratively(
            f"grep -h '{message}' {_SCHEDULER_MANAGER_LOG_DIR}/*.log 2>/dev/null | tail -1",
            iteration=18, timeout=10, not_desired_output=[""],
        )
        assert result["status"] == "Pass", f"'{message}' not found in scheduler_manager logs: {result['details']}"
        print(f"Latest '{message}': {result['output']}")


def test_step10_clear_nd_input(device):
    """PostCondition_1 — Clear ND_INPUT directory."""
    device.run("rm -rf /home/iriscli/ND_INPUT/*")


def test_step11_clear_nd_output(device):
    """PostCondition_2 — Clear ND_OUTPUT directory."""
    device.run("rm -rf /home/iriscli/ND_OUTPUT/*")
