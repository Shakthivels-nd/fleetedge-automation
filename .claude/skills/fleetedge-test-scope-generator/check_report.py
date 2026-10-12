#!/usr/bin/env python3
"""Sanity-check a rendered FleetEdge test-scope HTML report.

Usage: python3 check_report.py <report.html> [--repo-root .]

Paths written as "Proposed: src/tests/..." are new-test proposals and are not required to exist.
Checks: no leftover {{placeholders}}, all 8 tab buttons/panels + tab script present,
every src/tests/...py path mentioned exists, every Jira key is linked, and the
Monitoring panel doesn't cite device-only sources in table rows. Exit 1 on any failure.
"""
import argparse
import re
import sys
from pathlib import Path

TABS = ["overview", "architecture", "services", "testcases", "automation_pytest",
        "automation_monitoring", "findings", "gap_analysis"]
DEVICE_ONLY = re.compile(r"LOG_[ICEW]\b|\.nddevice/log|xattr|sqlite|VIDFILES|supervisorctl|\badb\b", re.I)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("report")
    ap.add_argument("--repo-root", default=".")
    a = ap.parse_args()
    html = Path(a.report).read_text()
    root = Path(a.repo_root)
    problems = []

    left = sorted(set(re.findall(r"\{\{[A-Z0-9_]+\}\}", html)))
    if left:
        problems.append(f"unreplaced placeholders: {left}")

    for t in TABS:
        if f'data-tab="{t}"' not in html or f'id="{t}"' not in html:
            problems.append(f"missing tab/panel: {t}")
    if "tabButtons.forEach" not in html:
        problems.append("tab-switching <script> block missing/modified")

    for p in sorted(set(re.findall(r"(?<!Proposed: )src/tests/[\w/.\-]+\.py", html))):
        if not (root / p).is_file():
            problems.append(f"cited test file does not exist: {p}")

    for k in sorted(set(re.findall(r"\b[A-Z][A-Z0-9]+-\d+\b", html))):
        if k.startswith(("UTF-", "ISO-")):
            continue
        if f"/browse/{k}" not in html:
            problems.append(f"ticket {k} mentioned but never linked to /browse/{k}")

    m = re.search(r'id="automation_monitoring".*?</section>', html, re.S)
    if m:
        body = m.group(0)
        for row in re.findall(r"<tr>.*?</tr>", body, re.S):
            if "colspan" in row:
                continue  # exclusion note may name excluded sources
            hits = DEVICE_ONLY.findall(row)
            if hits:
                problems.append(f"device-only source in a Monitoring row: {sorted(set(hits))}")

    if problems:
        print("FAIL")
        for p in problems:
            print(" -", p)
        return 1
    print("OK: structure, links, test-file paths and monitoring sources check out. "
          "Still recount KPIs against table rows by hand.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
