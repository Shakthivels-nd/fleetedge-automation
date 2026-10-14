"""
Feature: Scheduler — State Files New Session
Description:
  Verify the scheduler process checks files in all known states (NEW,
  RUN, UPLOAD, DELETE, RUN_FAILED, UPLOAD_FAILED).

  Ported from nd_test_bot's TC_1373_SCHEDULER_STATE_FILES_NEW_SESSION.

  Uses device.run_command_iteratively with not_desired_output=[""] so an
  empty grep (no match yet) is what drives the retry, rather than passing
  immediately on the first attempt. Each grep is piped through `tail -1`
  to capture only the latest matching log line. Original
  search_log(timeout, interval) pairs are preserved as
  (iteration=timeout/interval, timeout=interval).

  Log strings (UNVERIFIED -- ported from reference, not yet confirmed on FE)
  need a live check before this test is trusted.
"""

_LOG_DIR = "/home/ubuntu/.nddevice/log/scheduler"


def test_step1_verify_new_state_checked(device):
    """STEP_1 — Verify scheduler logs entering check_new_state."""
    result = device.run_command_iteratively(
        f"grep -h 'Entering:::check_new_state' {_LOG_DIR}/*.log 2>/dev/null | tail -1",
        iteration=6, timeout=20, not_desired_output=[""],
    )
    assert result["status"] == "Pass", f"Failed to check new state: {result['details']}"


def test_step2_verify_all_states_checked(device):
    """STEP_2 — Verify scheduler logs checking files in every known state."""
    for message in [
        "We have files in NEW_STATE",
        "We have files in RUN_STATE",
        "files in UPLOAD_STATE",
        "files in DELETE_STATE",
        "files in RUN_FAILED_STATE",
        "files in UPLOAD_FAILED_STATE",
    ]:
        result = device.run_command_iteratively(
            f"grep -h '{message}' {_LOG_DIR}/*.log 2>/dev/null | tail -1",
            iteration=4, timeout=10, not_desired_output=[""],
        )
        assert result["status"] == "Pass", f"'{message}' not found in scheduler logs: {result['details']}"
