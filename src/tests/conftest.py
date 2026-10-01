import pytest
import math
import os
from dotenv import load_dotenv
load_dotenv()

from src.utils.engine import connection
from src.utils.device_test import DeviceTest

pytest_plugins = ["src.tests.live_report"]


def _resolve_device_ip(request):
    """Get the device IP to connect to from --device-ip/DEVICE_IP, falling
    back to connection.voyager_ip's hardcoded default when unset (its
    pytest_addoption default is the literal string "Unknown" when DEVICE_IP
    isn't in the environment -- that must never be used as an actual IP)."""
    device_ip = request.config.getoption("--device-ip")
    if not device_ip or device_ip == "Unknown":
        return connection.voyager_ip
    return device_ip


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

    device_ip = _resolve_device_ip(request)
    connection.reboot_voyager(ip_address=device_ip)
    # Set the voyager to DRIVE mode
    connection.run_command_on_voyager(ip_address=device_ip, cmd='redis-cli xadd fe-vehicle-telemetry "*" json "{\"eventType\":\"prnd\", \"value\":\"DRIVE\", \"timestampMs\":\"1728479511759\"}"')
    yield
    # No teardown needed


@pytest.fixture(scope="session")
def pod_connection(request):
    """Fixture to set up and tear down the pod connection, shared for the whole session.

    Reads --device-ip (defaulting to the DEVICE_IP env var via
    pytest_addoption) so changing DEVICE_ID/DEVICE_IP in .env or via CLI
    actually changes which device gets connected to -- connect_to_pod's own
    default (connection.voyager_ip) is a hardcoded fallback, not env-aware.
    """
    device_ip = _resolve_device_ip(request)
    child = connection.connect_to_pod(ip_address=device_ip)
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
