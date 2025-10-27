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
pytest src/tests/test_pod_functions.py::test_connection_success -v --capture=tee-sys --html=src/reports/report.html | tee pytest.log
```

### ▶️ Run All Test Cases
Run:
```bash
pytest src/tests/ -v --capture=tee-sys --html=src/reports/report.html | tee pytest.log

```
### 🧑‍💻 Report
Path:
```bash
src\reports\report.html
```
