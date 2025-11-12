import pytest
import math
import datetime
import os
import json
from dotenv import load_dotenv
load_dotenv()

def pytest_addoption(parser):
    parser.addoption(
        "--ota-version",
        action="store",
        default=os.getenv("OTA_VERSION", "N/A"),
        help="OTA Version tested"
    )
    parser.addoption(
        "--env",
        action="store",
        default=os.getenv("ENVIRONMENT", "Staging"),
        help="Environment (e.g., staging, prod)"
    )
    parser.addoption(
        "--device-id",
        action="store",
        default=os.getenv("DEVICE_ID", "Unknown"),
        help="Device ID under test"
    )
    parser.addoption(
        "--device-ip",
        action="store",
        default=os.getenv("DEVICE_IP", "Unknown"),
        help="Device IP address under test"
    )

def pytest_sessionfinish(session, exitstatus):
    """Write environment.properties after all tests are finished"""
    config = session.config
    env_info = {
        "Device-ID": config.getoption("--device-id"),
        "Device-IP": config.getoption("--device-ip"),
        "OTA-Version": config.getoption("--ota-version"),
        "Environment": config.getoption("--env"),
        "Start-Time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # Where Allure stores results
    results_dir = config.getoption("allure_report_dir") or "src/reports/allure-results"
    os.makedirs(results_dir, exist_ok=True)
    env_file = os.path.join(results_dir, "environment.properties")

    # Only create if it doesn't exist to avoid overwriting
    if not os.path.exists(env_file):
        with open(env_file, "w") as f:
            for k, v in env_info.items():
                f.write(f"{k}={v}\n")

    executor_file = os.path.join(results_dir, "executor.json")
    if not os.path.exists(executor_file):
        executor_info = {
            "name": os.getenv("EXECUTOR_NAME", "FleetEdge Tests"),
            "type": os.getenv("EXECUTOR_TYPE", "CI"),
            # "buildName": os.getenv("BUILD_VERSION", config.getoption("--app-release-new") or "unknown"),
            "startTime": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "labels": [
                {"name": "user", "value": os.getenv("USER", "QA Team")},
                {"name": "branch", "value": os.getenv("GIT_BRANCH", "main")}
            ]
        }
        with open(executor_file, "w") as f:
            json.dump(executor_info, f, indent=4)

