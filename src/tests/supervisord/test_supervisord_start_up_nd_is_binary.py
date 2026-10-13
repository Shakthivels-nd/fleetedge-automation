"""
Test case : start_up_nd.sh is a binary
Purpose   : /usr/bin/start_up_nd.sh looks like a shell script but is a compiled
            binary. It is what starts supervisord.

Precondition
  The ND pod is up and running.

Steps and expected result
  1. Run `cat /usr/bin/start_up_nd.sh`
       -> The contents are unreadable (binary, not a text script).

How the test runs the cat
  A plain `cat` of a binary sends bytes the pod session cannot decode, so nothing
  useful would show in the command log. The test pipes the cat through `tr` so
  every non-printable byte shows as '?', then counts the non-printable bytes.
  It passes when there are some and the file does not start with `#!`.
"""

START_UP_SCRIPT = "/usr/bin/start_up_nd.sh"
NON_PRINTABLE = r"'[:print:][:space:]'"


def test_step1_cat_start_up_script_unreadable(device):
    """STEP 1 — Run `cat /usr/bin/start_up_nd.sh` and check the contents are unreadable (binary)."""
    shown = device.run(f"cat {START_UP_SCRIPT} | head -c 300 | tr -c {NON_PRINTABLE} '?'")
    count = device.run(f"cat {START_UP_SCRIPT} | tr -d {NON_PRINTABLE} | wc -c")

    assert shown and shown.strip(), f"cat {START_UP_SCRIPT} printed nothing (missing or empty file?)"
    assert not shown.lstrip().startswith("#!"), f"{START_UP_SCRIPT} is a shell script, expected a binary: {shown[:200]!r}"
    assert count and count.strip().isdigit(), f"Could not count non-printable bytes: {count!r}"
    assert int(count.strip()) > 0, f"{START_UP_SCRIPT} contains only printable text, expected an unreadable binary: {shown[:200]!r}"
