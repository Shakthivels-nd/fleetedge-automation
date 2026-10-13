"""
Test case : Supervisord logs availability
Purpose   : Check that supervisord writes its logs to /data, and that its logs are
            picked up for upload to the cloud along with the other service logs.

Precondition
  Supervisord logs are being created in /data.

Steps and expected result
  1. Run `ls -l /data`
       -> Supervisord log files are there. When a log gets full it is rotated, and
          the older copies get a number added at the end of the name
          (for example log_supervisord_<epoch>.log.1).
  2. Check the downloaded logs contain the supervisord logs
       -> The supervisord logs are picked up for upload.

How step 2 is checked here
  This framework cannot download logs from the cloud. Instead the test looks in
  the keep_alive_manager log, which is the service that packs logs for upload.
    - It must say it is adding the supervisor logs from /data to the upload.
    - If step 1 found rotated (numbered) files, it must also show them packed
      ("compressed", return value 0). Only rotated files are packed, never the
      log that is still being written.
  This shows the logs are going to the cloud, not that they arrived there.

Things to know
  - The sheet shows /data/log_supervisord.log. Current builds use
    /data/log_supervisord_<epoch>.log (a new file for every supervisord start).
    Both names are accepted.
  - A log is only rotated once it fills up (about 50 KB). A pod that has not
    reached that yet has no numbered files, and that is not a failure. Any
    numbered file that does exist must have a valid name.
  - The keep_alive_manager wording ("Adding supervisor logs to upload from /data/"
    and "FILE: ... compressed ... retVal: 0") comes from the rc.1 execution page
    and is UNVERIFIED on other builds.
"""

import re

LOG_NAME = re.compile(r"^log_supervisord(_\d+)?\.log(\.\d+)?$")
ROTATED = re.compile(r"\.log\.\d+$")
KEEP_ALIVE_LOG_DIR = "/home/ubuntu/.nddevice/log/keep_alive_manager/"


def test_step1_supervisord_logs_in_data(device):
    """STEP 1 — Run `ls -l /data` and check the supervisord logs are there, and any rotated file has a number at the end."""
    out = device.run("ls -l /data") or ""
    names = [line.split()[-1] for line in out.splitlines() if line.startswith("-") and "log_supervisord" in line]
    assert names, f"No supervisord log files found in /data: {out!r}"

    bad_names = [n for n in names if not LOG_NAME.match(n)]
    assert not bad_names, f"Unexpected supervisord log file names in /data: {bad_names}"

    current = [n for n in names if not ROTATED.search(n)]
    assert current, f"No current (not numbered) supervisord log file in /data: {names}"
    device.variables["rotated_supervisord_logs"] = [n for n in names if ROTATED.search(n)]


def test_step2_supervisord_logs_picked_for_upload(device):
    """STEP 2 — Check the keep_alive_manager log shows the supervisor logs in /data are added to the upload."""
    out = device.run(f"grep -ihr 'Adding supervisor logs to upload from /data' {KEEP_ALIVE_LOG_DIR} | tail -5")
    assert out and "supervisor logs to upload" in out, "keep_alive_manager never added the supervisor logs in /data to an upload"

    rotated = device.variables.get("rotated_supervisord_logs") or []
    if rotated:
        packed = device.run(f"grep -ihr 'FILE: .*log_supervisord.*compressed.*retVal: 0' {KEEP_ALIVE_LOG_DIR} | tail -5")
        assert packed and "log_supervisord" in packed, (
            f"Rotated supervisord logs {rotated} exist in /data but keep_alive_manager never packed one for upload"
        )
