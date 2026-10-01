"""
Feature: Scheduler — Deleter Deletes ND_OUTPUT/ND_INPUT Files
Description:
  Verify deleter logs successfully deleting the contents of both ND_OUTPUT
  and ND_INPUT.

  Ported from nd_test_bot's TC_1337_SCHEDULER_DELETERS_DELETES_ND_OUTPUT_ND_INPUT_FILES.

  Log strings "Deleted ND_OUTPUT contents: True" and "Deleted ND_INPUT
  contents: True" (UNVERIFIED -- ported from reference, not yet confirmed
  on FE) need a live check before this test is trusted.
"""


def test_step1_verify_nd_output_and_nd_input_deleted(device):
    """STEP_1 — Verify deleter logs deleting ND_OUTPUT and ND_INPUT contents."""
    for message in ["Deleted ND_OUTPUT contents: True", "Deleted ND_INPUT contents: True"]:
        output = device.search_log("/home/ubuntu/.nddevice/log/deleter", message, timeout=120, interval=20)
        assert output, f"'{message}' not found in deleter logs"
