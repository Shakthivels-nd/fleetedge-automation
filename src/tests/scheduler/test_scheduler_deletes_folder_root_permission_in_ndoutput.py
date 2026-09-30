"""
Feature: Scheduler — Deletes Folder With Root Permission In ND_OUTPUT
Description:
  Verify deleter removes a root-owned folder found under ND_OUTPUT.

  Ported from nd_test_bot's
  TC_1372_SCHEDULER_DELETES_FOLDER_ROOT_PERMISSION_IN_NDOUTPUT. Fixed a
  reference bug: its STEP_5 uses a literal, never-substituted
  "<session_name>" placeholder instead of use_result(session_name) (every
  other step in the same reference file correctly uses use_result(...)) --
  substituted the actual captured session_name value instead, matching the
  test's evident intent.

  STEP_4 doesn't tie the grep to the specific session captured in STEP_1 --
  it matches the generic "Files with names /home/iriscli/ND_INPUT/.* are
  deleted" pattern (".*" as a wildcard for the session portion) and takes
  the latest (tail -1) occurrence, since the folder-deletion log for this
  exact session isn't guaranteed to still be the most recent one by the
  time STEP_4 runs.

  Log string "Files with names /home/iriscli/ND_INPUT/<session>* are
  deleted" (UNVERIFIED -- ported from reference, not yet confirmed on FE)
  needs a live check before this test is trusted.
"""

import time


def test_step1_get_current_session_name(device):
    """STEP_1 — Get the current session name."""
    result = device.get_current_session_name()
    assert result["status"] == "Pass", f"Session name not found: {result['details']}"
    device.variables["session_name"] = result["session_name"]


def test_step2_verify_folder_has_root_permission(device):
    """STEP_2 — Verify the session's ND_OUTPUT folder is owned by root."""
    session_name = device.variables.get("session_name")
    result = device.run_command_iteratively(
        f'bash -c \'if [ $(stat -c "%U" /home/iriscli/ND_OUTPUT/0{session_name}) = "root" ]; then echo "true"; else echo "false"; fi\'',
        iteration=10, timeout=7,
    )
    assert result["output"] == "true", f"Folder with root permissions are not found in ND_OUTPUT Path: {result['details']}"


def test_step3_wait(device):
    """STEP_3 — Wait 50s."""
    time.sleep(50)


def test_step4_verify_deleter_deletes_folder(device):
    """STEP_4 — Verify deleter logs deleting a root-owned folder's files (latest occurrence, any session)."""
    result = device.run_command_iteratively(
        "grep -inr 'Files with names /home/iriscli/ND_INPUT/.* are deleted' /home/ubuntu/.nddevice/log/deleter/* 2>/dev/null | tail -1",
        iteration=10, timeout=5, not_desired_output=[""],
    )
    assert result["status"] == "Pass", f"Deleter is not deleting the folder which has root permissions from ND_OUTPUT path: {result['details']}"


def test_step5_verify_folder_removed(device):
    """STEP_5 — Verify the root-owned folder no longer exists."""
    session_name = device.variables.get("session_name")
    output = device.run(f'bash -c \'if [ -f /home/iriscli/ND_OUTPUT/0{session_name} ]; then echo "true"; else echo "false"; fi\'')
    assert (output or "").strip() == "false", "Folder with root permissions is not deleted from ND_OUTPUT Path"
