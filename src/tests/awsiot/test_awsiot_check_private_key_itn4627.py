"""
Feature: AWSIOT — Check Private Key
Description:
  Verify the device private key (ed25519key.pem) is present on disk.
"""


def test_step1_check_datetime(device):
    """Verify the device private key (ed25519key.pem) is present on disk.

    PreCondition_1 — Verify device datetime is in sync (non-blocking).
    """
    result = device.compare_datetime()
    if result["status"] != "Pass":
        print(f"datetime is incorrect: {result['details']}")


def test_step2_verify_private_key_present(device):
    """STEP_1 — Verify ed25519key.pem exists."""
    output = device.run("sh -c 'if [ -f /home/ubuntu/.nddevice/certificate/ed25519key.pem ]; then echo 1; else echo 0; fi'")
    assert output and output.strip() == "1", "Private key is not present"
