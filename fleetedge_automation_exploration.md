# fleetedge-automation Framework Exploration

## Architecture Overview
This framework now has a thin facade layer, similar in spirit to the pytest_device_validator reference's `DeviceTest`/`device_api.py`, sitting on top of a flat, function-based util layer:
1. **Connection** — SSH into a device pod via `pexpect` (no transport abstraction/classes)
2. **Engine** — a set of focused modules under `src/utils/engine/` for connection, log search, device/OTA checks, time/size helpers, cloud API, DB queries, and JIRA (previously one ~1400-line `pod_utils.py`; split for maintainability — see **Module Layout** below)
3. **Facade** — `DeviceTest` (src/utils/device_test.py) wraps the util modules behind one object with a `command_log`; `device_api.py` is the single source of truth registry of its methods (see **DeviceTest Facade** below)
4. **Tests** — one flat pytest file (`test_sanity_functions.py`), calling `device.<method>(...)` on a `DeviceTest` instance instead of importing util functions directly
5. **Logging** — simple stdlib logger, captured by pytest
6. **Reporting** — `pytest-html` generates one self-contained HTML report per run

There is still **no transport interface (ADB/Serial), no healing engine, no device pool** in this repo — `DeviceTest` wraps a single `pexpect` pod connection, it does not abstract over multiple transport types.

---

## MODULE LAYOUT (src/utils/, src/utils/engine/)

`pod_utils.py` used to contain every helper in the framework. It has been split by concern into modules under `src/utils/engine/` — the "engine" subpackage holds everything that actually talks to something external (pod over SSH, IDMS over HTTP, Postgres, JIRA) or does device-side checks/log parsing built on top of that connection. `src/utils/` itself (the parent) holds only the facade (`device_test.py`, `device_api.py`) and `logger.py`, which nothing external depends on:

| Module | Location | Contains |
|---|---|---|
| `connection.py` | `src/utils/engine/` | `connect_to_pod`, `run_command_on_voyager`, `run_command_on_pod`, `reboot_voyager`, `wait_for_ping`, `close_pod_connection`, `clean_output`, `voyager_ip` |
| `log_search.py` | `src/utils/engine/` | `search_logs_in_pod`, `grep_logs`, `search_log_interval`, `frequency_based_calls`, `event_based_api_call`, `UTC_TIMESTAMP_SERVICES` |
| `device_checks.py` | `src/utils/engine/` | `verify_file_presence`, `check_ota_md5sum`, `check_no_legacy_package_exists`, `list_log_folder_contents`, `validate_services_uptime_diff`, `check_private_key_markers`, `get_ota_version`, `check_file_availability`, `get_device_info` |
| `time_utils.py` | `src/utils/engine/` | `validate_size_range`, `get_current_time_utc`, `get_current_time_epoch`, `compare_time_difference_hms` |
| `cloud_api.py` | `src/utils/engine/` | `login_api`, `aws_ping_command` |
| `db_utils.py` | `src/utils/engine/` | `DB_CONFIG`, `DB_CONFIG_2`, `run_postgresql_query`, `wait_for_postgresql_result`, `fetch_api_calls_window` |
| `jira_client.py` | `src/utils/engine/` | `JiraCache` — JIRA known/unknown-issue classification (see **LIVE HTML REPORT**) |
| `pod_utils.py` | `src/utils/engine/` | thin re-export shim over the engine modules above (back-compat only) |
| `device_test.py` | `src/utils/` | `DeviceTest` facade (see **DEVICETEST FACADE**) |
| `device_api.py` | `src/utils/` | `DEVICE_API` registry |
| `logger.py` | `src/utils/` | `setup_logger` (unchanged) |

`pod_utils.py` is a **thin re-export shim** — it imports everything from the other `engine/` modules and re-exports it, plus keeps `load_dotenv()` and the old `if __name__ == "__main__"` block. It is importable as `from src.utils.engine.pod_utils import X` — new code should import from the specific `engine.<module>` directly instead (e.g. `from src.utils.engine.log_search import grep_logs`), or better, go through `DeviceTest`.

Dependency direction is one-way: every `engine/` module depends only on sibling `engine/` modules (for `run_command_on_pod`/`clean_output`) and `..logger` (one level up, for `setup_logger`). The one internal cross-call is `device_checks.get_device_info` → `device_checks.get_ota_version` (same module). `device_test.py` (in the parent `src/utils/`) imports each `engine/` module by name (`from .engine import connection`, etc.) — it's the only file outside `engine/` that reaches into it. No circular imports.

**WHERE TO ADD NEW DEVICE FUNCTIONS:** Add the function to whichever module matches its concern under `src/utils/engine/` (see table above), then add a thin wrapper method to `DeviceTest` (src/utils/device_test.py) and register it in `DEVICE_API` (src/utils/device_api.py) — see **DeviceTest Facade** below for the exact pattern.

**Gotcha if you move a file again:** `jira_client.py`'s `_PROJECT_ROOT` is computed as `Path(__file__).resolve().parent` repeated N times to reach the repo root — it's currently 4 (`engine` → `utils` → `src` → root). Moving the file changes how many `.parent`s are needed; get this wrong and `jira_config.ini` silently stops being found (no error — `_load_config()` just returns empty strings, which "smells" like normal unconfigured JIRA rather than a bug). This exact mistake happened when this doc's own module split moved `jira_client.py` into `engine/` — caught by testing `_load_config()` against the real `.ini` file after the move, not by inspection.

---

## DEVICETEST FACADE (src/utils/device_test.py + device_api.py)

Modeled on the pytest_device_validator reference's `DeviceTest`/`device_api.py` pairing, scaled down to what this repo actually has (no relay/camera/LED/fan hardware, no JIRA, no LLM codegen — those parts of the reference do not apply here).

### DeviceTest
`DeviceTest(pod_connection)` wraps an **already-connected** `pexpect.spawn` (as produced by the `pod_connection` fixture) — it does not open its own connection, unlike the reference's `DeviceTest.__init__(serial, ...)` which builds its own transport. Every util-module function that this repo has gets a thin wrapper method (`device.run(...)`, `device.search_log(...)`, `device.get_device_info()`, etc.) that delegates to the matching module and appends an entry to `command_log`.

- **`ota_version`** is detected once at construction (via `device_checks.get_ota_version`) and cached as a property — mirrors the reference's `DeviceTest.__init__` auto-detecting `device_type`/`ota_version`/`os_version`, but scoped to just `ota_version` since that's the only one this repo's util functions already compute. That one init-time call is **not** logged to `command_log` (matches the reference not logging its own init-time detection reads).
- **`command_log`** is a list of `{cmd, output, timestamp}` dicts, appended by every wrapper method. Simpler than the reference's `command_log` entries (`cmd, rc, stdout, stderr, duration_ms, timestamp`) since the underlying `run_command_on_pod` here returns a plain string/`None`, not a `CommandResult` dataclass — there's no separate rc/stdout/stderr to record.
- **`variables`** is a shared dict for test-step state, seeded with `ota_version` at init — same idea as the reference's `variables`, unused for anything beyond that today.
- Pure utilities that don't touch the pod (`get_current_time_utc`, `get_current_time_epoch`, `compare_time_difference_hms`, `validate_size_range`) are still exposed as `DeviceTest` methods for API consistency, but they don't append to `command_log` since there's no pod I/O to record.
- `clean_output` is deliberately **not** wrapped on `DeviceTest` — it's a pure string-transform helper, not a device operation, so tests still `from src.utils.engine.connection import clean_output` directly (mirrors the reference keeping `CommandResult` and other pure-data types outside the facade).

### device_api.py
`DEVICE_API: dict[str, dict]` lists every `DeviceTest` property/method with its `signature`, `returns`, and `description`. Unlike the reference (where this registry also drives an LLM prompt and a code validator in `agent/`), this repo has no agent layer — `device_api.py` here is purely a **human-readable reference / drift check**, not consumed by any codegen.

**When you add a method to `DeviceTest`, add it to `DEVICE_API` too.** Nothing enforces this automatically (no agent build step reads it), so it can silently drift — periodically diff `DeviceTest`'s public members against `DEVICE_API`'s keys if you suspect it has (they matched exactly, 1:1, as of the last check).

### Migration note
All 35 tests in `test_sanity_functions.py` were migrated from calling util functions directly (`run_command_on_pod(pod_connection, cmd)`) to calling `DeviceTest` methods (`device.run(cmd)`). A new `device` fixture (session-scoped as of the fixture-scope change, built from `pod_connection` — see **Test Lifecycle**) supplies the `DeviceTest` instance. The 6 pure-DB tests (`test_api_call_in_idms_upload_*`) that take **no fixture** were deliberately left calling `fetch_api_calls_window` directly from `db_utils` — routing them through `device.fetch_api_calls_window(...)` would have forced them to depend on `pod_connection` (a live SSH+pod session) when they never needed one.

---

## CONNECTION LAYER — pexpect over SSH (src/utils/engine/connection.py)

There is no `DeviceTransport`/`ADBTransport`/`SerialTransport` split. Connection is always: SSH to a jump host ("voyager"), then `kubectl exec` into a pod (`netra`) running on it, via `sshpass` + `pexpect.spawn`.

### Core connection functions
- `connect_to_pod(ip_address=voyager_ip, username="voyager", password="voyager", pod="netra") → pexpect.spawn`
  Opens a persistent SSH session, disables echo, `kubectl exec -it` into the pod's bash shell. Returned `child` is reused across a whole test module.
- `close_pod_connection(child) → None` — sends `exit`, closes the spawn.
- `run_command_on_pod(child, cmd, directory=None) → str | None`
  Runs a command on the **already-connected** persistent session; strips the echoed command line and shell noise via `clean_output`. This is the primary way tests talk to the device.
- `run_command_on_voyager(ip_address=voyager_ip, username="voyager", password="voyager", cmd="ls -l", directory=None) → str | None`
  One-off command executed directly on the **voyager host itself** (not inside the pod) — spawns its own `pexpect` session per call. Used for host-level operations like `sudo reboot`.
- `reboot_voyager() → None` — reboots the host (not the pod), waits for ping to come back (`wait_for_ping`), then sleeps 240s for the pod to fully initialize.
- `wait_for_ping(ip=voyager_ip, timeout=180, interval=5) → bool` — polls ICMP ping until reachable or timeout.
- `clean_output(output) → str` — strips ANSI escapes and shell prompt noise (`root@...`, etc.) from command output. Applied to nearly everything read back from the pod.

**Key difference from transport-based frameworks:** there's no reconnect/retry/self-healing logic here. If a command times out, `run_command_on_pod` just logs and returns `""`. No automatic reconnection on connection loss.

---

## LOG SEARCH (src/utils/engine/log_search.py)

### Core primitives, used by most tests
- `search_logs_in_pod(child, log_dir, search_term, start_timestamp=None, timeout=60, interval=5) → str | None`
  Polls `grep -Hn` across `*.log` files in a directory until a match **newer than `start_timestamp`** appears or timeout expires. Handles both epoch (ms/seconds) and UTC-string (`YYYY-MM-DD HH:MM:SS`) log timestamp formats automatically (auto-detects format by sampling matching lines first). This is the workhorse function nearly every test uses to confirm an event happened.
- `search_log_interval(pod_connection, service_name, message, start_time_epoch=None) → Dict`
  Collects **all** matching log timestamps in a service's log dir and computes intervals between consecutive occurrences — used to verify periodic behaviors (e.g. "runs every 10 minutes"). Returns `{status, count, intervals_ms, stats, details}`.
- `frequency_based_calls(pod_connection, api_pattern, service_name, expected_interval_minutes, cloud_check=False, api_key=None, tolerance_minutes=1) → Dict`
  Waits for **two** occurrences of a URL pattern in logs and checks the gap between them is within `expected_interval_minutes ± tolerance`. Returns `{status, occurrences, diff_minutes, details}`.
- `event_based_api_call(pod_connection, api_pattern, service_name, cloud_check=False, api_key=None, ...) → Dict`
  Captures the **latest single** occurrence of an API pattern in logs (for one-shot events like device registration, not periodic ones). Returns `{status, triggered_time_ms, cloud_delay_ms, details}`.
  Note: `cloud_check` param exists but is an unimplemented placeholder in both functions — it always no-ops.
- `grep_logs(pod_connection, service, pattern, log_root="/home/ubuntu/.nddevice/log", since_ts=None) → Dict`
  **Single-shot** grep (no polling) — ported from the pytest_device_validator reference's `DeviceTransport.search()`. Differs from `search_logs_in_pod` in a few ways:
  - Runs the grep exactly **once** and returns immediately — no retry loop/timeout, so callers who need "wait until it appears" should keep using `search_logs_in_pod`.
  - Uses `shlex.quote` on the pattern/path instead of raw string interpolation into the shell command.
  - Timestamp filtering is service-aware via a module-level `UTC_TIMESTAMP_SERVICES` set (`otacheck`, `keep_alive_manager`, `scheduler_manager`): those services get `since_ts` converted to a UTC datetime string and compared against the first 19 chars of each line (`awk`); all other services are assumed to prefix lines with `<epoch-ms>:` and are filtered numerically (`awk -F: '$1+0 > since_ts'`).
  - With no `since_ts`, uses basic regex (`grep -aih`, no `-E`) deliberately — so literal parentheses in a pattern (e.g. `"VOD req ACK (2) sent"`) match literally instead of being parsed as an extended-regex group.
  - On failure to match, additionally captures first-5/last-5 lines of each matching log file so the failure `details` carry context instead of just "not found".
  - Returns `{status: "Pass"/"Fail", output: str, details: [...]}` — the dict convention, not the reference's `CommandResult` dataclass (this framework has no such class).
  - `search_logs_in_pod` was **kept as-is** for existing polling-based tests; `grep_logs` is additive, not a replacement.

---

## DEVICE / OTA CHECKS (src/utils/engine/device_checks.py)

- `verify_file_presence(child, directories, patterns) → List[Dict]` — counts files matching regex patterns per directory (`ls | grep -E`).
- `check_file_availability(pod_connection, file_path) → Dict` — `{status, exists, file_name, file_path, details}` via `[ -f ... ]` test.
- `get_ota_version(pod_connection, directory="/home/ubuntu/.nddevice") → str | None` — detects OTA version by matching `X.Y.Z.rc.N` folder/tarball naming pattern.
- `check_ota_md5sum(pod_connection, ota_version, directory=...) → str` — parses `md5sum` output. Raises `AssertionError` on parse failure (older convention).
- `check_no_legacy_package_exists(pod_connection, ota_version, directory=...) → bool` — asserts only the expected `.tar.gz` exists. Raises `AssertionError` directly.
- `get_device_info(pod_connection, deviceconfig_path="/home/ubuntu/config/deviceconfig.ini") → Dict`
  `{status, device_type, device_id, ota_version, details}` — parses the ini file, with an `env | grep` fallback if fields are missing. Internally calls `get_ota_version`.
- `check_private_key_markers(pod_connection, directory="/home/ubuntu/.nddevice/certificate") → Dict[str, bool]` — checks cert/key files contain `PRIVATE` marker.
- `list_log_folder_contents(pod_connection, directory="/data/nd_files/log") → str` — debug helper, prints/returns `ls -lh`.
- `validate_services_uptime_diff(pod_connection, directory=..., max_diff_seconds=5) → None` — parses `supervisorctl status *`, asserts all service uptimes are within `max_diff_seconds` of each other (raises `AssertionError` directly rather than returning a dict).

**Convention:** most "check" helpers (added later in the file's history) return a `{status: "Pass"/"Fail", ..., details: [...]}` dict rather than raising — tests then `assert result['status'] == 'Pass'`. Older helpers (`validate_services_uptime_diff`, `check_ota_md5sum`, `check_no_legacy_package_exists`) raise `AssertionError` directly instead. **Both styles coexist — match whichever an area already uses when adding to it.**

---

## TIME / SIZE HELPERS (src/utils/engine/time_utils.py)
All return the `{status, ..., details}` dict convention:
- `get_current_time_utc() → Dict` — `{status, utc_time}`.
- `get_current_time_epoch() → Dict` — `{status, epoch_ms, epoch_seconds}`.
- `compare_time_difference_hms(timestamp1, expected_difference_minutes, timestamp2) → Dict` — accepts `HH:MM:SS` strings, datetimes, or epoch values; auto-swaps if out of order.
- `validate_size_range(min_size, size, max_size, inclusive=True) → Dict` — generic numeric range check with a details trail.

---

## CLOUD / API LAYER (src/utils/engine/cloud_api.py)

- `login_api() → (session_key, status, access_token)` — OAuth password-grant against `auth-staging.netradyne.com`, then opens a session. Retries up to 5x with exponential backoff. Hardcoded staging credentials (`device-test-automation`/`devicetestautomation`).
- `aws_ping_command(user_id, ping_command) → (test_status, response_status)` — logs in via `login_api()`, POSTs a ping command (e.g. `"reboot-phone"`, `"keep-alive"`) to `idms-staging.netradyne.com/restserver/api/v1/devices/{device_id}/ping`. `device_id` comes from `DEVICE_ID` env var, **not** a parameter.

---

## DATABASE LAYER (src/utils/engine/db_utils.py)
Two separate Postgres connections are configured via env vars, loaded through `python-dotenv`:

```python
DB_CONFIG   = {host: HOST,   dbname: DB_NAME, user: DB_USER, password: DB_PASSWORD, port: DB_PORT}
DB_CONFIG_2 = {host: HOST_2, dbname: DB_NAME, user: DB_USER, password: DB_PASSWORD, port: DB_PORT}
```
`DB_CONFIG_2` is meant for a different host (`HOST_2`) but currently falls back to the *same* `DB_NAME`/`DB_USER`/`DB_PASSWORD` as `DB_CONFIG` if a `_2` variant isn't set — only the host truly differs today.

- `run_postgresql_query(query, params=()) → List[tuple] | None` — uses `DB_CONFIG`. Autocommits; returns rows for `SELECT`, else `None`.
- `wait_for_postgresql_result(query, params=(), timeout=300, interval=10) → List | None` — polls `run_postgresql_query` until non-empty or timeout.
- `fetch_api_calls_window(device_id, msg_id, minutes_before=30, minutes_after=30, poll=False, timeout=120, interval=10) → Dict`
  Uses `DB_CONFIG_2` to query `ndrequest_audit_log` for a device's API calls (by `msg_id`) within a UTC time window around "now". Returns `{status, count, start_time, end_time, rows, details}` with rows mapped to `{device_id, session_id, timestamp, msg_id}`.
  `msg_id` is an internal numeric code per API type (e.g. `1`=keep-alive, `2`=version-check, `7`=upload-logs, `8`=upload-videolist, `10`=upload-devicestatus, `16`=upload-observations) — **no enum exists for these; they're inlined as magic numbers in each test.**

---

## ENVIRONMENT VARIABLES (.env, loaded via python-dotenv)
- `OTA_VERSION` — read by `pytest_addoption`'s `--ota-version` default; not consumed anywhere else since the Allure metadata writer that used to read it was removed (see **Reporting**)
- `ENVIRONMENT` — read by `pytest_addoption`'s `--env` default; same caveat as above
- `DEVICE_ID` — used by `aws_ping_command` (via `DeviceTest.aws_ping_command`) and by `pytest_addoption`'s `--device-id` default
- `DEVICE_IP` — read by `pytest_addoption`'s `--device-ip` default; not consumed elsewhere
- `HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_PORT` — Postgres `DB_CONFIG`
- `HOST_2` — Postgres `DB_CONFIG_2` host (falls back to `HOST` if unset)

Voyager pod SSH credentials (`voyager`/`voyager`) and pod name (`netra`) are **hardcoded** in `connection.py`, not env-driven.

`EXECUTOR_NAME`, `EXECUTOR_TYPE`, `USER`, `GIT_BRANCH` were previously read only by the now-removed Allure `pytest_sessionfinish` hook (for `executor.json`) — nothing in the codebase reads them anymore; safe to ignore or remove from `.env` if present.

`.env` itself is gitignored (see **Repo Hygiene** below) — never commit real credentials in it.

---

## LOGGING (src/utils/logger.py)
- `setup_logger(name="pod_logger", level=logging.INFO) → logging.Logger`
  Plain stdlib logger, timestamped format, single `StreamHandler` to stdout. No file logging, no per-device log files, no emojis — pytest (via `--capture=tee-sys`) captures stdout and folds it into each test's section of the HTML report. This replaces the reference framework's dedicated `LiveLogger` class entirely.

---

## TEST LIFECYCLE (src/tests/conftest.py)
No custom `DeviceTest.start_test/end_test` lifecycle hooks — lifecycle is handled by **pytest's own mechanisms** plus one hook:

- `pytest_addoption` — registers CLI/env-driven options: `--ota-version`, `--env`, `--device-id`, `--device-ip` (each defaults from the matching env var), plus `--skip-reboot` (see below). These are read by test code via `session.config.getoption(...)` where needed; nothing consumes them automatically now that the Allure `pytest_sessionfinish` metadata writer (which used to read them into `environment.properties`) has been removed — see **Reporting**.

Shared fixtures live in `conftest.py` (moved out of `test_sanity_functions.py` so any new test file/subfolder inherits them automatically — pytest discovers fixtures from `conftest.py` files walking up the directory tree, not from sibling test modules):
- `reboot_voyager_fixture` (autouse, `scope="session"`) — reboots voyager once for the whole pytest run, then sets the vehicle to DRIVE mode via a `redis-cli xadd` telemetry command. No teardown.
  - **`--skip-reboot`** CLI flag skips this entire flow (reboot, wait-for-ping, 240s pod-init sleep, DRIVE-mode `redis-cli` call) — the fixture still `yield`s so `pod_connection`/`device` still connect normally, it just connects to the pod as-is instead of forcing a fresh reboot first. Useful when running a small, targeted subset of tests (e.g. `pytest src/tests/btfv src/tests/power_monitor --skip-reboot`) against a pod that's already known to be in a good state — saves the 10+ minute reboot/DRIVE-mode setup cost. Default (flag omitted) is unchanged: full reboot + DRIVE mode every run.
- `pod_connection` (`scope="session"`) — opens one persistent `connect_to_pod()` session shared by every test across every test file in the run, closes it at session end.
- `device` (`scope="session"`) — wraps `pod_connection` in a `DeviceTest` facade instance shared the same way (see **DeviceTest Facade**).

**Implication:** all three are **session**-scoped, not module-scoped — the device reboots and connects exactly **once per pytest invocation**, regardless of how many test files/subfolders are collected (e.g. `test_sanity_functions.py` plus a growing `src/tests/bagheera/` with multiple files all share the same reboot + connection + `DeviceTest`). This was a deliberate change from the original module scope (one reboot per *file*, ~5-7 minutes each) once multiple test files became a real near-term plan — module scope would have multiplied that cost by the number of files in every full run. Trade-off: all files now share one device/pod state across the whole run, so a test in one file that leaves the device in a bad state (stuck config, killed service, etc.) can affect tests in files that run after it in the same session — there is no per-file reset. Verified via `pytest --setup-plan` across two throwaway test files in separate subfolders: the fixture chain shows `SETUP S` (session) once at the very top and `TEARDOWN S` once at the very end, not once per file.

---

## TEST NAMING CONVENTION
Every test function is suffixed with an **ITN ticket ID**: `test_<description>_itn<NNNN>`. This ties each test back to a Jira/tracker item. When adding a test, follow this pattern and get the real ITN number rather than inventing one.

---

## REPORTING
- **pytest-html** is the reporting engine, configured entirely via `pytest.ini` `addopts` — no CLI flags needed for a normal run:
  ```ini
  [pytest]
  addopts = -v --capture=tee-sys --html=src/reports/report.html --self-contained-html
  testpaths = src/tests
  markers =
      smoke: quick smoke tests
      regression: full suite tests
      critical: critical path validation
  ```
  `--self-contained-html` embeds all CSS/JS inline into one `.html` file — no separate assets folder to keep alongside it. `--capture=tee-sys` means stdout/stderr are both shown live in the terminal **and** captured into each test's report section (rather than only captured, which is pytest's default with `--capture=fd`).
  `testpaths` was pinned to the single `test_sanity_functions.py` file at first, then broadened to the whole `src/tests` directory so any new test file — including ones nested in a new subfolder, e.g. `src/tests/services/test_bagheera.py` — is picked up by plain `pytest` automatically. Verified by creating a throwaway `src/tests/_probe_services/test_probe_service.py` and confirming `pytest --collect-only` found it (35 → 36) with zero other changes. `conftest.py` and `live_report.py` sit in the same directory but aren't collected as tests since they don't match the `test_*.py` naming pattern.
- `run_test.sh` was a thin wrapper (`pytest --html=src/reports/report.html --self-contained-html | tee pytest.log`) — removed since nothing in the repo depended on it (no CI/Makefile reference) and it duplicated what plain `pytest.ini`-driven `pytest` already does; see README.md for the equivalent plain commands (including targeted/service runs and `--skip-reboot`, neither of which the old script supported).
- **Allure was removed** (previously configured via `--alluredir`/`--clean-alluredir` and a `run_test.sh` `allure generate` step) — it required a separately-installed `allure` CLI binary the Python `requirements.txt` never actually declared, and the repo now has two working report paths again (this doc previously flagged that as unresolved: "two reporting mechanisms are documented" — the pytest-html one is now the *only* one, both documented and configured to match).
- Removing Allure also required deleting `conftest.py`'s `pytest_sessionfinish` hook, which wrote Allure-specific `environment.properties`/`executor.json` files via `config.getoption("allure_report_dir")` — an option that only exists when `allure-pytest` is installed, so it would have raised `ValueError` on every run once Allure was uninstalled. pytest-html has no equivalent metadata-file mechanism, so that run-metadata capture (device id, OTA version, environment, executor) is gone; it was Allure-only and nothing else read those files.
- `requirements.txt` was also out of sync with actual imports — `python-dotenv`, `requests`, and `psycopg2-binary` are used throughout `src/utils/` but were missing, so `pip install -r requirements.txt` alone never actually installed everything the code needed. Fixed to list `pytest`, `pytest-html`, `pexpect`, `python-dotenv`, `requests`, `psycopg2-binary` (+ optional `jira`, see **Live HTML Report** below).

---

## LIVE HTML REPORT (src/tests/live_report.py + src/utils/engine/jira_client.py)

A **second**, independent report generator alongside pytest-html, ported from the pytest_device_validator reference's `live_report.py` plugin and cut down to this repo's scale (single process, one device, 35 flat test functions — no multi-device orchestration, no per-module step grouping).

### What it does differently from pytest-html
- **Live-updating**: rewrites `src/reports/live_report.html` after every test completes (throttled to at most once per second), with a `<meta http-equiv="refresh" content="10">` tag until the run finishes — open it in a browser mid-run to watch progress, unlike pytest-html which only writes once at session end.
- **One row per test function** (`test_<description>_itn<NNNN>`), with columns for verdict, duration, a truncated failure summary, timestamp, and an expandable detail panel.
- **Renders each test's `DeviceTest.command_log`** in that detail panel — every `device.run(...)`/`device.search_log(...)`/etc. call the test made, in order, with its output. Retrieved via `item.funcargs.get("device")` inside `pytest_runtest_makereport` (the fixture instance is still alive and populated at that point in the hook chain).
- **Known/unknown-issue badges** on failed tests, via `JiraCache` (see below) — optional, degrades to an "UNCLASSIFIED" badge with no errors if JIRA isn't configured.
- **Search/filter toolbar** (by test id/description text, and by verdict) — client-side JS, no server needed since it's a static file.

### How it's wired in
- `src/tests/conftest.py` declares `pytest_plugins = ["src.tests.live_report"]` — this is the mechanism that loads it (a bare `pytest_plugins = ["live_report"]` does **not** work here, since `src/tests/` is a proper package via its `__init__.py`; the plugin must be referenced by its full dotted path).
- `live_report.py` registers itself via `pytest_configure` → `config.pluginmanager.register(LiveReportPlugin(), "live_report_plugin")`, not via a `pytest11` entry point (that would require this repo to be packaged/installed, which it isn't).
- `--no-live-report` CLI flag disables it for a given run if needed (e.g. to isolate a pytest-html-only run for debugging).
- Artifacts: `src/reports/.live_results.jsonl` (one JSON line per completed test, purged and rebuilt fresh each run — the report is rendered by reading this file back, same pattern as the reference's per-device JSONL files, just single-file since there's only one device here) and `src/reports/live_report.html` (the rendered output). Both fall under the existing `src/reports/` line in `.gitignore`.

### DeviceTest.command_log shape difference from the reference
The reference's `command_log` entries carry `{cmd, rc, stdout, stderr, duration_ms, timestamp}` (from its `CommandResult` dataclass). This repo's `DeviceTest.command_log` (src/utils/device_test.py) entries are simpler — `{cmd, output, timestamp}` — because `run_command_on_pod` here returns a plain string/`None`, not a structured result object. The report's command-log rendering reflects that: no separate stdout/stderr/exit-code columns, just command + whatever it returned.

### JIRA integration (src/utils/engine/jira_client.py)
Ported from the reference's `jira_client.py` with two adaptations:
- **Ticket-key extraction**: the reference maps `TC_<service>_<num>_...` test-case IDs to `TC-<num>` JIRA tickets. This repo's tests are named `test_<description>_itn<NNNN>`, so `_extract_jira_ticket` instead regexes out `itn(\d+)` and maps it to `ITN-<NNNN>` — verified against every real test name in `test_sanity_functions.py`.
- **Credentials are environment-variables-only** (`JIRA_SERVER`, `JIRA_USERNAME`, `JIRA_API_TOKEN`, read via `.env`/`python-dotenv`) — **the reference's `jira_config.ini` file-based config was deliberately not ported**, because the copy of it in the reference repo has a live API token and an email address committed in plaintext. Never add an equivalent `.ini` file here; `.gitignore` has a defensive `jira_config.ini` line in case one gets created out of habit, but the code doesn't read it at all.
- Same prefetch-once/classify-many-times pattern as the reference: `JiraCache.prefetch(test_ids)` does one batch of JIRA API calls at `pytest_collection_modifyitems` time (all 35 test IDs' tickets in one pass), then `JiraCache.classify(test_id)` is a zero-API-call local lookup used per failed test when rendering.
- Fully optional at every layer: no `jira` package installed → `_get_jira_connection()` logs a warning and returns `None` → `prefetch()` returns `0` and does nothing → `classify()` returns `NO_JIRA` → the report shows an "UNCLASSIFIED" badge. No exceptions propagate from any of this into the test run itself.

---

## REPO HYGIENE
A `.gitignore` now exists at the repo root, covering: `__pycache__/`, `.pytest_cache/`, `.env`, `pytest.log`, and generated report output (`report/`, `report.html`, `src/reports/`, `src/FE_latest_report/`, ad hoc `*_report.zip`/`*_report/` dirs under `src/`). Before this, all of that showed up as untracked clutter on every `git status` and `.env` risked being committed by accident. If a new report/output path shows up untracked after a test run, add it to `.gitignore` rather than leaving it dangling.

---

## NEW DEVICE FUNCTION / TEST CHECKLIST

1. **New device/pod operation** (shell command, file check, log search, service check):
   - Add a plain function to the matching module under `src/utils/engine/` (see **Module Layout**) — e.g. a new log-search helper goes in `engine/log_search.py`, a new OTA/file check goes in `engine/device_checks.py`.
   - Accept `pod_connection` (the `pexpect.spawn` child) as the first parameter if it needs to run inside the pod.
   - Use `run_command_on_pod(child, cmd, directory=None)` (from `engine/connection.py`) to execute; results already pass through `clean_output`.
   - Prefer returning a `{status, ..., details}` dict (the newer convention) over raising `AssertionError` directly, unless extending an older function that already raises.
   - Add a thin wrapper method to `DeviceTest` (src/utils/device_test.py) that delegates to it and appends to `command_log`, then register it in `DEVICE_API` (src/utils/device_api.py) — see **DeviceTest Facade**.
   - If you also want it importable via the old `pod_utils` shim, add it to that module's import block and `__all__` list in `engine/pod_utils.py` — but prefer `device.<method>(...)` in new test code.

2. **New cloud/API check**:
   - If it's a log-based verification of an API call, reuse `device.frequency_based_calls(...)` (periodic) or `device.event_based_api_call(...)` (one-shot) rather than writing a new grep/timestamp parser.
   - If it needs a live HTTP call to IDMS, follow the `login_api()` + `aws_ping_command()` pattern in `engine/cloud_api.py`, then wrap it on `DeviceTest` if it takes a pod-independent identifier the way `aws_ping_command` does.

3. **New DB-based check**:
   - Reuse `run_postgresql_query` / `wait_for_postgresql_result` for `DB_CONFIG`, or `fetch_api_calls_window`-style direct `psycopg2.connect(**DB_CONFIG_2)` for the audit-log DB — all in `engine/db_utils.py`.
   - If checking a new API's audit rows, find/assign its `msg_id` — there's no registry, so grep existing tests for `msg_id=` to avoid colliding with an already-used code.
   - If the check doesn't need a live pod connection (pure DB query, like the `test_api_call_in_idms_upload_*` tests), don't force it through the `device`/`pod_connection` fixtures — call `engine.db_utils` directly and skip both fixtures, same as those tests do.

4. **New test**:
   - Add to `src/tests/test_sanity_functions.py`, or a new file/subfolder under `src/tests/` for a new service area — `pytest.ini`'s `testpaths = src/tests` already covers the whole tree, no config change needed. A new subfolder needs its own `__init__.py` (matching the existing `src/tests/__init__.py` pattern) if it should be an importable package rather than just a loose directory pytest walks into. Real examples of this pattern: `src/tests/btfv/test_btfv_service_status.py` and `src/tests/power_monitor/test_power_monitor_service_status.py` — one subfolder per service, each a self-contained `RUNNING`-status check via `supervisorctl status <service>`, run with `pytest src/tests/btfv src/tests/power_monitor`.
   - The shared fixtures (`reboot_voyager_fixture`, `pod_connection`, `device`) live in `src/tests/conftest.py`, so any new file/subfolder gets them automatically just by taking `device` (or `pod_connection`) as a test parameter — no import needed. They're **session**-scoped, so the whole pytest run (across every file) shares one reboot/connection/`DeviceTest` — don't assume a fresh device state at the start of your new file if other test files already ran earlier in the same invocation; see **Test Lifecycle**.
   - Take the `device` fixture (a `DeviceTest` instance) as the test parameter, and call `device.<method>(...)` — don't import util functions directly unless the test genuinely doesn't need the pod (see point 3).
   - Name it `test_<description>_itn<ticket>`.
   - Don't open new pod connections per test — the `device` fixture shares the session-scoped `pod_connection` across the whole run.
   - Add `@pytest.mark.smoke` / `regression` / `critical` if it fits one of the declared markers.

5. `DEVICE_API` in `device_api.py` is a **manual, unenforced** registry (unlike the reference, where it also feeds an LLM prompt/validator) — no agent/codegen layer exists here. Keep it in sync with `DeviceTest` by hand; nothing will fail loudly if it drifts.

---

## File Structure Reference

```
src/
  tests/
    conftest.py                ← pytest_addoption (CLI options incl. --skip-reboot) + pytest_plugins=["src.tests.live_report"]
    live_report.py              ← live-updating HTML report plugin (see LIVE HTML REPORT)
    functionality_map.py       ← test-to-functionality-group map, used by live_report.py's Coverage/Failures/Overview tabs
    test_sanity_functions.py   ← all core test cases, using the `device` (DeviceTest) fixture
    btfv/
      test_btfv_service_status.py        ← btfv supervisorctl RUNNING-status check
    power_monitor/
      test_power_monitor_service_status.py ← power_monitor supervisorctl RUNNING-status check
  utils/
    device_test.py               ← DeviceTest facade — wraps engine/ modules below, keeps command_log
    device_api.py                ← DEVICE_API registry — every DeviceTest method, kept in sync by hand
    logger.py                    ← setup_logger() — stdlib logger to stdout
    engine/
      connection.py                ← SSH/pexpect connection primitives
      log_search.py                ← log search & API-cadence verification
      device_checks.py             ← OTA/file/service/device-info checks
      time_utils.py                ← time & size comparison helpers
      cloud_api.py                 ← IDMS login + AWS ping command
      db_utils.py                  ← Postgres queries (DB_CONFIG, DB_CONFIG_2)
      jira_client.py                ← JiraCache — optional known/unknown-issue classification for live_report.py
      pod_utils.py                ← thin re-export shim over the engine modules above (back-compat only)

pytest.ini                  ← addopts (pytest-html), testpaths (src/tests, whole tree), markers
requirements.txt            ← pytest, pytest-html, pexpect, python-dotenv, requests, psycopg2-binary, jira (optional)
.gitignore                  ← pycache/pytest_cache/.env/generated report output/jira_config.ini
.env                        ← OTA_VERSION, ENVIRONMENT, DEVICE_ID, DEVICE_IP, HOST(_2), DB_*, JIRA_* (gitignored)
jira_config.ini             ← optional JIRA credentials fallback, [JIRA] section (gitignored — never commit real values)
README.md                   ← setup + run instructions (targeted/service runs, --skip-reboot, both report paths)
```

---

## Key Differences vs. the pytest_device_validator Reference Framework

| Aspect | pytest_device_validator | fleetedge-automation |
|---|---|---|
| Architecture | Layered (Facade/Connection/Engine/Analysis/Healing) | Facade (DeviceTest) over focused util modules + one test file |
| Transport | `DeviceTransport` interface, ADB + Serial impls | Single `pexpect`-over-SSH path (voyager → pod), no interface/abstraction |
| Public API | `DeviceTest` facade class, thin wrappers | `DeviceTest` facade class, thin wrappers — same pattern, much smaller surface |
| Self-healing | `SelfHealer` with regex rules, auto reconnect/reboot/retry | None — timeout just logs and returns empty |
| Device pool | `DeviceManager` with locking, multi-device | Single shared `pod_connection`/`device` fixture per test module |
| Logging | Custom `LiveLogger`, per-device files, emojis | Stdlib logger to stdout, captured into the pytest-html report; `command_log` on DeviceTest is much simpler (no rc/stdout/stderr split) |
| Reporting | Custom `live_report.py` pytest plugin — self-updating HTML, JIRA classification, multi-device tables, functionality-group coverage | Two reports: `pytest-html` (`src/reports/report.html`, session-end, no JIRA) **and** its own `live_report.py` (`src/reports/live_report.html`, live-updating, JIRA-aware, but single-device/single-file, no functionality grouping) |
| Agent/codegen | `agent/` layer generates tests from YAML via LLM, DEVICE_API feeds it | Not present — `device_api.py` here is a manual, unenforced reference only |
| Extension point | Add to right layer + update `DEVICE_API` registry | Add function to the matching `src/utils/engine/*.py` module, wrap on `DeviceTest`, update `DEVICE_API` |
| Return convention | `CommandResult` dataclass everywhere | Mixed: `{status, details}` dicts (newer) or bare `AssertionError` (older); no `CommandResult` type exists |
| Hardware scope | Relay/camera/LED/fan controllers, GPS spoofing, HealthStats payload validation | None of the above — pod-level checks only (services, files, logs, OTA, cloud API, DB) |
