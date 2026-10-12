"""
Feature: Scheduler — Detailed Copy Obs Generation
Description:
  Verify a minified copy of the inertial obs zip is generated after inertial
  processing completes.

  Ported from nd_test_bot's TC_1296_SCHEDULER_DETAILED_COPY_OBS_GENERATION.
  Uses device.run_command_iteratively (ported name/signature from
  nd_test_bot's Calculator_obj.run_command_iteratively) with no
  not_desired_output, matching the reference's call exactly: it retries up
  to 10 times (10s apart) until the grep command's own output is non-empty
  (grep exits non-zero / empty on no match, which run_command_iteratively's
  "not in []" check always accepts on the first successful match).

  Log string "obsZipDestFile size: /home/ubuntu/.nddevice/inertial_obs" is
  verified on FE. The reference's `b'` prefix (a Python bytes repr) does not
  appear in FE's log, so it is omitted from the grep.
"""


def test_step1_verify_minified_obs_copy_generated(device):
    """STEP_1 — Verify inference_inertial logs the minified obs zip destination file."""
    result = device.run_command_iteratively(
        "grep -inr \"obsZipDestFile size: /home/ubuntu/.nddevice/inertial_obs\" /home/ubuntu/.nddevice/log/inference_inertial/inference_inertial.log",
        iteration=10, timeout=10, not_desired_output=[""],
    )
    assert result["status"] == "Pass", f"Minified copy of obs is not generated: {result['details']}"
