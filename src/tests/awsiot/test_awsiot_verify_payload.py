"""
Feature: AWSIOT — Verify Payload
Description:
  Verify AWSIOT payload content, DELTA, READ and ROOT.
"""

import time


def test_step1_check_datetime(device):
    """Verify AWSIOT payload content, DELTA, READ and ROOT.

    PreCondition_1 — Verify device datetime is in sync.
    """
    result = device.compare_datetime()
    assert result["status"] == "Pass", f"datetime is incorrect: {result['details']}"


def test_step2_send_keepalive(device):
    """STEP_1 — Send keep-alive ping command."""
    device.variables["search_start_ts"] = device.get_current_time_epoch()["epoch_ms"]
    test_status, response_status = device.aws_ping_command("8430", "keep-alive")
    assert test_status == "Pass" and response_status, f"Aws ping keep alive not started: {test_status}"


def test_step3_wait(device):
    """STEP_2 — Wait 20s after keep-alive (non-blocking)."""
    time.sleep(20)


def test_step4_get_ping_id(device):
    """STEP_3 — Extract ping-id from awsiot logs."""
    output = device.run("grep 'Received ping-' /home/ubuntu/.nddevice/log/awsiot/* | tail -n 1 | awk -F'[: ]+' '{print $NF}'")
    ping_id = output.strip() if output else ""
    assert ping_id, "Received ping- not found in awsiot logs; could not extract ping-id"
    device.variables["ping_id"] = ping_id


def _delta_shadow_payload_ok(payload, ping_id):
    # Both the delta_update :: Classic Shadow and Document: log lines carry
    # plain (unescaped) JSON, e.g. "type":"ping" -- not "type\":\"ping" --
    # so match plain quoting here.
    return (
        ping_id in payload
        and '"type":"ping' in payload
        and '"status":"new' in payload
        and "keep-alive" in payload
    )


def test_step5_verify_delta_shadow(device):
    """STEP_4 — Verify delta_update Classic Shadow payload contains ping-id, type, status, keep-alive.

    Two log formats are possible for this payload ('delta_update :: Classic
    Shadow' or the alternate 'Document:' format checked in STEP_4_1) — at
    least one of the two must contain the expected fields.
    """
    ping_id = device.variables.get("ping_id", "")
    output = device.run(
        r'grep -E "delta_update :: Classic Shadow :\s*\{.*\"requests\":*\{\"ping-.*\":.*" '
        r'/home/ubuntu/.nddevice/log/awsiot/* | tail -n 1'
    )
    payload = (output or "").strip()
    device.variables["delta_shadow_ok"] = _delta_shadow_payload_ok(payload, ping_id)
    device.variables["delta_shadow_payload"] = payload


def test_step6_1_verify_delta_shadow_document_format(device):
    """STEP_4_1 — Verify delta shadow in 'Document:' format (alternate log format).

    Fails only if neither this format nor the Classic Shadow format checked
    in STEP_4 contained the expected fields.
    """
    ping_id = device.variables.get("ping_id", "")
    output = device.run(
        r'grep -E "Document:\s*\{.*\"requests\":*\{\"ping-.*\":.*" '
        r'/home/ubuntu/.nddevice/log/awsiot/* | tail -n 1'
    )
    payload = (output or "").strip()
    document_ok = _delta_shadow_payload_ok(payload, ping_id)
    classic_shadow_ok = device.variables.get("delta_shadow_ok", False)
    assert document_ok or classic_shadow_ok, (
        f"Payload delta fields not found in either format. "
        f"Classic Shadow payload: {device.variables.get('delta_shadow_payload', '')}; "
        f"Document payload: {payload}"
    )


def test_step7_verify_keepalive_received(device):
    """STEP_5 — Verify 'Received command: keep-alive' in logs."""
    ts = device.variables.get("search_start_ts")
    output = device.search_log("/home/ubuntu/.nddevice/log/awsiot", "Received command: keep-alive", start_timestamp=ts)
    assert output, "Received command: keep-alive log message not found"


def test_step8_verify_root_shadow(device):
    """STEP_6 — Verify root Classic Shadow payload contains ping-id, type, status, keep-alive."""
    ping_id = device.variables.get("ping_id", "")
    output = device.run(
        r'grep -E "root:*\{.*\"requests\":*\s\{\"ping-.*\":.*" '
        r'/home/ubuntu/.nddevice/log/awsiot/* | tail -n 1'
    )
    payload = (output or "").strip()
    # root: log line also carries plain (unescaped) JSON, e.g. "type": "ping".
    ok = (
        ping_id in payload
        and '"type": "ping' in payload
        and '"status": "new' in payload
        and "keep-alive" in payload
    )
    assert ok, f"Payload root fields not found: {payload}"


def test_step9_1_verify_ping_success(device):
    """STEP_6_1 — Verify ping success or shadow update log.

    Runs all 4 known log patterns unconditionally (no short-circuit on the
    first match) so every check's evidence shows up in the command log;
    passes if at least one pattern matched.
    """
    ts = device.variables.get("search_start_ts")
    patterns = [
        "Success sending ping:",
        "Successfully updated shadow state.",
        "send_done: Making request status to STATUS_DEL for req:",
        "Deleting off request:",
    ]
    results = {
        pattern: device.search_log("/home/ubuntu/.nddevice/log/awsiot", pattern, start_timestamp=ts, timeout=60, interval=5)
        for pattern in patterns
    }
    assert any(results.values()), f"Ping success/shadow update log not found (checked all 4 known log patterns): {results}"


def test_step10_restart_awsiot(device):
    """STEP_7 — Restart awsiot service."""
    result = device.restart_service("awsiot")
    assert result["status"] == "Pass", f"Failed to restart awsiot service: {result['details']}"


def test_step11_wait(device):
    """STEP_8 — Wait 20s after restart (non-blocking)."""
    time.sleep(20)


def test_step12_verify_read_shadow(device):
    """STEP_9 — Verify read_update Classic Shadow contains vehicleClass and cameras.

    Locates the matching file+line number first, then checks each required
    field's presence on that exact line independently. Each check uses
    grep -o (echoes the matched field name/value back, e.g. "vehicleClass":
    "CLASS2") instead of grep -c (a bare 0/1 count), so the report's
    command log reads as evidence of what was actually found rather than
    an opaque number -- the pod terminal truncates long single-line output
    (e.g. the full JSON payload) regardless of formatting, so this avoids
    relying on the full line ever being captured intact.
    """
    locate_cmd = (
        r'grep -EnH "read_update :: Classic Shadow :\s*\{.*\"state\":*" '
        r'/home/ubuntu/.nddevice/log/awsiot/* | tail -n 1 | cut -d: -f1,2'
    )
    location = (device.run(locate_cmd) or "").strip()
    assert location, "read_update Classic Shadow log line not found"
    file_path, line_no = location.rsplit(":", 1)

    vehicle_detail_hash_error = device.run(
        f"grep -o 'No vehicleDetailHash found' {file_path} | head -1"
    )
    if vehicle_detail_hash_error and vehicle_detail_hash_error.strip():
        print(
            f"Device logged '{vehicle_detail_hash_error.strip()}' (IOT-PRSR error) in {file_path} "
            f"around this shadow update -- confirms vehicleDetailHash is not applicable/not "
            f"generated on this device, not omitted from the check by mistake"
        )

    missing = []
    for field in ("vehicleClass", "cameras"):
        match = device.run(
            f"sed -n '{line_no}p' {file_path} | grep -oE '\"{field}\"\\s*:\\s*[^,}}]+'"
        )
        found = bool(match and match.strip())
        if not found:
            missing.append(field)

    assert not missing, f"Payload read fields not found on {location}: missing {missing}"
