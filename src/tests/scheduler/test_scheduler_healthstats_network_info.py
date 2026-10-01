"""
Feature: Scheduler — HealthStats Network Info
Description:
  Verify network info (MAC ID, IPv4, network status) is populated in
  HealthStatsManager's health.log.

  Ported from nd_test_bot's TC_1385_SCHEDULER_HEALTHSTATS_NETWORK_INFO.

  Log fields "mac_id", "ipv4s", "status" (UNVERIFIED -- ported from
  reference, not yet confirmed on FE) need a live check before this test is
  trusted.
"""

import time


def test_step1_verify_mac_id_populated(device):
    """STEP_1 — Verify mac_id is populated in health.log."""
    output = device.run("grep -oP \"(?<=mac_id': ')[^']*\" /home/ubuntu/.nddevice/log/health/health.log")
    assert (output or "").strip(), "Failed to populate Mac ID"


def test_step2_verify_ipv4_populated(device):
    """STEP_2 — Verify ipv4 is populated in health.log."""
    output = device.run("grep -oP \"(?<=ipv4s': \\[')[^']+\" /home/ubuntu/.nddevice/log/health/health.log")
    assert (output or "").strip(), "Failed to populate ipv4"


def test_step3_wait(device):
    """STEP_2_1 — Wait 60s."""
    time.sleep(60)


def test_step4_verify_network_status_true(device):
    """STEP_3 — Verify the network status is True."""
    output = device.run("grep \"status\" /home/ubuntu/.nddevice/log/health/health.log | awk -F\"status': \" '{print $2}' | awk -F',' '{print $1}' | sort | uniq")
    assert "True" in (output or ""), "Network status is not True"
