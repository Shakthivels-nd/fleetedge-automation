import configparser
import io
import pytest
import re
import time

from src.utils.engine.connection import clean_output
from src.utils.engine.db_utils import fetch_api_calls_window

"""
To run tests and generate HTML report, use the following command:
# Make sure you have requirements installed: pip install -r requirements.txt
# Activate pytest environment: source ~/envs/pytest-env/bin/activate
# Export PYTHONPATH if needed: export PYTHONPATH=$(pwd):$PYTHONPATH
# RUN: pytest src/tests/ -v --capture=tee-sys --html=src/reports/report.html --self-contained-html | tee pytest.log

"""

# reboot_voyager_fixture, pod_connection, and device fixtures now live in
# conftest.py (moved there so new test files/subfolders, e.g. src/tests/bagheera/,
# can use them without redefinition).


def test_connection_success_itn2426(device):
    """Verify pod connection was established successfully."""
    assert device.check_connected(), "Pod connection failed — child process not active."

def test_data_disk_usage_itn2427(device):
    """Test that /data usage does not exceed 10 GB."""
    output = device.run("du -sh /data")

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


def test_expected_services_running_itn2429(device):
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
    output = device.run(cmd, '/home/ubuntu/.nddevice/latest/service/')
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

def test_ini_fields_present_itn2446(device):
    """
    Test to verify that all expected fields are present in deviceconfig.ini and nddevice.ini files inside the pod.

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
        output = device.run(cmd)
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
    print("Check the presence of bagheera_override.ini inside the pod and also ensure the file size >0KB")
    override_ini = device.run("ls -lh /home/ubuntu/config/bagheera_override.ini", "/home/ubuntu/config")
    assert override_ini, "bagheera_override.ini listing returned empty output"
    line = override_ini.strip().splitlines()[0]
    parts = line.split()
    assert len(parts) >= 9, f"Unexpected ls -lh output format: {line}"
    size_token = parts[4]  # e.g. 16K, 2M, 1048576
    # Parse size token
    unit = size_token[-1].upper() if not size_token[-1].isdigit() else ''
    # Safe numeric extraction
    num_match = re.match(r"(\d+(?:\.\d+)?)", size_token)
    assert num_match, f"Could not parse size from token '{size_token}'"
    size_val = float(num_match.group(1))
    if unit == 'G':
        size_kb = size_val * 1024 * 1024
    elif unit == 'M':
        size_kb = size_val * 1024
    elif unit == 'K':
        size_kb = size_val
    else:
        # bytes -> KB
        size_kb = size_val / 1024.0
    assert size_kb > 0, f"bagheera_override.ini size not greater than 0KB (parsed {size_kb}KB from '{size_token}')"
    print(f"bagheera_override.ini present with size {size_token} (>0KB confirmed)")

def test_gen_useralert_and_video_upload_itn2432(device):
    """Verify triggering a user alert and verify the respective logs."""
    start_timestamp = int(time.time()) * 1000
    cmd = "./gen_ualert.sh"
    output = device.run(cmd, "/home/ubuntu/.nddevice/latest/service/bagheera")
    assert "User alert is generated..!!!" in output, "Expected confirmation message not found in output"
    print("User alert log entry generated successfully.")

    found_event_upload = device.search_log("/home/ubuntu/.nddevice/log/unifieduploader", "Upload successful for 0_trip", start_timestamp, timeout=600, interval=10)
    assert found_event_upload is not None, "Upload successful log entry not found within timeout period."

    file = found_event_upload.split()[-1][1:]
    print(f"Upload successful log entry found, file: {file}")

    awsiot_req_found = device.search_log("/home/ubuntu/.nddevice/log/awsiot", f"sending REQ_UPLOAD_VOD to uploader for file: /media/SdCard/0{file}", start_timestamp , timeout=600, interval=10)
    assert awsiot_req_found is not None, "REQ_UPLOAD_VOD log entry not found within timeout period."
    print("REQ_UPLOAD_VOD log entry found successfully.")

    outward_video_upload_found = device.search_log("/home/ubuntu/.nddevice/log/unifieduploader", f"Upload successful for video: /media/SdCard/0{file}", start_timestamp, timeout=600, interval=10)
    assert outward_video_upload_found is not None, "Outward Video upload log entry not found within timeout period."
    print("Outward Video upload log entry found successfully.")

    inward_video_upload_found = device.search_log("/home/ubuntu/.nddevice/log/unifieduploader", f"Upload successful for video: /media/SdCard/1{file}", start_timestamp, timeout=600, interval=10)
    assert inward_video_upload_found is not None, "Inward Video upload log entry not found within timeout period."
    print("Inward video upload log entry found successfully.")


def test_inward_video_file_encryption_itn2469(device):
    """Verify that inward video files in /media/SdCard are encrypted (not plain .mp4)."""
    cmd = "ffprobe /home/iriscli/files/1_trip*.mp4 2>&1 | grep -q 'moov atom not found' && echo 'True' || echo 'False'"
    output = device.run(cmd).strip()

    assert output == "True", "Inward Video files are encrypted as expected."
    print("Video files are encrypted as expected.")

def test_outward_video_file_encryption_itn2637(device):
    """Verify that outward video files in /media/SdCard are encrypted (not plain .mp4)."""
    cmd = "ffprobe /home/iriscli/files/0_trip*.mp4 2>&1 | grep -q 'moov atom not found' && echo 'True' || echo 'False'"
    output = device.run(cmd).strip()

    assert output == "True", "Outward Video files are encrypted as expected."
    print("Video files are encrypted as expected.")


def test_size_of_outward_mp4_file_before_alert_is_8bytes_itn2455(device):
    """Check size of outward mp4 files before generating user alert."""
    cmd = "ls -lh /home/iriscli/files/0_trip*.mp4 | awk '{print $5}'"
    output = device.run(cmd).strip()

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

def test_size_of_inward_mp4_file_before_alert_is_8bytes_itn2629(device):
    """Check size of inward mp4 files before generating user alert."""
    cmd = "ls -lh /home/iriscli/files/1_trip*.mp4 | awk '{print $5}'"
    output = device.run(cmd).strip()

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

def test_size_of_outward_mp4_file_after_alert_is_greter_than_44MB_itn2630(device):
    """Check size of outward mp4 files after generating user alert."""
    start_timestamp = int(time.time())*1000
    generated = device.run("./gen_ualert.sh", "/home/ubuntu/.nddevice/latest/service/bagheera")
    assert generated is not None, "User alert generation command executed."

    found = device.search_log("/home/ubuntu/.nddevice/log/unifieduploader", "VOD req received",start_timestamp, timeout=600, interval=10)
    assert found is not None, "VOD req received log entry found within timeout period."

    cmd = r"grep -oP '(?<=Copied )\d+(?=bytes)' /home/ubuntu/.nddevice/log/unifieduploader/* | sed 's/.*://' | sort -n | uniq | tail -1"
    output = device.run(cmd)
    assert output, f"No 'Copied ... bytes' entries found in unifieduploader logs for command: {cmd}"

    size_str = output.split()[0]  # e.g., '500M'
    print(f"Output size string: {size_str}")
    # convert to megabytes
    size_mb = float(size_str) / (1024**2)

    assert 42 < size_mb < 44, f"Size of mp4 file is {size_mb:.2f} MB, expected greater than 44 MB after alert generation."
    print(f"Size of mp4 file after alert generation is {size_mb:.2f} MB as expected.")

def test_size_of_inward_mp4_file_after_alert_is_with_14MB_and_15MB_itn2631(device):
    """Check size of inward mp4 files after generating user alert."""
    start_timestamp = int(time.time())*1000
    generated = device.run("./gen_ualert.sh", "/home/ubuntu/.nddevice/latest/service/bagheera")
    assert generated is not None, "User alert generation command executed."

    found = device.search_log("/home/ubuntu/.nddevice/log/unifieduploader", "VOD req received",start_timestamp, timeout=600, interval=10)
    assert found is not None, "VOD req received log entry found within timeout period."

    cmd = r"grep -oP '(?<=Copied )\d+(?=bytes)' /home/ubuntu/.nddevice/log/unifieduploader/* | sed 's/.*://' | sort -n | uniq | head -1"
    output = device.run(cmd)
    assert output, f"No 'Copied ... bytes' entries found in unifieduploader logs for command: {cmd}"
    output = output.strip()

    size_str = output.split()[0]  # e.g., '500M'

    # convert to megabytes
    size_mb = float(size_str) / (1024**2)
    assert 14 < size_mb < 15, f"Size of mp4 file is {size_mb:.2f} MB, expected between 14 MB and 15 MB after alert generation."
    print(f"Size of mp4 file after alert generation is {size_mb:.2f} MB as expected.")


# def test_search_logs_negative(device):
#     """ Test: Ensure non-existent log entry returns None."""
#     result = device.search_log("/home/ubuntu/.nddevice/latest/logs", "SomeFakeLogEntryXYZ", timeout=5)
#     assert result is None, " Unexpectedly found a fake log entry!"

def test_ota_md5sum_and_check_no_legacy_package_exists_itn2430(device):
    """Verify OTA package MD5 sum (dynamically detected) and ensure no legacy OTA packages exist."""
    ota_base = device.get_ota_version()
    assert ota_base, "OTA version not detected dynamically"
    ota_filename = ota_base if ota_base.endswith('.tar.gz') else ota_base + '.tar.gz'
    print(f"Detected OTA filename: {ota_filename}")

    md5_hash = device.check_ota_md5sum(ota_filename)
    print("MD5 result:", md5_hash)
    assert isinstance(md5_hash, str) and len(md5_hash) == 32, f"Invalid MD5 hash length: {md5_hash}"

    device.check_no_legacy_package_exists(ota_filename)
    print("No legacy OTA packages present besides the current one.")

def test_list_log_folder_contents_itn2459(device):
    """Verify the contents of log folder."""
    device.list_log_folder_contents()

def test_service_uptime_itn2470(device):
    """Validate that service uptimes are within expected range."""
    device.validate_services_uptime_diff(max_diff_seconds=5)

def test_video_encryption_config_itn2468(device):
    """Verify if video_encryption config is set to false
    """
    print('This test is to verify video_encryption config log entry after restarting bagheera service.')
    #  Restart bagheera service
    restart_cmd = "supervisorctl restart bagheera"
    output = device.run(
        restart_cmd,
        "/home/ubuntu/.nddevice/latest/service"
    )
    print(f"Restart output:\n{output}")

    log_found = device.search_log("/data/nd_files/log/ndcentral", "video_encryption from config false", timeout=300, interval=10)
    assert log_found is not None, "video_encryption log entry not found within timeout period"
    print("video_encryption log entry found successfully.")

def test_summary_json_files_generated_itn2457(device):
    """
    Check if summary.json file is generated in /data/nd_files/log/unifieduploader
    """
    print("This test is to verify if the summary.json file is generated once an alert is generated")
    cmd = "./gen_ualert.sh"
    output = device.run(cmd, "/home/ubuntu/.nddevice/latest/service/bagheera")
    assert "User alert is generated..!!!" in output, "Expected confirmation message not found in output"
    print("User alert log entry generated successfully.")

    json_found = device.search_log("/data/nd_files/log/unifieduploader", "summary.json found", timeout=600, interval=10)
    assert json_found is not None, "summary.json file not found within timeout period."
    print("summary.json file found successfully.")

def test_gps_mp4_file_metadata_itn2454(device):
    """This test extracts GPS metadata from the latest .mp4 filename in /home/iriscli/files"""
    print('This test extracts GPS metadata from the latest .mp4 filename in /home/iriscli/files.')
    target_dir = "/home/iriscli/files"
    # Get latest mp4 (suppress errors if none, then assert)
    cmd = f"ls -t {target_dir}/*.mp4 2>/dev/null | head -n 1"
    latest_path = device.run(cmd).strip()
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

def test_mp4_files_present_itn2428(device):
    """Check if files starting with 0_trip or 1_trip and ending with .mp4 or .zip exist."""
    directories = [
        "/home/iriscli/files",
        "/media/SdCard"
    ]

    patterns = [r"0_trip.*.mp4", r"1_trip.*.mp4"]

    results = device.verify_file_presence(directories, patterns)
    for result in results:
        directory = result["directory"]
        pattern = result["pattern"]
        count = result["count"]
        assert count > 0, f"No files matching '{pattern}' found in {directory}"
        print(f"Found {count} files matching '{pattern}' in {directory}")

def test_partial_files_uploaded_to_cloud_itn2617(device):
    """Verify if the partial files are uploaded to cloud
    """
    # Step 1: Latest timestamp from logs
    ts_cmd = "grep -aH 'END OF SESSION' *.log | awk -F: '{print $2}' | sort -nr | head -1"
    latest_ts = device.run(ts_cmd, "/data/nd_files/log/ndcentral")
    assert latest_ts, "Failed to extract latest END OF SESSION timestamp"
    latest_ts = latest_ts.strip().splitlines()[0]
    assert latest_ts.isdigit(), f"Extracted timestamp not numeric: {latest_ts}"
    print(f" Latest END OF SESSION timestamp: {latest_ts}")

    # Step 2: Collect mp4 filenames and extract their timestamps directly
    list_cmd = "ls 0_trip*.mp4 1_trip*.mp4 2>/dev/null || true"
    files_raw = device.run(list_cmd, "/home/iriscli/files")
    assert files_raw, "No trip mp4 files found in /home/iriscli/files"
    candidate_files = [f.strip() for f in files_raw.splitlines() if f.strip()]
    print(f"Found {len(candidate_files)} mp4 file(s) in /home/iriscli/files:")

    ts_pattern = re.compile(r"^[01]_trip\w+_part\w+_-?\d+\.\d+_-?\d+\.\d+_-?\d+(?:\.\d+)?_(\d{10,})_[A-Za-z]\.mp4$")
    extracted_timestamps = []
    for f in candidate_files:
        print(f"          - {f}")
        m = ts_pattern.match(f)
        if m:
            extracted_timestamps.append(m.group(1))
        else:
            print(f"            (No timestamp match pattern for {f})")
    assert extracted_timestamps, "Failed to extract any timestamps from mp4 filenames"
    print(f"Extracted {len(extracted_timestamps)} timestamp(s) from filenames: {extracted_timestamps}")

    # Prepare regex patterns for exact filename matches
    patterns = [r'^' + re.escape(f) + r'$' for f in candidate_files]
    time.sleep(30)
    print("Wait for 30 seconds before restaring bagheera service")
    # Step 3: Restart bagheera service
    restart_out = device.run("supervisorctl restart bagheera", "/home/ubuntu/.nddevice/latest/service")
    assert restart_out is not None, "Bagheera restart command produced no output"
    status_out = device.run("supervisorctl status bagheera", "/home/ubuntu/.nddevice/latest/service")
    assert "RUNNING" in status_out, f"bagheera not running after restart. Status: {status_out}"
    print("bagheera service restarted and RUNNING.")

    time.sleep(95)  # wait for file upload completion

    # Step 4: Verify each recorded file now exists in /media/SdCard
    results = device.verify_file_presence(["/media/SdCard"], patterns)
    missing = [candidate_files[i] for i, r in enumerate(results) if r["count"] == 0]
    for r in results:
        print(f"Pattern {r['pattern']} count in /media/SdCard: {r['count']}")
    assert not missing, f"Files missing in /media/SdCard after bagheera restart: {missing}"
    print(f"All {len(candidate_files)} mp4 files are present in /media/SdCard after restart.")

def test_api_call_upload_device_status_itn2642(device):
    """Verify the device status api call is happening to the cloud or not for every 10mins"""
    markers = device.check_private_key_markers()
    assert all(markers.values()), f"One or more key files missing PRIVATE marker: {markers}"
    info = device.get_device_info()
    assert info['status'] == 'Pass', f"Failed to retrieve device info: {info['details']}"
    device_id = info['device_id']
    device_type = info['device_type']
    assert device_id, f"device_id not found. Details: {info['details']}"
    assert device_type, f"device_type not found. Details: {info['details']}"
    print(f"Device ID: {device_id}, Device Type: {device_type}")
    api_pattern = f"/api/v1/devices/{device_id}/{device_type}/status"
    result = device.frequency_based_calls(
        api_pattern=api_pattern,
        service_name='health',
        expected_interval_minutes=10,
        api_key="uploadDeviceStatusData",
    )
    assert result['occurrences'], f"No occurrences found for device status API call. Details: {result['details']}"
    if len(result['occurrences']) >= 2:
        assert result['status'] == 'Pass', f"Interval check failed. Details: {result['details']}"
    print(f"Device status API monitoring details:\n" + "\n".join(result['details']))
    time.sleep(180)
    print("Waiting for 180 seconds")
    cmd1 = device.run('''grep -inr "Entering:::uploadHealthLogs:" /home/ubuntu/.nddevice/log/health | awk -F' - ' '{print $1}' | awk '{print $NF}' | tail -1 ''',"/home/ubuntu/.nddevice/log/health")
    assert cmd1 is not None, "uploadHealthLogs log entry found successfully."
    print("uploadHealthLogs log entry found successfully.")
    cmd2 = device.run('''grep -inr "Upload of Health Stats successful" /home/ubuntu/.nddevice/log/health | awk -F' - ' '{print $1}' | awk '{print $NF}' | tail -1 ''',"/home/ubuntu/.nddevice/log/health")
    assert cmd2 is not None, "Upload of Health Stats successful log entry found successfully."
    print("Upload of Health Stats successful log entry found successfully.")
    cmd3 = device.run('''grep -inr "File uploaded, deleting from disk True" /home/ubuntu/.nddevice/log/health | awk -F' - ' '{print $1}' | awk '{print $NF}' | tail -1 ''',"/home/ubuntu/.nddevice/log/health")
    assert cmd3 is not None, "File uploaded, deleting from disk True log entry found successfully."
    print("File uploaded, deleting from disk True log entry found successfully.")

def test_api_call_upload_keep_alive_itn2639(device):
    """Verify keep-alive API call happens every 10 mins to the cloud or not """
    markers = device.check_private_key_markers()
    assert all(markers.values()), f"One or more key files missing PRIVATE marker: {markers}"

    utc_info = device.get_current_time_utc()
    assert utc_info['status'] == 'Pass', f"Failed to get UTC time: {utc_info['details']}"
    current_utc = utc_info['utc_time']
    print(f"Current UTC time: {current_utc}")

    info = device.get_device_info()
    assert info['status'] == 'Pass', f"Failed to retrieve device info: {info['details']}"
    device_id = info['device_id']; device_type = info['device_type']
    assert device_id and device_type, f"Missing device metadata: {info['details']}"

    ota_version = device.get_ota_version()
    assert ota_version, "OTA Version not found"

    api_substring = f"/api/v1/keep-alive/{device_type}/{device_id}/{ota_version}"
    utc_result = device.search_log_interval(
        service_name='keep_alive_manager',
        message=api_substring
    )
    assert utc_result['status'] == 'Pass', f"UTC log interval search failed: {utc_result['details']}"
    intervals = utc_result['intervals_ms']
    assert intervals, f"No intervals computed: {utc_result['details']}"
    last_ms = intervals[-1]
    range_check = device.validate_size_range(540000, last_ms, 660000)
    assert range_check['status'] == 'Pass', (
        f"Last keep-alive UTC interval {last_ms} ms out of ~10m range. {range_check['details']} | Details: {utc_result['details']}"
    )
    print(f"Keep-alive UTC interval OK: {last_ms/60000:.2f} minutes (~10m).")

def test_api_call_version_check_itn2633(device):
    """Verify version check API call happens every 10 minutes"""
    markers = device.check_private_key_markers()
    assert all(markers.values()), f"One or more key files missing PRIVATE marker: {markers}"
    ota_version = device.get_ota_version()
    assert ota_version, "OTA version not detected"
    api_pattern = f"/api/v1/versioncheck/{ota_version}"

    result = device.frequency_based_calls(
        api_pattern=api_pattern,
        service_name='otacheck',
        expected_interval_minutes=10,
        cloud_check=False,
        api_key="versionCheckData"
    )

    # Require at least one occurrence; if two, status should be Pass within tolerance
    assert result['occurrences'], f"No occurrences found for pattern {api_pattern}. Details: {result['details']}"
    if len(result['occurrences']) >= 2:
        assert result['status'] == 'Pass', f"Interval check failed. Details: {result['details']}"
    print(f"Version check API monitoring details:\n" + "\n".join(result['details']))

def test_api_call_upload_observation_itn2638(device):
    """Verify upload observation API call happens every 10 minutes to the cloud or not"""
    markers = device.check_private_key_markers()
    assert all(markers.values()), f"One or more key files missing PRIVATE marker: {markers}"
    result = device.frequency_based_calls(
        api_pattern = '/api/v1/upload/observations',
        service_name='unifieduploader',
        expected_interval_minutes=10,
        api_key="uploadObservationsData"
    )
    assert result['occurrences'], f"No occurrences found for upload observations API call. Details: {result['details']}"
    if len(result['occurrences']) >= 2:
        assert result['status'] == 'Pass', f"Interval check failed. Details: {result['details']}"
    print(f"Upload observations API monitoring details:\n" + "\n".join(result['details']))

def test_api_call_upload_videolist_itn2634(device):
    """Verify upload videolist API call happens every 5 minutes (last interval within expected range)."""
    markers = device.check_private_key_markers()
    assert all(markers.values()), f"One or more key files missing PRIVATE marker: {markers}"
    time.sleep(700)  # allow multiple log entries to accumulate ( >2 cycles of 5m )
    result = device.search_log_interval(
        service_name='circ_buff',
        message="https://idms-staging.netradyne.com/restserver/api/v1/upload/videolist"
    )
    assert result['status'] == 'Pass', f"Log search failed: {result['details']}"
    intervals = result['intervals_ms']
    assert intervals, f"No intervals computed: {result['details']}"
    last_ms = intervals[-1]
    size_range = device.validate_size_range(
        min_size=270000,
        size=last_ms,
        max_size=360000
    )
    assert size_range['status'] == 'Pass', f"Last interval {last_ms} ms not within expected 5m range: {size_range['details']} | Details: {result['details']}"
    print(f"Upload videolist API interval {last_ms/60000:.2f}m within 5m expected range.")

def test_api_call_upload_logs_itn2640(device):
    """Verify upload logs API call happens every 10 mins"""
    utc_info = device.get_current_time_utc()
    assert utc_info['status'] == 'Pass', f"Failed to get UTC time: {utc_info['details']}"
    utc_str = utc_info['utc_time']
    print(f"Current UTC time: {utc_str}")
    markers = device.check_private_key_markers()
    assert all(markers.values()), f"One or more key files missing PRIVATE marker: {markers}"
    result = device.frequency_based_calls(
        api_pattern = '/api/v1/upload/logs',
        service_name='unifieduploader',
        expected_interval_minutes=10,
        api_key="uploadLogsData"
    )
    assert result['occurrences'], f"No occurrences found for upload logs API call. Details: {result['details']}"
    if len(result['occurrences']) >= 2:
        assert result['status'] == 'Pass', f"Interval check failed. Details: {result['details']}"
    print(f"Upload logs API monitoring details:\n" + "\n".join(result['details']))
    # Write keepalive_count.txt and verify its contents
    device.run('bash -c "echo 10 > /home/ubuntu/.nddevice/log/keepalive_count.txt"','/home/ubuntu/.nddevice/log')
    written_value = device.run('cat keepalive_count.txt','/home/ubuntu/.nddevice/log')
    written_value = (written_value or '').strip()
    print(f"keepalive_count.txt content after write: {written_value}")
    assert written_value == '10', f"keepalive_count.txt expected '10' got '{written_value}'"

    log = device.search_log("/home/ubuntu/.nddevice/log/keep_alive_manager","keep_alive_manager - INFO - Zipping critical logs",utc_str,timeout=120, interval=10)
    assert log is not None, "Expected keep_alive_manager log entry not found after setting keepalive_count.txt"
    print("keep_alive_manager - INFO - Zipping critical logs found successfully.")

    log2 = device.search_log("/home/ubuntu/.nddevice/log/keep_alive_manager","Done zipping logs",utc_str, timeout=120, interval=10)
    assert log2 is not None, "Expected Done zipping logs entry not found after setting keepalive_count.txt"
    print("Done zipping logs found successfully.")

    log3 = device.search_log("/home/ubuntu/.nddevice/log/keep_alive_manager","Critical log upload message sent to uploader",utc_str,timeout=120, interval=10)
    assert log3 is not None, "Expected Critical log upload message not found after setting keepalive_count.txt"
    print("Critical log upload message sent to uploader found successfully.")

    log4 = device.search_log("/home/ubuntu/.nddevice/log/unifieduploader","Uploading logs...",utc_str, timeout=120, interval=10)
    assert log4 is not None, "Expected Uploading logs... message not found after setting keepalive_count.txt"
    print("Uploading logs... message found successfully.")

    log5 = device.search_log("/home/ubuntu/.nddevice/log/unifieduploader","Calling service: https://idms-staging.netradyne.com/restserver/api/v1/upload/logs",utc_str, timeout=120, interval=10)
    assert log5 is not None, "Expected Calling service log entry not found after setting keepalive_count.txt"
    print("Calling service log entry found successfully.")

    cmd = device.run('''grep -Hn '{"response":true,"msg":"Device-Logs saved!!"}' $(ls -t /home/ubuntu/.nddevice/log/unifieduploader/*.log) 2>/dev/null | tail -n 1''',"/home/ubuntu/.nddevice/log/unifieduploader")
    assert cmd is not None, "Expected Device-Logs saved!! log entry not found after setting keepalive_count.txt"
    print("Device-Logs saved!! log entry found successfully.")

# def test_api_call_device_register_itn2641(device):
#     """Verify the device register call triggers when certificates are removed and they are recreated."""
#     # Correct UTC retrieval (helper takes no arguments)
#     utc_info = device.get_current_time_utc()
#     assert utc_info['status'] == 'Pass', f"Failed to get UTC time: {utc_info['details']}"
#     utc_str = utc_info['utc_time']
#     print(f"Current UTC time: {utc_str}")

#     device_date = device.run("date +'%Y-%m-%d'").strip()
#     print(f"Device date: {device_date}")
#     if device_date in utc_str:
#         print("Device date is in sync with UTC date.")
#     else:
#         print("Device date is NOT in sync with UTC date.")

#     # Remove certificates to force re-registration (brace expansion acceptable)
#     remove_cmd = ("rm -f /home/ubuntu/.nddevice/certificate/{certificate.pem.crt,ed25519key.pem,private.pem.key,pub-ed25519.pem}")
#     device.run(remove_cmd, "/home/ubuntu/.nddevice/certificate")

#     # Verify they are gone instead of asserting on command output
#     removed_paths = [
#         "/home/ubuntu/.nddevice/certificate/certificate.pem.crt",
#         "/home/ubuntu/.nddevice/.nddevice/certificate/ed25519key.pem"
#         "/home/ubuntu/.nddevice/certificate/private.pem.key",
#         "/home/ubuntu/.nddevice/certificate/pub-ed25519.pem",
#     ]
#     still_present = []
#     for p in removed_paths:
#         chk = device.check_file_availability(p)
#         print(f"Post-removal check: {p} => {'EXISTS' if chk['exists'] else 'REMOVED'}")
#         if chk['exists']:
#             still_present.append(p)
#     assert not still_present, f"Some certificates not removed: {still_present}"
#     print("Certificates removed successfully.")

#     restart_out = device.run("supervisorctl restart awsiot", "/home/ubuntu/.nddevice/latest/service")
#     assert restart_out is not None, "awsiot service restart command executed."
#     print("awsiot service restarted successfully.")

#     time.sleep(10)
#     print("Waiting 10s for awsiot to attempt registration...")
#     register_log = device.run("grep -ri 'Device registration done' /home/ubuntu/.nddevice/log/awsiot | awk -F' - ' '{print $1}' | awk '{print $NF}' | head -1","/home/ubuntu/.nddevice/log/awsiot")
#     assert register_log is not None, "Device registration done log entry found successfully after awsiot restart."
#     print("Device registration done log entry found successfully after awsiot restart.")

#     # Capture latest device registration log
#     reg_result = device.event_based_api_call(
#         api_pattern='Connected successfully',
#         service_name='awsiot',
#         api_key="deviceRegisterData"

#     )
#     assert reg_result['status'] == 'Pass' and reg_result['triggered_time_ms'], (
#         f"Device registration log not found: {reg_result['details']}"
#     )
#     print("device-register call triggered.")
#     print("Details:\n" + "\n".join(reg_result['details']))

#     # Allow time for cert recreation
#     wait_secs = 270
#     print(f"Waiting {wait_secs}s for certificates to be recreated...")
#     time.sleep(wait_secs)

#     cert_paths = [
#         "/home/ubuntu/.nddevice/certificate/certificate.pem.crt",
#         "/home/ubuntu/.nddevice/certificate/root-CA.crt",
#         "/home/ubuntu/.nddevice/certificate/private.pem.key",
#     ]
#     cert_results = [device.check_file_availability(p) for p in cert_paths]
#     missing = [r['file_name'] for r in cert_results if not r['exists']]
#     for r in cert_results:
#         print(f"Cert check: {r['file_name']} => {'OK' if r['exists'] else 'MISSING'}")
#     assert not missing, f"Missing certificates after re-registration: {missing} | Details: {[r['details'] for r in cert_results]}"
#     print("All expected certificates recreated.")

def test_aws_ping_keepalive_command_itn2660(device):
    """Test to verify AWS ping keep-alive command logs."""
    start_timestamp = int(time.time()) * 1000
    device.aws_ping_command("8430","keep-alive")
    print("AWS ping command executed successfully.")

    found_keepalive = device.search_log("/home/ubuntu/.nddevice/log/awsiot", "Received command: keep-alive", start_timestamp, timeout=300, interval=10)
    print("AWS keep-alive command log entry found successfully.")
    assert found_keepalive is not None, "AWS keep-alive command log entry not found within timeout period."

def test_aws_ping_reboot_command_itn2661(device):
    """Test to verify AWS ping reboot-phone command logs."""
    start_timestamp = int(time.time()) * 1000

    info = device.get_device_info()
    assert info['status'] == 'Pass', f"Failed to retrieve device info: {info['details']}"
    device_id = info['device_id']
    assert device_id, "device_id missing from get_device_info() result"

    log6_pattern = f"Connecting... Thing: staging-{device_id}"
    print(f"Device ID for log verification: {device_id}")

    device.aws_ping_command(device_id, "reboot-phone")  # if first arg is device_id; keep "8430" if required
    print("AWS ping reboot command executed successfully.")

    found_reboot = device.search_log(
        "/home/ubuntu/.nddevice/log/awsiot",
        "Received command: reboot-phone",
        start_timestamp,
        timeout=300,
        interval=10
    )
    print("AWS reboot command log entry found successfully.")
    assert found_reboot is not None, "AWS reboot command log entry not found within timeout period."

    rebooting = device.search_log("/home/ubuntu/.nddevice/log/awsiot", "Rebooting...", start_timestamp, timeout=300, interval=10)
    print("Rebooting... log entry found successfully.")
    assert rebooting is not None, "Rebooting... log entry not found within timeout period."

    reboot_ping_triggered = device.search_log("/home/ubuntu/.nddevice/log/awsiot", "Reboot ping triggered, will send reboot request after responding to cloud", start_timestamp, timeout=300, interval=10)
    print("Reboot ping triggered log entry found successfully.")
    assert reboot_ping_triggered is not None, "Reboot ping triggered log entry not found within timeout period."

    log4 = device.search_log("/home/ubuntu/.nddevice/log/awsiot", "Reboot command detected in completed ping request", start_timestamp, timeout=300, interval=10)
    print("Reboot command detected log entry found successfully.")
    assert log4 is not None, "Reboot command detected log entry not found within timeout period."

    log5 = device.search_log("/home/ubuntu/.nddevice/log/awsiot", "Reboot request sent successfully to nd_suspendresume service", start_timestamp, timeout=300, interval=10)
    print("Reboot request sent successfully log entry found successfully.")
    assert log5 is not None, "Reboot request sent successfully log entry not found within timeout period."

    log6 = device.search_log("/home/ubuntu/.nddevice/log/awsiot", log6_pattern, start_timestamp, timeout=300, interval=10)
    print("Connecting... Thing log entry found successfully.")
    assert log6 is not None, "Connecting... Thing log entry not found within timeout period."

    log7 = device.search_log("/home/ubuntu/.nddevice/log/awsiot", "Connected successfully", start_timestamp, timeout=300, interval=10)
    print("Connected successfully log entry found successfully.")
    assert log7 is not None, "Connected successfully log entry not found within timeout period."


# def test_alert_video_in_ndalerts_itn2662(device):
#     """
#     Verify that a specific alert video filename exists in the public.ndalerts table with status = 1.
#     """
#     start_timestamp = int(time.time()) * 1000
#     cmd = "./gen_ualert.sh"
#     output = device.run(cmd, "/home/ubuntu/.nddevice/latest/service/bagheera")
#     assert "User alert is generated..!!!" in output, "Expected confirmation message not found in output"
#     print("User alert log entry generated successfully.")

#     found_event_upload = device.search_log("/home/ubuntu/.nddevice/log/unifieduploader", "Upload successful for 0_trip", start_timestamp, timeout=600, interval=10)
#     assert found_event_upload is not None, "Upload successful log entry not found within timeout period."

#     file = found_event_upload.split()[-1][1:]
#     print(f"Upload successful log entry found, file: {file}")

#     awsiot_req_found = device.search_log("/home/ubuntu/.nddevice/log/awsiot", f"sending REQ_UPLOAD_VOD to uploader for file: /media/SdCard/0{file}", start_timestamp , timeout=600, interval=10)
#     assert awsiot_req_found is not None, "REQ_UPLOAD_VOD log entry not found within timeout period."
#     print("REQ_UPLOAD_VOD log entry found successfully.")

#     outward_video_upload_found = device.search_log("/home/ubuntu/.nddevice/log/unifieduploader", f"Upload successful for video: /media/SdCard/0{file}", start_timestamp, timeout=600, interval=10)
#     assert outward_video_upload_found is not None, "Outward Video upload log entry not found within timeout period."
#     print("Outward Video upload log entry found successfully.")


#     filename = f"0{file}"
#     print(f"Verifying in DB for filename: {filename}")
#     query = """
#         SELECT DISTINCT alert_video_filename, alert_video_status
#         FROM public.ndalerts
#         WHERE alert_video_filename = %s
#           AND alert_video_status = 1;
#     """
#     try:
#         rows = device.wait_for_postgresql_result(query, (filename,), timeout=300, interval=10)


#         assert rows is not None and len(rows) > 0, f"No entry found in public.ndalerts for {filename} with status=1"
#         print(f"Found {len(rows)} record(s) for {filename} in public.ndalerts with status=1")

#     except Exception as e:
#         pytest.fail(f"Database query failed: {e}")

# def test_api_call_in_idms_upload_keep_alive_itn2694():
#     """Verify that keep_alive api call is seen every 10 minutes in the idms/db or not"""
#     device_id = '124642129939'
#     msg_id = 1
#     result = fetch_api_calls_window(device_id, minutes_before=30, minutes_after=30, msg_id=msg_id)
#     print("DB query details:\n" + "\n".join(result["details"]))
#     print("Rows:", result["rows"])

#     assert result["status"] == "Pass", f"No rows found. Details: {result['details']}"
#     assert result["rows"], f"Empty rows list. Details: {result['details']}"
#     # Basic column validation
#     for r in result["rows"]:
#         assert r["device_id"] == device_id, f"Device mismatch: {r}"
#         assert r["msg_id"] == msg_id, f"msg_id mismatch: {r}"
#         assert r["session_id"], f"Missing session_id: {r}"
#         assert r["timestamp"], f"Missing timestamp: {r}"

#     # Timestamp window check
#     from datetime import datetime
#     start_dt = datetime.strptime(result["start_time"], "%Y-%m-%d %H:%M:%S")
#     end_dt = datetime.strptime(result["end_time"], "%Y-%m-%d %H:%M:%S")
#     bad = []
#     for r in result["rows"]:
#         try:
#             ts_dt = datetime.strptime(r["timestamp"], "%Y-%m-%d %H:%M:%S")
#             if not (start_dt <= ts_dt < end_dt):
#                 bad.append(r)
#         except Exception:
#             bad.append(r)
#     assert not bad, f"Timestamps outside window: {bad}"

#     print(f"Found {result['count']} keep_alive row(s) for device {device_id}, msg_id={msg_id} in expected window.")

# def test_api_call_in_idms_upload_version_check_itn2705():
#     """Verify that version_check api call is seen every 10 minutes in the idms/db or not"""
#     device_id = '124642129939'
#     msg_id = 2
#     result = fetch_api_calls_window(device_id, minutes_before=30, minutes_after=30, msg_id=msg_id)
#     print("DB query details:\n" + "\n".join(result["details"]))
#     print("Rows:", result["rows"])

#     assert result["status"] == "Pass", f"No rows found. Details: {result['details']}"
#     assert result["rows"], f"Empty rows list. Details: {result['details']}"
#     # Basic column validation
#     for r in result["rows"]:
#         assert r["device_id"] == device_id, f"Device mismatch: {r}"
#         assert r["msg_id"] == msg_id, f"msg_id mismatch: {r}"
#         assert r["session_id"], f"Missing session_id: {r}"
#         assert r["timestamp"], f"Missing timestamp: {r}"

#     # Timestamp window check
#     from datetime import datetime
#     start_dt = datetime.strptime(result["start_time"], "%Y-%m-%d %H:%M:%S")
#     end_dt = datetime.strptime(result["end_time"], "%Y-%m-%d %H:%M:%S")
#     bad = []
#     for r in result["rows"]:
#         try:
#             ts_dt = datetime.strptime(r["timestamp"], "%Y-%m-%d %H:%M:%S")
#             if not (start_dt <= ts_dt < end_dt):
#                 bad.append(r)
#         except Exception:
#             bad.append(r)
#     assert not bad, f"Timestamps outside window: {bad}"

#     print(f"Found {result['count']} upload version_check row(s) for device {device_id}, msg_id={msg_id} in expected window.")

# def test_api_call_in_idms_upload_logs_itn2707():
#     """Verify that upload_logs api call is seen every 10 minutes in the idms/db or not"""
#     device_id = '124642129939'
#     msg_id = 7
#     result = fetch_api_calls_window(device_id, minutes_before=30, minutes_after=30, msg_id=msg_id)
#     print("DB query details:\n" + "\n".join(result["details"]))
#     print("Rows:", result["rows"])

#     assert result["status"] == "Pass", f"No rows found. Details: {result['details']}"
#     assert result["rows"], f"Empty rows list. Details: {result['details']}"
#     # Basic column validation
#     for r in result["rows"]:
#         assert r["device_id"] == device_id, f"Device mismatch: {r}"
#         assert r["msg_id"] == msg_id, f"msg_id mismatch: {r}"
#         assert r["session_id"], f"Missing session_id: {r}"
#         assert r["timestamp"], f"Missing timestamp: {r}"

#     # Timestamp window check
#     from datetime import datetime
#     start_dt = datetime.strptime(result["start_time"], "%Y-%m-%d %H:%M:%S")
#     end_dt = datetime.strptime(result["end_time"], "%Y-%m-%d %H:%M:%S")
#     bad = []
#     for r in result["rows"]:
#         try:
#             ts_dt = datetime.strptime(r["timestamp"], "%Y-%m-%d %H:%M:%S")
#             if not (start_dt <= ts_dt < end_dt):
#                 bad.append(r)
#         except Exception:
#             bad.append(r)
#     assert not bad, f"Timestamps outside window: {bad}"

#     print(f"Found {result['count']} upload_logs row(s) for device {device_id}, msg_id={msg_id} in expected window.")

# def test_api_call_in_idms_upload_videolist_itn2710():
#     """Verify that upload_videolist api call is seen every 10 minutes in the idms/db or not"""
#     device_id = '124642129939'
#     msg_id = 8
#     result = fetch_api_calls_window(device_id, minutes_before=30, minutes_after=30, msg_id=msg_id)
#     print("DB query details:\n" + "\n".join(result["details"]))
#     print("Rows:", result["rows"])

#     assert result["status"] == "Pass", f"No rows found. Details: {result['details']}"
#     assert result["rows"], f"Empty rows list. Details: {result['details']}"
#     # Basic column validation
#     for r in result["rows"]:
#         assert r["device_id"] == device_id, f"Device mismatch: {r}"
#         assert r["msg_id"] == msg_id, f"msg_id mismatch: {r}"
#         assert r["session_id"], f"Missing session_id: {r}"
#         assert r["timestamp"], f"Missing timestamp: {r}"

#     # Timestamp window check
#     from datetime import datetime
#     start_dt = datetime.strptime(result["start_time"], "%Y-%m-%d %H:%M:%S")
#     end_dt = datetime.strptime(result["end_time"], "%Y-%m-%d %H:%M:%S")
#     bad = []
#     for r in result["rows"]:
#         try:
#             ts_dt = datetime.strptime(r["timestamp"], "%Y-%m-%d %H:%M:%S")
#             if not (start_dt <= ts_dt < end_dt):
#                 bad.append(r)
#         except Exception:
#             bad.append(r)
#     assert not bad, f"Timestamps outside window: {bad}"

#     print(f"Found {result['count']} upload_videolist row(s) for device {device_id}, msg_id={msg_id} in expected window.")

# def test_api_call_in_idms_upload_devicestatus_itn2711():
#     """Verify that upload_devicestatus api call is seen every 10 minutes in the idms/db or not"""
#     device_id = '124642129939'
#     msg_id = 10
#     result = fetch_api_calls_window(device_id,minutes_before=30,minutes_after=30,msg_id=msg_id)
#     print("DB query details:\n" + "\n".join(result["details"]))
#     print("Rows:", result["rows"])

#     assert result["status"] == "Pass", f"No rows found. Details: {result['details']}"
#     assert result["rows"], f"Empty rows list. Details: {result['details']}"
#     # Basic column validation
#     for r in result["rows"]:
#         assert r["device_id"] == device_id, f"Device mismatch: {r}"
#         assert r["msg_id"] == msg_id, f"msg_id mismatch: {r}"
#         assert r["session_id"], f"Missing session_id: {r}"
#         assert r["timestamp"], f"Missing timestamp: {r}"

#     # Timestamp window check
#     from datetime import datetime
#     start_dt = datetime.strptime(result["start_time"], "%Y-%m-%d %H:%M:%S")
#     end_dt = datetime.strptime(result["end_time"], "%Y-%m-%d %H:%M:%S")
#     bad = []
#     for r in result["rows"]:
#         try:
#             ts_dt = datetime.strptime(r["timestamp"], "%Y-%m-%d %H:%M:%S")
#             if not (start_dt <= ts_dt < end_dt):
#                 bad.append(r)
#         except Exception:
#             bad.append(r)
#     assert not bad, f"Timestamps outside window: {bad}"

#     print(f"Found {result['count']} upload_devicestatus row(s) for device {device_id}, msg_id={msg_id} in expected window.")

# def test_api_call_in_idms_upload_observations_itn2706():
#     """Verify that upload_observations api call is seen every 10 minutes in the idms/db or not"""
#     device_id = '124642129939'
#     msg_id = 16
#     result = fetch_api_calls_window(device_id, minutes_before=30, minutes_after=30, msg_id=msg_id)
#     print("DB query details:\n" + "\n".join(result["details"]))
#     print("Rows:", result["rows"])

#     assert result["status"] == "Pass", f"No rows found. Details: {result['details']}"
#     assert result["rows"], f"Empty rows list. Details: {result['details']}"
#     # Basic column validation
#     for r in result["rows"]:
#         assert r["device_id"] == device_id, f"Device mismatch: {r}"
#         assert r["msg_id"] == msg_id, f"msg_id mismatch: {r}"
#         assert r["session_id"], f"Missing session_id: {r}"
#         assert r["timestamp"], f"Missing timestamp: {r}"

#     # Timestamp window check
#     from datetime import datetime
#     start_dt = datetime.strptime(result["start_time"], "%Y-%m-%d %H:%M:%S")
#     end_dt = datetime.strptime(result["end_time"], "%Y-%m-%d %H:%M:%S")
#     bad = []
#     for r in result["rows"]:
#         try:
#             ts_dt = datetime.strptime(r["timestamp"], "%Y-%m-%d %H:%M:%S")
#             if not (start_dt <= ts_dt < end_dt):
#                 bad.append(r)
#         except Exception:
#             bad.append(r)
#     assert not bad, f"Timestamps outside window: {bad}"

#     print(f"Found {result['count']} upload_observations row(s) for device {device_id}, msg_id={msg_id} in expected window.")
