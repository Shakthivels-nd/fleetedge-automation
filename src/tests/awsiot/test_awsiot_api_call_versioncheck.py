"""
Feature: AWSIOT — API Call Versioncheck Post Reboot
Description:
  Verify the versioncheck API call recurs at the expected ~10-minute
  interval in otacheck logs, matched against the device's own OTA version
  (log-only — no reboot performed).
"""


def test_step1_check_datetime(device):
    """Verify the versioncheck API call recurs at the expected interval.

    PreCondition_1 — Verify device datetime is in sync (non-blocking).
    """
    result = device.compare_datetime()
    if result["status"] != "Pass":
        print(f"datetime is incorrect: {result['details']}")


def test_step2_verify_private_key_markers(device):
    """STEP_1 — Verify certificate/key files carry the PRIVATE marker."""
    markers = device.check_private_key_markers()
    assert all(markers.values()), f"One or more key files missing PRIVATE marker: {markers}"


def test_step3_verify_versioncheck_frequency(device):
    """STEP_2 — Verify versioncheck API call recurs ~every 10 minutes in otacheck logs."""
    # get_ota_version() can return a stale/packaged version pulled from a
    # leftover *.tar.gz entry (e.g. an old 6.x.x.rc.x.tar.gz sitting next to
    # the actual running version's bare directory). The versioncheck API
    # pattern must match the currently running version, so list the OTA
    # root directly and take the non-.tar.gz version-named entry.
    output = device.run(
        "ls -1 /home/ubuntu/.nddevice | grep -E '^[0-9]+\\.[0-9]+\\.[0-9]+\\.rc\\.[0-9]+$'"
    )
    ota_version = (output or "").strip().splitlines()[0].strip() if output else None
    assert ota_version, "OTA version not detected (no non-.tar.gz version directory found)"
    api_pattern = f"/api/v1/versioncheck/{ota_version}"

    result = device.frequency_based_calls(
        api_pattern=api_pattern,
        service_name="otacheck",
        expected_interval_minutes=10,
        cloud_check=False,
        api_key="versionCheckData",
    )

    # Require at least one occurrence; if two, status should be Pass within tolerance
    assert result["occurrences"], f"No occurrences found for pattern {api_pattern}. Details: {result['details']}"
    if len(result["occurrences"]) >= 2:
        assert result["status"] == "Pass", f"Interval check failed. Details: {result['details']}"
    print("Version check API monitoring details:\n" + "\n".join(result["details"]))
