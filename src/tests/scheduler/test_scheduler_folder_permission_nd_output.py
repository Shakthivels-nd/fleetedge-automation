"""
Feature: Scheduler — Folder Permission In ND_OUTPUT
Description:
  Verify the count of root-owned top-level folders in ND_OUTPUT.

  Ported from nd_test_bot's TC_1371_SCHEDULER_FOLDER_PERMISION_ND_OUTPUT.
  Ported literally: the reference's own pass condition is count != "1" (not
  == "0"), which reads oddly for a test titled "verify whether any folder
  has root permissions" -- kept as-is per user instruction rather than
  reinterpreting the reference's intent. Flagging for the user to verify
  this is the actual intended behavior, not a reference bug.
"""


def test_step1_restart_bagheera(device):
    """PreCondition_1 — Restart bagheera service."""
    result = device.restart_service("bagheera")
    assert result["status"] == "Pass", f"Failed to restart bagheera service: {result['details']}"


def test_step2_verify_root_owned_folder_count(device):
    """STEP_1 — Verify the root-owned folder count in ND_OUTPUT is not exactly 1 (ported literally, see module docstring)."""
    output = device.run("find /home/iriscli/ND_OUTPUT -maxdepth 1 -user root | wc -l")
    folder_count = (output or "").strip()
    assert folder_count != "1", "Folder with root permissions are not found in ND_OUTPUT Path"
