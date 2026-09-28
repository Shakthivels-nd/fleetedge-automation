"""
AWSIOT — Verify KA Certificate Check
"""


def test_step1_set_ka_cert_check_disabled(device):
    """Verify AWSIOT certificate-check-disabled-on-keep-alive-api.

    PreCondition_1 — Set certificate-check-disabled-on-keep-alive-api to True via cloud.
    """
    success, status = device.toggle_ka_certificate_check(disabled=True)
    assert success, f"Failed to set ka_certificate_check_disabled: status={status}"


def test_step2_restart_awsiot(device):
    """STEP_1 — Restart awsiot service."""
    device.variables["search_start_ts"] = device.get_current_time_epoch()["epoch_ms"]
    result = device.restart_service("awsiot")
    assert result["status"] == "Pass", f"Failed to restart awsiot service: {result['details']}"


def test_step3_verify_certificate_check(device):
    """STEP_2 — Verify certificate-check-disabled-on-keep-alive-api log entry."""
    ts = device.variables.get("search_start_ts")
    output = device.search_log("/home/ubuntu/.nddevice/log/awsiot", "certificate-check-disabled-on-keep-alive-api found:", start_timestamp=ts)
    assert output, "certificate-check-disabled-on-keep-alive-api not found in awsiot logs"
    assert "unknown" not in output.lower(), f"certificate-check-disabled-on-keep-alive-api is unknown: '{output}'"


def test_step4_restore_ka_cert_check(device):
    """PostCondition_1 — Restore certificate-check-disabled-on-keep-alive-api to False."""
    device.toggle_ka_certificate_check(disabled=False)
