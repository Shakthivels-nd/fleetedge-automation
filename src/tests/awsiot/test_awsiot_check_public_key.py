"""
Feature: AWSIOT — Check Public Key
Description:
  Verify the device public key (pub-ed25519.pem) is present on disk.
"""


def test_step1_check_datetime(device):
    """Verify the device public key (pub-ed25519.pem) is present on disk.

    PreCondition_1 — Verify device datetime is in sync (non-blocking).
    """
    result = device.compare_datetime()
    if result["status"] != "Pass":
        print(f"datetime is incorrect: {result['details']}")


def test_step2_verify_public_key_present(device):
    """STEP_1 — Verify pub-ed25519.pem exists."""
    output = device.run("sh -c 'if [ -f /home/ubuntu/.nddevice/certificate/pub-ed25519.pem ]; then echo 1; else echo 0; fi'")
    assert output and output.strip() == "1", "Public key is not present"
