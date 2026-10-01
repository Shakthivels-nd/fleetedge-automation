"""
Feature: Scheduler — Partial File Process After Linux Signal Crash
Description:
  Verify partial files are processed after scheduler_manager crashes
  (SIGKILL) and supervisor restarts it.

  Ported from nd_test_bot's TC_1431_SCHEDULER_PARTIAL_FILE_PROCESS_LINUX_SIGN_CRASH.
  No device reboot needed here (unlike the sibling TC_1430/TC_1432 in this
  batch) -- this test kills scheduler_manager's own process directly, which
  FE's supervisor auto-restarts, matching the reference's crash/recovery
  scenario without needing device-level reboot tracking.

  Log string "Inside filename /home/iriscli/ND_INPUT/<session>" (UNVERIFIED
  -- ported from reference, not yet confirmed on FE) needs a live check
  before this test is trusted.
"""

import time


def test_step1_verify_bagheera_active(device):
    """PreCondition_2 — Verify bagheera service is RUNNING."""
    result = device.is_service_active("bagheera")
    assert result["status"] == "Pass", f"bagheera is not RUNNING: {result['state']}"


def test_step2_capture_session_name(device):
    """STEP_1 — Capture the current session name."""
    cmd = (
        "( timeout 170 tail -F /home/ubuntu/.nddevice/log/ndcentral/* 2>/dev/null | "
        "grep --line-buffered -m 1 'creating folder for session' | "
        "awk -F'creating folder for session ' '{print $2}' | awk '{print $1}' ) 2>/dev/null"
    )
    output = device.run(cmd, timeout=180)
    session_name = (output or "").strip()
    assert session_name, f"Session name not found: {output!r}"
    device.variables["session_name"] = session_name


def test_step3_kill_scheduler_manager(device):
    """STEP_2/STEP_3 — Kill scheduler_manager's process (SIGKILL)."""
    pid = device.run("pidof scheduler_manager | tr ' ' '\\n' | sort -n | head -n 1")
    assert pid and pid.strip(), "Failed to get PID of scheduler_manager"
    device.run(f"kill -9 {pid.strip()}")


def test_step4_wait(device):
    """STEP_4 — Wait 15s."""
    time.sleep(15)


def test_step5_verify_scheduler_manager_active_again(device):
    """STEP_7 — Verify scheduler_manager is active again after the crash (supervisor auto-restart)."""
    result = device.is_service_active("scheduler_manager")
    assert result["status"] == "Pass", f"Scheduler Manager service is not active: {result['state']}"


def test_step6_wait(device):
    """STEP_8 — Wait 70s."""
    time.sleep(70)


def test_step7_verify_partial_files_processed(device):
    """STEP_9 — Verify scheduler logs processing the partial file from the crashed session."""
    session_name = device.variables.get("session_name")
    output = device.run(f"grep -inr 'Inside filename /home/iriscli/ND_INPUT/0{session_name}' /home/ubuntu/.nddevice/log/scheduler/*")
    assert output, "Partial files are not processed"
