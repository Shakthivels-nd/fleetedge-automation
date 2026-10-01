"""
Feature: Scheduler — Processed File Written To Disk
Description:
  Verify a processed file is written to disk as a zip file.

  Ported from nd_test_bot's TC_1349_SCHEDULER_PROCESSED_FILE_WRITTEN_TO_DISK.
  The reference branches on device_type (krait path /data/nd_files/nd_sdcard/
  vs bagheera path /media/data/nd_sdcard/) -- neither matches FE's real
  video path. Dropped the krait branch and the device-type check entirely,
  using FE's confirmed real path /media/SdCard/ (same path already
  confirmed via live device grep in the awsiot port's
  test_awsiot_send_request_to_uploader.py).

  Log strings "nd_file_operate_device: file operation complete" and
  "syncing content to disk /media/SdCard/.*zip" (UNVERIFIED -- ported from
  reference, not yet confirmed on FE) need a live check before this test is
  trusted.
"""


def test_step1_verify_processed_file_written_to_disk(device):
    """STEP_1 — Verify scheduler_manager logs the file operation completing and syncing to disk."""
    for message in [
        "nd_file_operate_device: file operation complete",
        "syncing content to disk /media/SdCard/.*zip",
    ]:
        output = device.search_log("/home/ubuntu/.nddevice/log/scheduler_manager", message, timeout=120, interval=10)
        assert output, f"'{message}' not found in scheduler_manager logs"
