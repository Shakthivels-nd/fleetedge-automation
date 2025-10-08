import pytest, re
from pod_utils import connect_to_pod, run_command_on_pod, close_pod_connection, search_logs_in_pod, clean_output

# RUN: pytest -v --html=report.html --self-contained-html | tee pytest.log

@pytest.fixture(scope="module")
def pod_connection():
    """Fixture to set up and tear down the pod connection."""
    child = connect_to_pod("172.16.22.119")
    yield child
    close_pod_connection(child)


def test_connection_success(pod_connection):
    """Test: Verify pod connection was established successfully."""
    assert pod_connection.isalive(), "Pod connection failed — child process not active."

def test_data_disk_usage(pod_connection):
    """Test that /data usage does not exceed 10 GB."""
    output = run_command_on_pod(pod_connection, "du -sh /data")
    
    # Output example: '2.8G\t/data'
    size_str = output.split()[0]  # '2.8G'
    
    # Convert to GB
    if size_str.endswith("G"):
        size_gb = float(size_str[:-1])
    elif size_str.endswith("M"):
        size_gb = float(size_str[:-1]) / 1024
    elif size_str.endswith("K"):
        size_gb = float(size_str[:-1]) / (1024*1024)
    else:  # assume bytes
        size_gb = float(size_str) / (1024*1024*1024)
    
    assert size_gb <= 10, f"/data usage is {size_gb:.2f} GB — exceeds 10 GB limit!"


def test_files_present_by_grep(pod_connection):
    """Check if files starting with 0_trip or 1_trip and ending with .mp4 or .zip exist."""

    directories = [
        "/home/iriscli/files",
        "/media/SdCard"
    ]

    patterns = [r"0_trip.*.mp4", r"1_trip.*.mp4"]

    for directory in directories:
        for pattern in patterns:
            cmd = f"ls {directory} | grep -E '{pattern}' | wc -l"
            output = run_command_on_pod(pod_connection, cmd).strip()
            
            # Extract first number from output
            match = re.search(r'\d+', output)
            count = int(match.group()) if match else 0

            assert count > 0, f"No files found in {directory} matching pattern: {pattern}"
            print(f"Found {count} files in {directory} for pattern '{pattern}'")

def test_expected_services_running(pod_connection):
    """Check if specific expected services are running."""

    expected_services = [
        "HealthStatsManager",
        "SendMetricgRPC",
        "nd_suspendresume",
        "nd_system_status",
        "service_mon",
        "analyticsService",
        "audioPlayback",
        "awsiot",
        "bagheera",
        "btfv",
        "circular_buffer",
        "inertialAnalyticsClient",
        "inwardAnalyticsClient",
        "outwardAnalyticsClient",
        "overspeedClient",
        "power_monitor",
        "scheduler_manager",
        "service_mon",
        "speed",
        "svc",
        "time_sync",
        "uploader",
    ]

    cmd = "supervisorctl status *"
    output = run_command_on_pod(pod_connection, cmd, 'ubuntu/.nddevice/latest/service/')
    output = clean_output(output)

    lines = output.splitlines()
    status_dict = {}
    for line in lines:
        parts = line.split()
        if len(parts) < 2:
            continue
        service_name = parts[0]
        status = parts[1]
        status_dict[service_name] = status

    for service in expected_services:
        service_status = status_dict.get(service, "NOT_FOUND")
        assert service_status == "RUNNING", f"Service '{service}' is not running (status: {service_status})"
        print(f"Service '{service}' is running")

# def test_search_logs_positive(pod_connection):
#     """✅ Test: Search for an expected log entry."""
#     result = search_logs_in_pod(pod_connection, "/home/ubuntu/.nddevice/latest/logs", "Alert sent to user", timeout=10)
#     assert result is not None, "❌ Expected log message not found in logs."


# def test_search_logs_negative(pod_connection):
#     """✅ Test: Ensure non-existent log entry returns None."""
#     result = search_logs_in_pod(pod_connection, "/home/ubuntu/.nddevice/latest/logs", "SomeFakeLogEntryXYZ", timeout=5)
#     assert result is None, "❌ Unexpectedly found a fake log entry!"
