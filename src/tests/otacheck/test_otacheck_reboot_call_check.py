"""
Feature: otacheck — OTA Call Decision After Reboot (no-reboot variant)
Description:
  Ported from nd_test_bot's TC_28_OTACHECK_REBOOTCALL_CHECK. The reference
  reboots the device and expects 'rebootTimeOta:True' and 'callOta = True'
  in otacheck's log within 2 mins of boot. FE has no device reboot
  mechanism, so the reboot itself is dropped and this verifies what can be
  observed on a running pod instead:
    1. otacheck evaluates its 'rebootTimeOta:<bool> or countFromFile:<bool>
       or uptimeOta:<bool>' decision line on every cycle.
    2. 'callOta = True' is present in otacheck's logs.
  'rebootTimeOta:True' itself can't be induced without a reboot, so it is
  NOT asserted here; the reboot-triggered path is uncovered.
"""

LOG_DIR = "/home/ubuntu/.nddevice/log/otacheck"
DECISION_LINE = "rebootTimeOta:"


def test_step1_verify_ota_decision_logged_each_cycle(device):
    """STEP 1 — Verify otacheck logs its rebootTimeOta/countFromFile/uptimeOta decision line (latest occurrence)."""
    output = device.run(f"grep -ah '{DECISION_LINE}' {LOG_DIR}/*.log 2>/dev/null | sort | tail -n 1")
    assert output and DECISION_LINE in output, f"'{DECISION_LINE}' decision line not found in otacheck logs."


def test_step2_verify_call_ota_logged(device):
    """STEP 2 — Verify 'callOta = True' is present in otacheck logs."""
    output = device.run(f"grep -ah 'callOta = True' {LOG_DIR}/*.log 2>/dev/null | tail -n 1")
    assert output and "callOta = True" in output, "'callOta = True' not found in otacheck logs."
