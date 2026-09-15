import pytest
import math
import os
from dotenv import load_dotenv
load_dotenv()

from src.utils.engine import connection
from src.utils.device_test import DeviceTest

pytest_plugins = ["src.tests.live_report"]


@pytest.fixture(scope="session", autouse=True)
def reboot_voyager_fixture(request):
    """
    Fixture to reboot voyager once before the whole test session.
    And set the voyager to DRIVE mode by sending a redis command.

    Session-scoped: one reboot total per pytest run, shared across every
    test file/module (including src/tests/bagheera/*). Changed from
    module scope so adding more test files doesn't multiply the ~5-7 minute
    reboot cost per file. Trade-off: all files now share one device state,
    so a test in one file that leaves the device in a bad state can affect
    files that run after it in the same session.

    Pass --skip-reboot to skip this whole flow (reboot, wait, DRIVE mode)
    when the pod is already in a known-good state and you just want to
    run a couple of tests against it directly.
    """
    if request.config.getoption("--skip-reboot"):
        print("\n[Setup] --skip-reboot passed: skipping voyager reboot and DRIVE mode setup.")
        yield
        return

    connection.reboot_voyager()
    # Set the voyager to DRIVE mode
    connection.run_command_on_voyager(cmd='redis-cli xadd fe-vehicle-telemetry "*" json "{\"eventType\":\"prnd\", \"value\":\"DRIVE\", \"timestampMs\":\"1728479511759\"}"')
    yield
    # No teardown needed


@pytest.fixture(scope="session")
def pod_connection():
    """Fixture to set up and tear down the pod connection, shared for the whole session."""
    child = connection.connect_to_pod()
    yield child
    connection.close_pod_connection(child)


@pytest.fixture(scope="session")
def device(pod_connection):
    """Fixture providing a DeviceTest facade over the pod connection, shared for the whole session."""
    return DeviceTest(pod_connection)


def pytest_addoption(parser):
    parser.addoption(
        "--skip-reboot",
        action="store_true",
        default=False,
        help="Skip the session-level voyager reboot + DRIVE mode setup and connect to the pod as-is",
    )
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
