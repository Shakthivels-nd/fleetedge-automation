# 🚗 Amazon Fleet Edge Device Automation

## 📘 Overview
This repository contains the automation framework for **Amazon Fleet Edge devices**, built using **Python** and **Pytest**.  
It automates **functional** and **validation tests** for Fleet Edge device workflows — including connectivity, service validation, and OTA update checks.

---

## ⚙️ Setup Instructions

Before running tests, make sure your environment is properly configured.

### 1️⃣ Install Dependencies
Run:
```bash
pip install -r requirements.txt
```

### ▶️ Run a Specific Test Case
Run:
```bash
pytest src/tests/test_sanity_functions.py::test_connection_success_itn2426 | tee pytest.log
```

### ▶️ Run Multiple Specific Test Cases
Use `-k` with `or` to select several tests by name in one run (so they all land in the same report):
```bash
pytest src/tests/test_sanity_functions.py -k "test_connection_success_itn2426 or test_ini_fields_present_itn2446" | tee pytest.log
```

### ▶️ Run a Service's Tests (e.g. btfv, power_monitor)
Each service under test lives in its own subfolder of `src/tests/`, e.g.:
```bash
pytest src/tests/btfv src/tests/power_monitor | tee pytest.log
```

### ▶️ Run All Test Cases
Run:
```bash
pytest | tee pytest.log
```

`-v`, `--capture=tee-sys`, `--html=src/reports/report.html` and `--self-contained-html` are already set in `pytest.ini`, so they don't need to be passed on the command line.

### 🚫 Skip the Voyager Reboot / DRIVE Mode Setup
By default, every pytest run reboots the voyager host, waits for it to come back, and sets the vehicle to DRIVE mode before any test runs (`reboot_voyager_fixture` in `conftest.py`) — this alone takes 10+ minutes. If the pod is already in a known-good state and you just want to run a couple of tests against it directly, pass `--skip-reboot`:
```bash
pytest src/tests/btfv src/tests/power_monitor --skip-reboot | tee pytest.log
```

### 🧑‍💻 Reports
Two reports are generated per run:
- **`src/reports/report.html`** — pytest-html, self-contained, written once at the end of the run.
- **`src/reports/live_report.html`** — a live-updating dashboard (auto-refreshes every 10s while tests run) with per-test command logs and pass/fail filtering. Open it in a browser during a run to watch progress.

Both are single self-contained HTML files — open directly in a browser, no separate assets needed.
