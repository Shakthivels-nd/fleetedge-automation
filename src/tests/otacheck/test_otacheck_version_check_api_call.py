"""
Feature: otacheck — Version Check API Call Successful
Description:
  Ported from nd_test_bot's TC_73_OTACHECK_VERSIONCHECKAPI_INTERNET_STABILITY_60MIN,
  STEP_11 only (user decision 2026-10-08), with the version check API call
  detected the same way sanity does (test_api_call_version_check_itn2633):
  the API pattern is /api/v1/versioncheck/<ota_version>, where ota_version
  comes from the installed version folder (not the .tar.gz package).

  The reference first removes the default route, waits, restores
  networking and injects counter=10; none of that is ported (see
  PORT_TRACKER.csv), so this does NOT prove the call succeeds after
  internet unavailability — only that the latest version check API call is
  in otacheck's logs and succeeded (JWT response code = 1).
"""

LOG_DIR = "/home/ubuntu/.nddevice/log/otacheck"


def test_step1_get_ota_version(device):
    """STEP 1 — Get the device's OTA version from the installed version folder."""
    ota_version = device.get_ota_version(folders_only=True)
    assert ota_version, "OTA version not detected on the pod."
    device.variables["ota_version"] = ota_version


def test_step2_verify_version_check_api_call(device):
    """STEP 2 — Verify the latest /api/v1/versioncheck/<ota_version> call is logged by otacheck."""
    ota_version = device.variables.get("ota_version")
    assert ota_version, "ota_version not set from STEP 1."
    api_pattern = f"/api/v1/versioncheck/{ota_version}"
    result = device.event_based_api_call(api_pattern=api_pattern, service_name="otacheck")
    assert result["status"] == "Pass", f"Version check API call '{api_pattern}' not found in otacheck logs. Details: {result['details']}"
    print("Version check API call details:\n" + "\n".join(result["details"]))


def test_step3_verify_version_check_response(device):
    """STEP 3 — Verify the latest JWT response code = 1 and versioncheckresponse.txt download in otacheck logs."""
    missing = []
    for term in ["JWT response code = 1", "wget -O", "versioncheckresponse.txt"]:
        output = device.run(f"grep -ah '{term}' {LOG_DIR}/*.log 2>/dev/null | sort | tail -n 1")
        if not (output and term in output):
            missing.append(term)
    assert not missing, f"Not found in otacheck logs: {missing}"
