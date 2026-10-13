"""
Test case : ND Software Startup Sequence
Purpose   : Check that ND software starts up as expected after the pod launches.

Precondition
  The ND pod is up and running.

Steps and expected result
  1. Run `ps 1` (the test uses `ps -ww 1` so the full command line is shown)
       -> Supervisord is running as process 1 (it is now called systemctlnd).
  2. Read the supervisord log in /data
       -> It has the start-up lines: running as root warning, one "Included extra
          file" line for every service, RPC interface initialized, unix_http_server
          warning, and "supervisord started with pid 1".
  3. Run `supervisorctl status`
       -> Every service is RUNNING and `startup` is EXITED (it runs once and exits).
  4. Run `ls -l /data/log_supervisord*`
       -> Supervisord log files exist in /data and the current one is not empty.

Differences from the test-case sheet (the device has changed since it was written)
  - Log file name: the sheet says /data/log_supervisord.log. Current builds use
    /data/log_supervisord_<epoch>.log. The test handles both.
  - Service list: read from /etc/supervisor/conf.d/*.service on the device (plus
    `startup` and `cron`) instead of the 2024 list in the sheet.
  - Not checked: "cron is the first service started". The sheet's log patterns do
    not verify it, and the rc.1 log shows `startup` starting before `cron`.
"""

import re

LOG_PREFIX = "/data/log_supervisord"
CONF_D = "/etc/supervisor/conf.d"
BUILTIN_PROGRAMS = {"startup", "cron"}  # defined in supervisord.conf, not conf.d
STATES = {"RUNNING", "STOPPED", "STARTING", "BACKOFF", "STOPPING", "EXITED", "FATAL", "UNKNOWN"}


def _log_files(device):
    """Supervisord log files from the latest run: newest epoch's files, or the old-style names if none."""
    if "supervisord_logs" in device.variables:
        return device.variables["supervisord_logs"]
    out = device.run(f"ls {LOG_PREFIX}*") or ""
    files = [t for t in out.split() if t.startswith(LOG_PREFIX)]
    epochs = {int(m.group(1)) for f in files if (m := re.search(r"log_supervisord_(\d+)\.log", f))}
    if epochs:
        newest = max(epochs)
        files = [f for f in files if f"log_supervisord_{newest}.log" in f]
    device.variables["supervisord_logs"] = files
    return files


def _status_by_service(output):
    """{service: state} from `supervisorctl status` output."""
    result = {}
    for line in (output or "").splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1] in STATES:
            result[parts[0]] = parts[1]
    return result


def test_step1_supervisord_is_pid_1(device):
    """STEP 1 — Run `ps 1` and check supervisord (systemctlnd) is process 1."""
    # -ww: plain `ps` cuts each line at the terminal width (80 columns) and drops the "-s -n -c ..." arguments
    out = device.run("ps -ww 1")
    assert out and "systemctlnd" in out and "-s -n" in out, f"pid 1 is not systemctlnd -s -n: {out!r}"


def test_step2_supervisord_log_boot_lines(device):
    """STEP 2 — Read the supervisord log in /data and check it has the start-up lines for every service."""
    files = _log_files(device)
    assert files, f"No supervisord log files found in /data ({LOG_PREFIX}*)"
    joined = " ".join(files)

    conf = device.run(f"ls {CONF_D}/*.service") or ""
    unit_files = [t for t in conf.split() if t.endswith(".service")]
    assert unit_files, f"No .service files found in {CONF_D}"

    included = device.run(f'grep -ha "Included extra file" {joined}') or ""
    missing = [u for u in unit_files if f'"{u}" during parsing' not in included]
    assert not missing, f"'Included extra file' line missing for: {missing}"

    boot = device.run(f'grep -ha -E "CRIT|RPC interface|supervisord started" {joined}') or ""
    for expected in (
        "Supervisor is running as root",
        "RPC interface 'supervisor' initialized",
        "Server 'unix_http_server' running without any HTTP authentication checking",
        "supervisord started with pid 1",
    ):
        assert expected in boot, f"Expected boot line not found in supervisord log: {expected!r}"


def test_step3_supervisorctl_status(device):
    """STEP 3 — Run `supervisorctl status` and check every service is RUNNING and startup is EXITED."""
    conf = device.run(f"ls {CONF_D}/*.service") or ""
    expected = {t.rsplit("/", 1)[-1][: -len(".service")] for t in conf.split() if t.endswith(".service")}
    expected |= BUILTIN_PROGRAMS

    status = _status_by_service(device.run("supervisorctl status"))
    missing = sorted(expected - status.keys())
    unexpected_state = {s: st for s, st in status.items() if s in expected and st != ("EXITED" if s == "startup" else "RUNNING")}
    assert not missing, f"Services not listed by supervisorctl status: {missing}"
    assert not unexpected_state, f"Services not in the expected state (startup EXITED, others RUNNING): {unexpected_state}"


def test_step4_supervisord_log_files_in_data(device):
    """STEP 4 — Run `ls -l /data/log_supervisord*` and check the log files exist and the current one is not empty."""
    out = device.run(f"ls -l {LOG_PREFIX}*") or ""
    entries = [l.split() for l in out.splitlines() if LOG_PREFIX in l and l.startswith("-")]
    assert entries, f"No supervisord log files in /data: {out!r}"
    base = [e for e in entries if e[-1].endswith(".log")]
    assert base, f"No current (unnumbered) supervisord log file: {[e[-1] for e in entries]}"
    assert any(int(e[4]) > 0 for e in base), f"Current supervisord log file is empty: {[(e[-1], e[4]) for e in base]}"
