"""
Feature: Scheduler — Complete File Operation
Description:
  Verify scheduler_manager's buffer size and operated size match (confirming
  a file operation completed), and that it logs the operation as complete.

  Ported from nd_test_bot's TC_1258_SCHEDULER_COMPLETE_FILE_OPERATION.

  Log strings "nd_buff_operate" (with "op_buffer_size"/"Operated Size"
  fields) and "nd_file_operate_device: file operation complete"
  (UNVERIFIED -- ported from reference, not yet confirmed on FE) need a
  live check before this test is trusted.
"""


def test_step1_get_buffer_size(device):
    """STEP_1 — Extract the operated buffer size from scheduler_manager logs."""
    output = device.run(
        "grep -inr 'nd_buff_operate' /home/ubuntu/.nddevice/log/scheduler_manager/* | "
        "awk -F'op_buffer_size ' '{print $2}' | awk '{print $1}' | grep -v '^$' | head -n 1"
    )
    buffer_size = (output or "").strip()
    assert buffer_size, "Buffer size not found"
    device.variables["buffer_size"] = buffer_size


def test_step2_get_operated_size(device):
    """STEP_2 — Extract the operated size from scheduler_manager logs."""
    output = device.run(
        "grep -inr 'nd_buff_operate' /home/ubuntu/.nddevice/log/scheduler_manager/* | "
        "awk -F'Operated Size ' '{print $2}' | awk '{print $1}' | grep -v '^$' | head -n 1"
    )
    operated_size = (output or "").strip()
    assert operated_size, "Operated size not found"
    device.variables["operated_size"] = operated_size


def test_step3_verify_sizes_equal(device):
    """STEP_3 — Verify buffer size and operated size match."""
    buffer_size = device.variables.get("buffer_size")
    operated_size = device.variables.get("operated_size")
    assert buffer_size == operated_size, (
        f"Buffer size and operated size are not equal: {buffer_size!r} != {operated_size!r}"
    )


def test_step4_verify_file_operation_complete(device):
    """STEP_4 — Verify scheduler_manager logs the file operation as complete."""
    output = device.run("grep -inr 'nd_file_operate_device: file operation complete' /home/ubuntu/.nddevice/log/scheduler_manager/* | head -n 1")
    assert output, "File operation is not complete"
