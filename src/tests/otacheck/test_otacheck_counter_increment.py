"""
Feature: otacheck — Counter Increment
Description:
  Ported from the pytest_device_validator reference's TC_38
  (test_tc_38_otacheck_counter_increment.py). The reference used a
  device.check_otacheck_counter() helper that samples the counter file
  multiple times, computes the diff between each consecutive pair of
  samples, and asserts at least one of those diffs is exactly +1 — this
  specifically catches otacheck ticking the counter by the wrong amount
  (e.g. skipping a value or double-incrementing), not just "it went up by
  some amount eventually."

  FE's DeviceTest has no check_otacheck_counter() helper, so this takes
  its own multiple samples of the counter file directly and reproduces
  the same "at least one +1 diff" check — same intent AND same strength
  as the reference, not a weaker "just increased" check (an earlier
  version of this test only checked after > before, which would have
  wrongly passed if the counter jumped by e.g. +6 between reads; fixed
  after review against the reference).

  Counter file path confirmed present on FE: /dev/shm/otacheck_count.txt.
"""

import re
import time

COUNTER_FILE = "/dev/shm/otacheck_count.txt"
SAMPLE_COUNT = 5
SAMPLE_INTERVAL_SECONDS = 15


def _read_counter(device):
    """Read otacheck's counter file and parse its integer value.

    The file has no trailing newline, so its content directly touches the
    shell prompt that reappears right after (e.g. "33root@netradyne-...").
    clean_output()'s prompt-stripping regex requires a word boundary before
    "root@", which digit-then-letter doesn't provide, so it leaves a
    "33root@" style tail behind instead of stripping it — confirmed against
    a real pod output. Extract the leading digits directly rather than
    requiring the whole string to be clean.
    """
    output = device.run(f"cat {COUNTER_FILE}")
    assert output is not None, f"Failed to read {COUNTER_FILE}."
    match = re.match(r"\s*(\d+)", output)
    assert match, f"Unexpected content in {COUNTER_FILE}: {output!r}"
    return int(match.group(1))


def test_step1_sample_counter_over_time(device):
    """STEP 1 — Sample otacheck's counter file repeatedly to observe its increments."""
    samples = [_read_counter(device)]
    for _ in range(SAMPLE_COUNT - 1):
        time.sleep(SAMPLE_INTERVAL_SECONDS)
        samples.append(_read_counter(device))
    device.variables["counter_samples"] = samples


def test_step2_verify_counter_increments_by_one(device):
    """STEP 2 — Verify at least one consecutive-sample diff is exactly +1
    (mirrors the reference's `1 in diffs` check — not just any increase)."""
    samples = device.variables.get("counter_samples")
    assert samples and len(samples) >= 2, f"Not enough counter samples to compute diffs: {samples}"
    diffs = [b - a for a, b in zip(samples, samples[1:])]
    assert 1 in diffs, (
        f"Expected at least one +1 counter increment between consecutive samples, "
        f"got samples={samples}, diffs={diffs}."
    )
