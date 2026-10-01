"""
Feature: Scheduler — Log Format Related Files
Description:
  Verify each scheduler-related log file uses its expected timestamp format
  (scheduler_manager uses 13-digit epoch; scheduler/inference_inertial/
  inference/deleter use a "YYYY-MM-DD HH:MM:SS,mmm" datetime).

  Ported from nd_test_bot's TC_1421_SCHEDULER_LOG_FORMAT_RELATED_FILES.
"""

EPOCH_PATTERN = r"^[0-9]\{13\}"
DATETIME_PATTERN = r"^[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\} [0-9]\{2\}:[0-9]\{2\}:[0-9]\{2\},[0-9]\{3\}"


def test_step1_verify_scheduler_manager_epoch_format(device):
    """STEP_1 — Verify scheduler_manager logs use epoch-ms timestamps."""
    output = device.run(f"grep -o '{EPOCH_PATTERN}' /home/ubuntu/.nddevice/log/scheduler_manager/* | head")
    assert (output or "").strip(), "Scheduler_manager logs are not in epoch format"


def test_step2_verify_scheduler_datetime_format(device):
    """STEP_2 — Verify scheduler logs use datetime timestamps."""
    output = device.run(f"grep -o '{DATETIME_PATTERN}' /home/ubuntu/.nddevice/log/scheduler/* | head")
    assert (output or "").strip(), "Scheduler logs are not in date time format"


def test_step3_verify_inference_inertial_datetime_format(device):
    """STEP_3 — Verify inference_inertial logs use datetime timestamps."""
    output = device.run(f"grep -o '{DATETIME_PATTERN}' /home/ubuntu/.nddevice/log/inference_inertial/* | head")
    assert (output or "").strip(), "Inertial logs are not in date time format"


def test_step4_verify_inference_datetime_format(device):
    """STEP_4 — Verify inference logs use datetime timestamps."""
    output = device.run(f"grep -o '{DATETIME_PATTERN}' /home/ubuntu/.nddevice/log/inference/* | head")
    assert (output or "").strip(), "Inference logs are not in date time format"


def test_step5_verify_deleter_datetime_format(device):
    """STEP_5 — Verify deleter logs use datetime timestamps."""
    output = device.run(f"grep -o '{DATETIME_PATTERN}' /home/ubuntu/.nddevice/log/deleter/* | head")
    assert (output or "").strip(), "Deleter logs are not in date time format"
