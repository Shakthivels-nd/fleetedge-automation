"""
Feature: Scheduler — No File Pileup From Deleter
Description:
  Verify there is no file pileup in ND_INPUT for two consecutive sessions
  (confirming deleter successfully deletes each session's files).

  Ported from nd_test_bot's TC_1483_SCHEDULER_NO_PILEUP_DELETER.
"""

import time


def test_step1_clear_nd_input(device):
    """PreCondition_1 — Clear ND_INPUT directory."""
    device.run("rm -rf /home/iriscli/ND_INPUT/*")


def test_step2_clear_nd_output(device):
    """PreCondition_2 — Clear ND_OUTPUT directory."""
    device.run("rm -rf /home/iriscli/ND_OUTPUT/*")


def test_step3_wait(device):
    """PreCondition_3 — Wait 30s."""
    time.sleep(30)


def test_step4_get_first_session_name(device):
    """STEP_1 — Get the current session name (non-blocking)."""
    result = device.get_current_session_name(cam_num=0)
    if result["status"] != "Pass":
        print(f"First session name not found: {result['details']}")
    device.variables["session_name_first"] = result.get("session_name")


def test_step5_restart_bagheera_first(device):
    """STEP_2 — Restart bagheera service."""
    device.variables["restart_first_ts"] = device.get_current_time_epoch()["epoch_ms"]  # device-clock epoch ms, just before the first restart
    result = device.restart_service("bagheera")
    assert result["status"] == "Pass", f"Failed to restart bagheera service: {result['details']}"


def test_step6_get_second_session_name(device):
    """STEP_3 — Get the current session name (non-blocking)."""
    result = device.get_current_session_name(cam_num=0)
    if result["status"] != "Pass":
        print(f"Second session name not found: {result['details']}")
    device.variables["session_name_second"] = result.get("session_name")


def test_step7_wait(device):
    """STEP_4 — Wait 10s."""
    time.sleep(10)


def test_step8_restart_bagheera_second(device):
    """STEP_5 — Restart bagheera service again."""
    device.variables["restart_second_ts"] = device.get_current_time_epoch()["epoch_ms"]  # device-clock epoch ms, just before the second restart
    result = device.restart_service("bagheera")
    assert result["status"] == "Pass", f"Failed to restart bagheera service: {result['details']}"


def test_step9_wait(device):
    """STEP_6 — Wait 90s."""
    time.sleep(90)


def test_step10_verify_no_file_pile_first_session(device):
    """STEP_7 — Verify no leftover files for the first session in ND_INPUT."""
    session_name_first = device.variables.get("session_name_first")
    assert session_name_first, "session_name_first was not captured"
    output = device.run(f"bash -c '[[ -e /home/iriscli/ND_INPUT/{session_name_first}* ]] && echo true || echo false'")
    assert (output or "").strip() == "false", "File pile due to deleter couldn't delete the files"


def test_step11_verify_no_file_pile_second_session(device):
    """STEP_8 — Verify no leftover files for the second session in ND_INPUT."""
    session_name_second = device.variables.get("session_name_second")
    assert session_name_second, "session_name_second was not captured"
    output = device.run(f"bash -c '[[ -e /home/iriscli/ND_INPUT/{session_name_second}* ]] && echo true || echo false'")
    assert (output or "").strip() == "false", "File pile due to deleter couldn't delete the files"


_DELETER_LOG_DIR = "/home/ubuntu/.nddevice/log/deleter"


def _wait_for_deleter_line(device, session_name, since_ts_ms):
    """Poll (up to 30 x 10s) for the deleter's "Files with names <session>* are deleted" line logged
    since since_ts_ms. Searches the current AND rotated deleter logs (deleter.log.<date>), unlike
    device.search_log whose `*.log` glob skips rotated files. Deleter lines start with a UTC datetime."""
    start_sec = int(since_ts_ms) // 1000
    cmd = (
        f"grep -rh 'Files with names /home/iriscli/ND_INPUT/{session_name}' {_DELETER_LOG_DIR} 2>/dev/null | "
        f"awk -v ts=\"$(date -u -d @{start_sec} '+%Y-%m-%d %H:%M:%S')\" 'substr($0,1,19) >= ts' | tail -n 1"
    )
    return device.run_command_iteratively(cmd, iteration=30, timeout=10, not_desired_output=[""])


def test_step12_verify_deleter_deleted_first_session(device):
    """STEP_9 — Verify deleter logs deleting the first session's files."""
    session_name_first = device.variables.get("session_name_first")
    restart_first_ts = device.variables.get("restart_first_ts")
    assert restart_first_ts, "restart_first_ts was not captured before the first restart"
    result = _wait_for_deleter_line(device, session_name_first, restart_first_ts)
    assert result["status"] == "Pass", f"Session name first files are not deleted by deleter: {result['details']}"
    print(f"Deleter line: {result['output']}")


def test_step13_verify_deleter_deleted_second_session(device):
    """STEP_10 — Verify deleter logs deleting the second session's files."""
    session_name_second = device.variables.get("session_name_second")
    restart_second_ts = device.variables.get("restart_second_ts")
    assert restart_second_ts, "restart_second_ts was not captured before the second restart"
    result = _wait_for_deleter_line(device, session_name_second, restart_second_ts)
    assert result["status"] == "Pass", f"Session name second files are not deleted by deleter: {result['details']}"
    print(f"Deleter line: {result['output']}")
