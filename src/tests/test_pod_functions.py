import pytest, re, configparser, io
from src.utils.pod_utils import connect_to_pod, run_command_on_pod, close_pod_connection, search_logs_in_pod, clean_output, verify_file_presence

# RUN:  pytest src/tests/ -v --capture=tee-sys --html=src/reports/report.html --self-contained-html | tee pytest.log

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


def test_mp4_files_present(pod_connection):
    """Check if files starting with 0_trip or 1_trip and ending with .mp4 or .zip exist."""

    directories = [
        "/home/iriscli/files",
        "/media/SdCard"
    ]

    patterns = [r"0_trip.*.mp4", r"1_trip.*.mp4"]

    results =  verify_file_presence(pod_connection, directories, patterns)
    for result in results:
        directory = result["directory"]
        pattern = result["pattern"]
        count = result["count"]
        assert count > 0, f"No files matching '{pattern}' found in {directory}"
        print(f"Found {count} files matching '{pattern}' in {directory}")

def test_expected_services_running(pod_connection):
    """Check if specific expected services are running."""

    expected_services = [
        "HealthStatsManager",
        "SendMetricgRPC",
        "analyticsService",
        "audioPlayback",
        "awsiot",
        "bagheera",
        "btfv",
        "circular_buffer",
        "inwardAnalyticsClient",
        "nd_fe_alerts",
        "nd_suspendresume",
        "nd_system_status",
        "outwardAnalyticsClient",
        "podlogger",
        "power_monitor",
        "scheduler_manager",
        "service_mon",
        "speed",
        "svc",
        "time_sync",
        "unifiedAnalyticsClient",
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

def test_ini_fields_present(pod_connection):
    """
    Test to verify that all expected fields are present in device .ini files inside the pod.
    Uses Python's built-in configparser to parse the .ini contents.
    """
    ini_files = [
        "/home/ubuntu/config/deviceconfig.ini",
        "/home/ubuntu/.nddevice/nddevice.ini"
    ]

    expected_fields = {
        "deviceconfig.ini": {
            "identity": ["deviceid", "sessionid", "devicetype", "devicesubtype"],
            "vehicle": ["vehclass"],
            "cleanup": ["lanecal", "savemp4"]
        },
        "nddevice.ini": {
            "version": ["nddevice", "state"],
            "upgrade": ["nddevice", "state"],
            "other": ["state"]
        }
    }
    for ini_file in ini_files:
        filename = ini_file.split("/")[-1]
        cmd = f"cat {ini_file}"
        output = run_command_on_pod(pod_connection, cmd)
        output = clean_output(output)

        config = configparser.ConfigParser()
        config.read_file(io.StringIO(output))

        for section, fields in expected_fields.get(filename, {}).items():
            assert config.has_section(section), f"Section '{section}' missing in {filename}"
            for field in fields:
                assert config.has_option(section, field), f"Field '{field}' missing in section '{section}' of {filename}"
                value = config.get(section, field)
                assert value, f"Field '{field}' in section '{section}' of {filename} is empty"
                print(f"Field '{field}' in section '{section}' of {filename} has value: {value}")
 
def test_gen_useralert_and_video_upload(pod_connection):
    """Test: Generate a user alert log entry."""
    cmd = "./gen_ualert.sh"
    output = run_command_on_pod(pod_connection, cmd, "/home/ubuntu/.nddevice/latest/service/bagheera")
    assert "User alert is generated..!!!" in output, "Expected confirmation message not found in output"
    print("User alert log entry generated successfully.")

    found_event_upload = search_logs_in_pod(pod_connection, "/home/ubuntu/.nddevice/log/unifieduploader", "Upload successful for 0_trip", timeout=600, interval=10)
    assert found_event_upload is not None, "Upload successful log entry not found within timeout period."

    file = found_event_upload.split()[-1]
    print(f"Upload successful log entry found, file: {file}")

    awsiot_req_found = search_logs_in_pod(pod_connection, "/home/ubuntu/.nddevice/log/awsiot", f"sending REQ_UPLOAD_VOD to uploader for file: /media/SdCard/{file}", timeout=600, interval=10)
    assert awsiot_req_found is not None, "REQ_UPLOAD_VOD log entry not found within timeout period."
    print("REQ_UPLOAD_VOD log entry found successfully.")

    video_upload_found = search_logs_in_pod(pod_connection, "/home/ubuntu/.nddevice/log/unifieduploader", f"Upload successful for video: /media/SdCard/{file}", timeout=600, interval=10)
    assert video_upload_found is not None, "Video upload log entry not found within timeout period."
    print("Video upload log entry found successfully.")


def test_inward_video_file_encryption(pod_connection):
    """Test: Verify that video files in /media/SdCard are encrypted (not plain .mp4)."""
    cmd = "ffprobe /home/iriscli/files/1_trip*.mp4 2>&1 | grep -q 'moov atom not found' && echo 'True' || echo 'False'"
    output = run_command_on_pod(pod_connection, cmd).strip()
    
    assert output == "True", "Inward Video files are encrypted as expected."
    print("Video files are encrypted as expected.")

def test_outward_video_file_encryption(pod_connection):
    """Test: Verify that video files in /media/SdCard are encrypted (not plain .mp4)."""
    cmd = "ffprobe /home/iriscli/files/0_trip*.mp4 2>&1 | grep -q 'moov atom not found' && echo 'True' || echo 'False'"
    output = run_command_on_pod(pod_connection, cmd).strip()
    
    assert output == "True", "Outward Video files are encrypted as expected."
    print("Video files are encrypted as expected.")


def test_size_of_outward_mp4_file_before_alert_is_8bytes(pod_connection):
    """Test: Check size of mp4 files before generating user alert."""
    cmd = "ls -lh /home/iriscli/files/0_trip*.mp4 | awk '{print $5}'"
    output = run_command_on_pod(pod_connection, cmd).strip()
    
    size_str = output.split()[0]  # e.g., '500M'
    
    # convert to bytes
    if size_str.endswith("G"):
        size_bytes = float(size_str[:-1]) * (1024**3)
    elif size_str.endswith("M"):
        size_bytes = float(size_str[:-1]) * (1024**2)
    elif size_str.endswith("K"):
        size_bytes = float(size_str[:-1]) * 1024
    else:  # assume bytes
        size_bytes = float(size_str)

    assert size_bytes == 8, f"Size of mp4 file is {size_bytes} bytes, expected 8 bytes before alert generation."
    print(f"Size of mp4 file before alert generation is {size_bytes} bytes as expected.")

def test_size_of_inward_mp4_file_before_alert_is_8bytes(pod_connection):
    """Test: Check size of mp4 files before generating user alert."""
    cmd = "ls -lh /home/iriscli/files/1_trip*.mp4 | awk '{print $5}'"
    output = run_command_on_pod(pod_connection, cmd).strip()
    
    size_str = output.split()[0]  # e.g., '500M'
    
    # convert to bytes
    if size_str.endswith("G"):
        size_bytes = float(size_str[:-1]) * (1024**3)
    elif size_str.endswith("M"):
        size_bytes = float(size_str[:-1]) * (1024**2)
    elif size_str.endswith("K"):
        size_bytes = float(size_str[:-1]) * 1024
    else:  # assume bytes
        size_bytes = float(size_str)

    assert size_bytes == 8, f"Size of mp4 file is {size_bytes} bytes, expected 8 bytes before alert generation."
    print(f"Size of mp4 file before alert generation is {size_bytes} bytes as expected.")

def test_size_of_outward_mp4_file_after_alert_is_greter_than_44MB(pod_connection):
    """Test: Check size of mp4 files after generating user alert."""
    generated = run_command_on_pod(pod_connection, "./gen_ualert.sh", "/home/ubuntu/.nddevice/latest/service/bagheera")
    assert generated is not None, "User alert generation command executed."

    found = search_logs_in_pod(pod_connection, "/home/ubuntu/.nddevice/log/unifieduploader", "VOD req received", timeout=600, interval=10)
    assert found is not None, "VOD req received log entry found within timeout period."

    cmd = r"grep -oP '(?<=Copied )\d+(?=bytes)' /home/ubuntu/.nddevice/log/unifieduploader/* | sed 's/.*://' | sort -n | uniq | tail -1"
    output = run_command_on_pod(pod_connection, cmd)
    
    size_str = output.split()[0]  # e.g., '500M'
    print(f"Output size string: {size_str}")
    # convert to megabytes
    size_mb = float(size_str) / (1024**2)

    assert 42 < size_mb < 44, f"Size of mp4 file is {size_mb:.2f} MB, expected greater than 44 MB after alert generation."
    print(f"Size of mp4 file after alert generation is {size_mb:.2f} MB as expected.")

def test_size_of_inward_mp4_file_after_alert_is_with_14MB_and_15MB(pod_connection):
    """Test: Check size of mp4 files after generating user alert."""
    generated = run_command_on_pod(pod_connection, "./gen_ualert.sh", "/home/ubuntu/.nddevice/latest/service/bagheera")
    assert generated is not None, "User alert generation command executed."

    found = search_logs_in_pod(pod_connection, "/home/ubuntu/.nddevice/log/unifieduploader", "VOD req received", timeout=600, interval=10)
    assert found is not None, "VOD req received log entry found within timeout period."

    cmd = r"grep -oP '(?<=Copied )\d+(?=bytes)' /home/ubuntu/.nddevice/log/unifieduploader/* | sed 's/.*://' | sort -n | uniq | head -1"
    output = run_command_on_pod(pod_connection, cmd).strip()
    
    size_str = output.split()[0]  # e.g., '500M'
    
    # convert to megabytes
    size_mb = float(size_str) / (1024**2)
    assert 14 < size_mb < 15, f"Size of mp4 file is {size_mb:.2f} MB, expected between 14 MB and 15 MB after alert generation."
    print(f"Size of mp4 file after alert generation is {size_mb:.2f} MB as expected.")


# def test_search_logs_negative(pod_connection):
#     """✅ Test: Ensure non-existent log entry returns None."""
#     result = search_logs_in_pod(pod_connection, "/home/ubuntu/.nddevice/latest/logs", "SomeFakeLogEntryXYZ", timeout=5)
#     assert result is None, "❌ Unexpectedly found a fake log entry!"
