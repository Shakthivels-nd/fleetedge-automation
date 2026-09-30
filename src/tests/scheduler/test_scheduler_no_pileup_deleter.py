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


def test_step12_verify_deleter_deleted_first_session(device):
    """STEP_9 — Verify deleter logs deleting the first session's files."""
    session_name_first = device.variables.get("session_name_first")
    output = device.search_log("/home/ubuntu/.nddevice/log/deleter", f"Files with names /home/iriscli/ND_INPUT/{session_name_first}", timeout=30, interval=5)
    assert output, "Session name first files are not deleted by deleter"


def test_step13_verify_deleter_deleted_second_session(device):
    """STEP_10 — Verify deleter logs deleting the second session's files."""
    session_name_second = device.variables.get("session_name_second")
    output = device.search_log("/home/ubuntu/.nddevice/log/deleter", f"Files with names /home/iriscli/ND_INPUT/{session_name_second}", timeout=30, interval=5)
    assert output, "Session name second files are not deleted by deleter"
