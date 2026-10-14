"""
Feature: AWSIOT — Verify Vehicle Class
Description:
  Verify the device's vehicle class (vehclass in deviceconfig.ini) is one of
  the known valid classes.
"""

VALID_CLASSES = {f"CLASS{n}" for n in (1, 2, 3, 4, 5, 6, 7, 8, 11)}


def test_step1_check_datetime(device):
    """Verify the device's vehicle class is one of the known valid classes.

    PreCondition_1 — Verify device datetime is in sync (non-blocking).
    """
    result = device.compare_datetime()
    if result["status"] != "Pass":
        print(f"datetime is incorrect: {result['details']}")


def test_step2_verify_vehicle_class(device):
    """STEP_1 — Verify vehclass in deviceconfig.ini is a valid class."""
    output = device.run("grep -i '^vehclass' /home/ubuntu/config/deviceconfig.ini")
    assert output and output.strip(), "vehclass not found in deviceconfig.ini"
    vclass = output.strip().split("=")[-1].strip().upper()
    assert vclass in VALID_CLASSES, f"Vehicle class is invalid: {vclass}"
