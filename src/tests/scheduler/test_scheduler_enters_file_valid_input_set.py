"""
Feature: Scheduler — Enters File Valid Input Set
Description:
  Verify scheduler generates a checksum + metadata file pair in ND_INPUT
  and then accepts that pair as a valid input set.

  Ported from nd_test_bot's TC_1227_SCHEDULER_ENTERS_FILE_VALID_INPUT_SET.
  No sudo (pod session already runs as root). Uses
  device.run_command_iteratively (ported name/signature from nd_test_bot's
  Calculator_obj.run_command_iteratively) to poll for each file's
  appearance, matching the reference's iteration/timeout counts exactly.

  Path /home/iriscli/ND_INPUT, the *.chm.* checksum / *_ymetadata.txt
  metadata filename patterns, and the log string "Inside filename
  /home/iriscli/ND_INPUT" (UNVERIFIED -- ported from reference, not yet
  confirmed on FE) need a live check before this test is trusted.
"""

import time


def test_step1_clear_nd_input(device):
    """STEP_1 — Clear ND_INPUT directory."""
    device.run("rm -rf /home/iriscli/ND_INPUT/*")


def test_step2_verify_checksum_file_created(device):
    """STEP_2 — Verify a checksum (*.chm.*) file is created in ND_INPUT."""
    result = device.run_command_iteratively(
        "ls /home/iriscli/ND_INPUT/*.chm.* | wc -l",
        iteration=11, timeout=10, not_desired_output=["0"],
    )
    assert result["status"] == "Pass", f"Checksum file not created in ND_INPUT directory: {result['details']}"


def test_step3_verify_metadata_file_created(device):
    """STEP_3 — Verify a metadata (*_ymetadata.txt) file is created in ND_INPUT."""
    result = device.run_command_iteratively(
        "ls /home/iriscli/ND_INPUT/*_ymetadata.txt | wc -l",
        iteration=3, timeout=5, not_desired_output=["0"],
    )
    assert result["status"] == "Pass", f"Metadata file not created in ND_INPUT directory: {result['details']}"


def test_step3_1_wait(device):
    """STEP_3_1 — Wait 15s for scheduler to process the input set."""
    time.sleep(15)


def test_step4_verify_scheduler_enters_valid_input_set(device):
    """STEP_4 — Verify scheduler logs entering the file as a valid input set from ND_INPUT."""
    output = device.search_log("/home/ubuntu/.nddevice/log/scheduler", "Inside filename /home/iriscli/ND_INPUT", timeout=30, interval=5)
    assert output, "Scheduler did not enter file as valid input set received from ND_INPUT"
