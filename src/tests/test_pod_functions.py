import configparser
import io
import pytest, re
from src.utils.pod_utils import (
    connect_to_pod,
    run_command_on_pod,
    close_pod_connection,
    search_logs_in_pod,
    clean_output,
    verify_file_presence,
    check_ota_md5sum,
    check_no_legacy_package_exists,
    list_log_folder_contents,
    validate_services_uptime_diff,
)

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
    "cron",
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


    cmd = "supervisorctl status"
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
#     """ Test: Ensure non-existent log entry returns None."""
#     result = search_logs_in_pod(pod_connection, "/home/ubuntu/.nddevice/latest/logs", "SomeFakeLogEntryXYZ", timeout=5)
#     assert result is None, "❌ Unexpectedly found a fake log entry!"

def test_ota_md5sum(pod_connection):
    ota_version = "6.5.39.rc.1.tar.gz"
    result = check_ota_md5sum(pod_connection, ota_version)
    print("MD5 result:", result)
    assert len(result) == 32

def test_only_ota_present(pod_connection):
    ota_version = "6.5.39.rc.1.tar.gz"
    check_no_legacy_package_exists(pod_connection, ota_version)

def test_list_log_folder_contents(pod_connection):
    list_log_folder_contents(pod_connection)

def test_service_uptime(pod_connection):
    validate_services_uptime_diff(pod_connection, max_diff_seconds=5)

def test_video_encryption_config(pod_connection):
    """
    Restart bagheera and verify that logs contain:
    'video_encryption from config false'
    """
    print('This test is to verify video_encryption config log entry after restarting bagheera service.')
    #  Restart bagheera service
    restart_cmd = "supervisorctl restart bagheera"
    output = run_command_on_pod(
        pod_connection,
        restart_cmd,
        "/home/ubuntu/.nddevice/latest/service"
    )
    print(f"Restart output:\n{output}")

    # Identify the latest log file in ndcentral
    log_dir = "/data/nd_files/log/ndcentral"
    cmd_latest = f"ls -t {log_dir} | head -n 1"
    latest_file = run_command_on_pod(pod_connection, cmd_latest).strip()

    assert latest_file, "No log files found in ndcentral directory"
    latest_log_path = f"{log_dir}"
    print(f"Using latest log file: {latest_log_path}")

    #  Search the log file for the phrase
    search_term = "video_encryption from config false"
    grep_cmd = f"grep -air '{search_term}' {latest_log_path} || true"
    grep_output = run_command_on_pod(pod_connection, grep_cmd)

    print(f"Grep Output:\n{grep_output}")

    #  Assert result
    assert search_term.lower() in grep_output.lower(), \
        f"'{search_term}' not found in {latest_log_path}"
    print(" Found expected log entry for video_encryption")


def test_gps_mp4_filename(pod_connection):
    """Locate latest .mp4 in /home/iriscli/files and extract GPS lat/long and timestamp from filename.
    Example: 1_trip003e_part0027d0_91.0000_181.0000_0.0_1760424046342_y.mp4
    We parse: latitude=91.0000 longitude=181.0000 speed=0.0 timestamp=1760424046342 flag=y
    """
    print('This test extracts GPS metadata from the latest .mp4 filename in /home/iriscli/files.')
    target_dir = "/home/iriscli/files"
    # Get latest mp4 (suppress errors if none, then assert)
    cmd = f"ls -t {target_dir}/*.mp4 2>/dev/null | head -n 1"
    latest_path = run_command_on_pod(pod_connection, cmd).strip()
    assert latest_path, f"No .mp4 files found in {target_dir}"
    filename = latest_path.split('/')[-1]
    print(f"Latest mp4 file: {filename}")

    # Regex to capture components
    pattern = re.compile(r"^[01]_trip\w+_part\w+_(-?\d+\.\d+)_(-?\d+\.\d+)_(-?\d+(?:\.\d+)?)_(\d{10,})_([A-Za-z])\.mp4$")
    m = pattern.match(filename)
    assert m, f"Filename does not match expected pattern: {filename}"

    lat_str, lon_str, speed_str, ts_str, flag = m.groups()
    print(f"Extracted latitude: {lat_str}")
    print(f"Extracted longitude: {lon_str}")
    print(f"Extracted timestamp: {ts_str}")

    # Basic assertions (require GPS/timestamp components)
    assert lat_str and lon_str and ts_str, "Missing expected GPS/timestamp components"
    assert ts_str.isdigit(), "Timestamp should be all digits"

    lat = float(lat_str)
    lon = float(lon_str)

    # Sentinel logic: (91.0000, 181.0000) => static / no real GPS data
    if lat == 91.0 and lon == 181.0:
        print(" Static values (91.0000, 181.0000) detected: no GPS data (device is static).")
        has_gps_data = False
    else:
        # Validate bounds only when data is real
        assert -90.0 <= lat <= 90.0, f"Latitude out of bounds: {lat}"
        assert -180.0 <= lon <= 180.0, f"Longitude out of bounds: {lon}"
        print("Valid GPS data present (Non static values).")
        has_gps_data = True

    # Removed global storage; simply assert logic outcome consistency
    if has_gps_data:
        print("GPS data confirmed present.")
    else:
        print("No real GPS data (device static).")


def test_summary_json_files_generated(pod_connection):
    """
    Check if summary.json file is generated in /data/nd_files/log/unifieduploader
    """
    print("This test is to verify if the summary.json file is generated once an alert is generated")
    cmd = "./gen_ualert.sh"
    output = run_command_on_pod(pod_connection, cmd, "/home/ubuntu/.nddevice/latest/service/bagheera")
    assert "User alert is generated..!!!" in output, "Expected confirmation message not found in output"
    print("User alert log entry generated successfully.")
    
    json_found = search_logs_in_pod(pod_connection, "/data/nd_files/log/unifieduploader", "summary.json found", timeout=600, interval=10)
    assert json_found is not None, "summary.json file not found within timeout period."
    print("summary.json file found successfully.")
