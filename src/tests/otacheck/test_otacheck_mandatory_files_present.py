"""
Feature: otacheck — Mandatory Files Present
Description:
  Ported from nd_test_bot's TC_32_OTACHECK_CHECK_MANDATORYFILES_POST_EVERYREBOOT,
  from STEP_6 onward (the /dev/shm path used on FE; STEP_3-5's
  /dev/shm/nd_files_c path is not used on FE). The reference reboots the
  device first; FE has no reboot mechanism, so the reboot and its 30s wait
  are dropped and this only verifies the files exist on the running pod —
  NOT that they are recreated after a reboot.
"""

SHM_DIR = "/dev/shm"


def _assert_file_exists(device, name):
    path = f"{SHM_DIR}/{name}"
    result = device.check_file_availability(path)
    assert result["status"] == "Pass", f"{path} does not exist: {result}"


def test_step1_otacheck_pid_exists(device):
    """STEP 1 — Verify /dev/shm/otacheck.pid exists."""
    _assert_file_exists(device, "otacheck.pid")


def test_step2_otacheck_state_exists(device):
    """STEP 2 — Verify /dev/shm/otacheck_state.txt exists."""
    _assert_file_exists(device, "otacheck_state.txt")


def test_step3_otacheck_count_exists(device):
    """STEP 3 — Verify /dev/shm/otacheck_count.txt exists."""
    _assert_file_exists(device, "otacheck_count.txt")
