"""
Test case : Intentional service crash
Purpose   : Check that when a service crashes with a segmentation fault (SIGSEGV),
            supervisord notices, writes it in its log, and starts the service again.

Precondition
  bagheera is running.

Steps and expected result
  1. Find the process id (pid) of bagheera and note the time.
  2. Crash bagheera with a segmentation fault (`kill -11`).
  3. Wait for bagheera to be running again.
       -> It has a new pid.
  4. Check the supervisord log.
       -> It has a WARN line saying bagheera exited because of the segmentation
          fault and that this was not expected. Either wording is accepted:
          "terminated by SIGSEGV" or "exit status 11" (11 is the SIGSEGV number).
       -> After it, an INFO line saying supervisord started bagheera again with the
          new pid, and an INFO line saying bagheera entered the RUNNING state.

Differences from the sheet
  - The sheet runs a bagheera binary that crashes by itself. That needs a special
    build, so the test sends the same signal (SIGSEGV) with `kill -11`. From
    supervisord's point of view the result is the same.
  - The sheet's line says "terminated by SIGSEGV (core dumped)". On current builds
    bagheera catches the signal and exits with the signal number as its exit code, so
    the log says "exit status 11; not expected" instead (a `kill -6` likewise gives
    "exit status 6"). Both forms mean supervisord saw the crash, so both pass.
  - The log is read from the newest /data/log_supervisord*.log file. Only lines from
    after step 1 count, using the UTC time noted in step 1.
"""

import re
import time

SERVICE = "bagheera"
WAIT_FOR_NEW_PROCESS_SECONDS = 30
LOG_LINE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ (\w+) (.*)$")


def test_step1_find_service_pid(device):
    """STEP 1 — Find the process id of bagheera and note the current UTC time."""
    pid = device.get_service_pid(SERVICE)["pid"]
    assert pid, f"{SERVICE} is not RUNNING"
    now = (device.run("date -u '+%Y-%m-%d %H:%M:%S'") or "").strip()
    assert re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", now), f"Could not read the device time: {now!r}"
    device.variables["pid_before_crash"] = pid
    device.variables["time_before_crash"] = now


def test_step2_crash_service(device):
    """STEP 2 — Crash bagheera with a segmentation fault (`kill -11`)."""
    device.run(f"kill -11 {device.variables['pid_before_crash']}")


def test_step3_service_running_again(device):
    """STEP 3 — Wait for bagheera to be running again with a new pid."""
    old_pid = device.variables["pid_before_crash"]
    deadline = time.time() + WAIT_FOR_NEW_PROCESS_SECONDS
    while time.time() < deadline:
        pid = device.get_service_pid(SERVICE)["pid"]
        if pid and pid != old_pid:
            device.variables["pid_after_crash"] = pid
            return
        time.sleep(2)
    assert False, f"{SERVICE} did not come back with a new pid within {WAIT_FOR_NEW_PROCESS_SECONDS}s of the crash (old pid {old_pid})"


def test_step4_supervisord_log_shows_crash_and_restart(device):
    """STEP 4 — Check the supervisord log shows bagheera exited from the segmentation fault, then was started again and is RUNNING."""
    log_file = (device.run("ls -t /data/log_supervisord*.log | head -1") or "").strip()
    assert log_file.startswith("/data/log_supervisord"), f"No supervisord log file found in /data: {log_file!r}"
    out = device.run(f"grep -a {SERVICE} {log_file} | tail -n 15") or ""

    start = device.variables["time_before_crash"]
    new_pid = device.variables["pid_after_crash"]
    lines = []
    for raw in out.splitlines():
        m = LOG_LINE.match(raw.strip())
        if m and m.group(1) >= start:
            lines.append((m.group(2), m.group(3)))

    crash = [
        i for i, (_, text) in enumerate(lines)
        if f"exited: {SERVICE}" in text and ("terminated by SIGSEGV" in text or "exit status 11" in text)
    ]
    assert crash, (
        f"No 'exited: {SERVICE}' line for SIGSEGV (terminated by SIGSEGV, or exit status 11) in {log_file} "
        f"after {start} UTC. Lines seen: {lines}"
    )
    level, text = lines[crash[-1]]
    assert level == "WARN" and "not expected" in text, f"Crash line should be WARN and 'not expected': {level} {text}"

    after = lines[crash[-1] + 1:]
    assert any(lv == "INFO" and f"spawned: '{SERVICE}' with pid {new_pid}" in t for lv, t in after), (
        f"No INFO line saying {SERVICE} was started again with pid {new_pid}. Lines after the crash: {after}"
    )
    assert any(lv == "INFO" and f"success: {SERVICE} entered RUNNING state" in t for lv, t in after), (
        f"No INFO line saying {SERVICE} entered RUNNING state. Lines after the crash: {after}"
    )
