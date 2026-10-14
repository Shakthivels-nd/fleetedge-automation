"""
Feature: AWSIOT — Check Certificates
Description:
  Verify all expected certificate/key files are present on disk:
  certificate.pem.crt, ed25519key.pem, private.pem.key, pub-ed25519.pem,
  root-CA.crt. (cacert.pem is not present on FE devices, unlike the
  reference framework's TC_975 — dropped.)
"""

CERT_DIR = "/home/ubuntu/.nddevice/certificate"


def test_step1_check_datetime(device):
    """Verify all expected certificate/key files are present on disk.

    PreCondition_1 — Verify device datetime is in sync (non-blocking).
    """
    result = device.compare_datetime()
    if result["status"] != "Pass":
        print(f"datetime is incorrect: {result['details']}")


def _verify_present(device, filename):
    output = device.run(f"[ -f {CERT_DIR}/{filename} ] && echo exists || echo missing")
    assert output and output.strip() == "exists", f"{filename} is not present"


def test_step2_verify_certificate_pem_crt(device):
    """STEP_1 — Verify certificate.pem.crt is present."""
    _verify_present(device, "certificate.pem.crt")


def test_step3_verify_ed25519key_pem(device):
    """STEP_2 — Verify ed25519key.pem is present."""
    _verify_present(device, "ed25519key.pem")


def test_step4_verify_private_pem_key(device):
    """STEP_3 — Verify private.pem.key is present."""
    _verify_present(device, "private.pem.key")


def test_step5_verify_pub_ed25519_pem(device):
    """STEP_4 — Verify pub-ed25519.pem is present."""
    _verify_present(device, "pub-ed25519.pem")


def test_step6_verify_root_ca_crt(device):
    """STEP_5 — Verify root-CA.crt is present."""
    _verify_present(device, "root-CA.crt")
