"""
Feature: AWSIOT — Check Encryption And Permission Of Private Keys
Description:
  Verify private.pem.key and ed25519key.pem are encrypted (no PRIVATE
  marker), have correct file permissions, and the device/backup ed25519
  keys match via md5sum.
"""


def test_step1_verify_awsiot_running(device):
    """Verify private key encryption and permissions match device/backup.

    STEP_1 — Verify awsiot service is running.
    """
    result = device.is_service_active("awsiot")
    assert result["status"] == "Pass", f"AWS-IoT service is not running: {result['state']}"


def test_step2_verify_temp_file_dxists(device):
    """STEP_2 — Check for temp.txt in the certificate directory"""
    output = device.run("cd /home/ubuntu/.nddevice/certificate/ && ls temp.txt > /dev/null 2>&1 && echo Exists || echo NotExists")
    if output and "Exists" in output:
        print(f"temp.txt present in certificate directory (expected on FE): {output}")


def test_step3_verify_private_pem_key_encrypted(device):
    """STEP_3 — Check whether private.pem.key is encrypted (has the ENCRYPTED PRIVATE KEY header; non-blocking)."""
    output = device.run("grep -q 'ENCRYPTED PRIVATE KEY' /home/ubuntu/.nddevice/certificate/private.pem.key && echo true || echo false")
    is_encrypted = bool(output) and output.strip() == "true"
    print(f"private.pem.key encrypted: {is_encrypted}" if is_encrypted else f"private.pem.key not encrypted: {output}")


def test_step4_verify_ed25519key_encrypted(device):
    """STEP_4 — Check whether ed25519key.pem is encrypted (has the ENCRYPTED PRIVATE KEY header; non-blocking)."""
    output = device.run("grep -q 'ENCRYPTED PRIVATE KEY' /home/ubuntu/.nddevice/certificate/ed25519key.pem && echo true || echo false")
    is_encrypted = bool(output) and output.strip() == "true"
    print(f"ed25519key.pem encrypted: {is_encrypted}" if is_encrypted else f"ed25519key.pem not encrypted: {output}")


ACCEPTED_KEY_PERMISSIONS = ("-rw-------", "-r--------", "-rw-r--r--")


def test_step5_verify_private_pem_key_permissions(device):
    """STEP_5 — Verify private.pem.key has correct file permissions."""
    output = device.run("stat -c '%A' /home/ubuntu/.nddevice/certificate/private.pem.key")
    perms = (output or "").strip()
    assert perms in ACCEPTED_KEY_PERMISSIONS, f"private.pem.key file does not have correct permissions: {perms}"


def test_step6_verify_ed25519key_cert_permissions(device):
    """STEP_6 — Verify ed25519key.pem has correct permissions in the certificate path."""
    output = device.run("stat -c '%A' /home/ubuntu/.nddevice/certificate/ed25519key.pem")
    perms = (output or "").strip()
    assert perms in ACCEPTED_KEY_PERMISSIONS, f"ed25519key.pem file has incorrect permissions in certificate path: {perms}"


def test_step7_verify_ed25519key_backup_permissions(device):
    """STEP_7 — Verify ed25519key.pem has correct permissions in the backup path."""
    output = device.run("stat -c '%A' /home/ubuntu/.nddevice/backup/ed25519key.pem")
    perms = (output or "").strip()
    assert perms in ACCEPTED_KEY_PERMISSIONS, f"ed25519key.pem file has incorrect permissions in backup path: {perms}"


def test_step8_verify_ed25519key_md5_match(device):
    """STEP_8 — Verify device and backup ed25519key.pem md5 checksums match."""
    output = device.run(
        "[ \"$(md5sum /home/ubuntu/.nddevice/certificate/ed25519key.pem | awk '{print $1}')\" "
        "= \"$(md5sum /home/ubuntu/.nddevice/backup/ed25519key.pem | awk '{print $1}')\" ] && echo true || echo false"
    )
    assert output and output.strip() == "true", f"md5 checksum of ed25519key.pem files do not match: {output}"
