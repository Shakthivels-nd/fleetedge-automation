from src.utils.engine.connection import clean_output


def test_btfv_service_status(device):
    """Check that the btfv service is running (no other checks required)."""
    cmd = "supervisorctl status btfv"
    output = device.run(cmd, "/home/ubuntu/.nddevice/latest/service/")
    output = clean_output(output)

    status = "NOT_FOUND"
    for line in output.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] == "btfv":
            status = parts[1]
            break

    assert status == "RUNNING", f"Service 'btfv' is not running (status: {status})"
