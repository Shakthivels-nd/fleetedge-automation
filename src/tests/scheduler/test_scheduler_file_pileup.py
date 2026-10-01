"""
Feature: Scheduler — File Pileup
Description:
  Verify inertial_obs.obsdata files don't pile up in ND_OUTPUT -- at most
  one should exist at any time.

  Ported from nd_test_bot's TC_1220_SCHEDULER_FILE_PILEUP. No sudo: the pod
  session already runs as root, and sudo isn't installed on these devices
  (same as every other awsiot/scheduler port in this repo).

  Uses device.run_command_iteratively (ported from nd_test_bot's
  Calculator_obj.run_command_iteratively, see device_test.py) with
  revert=True, matching the reference's exact call: the loop retries while
  the file count is "0" or "1" (i.e. no pileup so far), and only escapes
  early if the count becomes something else (pileup found). revert=True
  flips that outcome, since exhausting all retries while the count stayed
  in {"0", "1"} is the PASS condition (no pileup was ever observed) and an
  early-escape (count left {"0","1"}) is the FAIL condition (pileup found).

  Paths /home/iriscli/ND_INPUT, /home/iriscli/ND_OUTPUT, and the
  inertial_obs.obsdata filename (UNVERIFIED -- ported from reference, not
  yet confirmed on FE) need a live check before this test is trusted.
"""


def test_step1_clear_nd_input(device):
    """STEP_1 — Clear ND_INPUT directory."""
    device.run("rm -rf /home/iriscli/ND_INPUT/*")


def test_step1_1_clear_nd_output(device):
    """STEP_1_1 — Clear ND_OUTPUT directory."""
    device.run("rm -rf /home/iriscli/ND_OUTPUT/*")


def test_step2_verify_no_file_pileup(device):
    """STEP_2 — Verify inertial_obs.obsdata never accumulates beyond 1 file across 7 checks, 10s apart."""
    result = device.run_command_iteratively(
        "find /home/iriscli/ND_OUTPUT -name 'inertial_obs.obsdata' | wc -l",
        iteration=7, timeout=10, not_desired_output=["0", "1"], revert=True,
    )
    assert result["status"] == "Pass", f"File pileup found in inertial_obs: {result['details']}"
