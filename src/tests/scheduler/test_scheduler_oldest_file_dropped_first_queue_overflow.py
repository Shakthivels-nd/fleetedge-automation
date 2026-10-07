"""
Feature: Scheduler — Oldest File Dropped First On Queue Overflow
Description:
  Verify the oldest session is dropped first when the scheduler's queue
  overflows (more than 16 fake RUN_STATE files created).

  Ported from nd_test_bot's TC_1445_SCHEDULER_OLDEST_FILE_DROPPED_FIRST_QUEUE_OVERFLOW.
  Uses the same fake-file-creation loop as
  test_scheduler_queue_overflow_more_files_run_state.py (see that file's
  docstring for why this isn't a new framework API). `systemctl restart
  scheduler_manager` replaced with device.restart_service.

  Log strings "RUN_STATE count =" and "ERROR - Queue OVERFLOW" (UNVERIFIED
  -- ported from reference, not yet confirmed on FE) need a live check
  before this test is trusted.
"""

import time


_SCHEDULER_LOG_DIR = "/home/ubuntu/.nddevice/log/scheduler"


def _since_start(device, pattern):
    """grep the scheduler logs (current + rotated) for pattern, keeping only lines logged since
    the test started, oldest first. Scheduler lines start with a UTC datetime
    ('2026-10-06 13:17:02,244 - ...'), so a plain sort orders them chronologically."""
    start_sec = int(device.variables["search_start_ts"]) // 1000
    return (
        f"grep -rh '{pattern}' {_SCHEDULER_LOG_DIR} 2>/dev/null | "
        f"awk -v ts=\"$(date -u -d @{start_sec} '+%Y-%m-%d %H:%M:%S')\" 'substr($0,1,19) >= ts' | sort"
    )


_COUNT = " | awk -F'=' '{print $3}' | xargs"


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


def test_step1_clear_nd_input(device):
    """PreCondition_1 — Clear ND_INPUT directory."""
    device.run("rm -rf /home/iriscli/ND_INPUT/*")


def test_step2_clear_nd_output(device):
    """PreCondition_2 — Clear ND_OUTPUT directory."""
    device.run("rm -rf /home/iriscli/ND_OUTPUT/*")


def test_step3_wait(device):
    """PreCondition_3 — Wait 120s."""
    time.sleep(120)


def test_step4_create_25_fake_run_state_files(device):
    """STEP_1 — Create 25 fake RUN_STATE files in ND_INPUT, 0.5s apart."""
    # Device-clock epoch (ms) before any file is created: the log checks below only consider
    # lines logged after this point, never ones left over from earlier runs.
    device.variables["search_start_ts"] = device.get_current_time_epoch()["epoch_ms"]
    _create_files_in_loop(device, num_files=25, sleep_seconds=0.5)


def test_step5_restart_scheduler_manager(device):
    """STEP_3 — Restart scheduler_manager service."""
    device.restart_service("scheduler_manager")


def test_step6_wait(device):
    """STEP_3_1 — Wait 5s."""
    time.sleep(5)


def test_step7_get_run_state_count(device):
    """STEP_4 — Get the latest RUN_STATE count logged since the test started."""
    result = device.run_command_iteratively(
        _since_start(device, "RUN_STATE count =") + " | tail -n 1" + _COUNT,
        iteration=13, timeout=5, not_desired_output=[""],
    )
    assert result["status"] == "Pass", f"RUN_STATE count not found: {result['details']}"
    device.variables["run_state_count"] = result["output"]


def test_step8_verify_run_state_count_greater_than_15(device):
    """STEP_6 — Check RUN_STATE count is greater than 15 (queue was fed >16 files)."""
    # The reference's fail_method for this step is action "continue": it logs the
    # message but does not stop the test, so this is deliberately non-fatal.
    run_state_count = device.variables.get("run_state_count")
    if not (run_state_count and int(run_state_count) > 15):
        print(f"RUN_STATE count is less than 16: {run_state_count!r}")


def test_step9_verify_queue_overflow_logged(device):
    """STEP_7 — Verify the queue overflow error was logged since the test started."""
    # In the reference this step passes when the grep FINDS the overflow line (its status
    # condition is `!= "Fail"`, and grep exits non-zero only when nothing matches).
    output = device.run(_since_start(device, "ERROR - Queue OVERFLOW") + " | tail -n 1")
    print(f"Queue overflow: {output}")
    assert output, "Queue Overflow not found"


def test_step10_get_oldest_run_state_count(device):
    """STEP_8 — Get the oldest (first-logged since start) RUN_STATE count."""
    output = device.run(_since_start(device, "RUN_STATE count =") + " | head -n 1" + _COUNT)
    run_state_count_oldest = (output or "").strip()
    assert run_state_count_oldest, "Oldest file not found"
    device.variables["run_state_count_oldest"] = run_state_count_oldest


def test_step11_get_newest_run_state_count(device):
    """STEP_9 — Get the second-oldest (next-logged since start) RUN_STATE count."""
    output = device.run(_since_start(device, "RUN_STATE count =") + " | head -n 2 | tail -n 1" + _COUNT)
    run_state_count_newest = (output or "").strip()
    assert run_state_count_newest, "Newest file not found"
    device.variables["run_state_count_newest"] = run_state_count_newest


def test_step12_verify_oldest_file_dropped_first(device):
    """STEP_10 — Verify the newest count is >= the oldest count (oldest file dropped first)."""
    newest = int(device.variables["run_state_count_newest"])
    oldest = int(device.variables["run_state_count_oldest"])
    assert newest >= oldest, "Older file is not dropped first"


def test_step13_clear_nd_input(device):
    """PostCondition_1 — Clear ND_INPUT directory."""
    device.run("rm -rf /home/iriscli/ND_INPUT/*")


def test_step14_clear_nd_output(device):
    """PostCondition_2 — Clear ND_OUTPUT directory."""
    device.run("rm -rf /home/iriscli/ND_OUTPUT/*")
