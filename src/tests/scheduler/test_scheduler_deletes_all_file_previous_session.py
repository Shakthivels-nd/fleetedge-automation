"""
Feature: Scheduler — Deletes All Files From Previous Session
Description:
  Verify deleter logs deleting all files for a session (any session, not
  tied to a specific captured name).

  Ported from nd_test_bot's TC_1339_SCHEDULER_DELETES_ALL_FILE_PREVIOUS_SESSION.
  Simplified to a single step: grep for the generic "Files with names
  /home/iriscli/ND_INPUT/.* are deleted" pattern (session portion matched
  by ".*") via device.run_command_iteratively with not_desired_output=[""]
  (empty grep output drives the retry), piped through `tail -1` to capture
  only the latest matching deletion line.

  Log string "Files with names /home/iriscli/ND_INPUT/<session>* are
  deleted" (UNVERIFIED -- ported from reference, not yet confirmed on FE)
  needs a live check before this test is trusted.
"""

_LOG_DIR = "/home/ubuntu/.nddevice/log/deleter"


def test_step1_verify_session_files_deleted(device):
    """STEP_1 — Verify deleter logs deleting all files for a session."""
    result = device.run_command_iteratively(
        f"grep 'Files with names /home/iriscli/ND_INPUT/.* are deleted' {_LOG_DIR}/* 2>/dev/null | tail -1",
        iteration=6, timeout=15, not_desired_output=[""],
    )
    assert result["status"] == "Pass", f"Deleter failed to delete files for a session: {result['details']}"
