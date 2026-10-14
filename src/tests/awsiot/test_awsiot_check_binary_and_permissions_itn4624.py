"""
Feature: AWSIOT — Check Binary And Permissions
Description:
  Verify AwsIotWrapper and registerDevice are valid ELF binaries with
  executable permissions.
"""


def test_step1_verify_awsiot_running(device):
    """Verify AwsIotWrapper and registerDevice are ELF binaries with executable permissions.

    STEP_1 — Verify awsiot service is running.
    """
    result = device.is_service_active("awsiot")
    assert result["status"] == "Pass", f"AWS-IoT service is not running: {result['state']}"


def test_step2_verify_awsiotwrapper_is_binary(device):
    """STEP_2 — Verify AwsIotWrapper file is in ELF binary format."""
    output = device.run("head -c 4 /home/ubuntu/.nddevice/latest/service/awsiot/AwsIotWrapper | od -An -t x1 | tr -d ' '")
    assert output and output.strip() == "7f454c46", f"AwsIotWrapper file is not in Binary format: {output}"


def test_step3_verify_registerdevice_is_binary(device):
    """STEP_3 — Verify registerDevice file is in ELF binary format."""
    output = device.run("head -c 4 /home/ubuntu/.nddevice/latest/service/awsiot/registerDevice | od -An -t x1 | tr -d ' '")
    assert output and output.strip() == "7f454c46", f"registerDevice file is not in Binary format: {output}"


def test_step4_verify_awsiotwrapper_permissions(device):
    """STEP_4 — Verify AwsIotWrapper file has executable permissions."""
    output = device.run("stat -c '%A' /home/ubuntu/.nddevice/latest/service/awsiot/AwsIotWrapper")
    assert output and "x" in output, f"AwsIotWrapper file does not have executable permissions: {output}"


def test_step5_verify_registerdevice_permissions(device):
    """STEP_5 — Verify registerDevice file has executable permissions."""
    output = device.run("stat -c '%A' /home/ubuntu/.nddevice/latest/service/awsiot/registerDevice")
    assert output and "x" in output, f"registerDevice file does not have executable permissions: {output}"
