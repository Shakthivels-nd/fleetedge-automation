from src.utils.engine.connection import clean_output


def test_power_monitor_service_status(device):
    """Check that the power_monitor service is running (no other checks required)."""
    cmd = "supervisorctl status power_monitor"
    output = device.run(cmd, "/home/ubuntu/.nddevice/latest/service/")
    output = clean_output(output)

    status = "NOT_FOUND"
    for line in output.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] == "power_monitor":
            status = parts[1]
            break

    assert status == "RUNNING", f"Service 'power_monitor' is not running (status: {status})"
