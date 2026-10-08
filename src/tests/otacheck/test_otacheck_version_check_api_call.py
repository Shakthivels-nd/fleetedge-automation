"""
Feature: otacheck — Version Check API Call Successful
Description:
  Ported from nd_test_bot's TC_73_OTACHECK_VERSIONCHECKAPI_INTERNET_STABILITY_60MIN,
  STEP_11 only (user decision 2026-10-08). The reference first removes the
  default route, waits, restores networking and injects counter=10; none of
  that is ported (see PORT_TRACKER.csv), so this does NOT prove the call
  succeeds after internet unavailability — only that otacheck's logs show a
  successful version check API call.

  Reference's search_logs list ["JWT response code = 1", "wget -O",
  "versioncheckresponse.txt"] is checked as: each term present in
  otacheck's logs (latest occurrence of each).
"""

LOG_DIR = "/home/ubuntu/.nddevice/log/otacheck"
TERMS = ["JWT response code = 1", "wget -O", "versioncheckresponse.txt"]


def test_step1_verify_version_check_api_call(device):
    """STEP 1 — Verify the version check API call succeeded (JWT ok, wget of versioncheckresponse.txt) in otacheck logs."""
    missing = []
    for term in TERMS:
        output = device.run(f"grep -ah '{term}' {LOG_DIR}/*.log 2>/dev/null | sort | tail -n 1")
        if not (output and term in output):
            missing.append(term)
    assert not missing, f"Not found in otacheck logs: {missing}"
