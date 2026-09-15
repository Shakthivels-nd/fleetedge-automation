"""
live_report.py — pytest plugin for real-time HTML report generation.

Generates a live-updating HTML dashboard as tests run: the report file is
rewritten after each test completes, so it can be opened in a browser and
watched while the suite is still executing (auto-refreshes every 10s until
the run finishes).

Ported from the pytest_device_validator reference framework's live_report.py,
cut down to what this repo actually is: a single pytest process against one
device, ~35 flat test functions (no multi-step test cases, no multi-device
orchestration, no relay/camera hardware). One row per test function.

Tabs (Overview / Failures / Coverage / All Tests / Device) mirror the
reference's tab layout, scaled to this repo's single-device, flat-test-list
shape — see functionality_map.py for the (much smaller) test-to-functionality
grouping used by the Coverage tab and Failures tab.

Each test's command_log (from the `device` fixture's DeviceTest instance,
see src/utils/device_test.py) is captured and rendered in an expandable
detail panel per row, alongside captured stdout and the failure message.

Known/unknown-issue classification (JIRA) is optional: if JIRA_SERVER/
JIRA_USERNAME/JIRA_API_TOKEN aren't set (or the `jira` package isn't
installed), every failure just shows as unclassified rather than erroring.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

try:
    from src.utils.engine.jira_client import JiraCache
    _JIRA_AVAILABLE = True
except Exception:
    _JIRA_AVAILABLE = False

from src.tests.functionality_map import get_functionality_group_from_nodeid


REPORT_DIR = Path("src/reports")
RESULTS_FILE = REPORT_DIR / ".live_results.jsonl"
REPORT_PATH = REPORT_DIR / "live_report.html"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--no-live-report",
        action="store_true",
        default=False,
        help="Disable the live-updating HTML report plugin (live_report.py)",
    )


def pytest_configure(config: pytest.Config) -> None:
    if config.getoption("--no-live-report"):
        return
    config.pluginmanager.register(LiveReportPlugin(config), "live_report_plugin")


class LiveReportPlugin:
    def __init__(self, config: Optional[pytest.Config] = None):
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        # Purge stale artifacts from any previous run before this one starts.
        if RESULTS_FILE.exists():
            RESULTS_FILE.unlink()
        self.start_time = time.time()
        self._last_write = 0.0
        self._jira_cache: Optional["JiraCache"] = None
        self._device_id = config.getoption("--device-id") if config else "Unknown"
        self._device_ip = config.getoption("--device-ip") if config else "Unknown"
        self._ota_version = config.getoption("--ota-version") if config else "N/A"
        self._write_report()  # initial empty report so the file exists immediately

    # ── Hooks ──────────────────────────────────────────────────────────

    @pytest.hookimpl(trylast=True)
    def pytest_collection_modifyitems(self, items: List[pytest.Item]) -> None:
        """Pre-fetch JIRA linked issues for all collected tests, once."""
        if not _JIRA_AVAILABLE:
            return
        test_ids = [item.nodeid.split("::")[-1] for item in items]
        try:
            self._jira_cache = JiraCache()
            self._jira_cache.prefetch(test_ids)
        except Exception:
            self._jira_cache = None

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item: pytest.Item, call):
        """Attach captured command_log (from the `device` fixture, if used) and
        the assertion message to the report object for this phase."""
        outcome = yield
        report = outcome.get_result()
        if call.when != "call":
            return

        device = item.funcargs.get("device")
        report._command_log = list(getattr(device, "command_log", []) or [])
        report._assertion_msg = str(call.excinfo.value) if call.excinfo is not None else ""
        report._doc = (item.function.__doc__ or "").strip() if hasattr(item, "function") else ""

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        if report.when == "call" or (report.when in ("setup", "teardown") and report.failed):
            pass
        else:
            return

        result = self._build_result(report)
        self._append_result(result)

        now = time.time()
        if now - self._last_write >= 1.0:
            self._last_write = now
            self._write_report()

    def pytest_sessionfinish(self, session: pytest.Session) -> None:
        self._write_report(final=True)

    # ── Result building ──────────────────────────────────────────────

    def _build_result(self, report: pytest.TestReport) -> Dict[str, Any]:
        test_id = report.nodeid.split("::")[-1]

        if report.passed:
            verdict = "PASS"
        elif report.failed:
            verdict = "FAIL"
        elif report.skipped:
            verdict = "SKIP"
        else:
            verdict = "ERROR"

        stdout_content = ""
        for section_name, section_content in report.sections:
            if "stdout" in section_name.lower() and "call" in section_name.lower():
                stdout_content = section_content.strip()
                break

        return {
            "test_id": test_id,
            "nodeid": report.nodeid,
            "doc": getattr(report, "_doc", ""),
            "verdict": verdict,
            "duration_s": report.duration,
            "stdout": stdout_content,
            "assertion_msg": getattr(report, "_assertion_msg", ""),
            "command_log": getattr(report, "_command_log", []),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "functionality_group": get_functionality_group_from_nodeid(report.nodeid, test_id),
        }

    def _append_result(self, result: Dict[str, Any]) -> None:
        with open(RESULTS_FILE, "a") as f:
            f.write(json.dumps(result) + "\n")

    def _load_results(self) -> List[Dict[str, Any]]:
        if not RESULTS_FILE.exists():
            return []
        results = []
        for line in RESULTS_FILE.read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return results

    # ── HTML rendering — shared helpers ───────────────────────────────

    @staticmethod
    def _esc(text: str) -> str:
        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )

    def _issue_badge(self, test_id: str) -> str:
        if not self._jira_cache or not self._jira_cache.available:
            return '<span class="badge-unknown">UNCLASSIFIED</span>'
        info = self._jira_cache.classify(test_id)
        classification = info.get("classification", "NO_JIRA")
        if classification == "KNOWN_ISSUE":
            badge = '<span class="badge-known">KNOWN</span>'
        elif classification == "UNKNOWN_ISSUE":
            badge = '<span class="badge-unknown">UNKNOWN</span>'
        else:
            return '<span class="badge-unclassified">&mdash;</span>'
        active_bugs = info.get("active_bugs", [])
        if active_bugs:
            links = []
            for key, status, link in active_bugs:
                key_e, link_e, status_e = self._esc(key), self._esc(link), self._esc(status)
                if link:
                    links.append(f'<a class="jira-link" href="{link_e}" target="_blank" title="{status_e}">{key_e}</a>')
                else:
                    links.append(f'<span style="font-size:10px">{key_e}</span>')
            badge += "<br>" + " ".join(links)
        return badge

    def _render_command_log(self, command_log: List[Dict[str, Any]]) -> str:
        if not command_log:
            return '<div class="no-cmds">No commands recorded for this test.</div>'
        rows = []
        for entry in command_log:
            cmd = self._esc(entry.get("cmd", ""))
            output = entry.get("output")
            ts = self._esc(entry.get("timestamp", ""))
            output_html = ""
            if output is not None:
                output_str = output if isinstance(output, str) else json.dumps(output, indent=2, default=str)
                output_html = f"<pre>{self._esc(output_str)}</pre>"
            rows.append(
                f'<div class="cmd-entry">'
                f'<div class="cmd-line"><code>{cmd}</code><span class="cmd-ts">{ts}</span></div>'
                f'{output_html}'
                f'</div>'
            )
        return "\n".join(rows)

    def _render_row(self, result: Dict[str, Any], index: int, uid_prefix: str = "row") -> tuple:
        uid = f"{uid_prefix}-{index}"
        verdict = result["verdict"]
        badge_cls = f"badge-{verdict.lower()}"
        row_cls = "row-fail" if verdict in ("FAIL", "ERROR") else ""

        issue_cell = (
            f'<td class="col-issue">{self._issue_badge(result["test_id"])}</td>'
            if verdict == "FAIL"
            else '<td class="col-issue"><span class="dim">&mdash;</span></td>'
        )

        summary = self._esc(result.get("assertion_msg") or "")[:200]

        row_html = (
            f'<tr class="tr {row_cls}" data-verdict="{verdict}" '
            f'data-search="{self._esc(result["test_id"] + " " + result.get("doc", "")).lower()}">'
            f'<td class="col-idx">{index}</td>'
            f'<td class="col-id" title="{self._esc(result["nodeid"])}">{self._esc(result["test_id"])}</td>'
            f'<td class="col-doc">{self._esc(result.get("doc", ""))}</td>'
            f'<td class="col-verdict"><span class="{badge_cls}">{verdict}</span></td>'
            f'{issue_cell}'
            f'<td class="col-duration">{result["duration_s"]:.2f}s</td>'
            f'<td class="col-summary" title="{self._esc(result.get("assertion_msg", ""))}">{summary}</td>'
            f'<td class="col-time">{self._esc(result["timestamp"])}</td>'
            f'<td class="col-details"><button type="button" class="expand-btn" onclick="toggleDetail(\'{uid}\')">+</button></td>'
            f'</tr>\n'
        )

        cmd_html = self._render_command_log(result.get("command_log", []))
        stdout_html = ""
        if result.get("stdout"):
            stdout_html = (
                f'<div class="detail-block"><div class="detail-label">Captured stdout</div>'
                f'<pre>{self._esc(result["stdout"])}</pre></div>'
            )
        assertion_html = ""
        if result.get("assertion_msg"):
            assertion_html = (
                f'<div class="detail-block"><div class="detail-label">Assertion</div>'
                f'<pre>{self._esc(result["assertion_msg"])}</pre></div>'
            )

        detail_html = (
            f'<tr class="detail-row" id="detail-{uid}" hidden>'
            f'<td colspan="9">'
            f'<div class="detail-panel">'
            f'{assertion_html}'
            f'{stdout_html}'
            f'<div class="detail-block"><div class="detail-label">Command log ({len(result.get("command_log", []))})</div>'
            f'{cmd_html}</div>'
            f'</div>'
            f'</td></tr>\n'
        )
        return row_html, detail_html

    def _render_table(self, results: List[Dict[str, Any]], uid_prefix: str, table_id: str) -> str:
        rows_html = ""
        details_html = ""
        for i, result in enumerate(results, 1):
            row, detail = self._render_row(result, i, uid_prefix=uid_prefix)
            rows_html += row
            details_html += detail
        return (
            f'<table id="{table_id}">'
            f'<thead><tr>'
            f'<th>#</th><th>Test ID</th><th>Description</th><th>Result</th><th>Issue</th>'
            f'<th>Duration</th><th>Summary</th><th>Time</th><th>Details</th>'
            f'</tr></thead>'
            f'<tbody>{rows_html}{details_html}</tbody>'
            f'</table>'
        )

    # ── HTML rendering — tab bodies ────────────────────────────────────

    def _render_overview_tab(self, results: List[Dict[str, Any]]) -> str:
        total = len(results)
        passed = sum(1 for r in results if r["verdict"] == "PASS")
        failed = sum(1 for r in results if r["verdict"] == "FAIL")
        skipped = sum(1 for r in results if r["verdict"] == "SKIP")
        errors = sum(1 for r in results if r["verdict"] == "ERROR")
        pass_rate = f"{(passed / total * 100):.1f}" if total else "0.0"

        # Pass rate by functionality group
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for r in results:
            groups.setdefault(r.get("functionality_group", "Other"), []).append(r)

        func_rows = ""
        for name in sorted(groups.keys()):
            g = groups[name]
            g_total = len(g)
            g_pass = sum(1 for r in g if r["verdict"] == "PASS")
            g_pct = (g_pass / g_total * 100) if g_total else 0
            bar_color = "#16a34a" if g_pct == 100 else ("#dc2626" if g_pct < 50 else "#ea580c")
            func_rows += (
                f'<div class="func-rate-row">'
                f'<span class="func-rate-name">{self._esc(name)}</span>'
                f'<div class="func-rate-bar"><div class="func-rate-fill" style="width:{g_pct:.0f}%;background:{bar_color}"></div></div>'
                f'<span class="func-rate-pct">{g_pct:.0f}% <span class="dim">({g_pass}/{g_total})</span></span>'
                f'</div>'
            )
        if not func_rows:
            func_rows = '<div class="no-cmds">No results yet.</div>'

        return f"""
<div class="kpis">
  <div class="kpi k-pass"><div class="kpi-label">Pass rate</div><div class="kpi-value">{pass_rate}%</div><div class="kpi-sub">{passed} of {total} passed</div></div>
  <div class="kpi k-fail"><div class="kpi-label">Failed</div><div class="kpi-value">{failed}</div><div class="kpi-sub">see Failures tab</div></div>
  <div class="kpi k-skip"><div class="kpi-label">Skipped</div><div class="kpi-value">{skipped}</div><div class="kpi-sub">not executed</div></div>
  <div class="kpi k-error"><div class="kpi-label">Error</div><div class="kpi-value">{errors}</div><div class="kpi-sub">setup/teardown failure</div></div>
</div>
<div class="card">
  <div class="card-h">Pass rate by functionality</div>
  <div class="card-b"><div class="func-rate-list">{func_rows}</div></div>
</div>
"""

    def _render_failures_tab(self, results: List[Dict[str, Any]]) -> str:
        failed = [r for r in results if r["verdict"] in ("FAIL", "ERROR")]
        if not failed:
            return '<div class="card"><div class="card-b"><div class="no-cmds">No failures — everything passed.</div></div></div>'

        groups: Dict[str, List[Dict[str, Any]]] = {}
        for r in failed:
            groups.setdefault(r.get("functionality_group", "Other"), []).append(r)

        sections = ""
        for name in sorted(groups.keys()):
            g_results = groups[name]
            rows = ""
            for r in g_results:
                reason = self._esc(r.get("assertion_msg") or "")[:400]
                issue_html = self._issue_badge(r["test_id"])
                rows += (
                    f'<tr class="row-fail">'
                    f'<td>{self._esc(r["test_id"])}</td>'
                    f'<td><span class="badge-{r["verdict"].lower()}">{r["verdict"]}</span></td>'
                    f'<td>{issue_html}</td>'
                    f'<td style="font-size:11.5px">{reason}</td>'
                    f'<td>{r["duration_s"]:.2f}s</td>'
                    f'</tr>'
                )
            sections += (
                f'<div class="card" style="margin-bottom:14px">'
                f'<div class="card-h">{self._esc(name)} <span class="muted">({len(g_results)} failed)</span></div>'
                f'<div class="card-b" style="padding:0"><div class="scroll-table"><table>'
                f'<tr><th>Test</th><th>Result</th><th>Issue</th><th>Reason</th><th>Duration</th></tr>{rows}'
                f'</table></div></div>'
                f'</div>'
            )
        return sections

    def _render_coverage_tab(self, results: List[Dict[str, Any]]) -> str:
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for r in results:
            groups.setdefault(r.get("functionality_group", "Other"), []).append(r)

        rows = ""
        for name in sorted(groups.keys()):
            g = groups[name]
            g_total = len(g)
            g_pass = sum(1 for r in g if r["verdict"] == "PASS")
            g_fail = sum(1 for r in g if r["verdict"] in ("FAIL", "ERROR"))
            g_skip = sum(1 for r in g if r["verdict"] == "SKIP")
            g_pct = f"{(g_pass / g_total * 100):.0f}%" if g_total else "0%"
            rows += (
                f'<tr>'
                f'<td style="font-weight:600">{self._esc(name)}</td>'
                f'<td style="text-align:center">{g_total}</td>'
                f'<td style="text-align:center"><span class="badge-pass">{g_pass}</span></td>'
                f'<td style="text-align:center"><span class="badge-fail">{g_fail}</span></td>'
                f'<td style="text-align:center"><span class="badge-skip">{g_skip}</span></td>'
                f'<td style="text-align:center">{g_pct}</td>'
                f'</tr>'
            )
        if not rows:
            rows = '<tr><td colspan="6" class="no-cmds">No results yet.</td></tr>'

        return f"""
<div class="card">
  <div class="card-h">Coverage by functionality group</div>
  <div class="card-b" style="padding:0">
    <div class="scroll-table">
      <table>
        <tr><th>Functionality</th><th>Total</th><th>Pass</th><th>Fail</th><th>Skip</th><th>Pass %</th></tr>
        {rows}
      </table>
    </div>
  </div>
</div>
"""

    def _render_device_tab(self, results: List[Dict[str, Any]]) -> str:
        total = len(results)
        passed = sum(1 for r in results if r["verdict"] == "PASS")
        failed = sum(1 for r in results if r["verdict"] in ("FAIL", "ERROR"))
        skipped = sum(1 for r in results if r["verdict"] == "SKIP")

        device_table = f"""
<div class="card" style="margin-bottom:14px">
  <div class="card-h">Device under test</div>
  <div class="card-b" style="padding:0"><div class="scroll-table"><table>
    <tr><th>Device ID</th><th>Device IP</th><th>OTA Version</th><th>Total</th><th>Pass</th><th>Fail</th><th>Skip</th></tr>
    <tr>
      <td>{self._esc(self._device_id)}</td>
      <td>{self._esc(self._device_ip)}</td>
      <td>{self._esc(self._ota_version)}</td>
      <td>{total}</td>
      <td><span class="badge-pass">{passed}</span></td>
      <td><span class="badge-fail">{failed}</span></td>
      <td><span class="badge-skip">{skipped}</span></td>
    </tr>
  </table></div></div>
</div>
"""
        table_html = self._render_table(results, uid_prefix="dev-row", table_id="device-results-table")
        return device_table + f'<div class="card"><div class="card-h">All results for this device</div><div class="card-b" style="padding:0">{table_html}</div></div>'

    def _render_all_tests_tab(self, results: List[Dict[str, Any]]) -> str:
        toolbar = """
<div class="toolbar">
  <input type="text" id="search" placeholder="Filter by test id or description..." onkeyup="filterRows()">
  <select id="verdict-filter" onchange="filterRows()">
    <option value="">All results</option>
    <option value="PASS">Passed</option>
    <option value="FAIL">Failed</option>
    <option value="SKIP">Skipped</option>
    <option value="ERROR">Error</option>
  </select>
</div>
"""
        table_html = self._render_table(results, uid_prefix="row", table_id="results-table")
        return toolbar + table_html

    def _write_report(self, final: bool = False) -> None:
        results = self._load_results()
        total = len(results)
        passed = sum(1 for r in results if r["verdict"] == "PASS")
        failed = sum(1 for r in results if r["verdict"] == "FAIL")
        skipped = sum(1 for r in results if r["verdict"] == "SKIP")
        errors = sum(1 for r in results if r["verdict"] == "ERROR")
        pass_rate = f"{(passed / total * 100):.1f}" if total else "0.0"
        elapsed = time.time() - self.start_time
        elapsed_fmt = f"{int(elapsed // 60)}m {int(elapsed % 60)}s"
        status_label = "COMPLETE" if final else "IN PROGRESS"
        generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        overview_html = self._render_overview_tab(results)
        failures_html = self._render_failures_tab(results)
        coverage_html = self._render_coverage_tab(results)
        all_tests_html = self._render_all_tests_tab(results)
        device_html = self._render_device_tab(results)

        refresh_meta = "" if final else '<meta http-equiv="refresh" content="10">'

        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
{refresh_meta}
<title>FleetEdge Automation Report</title>
<style>
{_CSS}
</style>
</head>
<body>
<div class="header">
  <h1>FleetEdge Automation Report</h1>
  <div class="status-badge status-{status_label.lower().replace(' ', '-')}">{status_label}</div>
</div>
<div class="meta-bar">
  <span>Generated: {generated}</span>
  <span>Elapsed: {elapsed_fmt}</span>
  <span>Device: {self._esc(self._device_id)}</span>
</div>
<div class="summary-cards">
  <div class="card"><div class="card-num">{total}</div><div class="card-label">Total</div></div>
  <div class="card pass"><div class="card-num">{passed}</div><div class="card-label">Passed</div></div>
  <div class="card fail"><div class="card-num">{failed}</div><div class="card-label">Failed</div></div>
  <div class="card skip"><div class="card-num">{skipped}</div><div class="card-label">Skipped</div></div>
  <div class="card error"><div class="card-num">{errors}</div><div class="card-label">Error</div></div>
  <div class="card"><div class="card-num">{pass_rate}%</div><div class="card-label">Pass rate</div></div>
</div>
<div class="tabs">
  <button class="tab-btn active" data-tab="overview" onclick="switchTab('overview')">Overview</button>
  <button class="tab-btn" data-tab="failures" onclick="switchTab('failures')">Failures<span class="cnt">{failed + errors}</span></button>
  <button class="tab-btn" data-tab="coverage" onclick="switchTab('coverage')">Coverage</button>
  <button class="tab-btn" data-tab="alltests" onclick="switchTab('alltests')">All Tests<span class="cnt">{total}</span></button>
  <button class="tab-btn" data-tab="device" onclick="switchTab('device')">Device Tables</button>
</div>
<div class="tab-wrap">
  <div id="tab-overview" class="tab-content active">{overview_html}</div>
  <div id="tab-failures" class="tab-content">{failures_html}</div>
  <div id="tab-coverage" class="tab-content">{coverage_html}</div>
  <div id="tab-alltests" class="tab-content">{all_tests_html}</div>
  <div id="tab-device" class="tab-content">{device_html}</div>
</div>
<script>
{_JS}
</script>
</body>
</html>
"""
        REPORT_PATH.write_text(html, encoding="utf-8")


_CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body { font-family: -apple-system, Segoe UI, Helvetica, Arial, sans-serif; margin: 0; background: #f4f5f7; color: #1a1a1a; }
.header { display: flex; align-items: center; gap: 16px; padding: 20px 24px; background: #1e293b; color: white; }
.header h1 { margin: 0; font-size: 20px; }
.status-badge { padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 700; }
.status-in-progress { background: #f59e0b; color: #1a1a1a; }
.status-complete { background: #16a34a; }
.meta-bar { display: flex; gap: 24px; padding: 8px 24px; font-size: 12px; color: #666; background: #e2e8f0; }
.summary-cards { display: flex; gap: 12px; padding: 16px 24px; flex-wrap: wrap; }
.card { background: white; border-radius: 8px; box-shadow: 0 1px 2px rgba(0,0,0,.08); }
.summary-cards .card { padding: 12px 20px; text-align: center; min-width: 90px; }
.card-num { font-size: 24px; font-weight: 700; }
.card-label { font-size: 11px; color: #666; text-transform: uppercase; }
.card.pass .card-num { color: #16a34a; }
.card.fail .card-num { color: #dc2626; }
.card.skip .card-num { color: #ea580c; }
.card.error .card-num { color: #2563eb; }
.card-h { padding: 10px 16px; font-weight: 700; font-size: 13px; border-bottom: 1px solid #eef0f2; }
.card-b { padding: 14px 16px; }
.muted { font-weight: 500; font-size: 11px; color: #94a3b8; }

.tabs { display: flex; gap: 2px; padding: 0 24px; background: #1e293b; }
.tab-btn { padding: 11px 20px; font-size: 13px; font-weight: 600; color: rgba(255,255,255,.65); cursor: pointer; border: none; background: transparent; border-bottom: 3px solid transparent; }
.tab-btn:hover { color: #fff; background: rgba(255,255,255,.08); }
.tab-btn.active { color: #fff; border-bottom-color: #2563eb; }
.tab-btn .cnt { display: inline-block; margin-left: 6px; font-size: 10.5px; padding: 1px 7px; border-radius: 10px; background: rgba(255,255,255,.2); }
.tab-btn.active .cnt { background: #2563eb; }
.tab-wrap { padding: 16px 24px 24px; }
.tab-content { display: none; }
.tab-content.active { display: block; }

.kpis { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 16px; }
.kpi { background: white; border-radius: 8px; padding: 14px 18px; box-shadow: 0 1px 2px rgba(0,0,0,.08); min-width: 140px; flex: 1; }
.kpi-label { font-size: 11px; color: #64748b; text-transform: uppercase; font-weight: 700; }
.kpi-value { font-size: 26px; font-weight: 700; margin: 4px 0; }
.kpi-sub { font-size: 11px; color: #94a3b8; }
.k-pass .kpi-value { color: #16a34a; }
.k-fail .kpi-value { color: #dc2626; }
.k-skip .kpi-value { color: #ea580c; }
.k-error .kpi-value { color: #2563eb; }

.func-rate-list { display: flex; flex-direction: column; gap: 10px; }
.func-rate-row { display: flex; align-items: center; gap: 10px; }
.func-rate-name { width: 220px; font-size: 12.5px; font-weight: 600; flex-shrink: 0; }
.func-rate-bar { flex: 1; height: 10px; background: #eef2f7; border-radius: 6px; overflow: hidden; }
.func-rate-fill { height: 100%; border-radius: 6px; }
.func-rate-pct { width: 110px; font-size: 11.5px; text-align: right; flex-shrink: 0; }

.toolbar { display: flex; gap: 8px; padding: 0 0 12px; }
.toolbar input, .toolbar select { padding: 6px 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 13px; }
.toolbar input { flex: 1; max-width: 320px; }
table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; }
th, td { padding: 8px 10px; text-align: left; font-size: 12.5px; border-bottom: 1px solid #eef0f2; }
th { background: #f1f5f9; font-size: 11px; text-transform: uppercase; color: #475569; }
.scroll-table { max-height: 520px; overflow: auto; }
.tr.row-fail, tr.row-fail { background: #fef2f2; }
.col-summary { max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.col-doc { max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #475569; }
.badge-pass, .badge-fail, .badge-skip, .badge-error, .badge-known, .badge-unknown, .badge-unclassified {
  display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 700; color: white;
}
.badge-pass { background: #16a34a; }
.badge-fail { background: #dc2626; }
.badge-skip { background: #ea580c; }
.badge-error { background: #2563eb; }
.badge-known { background: #d97706; }
.badge-unknown { background: #db2777; }
.badge-unclassified { background: #94a3b8; }
.dim { color: #94a3b8; font-size: 10px; }
.jira-link { font-size: 10px; color: #2563eb; }
.expand-btn { border: 1px solid #cbd5e1; background: white; border-radius: 4px; width: 24px; height: 24px; cursor: pointer; font-size: 14px; line-height: 1; }
.detail-row td { background: #f8fafc; padding: 0; }
.detail-panel { padding: 12px 20px; }
.detail-block { margin-bottom: 10px; }
.detail-label { font-size: 11px; font-weight: 700; text-transform: uppercase; color: #64748b; margin-bottom: 4px; }
.detail-block pre { background: #0f172a; color: #e2e8f0; padding: 8px 10px; border-radius: 6px; overflow: auto; max-height: 300px; font-size: 11.5px; margin: 0; white-space: pre-wrap; word-break: break-word; }
.cmd-entry { margin-bottom: 6px; }
.cmd-entry pre { max-height: 160px; }
.cmd-line { display: flex; justify-content: space-between; gap: 12px; }
.cmd-line code { background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-size: 11.5px; }
.cmd-ts { font-size: 10px; color: #94a3b8; }
.no-cmds { color: #94a3b8; font-size: 12px; font-style: italic; }
"""

_JS = """
var ACTIVE_TAB_KEY = 'fe_live_report_active_tab';
function switchTab(name) {
  document.querySelectorAll('.tab-content').forEach(function (el) { el.classList.remove('active'); });
  document.querySelectorAll('.tab-btn').forEach(function (el) { el.classList.remove('active'); });
  var tab = document.getElementById('tab-' + name); if (tab) tab.classList.add('active');
  var btn = document.querySelector('.tab-btn[data-tab="' + name + '"]'); if (btn) btn.classList.add('active');
  try { localStorage.setItem(ACTIVE_TAB_KEY, name); } catch (e) {}
}
(function restoreActiveTab() {
  var saved = null;
  try { saved = localStorage.getItem(ACTIVE_TAB_KEY); } catch (e) {}
  if (saved && document.getElementById('tab-' + saved)) { switchTab(saved); }
})();
function toggleDetail(uid) {
  var row = document.getElementById('detail-' + uid);
  if (row) { row.hidden = !row.hidden; }
}
function filterRows() {
  var q = document.getElementById('search').value.toLowerCase();
  var verdict = document.getElementById('verdict-filter').value;
  var rows = document.querySelectorAll('#results-table tbody tr.tr');
  rows.forEach(function (row) {
    var matchesSearch = !q || row.getAttribute('data-search').indexOf(q) !== -1;
    var matchesVerdict = !verdict || row.getAttribute('data-verdict') === verdict;
    row.style.display = (matchesSearch && matchesVerdict) ? '' : 'none';
  });
}
"""
