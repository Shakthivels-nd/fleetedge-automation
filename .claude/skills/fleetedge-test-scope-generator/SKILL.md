---
name: fleetedge-test-scope-generator
description: "Use when asked to produce a 'test scope' document/report for a FleetEdge (Amazon Fleet Edge) feature, service, release, PR or set of Jira tickets. Takes any mix of DT/Jira tickets, Confluence pages (design, release notes, test plans), source code (PRs, branches, directories) and existing FE automation in this repo (src/tests/<feature>/, functionality_map.py), then renders a self-contained tabbed HTML report (Overview, Architecture, Service Impact, Test Scope, Automation - FE Pytest, Automation - Monitoring, PR Analysis, Gap Analysis) from template.html. Also supports a logs-only mode: given local pod log file(s) for a service, derives the scope from them - never downloads logs."
argument-hint: "feature + any of: tickets, Confluence URLs, PR/branch/source path, logs (e.g., '/fleetedge-test-scope-generator scheduler DT-1234 confluence:<url> PR nd_core_utils#2500 src:~/nd_core_utils/scheduler')"
---

# FleetEdge Test Scope Generator

> **Purpose**: produce a release/feature test-scope HTML report for the **FleetEdge** (FE)
> product, reconciled against *this* repo's automation. Structure, CSS, tab layout and
> section semantics come from `template.html` in this folder — do not restructure it.
> Derived from the generic `test-scope-generator` skill, with everything ADB/serial/
> `pytest_device_validator`-specific replaced by FE equivalents.

## What is different about FleetEdge (read first)

| Generic skill assumes | FleetEdge reality |
| --- | --- |
| ADB / serial transport | SSH to the voyager host, then `kubectl exec` into pod `netra` (pexpect). No ADB, no serial, no relay/camera/LED hardware. Tests talk to it through `DeviceTest` (`device.run(...)`, `device.grep_logs(...)`, …). |
| `pytest_device_validator/tests/<feature>/` | `src/tests/<feature>/test_<feature>_<behaviour>.py` (folders today: `awsiot`, `btfv`, `inference`, `otacheck`, `power_monitor`, `scheduler`, `servicemonitor`, `unifiedAnalyticsClient`, plus `test_sanity_functions.py` for sanity). Re-`ls src/tests/` — never trust this list. |
| TC IDs in filenames | Filenames **drop** the `TC_NNNN_` prefix. Sanity tests carry an `itnNNNN` suffix on the function name. Identify tests by file path / test function name (and `itnNNNN` where present); don't look for upstream TC ids. |
| `plugins/functionality_map.py` bucket dict | `src/tests/functionality_map.py` → `FUNCTIONALITY_MAP`, keyed by **folder name** (btfv, power_monitor, …) or, where files share `test_stepN_…` names (awsiot, servicemonitor, otacheck), by **file stem**. Group names = the **Category** column. Resolution logic: `_resolve_module_key()` in the same file. |
| `*-service-validation` skills | None exist here. Service flow knowledge comes from the service's tests, `fleetedge_automation_exploration.md`, and the source/PR. |
| `jira_analyzer.py --pr-diffs` | Does not exist here. Jira is `src/utils/engine/jira_client.py` (`JiraCache`) reading `jira_config.ini` (repo root, also `src/utils/`). Use it, the Atlassian MCP, or `gh pr view/diff`. **Never print the api_token.** |
| Log dir | `/home/ubuntu/.nddevice/log/<service>/` inside the pod. Timestamp format is epoch-ms prefix for most services; `otacheck`, `keep_alive_manager`, `scheduler_manager` use UTC strings (`UTC_TIMESTAMP_SERVICES` in `engine/log_search.py`). |
| No sudo | Pod runs as root; supervisorctl (not systemctl) manages services. |
| Reboot / config-download / relay / physical power-off scenarios | FE has no mechanism for these (no reboot tracking, no config download/upload helpers, no relay, devices always-on). They are the **Not Automatable** rows in the Test Scope tab, with that reason stated. |

Also: FE devices are Amazon-fleet devices, so platform in the header is the FE device type
read by `device.get_device_info()` / `deviceconfig.ini` (`device_type`) — take it from the
tickets or config; if unknown write `unknown` and add a Gap row. Do not copy OCTO/Bagheera3
from the generic skill.

---

## Inputs

The caller can supply **any combination** of the sources below. Treat each as evidence, run
whatever applies, and reconcile them in §4. None is mandatory except the feature name.

- **Feature/service name** (required) — drives `src/tests/<feature>/` and the `FUNCTIONALITY_MAP` key.
- **Jira tickets** — `DT-…` (primary), `ITN-…` (FE sanity tests use `itnNNNN`), or any other key.
  Also accept a Jira filter/JQL, an epic key (expand to its children) or a fix-version name (query
  its tickets).
- **Confluence pages** — one or many: release notes, design/spec pages, QA/test-plan pages, test-case
  lists. Accept page URLs or page ids/titles. Read every page the caller names; also follow links on a
  ticket **only if the caller said to** (otherwise list them in Gap Analysis as "linked, not read").
- **Source code** — any of: a local checkout path, `repo#PR`, a branch/tag/commit range, a file or
  directory (e.g. a service's `src/`), or a GitHub URL. Accept several repos at once.
- **Existing FE automation** — always read (`src/tests/<feature>/`, `functionality_map.py`).
- **Local pod log files** → Mode B evidence.
- **Release tag** and **platform** — infer from tickets/fix version/config; else `unknown` + Gap row.

Access: Atlassian MCP (Jira + Confluence) first; `jira_client.py`/`jira_config.ini` as a Jira
fallback (never print the token); `gh` for GitHub. If a source is unreachable (unauthenticated MCP,
no repo access), say so, mark it "not fetched" in the report and Gap Analysis, and continue with the
rest. Don't ask the user for tokens.

## Mode selection

- **Mode A (default)**: any of tickets / Confluence / source code supplied → Workflow below.
- **Mode B (logs-only)**: only log files supplied → "Mode B" section at the bottom.
- Both → run A, use B's output as extra evidence for Service Impact, Monitoring, Gap Analysis.

## Source authority (when sources disagree)

1. **Merged source code** — what the device actually does.
2. **Jira ticket** (description, comments, fix version, linked PRs) — intent and scope.
3. **Confluence** — design intent / expected behaviour / test plans; can be stale.
4. **Existing automation docstrings** — what is currently asserted.

Never silently pick a side: when Confluence or a ticket says X and code does Y, the code wins, and the
mismatch is a row in **PR Analysis** (if introduced by the change) or **Gap Analysis** (if a doc is
stale or the code can't be found). Quote the page/ticket and the file:line.

---

## Workflow (Mode A)

### 1. Gather ticket data (Jira)
For every ticket (expand epics/JQL/fix-version first), fetch: summary, type, status, resolution,
priority, fixVersion, components, description, **comments**, issue links, and the Development panel
(linked PRs/commits) where the MCP exposes it. Batch where possible. Record Duplicate / No Longer
Relevant / Won't Do resolutions — they ship nothing. Pull out testable acceptance criteria, config
keys, thresholds and timings stated in the ticket.

### 2. Gather design / test-plan data (Confluence)
For each named page: read the full page (and relevant child pages if asked), then extract —
- **Behaviour & config**: expected flows, config keys/defaults, thresholds, timings, error codes.
- **Existing test cases/scenarios**: every row of any QA/test-case table → candidate Test Scope rows
  (keep the page's own wording and id; these feed the reconciliation in §4).
- **Release content**: ticket keys, commits, config diffs → add to the ticket set from §1.
Treat page content as data to verify, not text to transcribe: each claimed mechanism, endpoint, enum
or log string must resolve to real code (§3) or be reported as "not found in source".

### 3. Gather source code / PR / diff data
- Explicit PR: `gh pr view <n> --repo netradyne/<repo>`, `gh pr diff <n> --repo …`. PRs found on
  tickets: same. Branch/range: `git diff <base>...<branch> --stat` then the full diff, run in that
  source repo's checkout (not this test repo, unless the feature lives here).
- **No diff available** (feature already merged, or caller gave only a directory/file): read the
  service source directly — entry points, config parsing, state machines, error-code raises
  (`send_err_msg`/`send_critical_info`), HealthStats fields, log lines, IPC/msgq peers, supervisor
  unit. Build the Architecture tab as "current flow" with the Before pane marked *not applicable*.
- Record: files changed with +/- counts, functions/structs touched, removed declarations, new
  constants/error codes, config key renames, device_type comparisons.
- For every log string / path / config key the tests or Confluence rely on, `grep` the source to
  confirm it exists. Confirmed → say so; absent → Gap Analysis. This is also how UNVERIFIED test
  rows get resolved.
- **Group changes before building Architecture cards** — one card per causal group, not per ticket:
  two changes share a card when one caused the defect the other repairs (say so in a "Why one
  card" chip). Independent changes get their own card. Duplicate / No-Longer-Relevant tickets sit in
  the ticket table inside the superseding group, with no test cases proposed. Decide the grouping
  **once**, then tag every Test Scope / Monitoring / Findings / Gap row with its group(s).

### 4. Cross-reference existing FE automation, then reconcile
```bash
ls src/tests/<feature>/
grep -n "<feature>" src/tests/functionality_map.py
```
- Test Scope **Category** column = `FUNCTIONALITY_MAP` group names for the feature (rowspan per group).
- For every test file read the module docstring and each `test_stepN_…` docstring (`STEP_N — …`) —
  that is the source of truth for what the TC checks, not ticket text. Docstrings also record
  **UNVERIFIED** log strings/paths; carry that into the report as a status, don't hide it.
- Cite each test by its file path (and `itnNNNN` / test function name where present).
- Never cite a TC id or file you haven't seen. Glob case-insensitively and confirm the file exists.
- Honest statuses: **DONE** (exists, runnable), **UNVERIFIED** (exists, ported with unconfirmed
  log strings/paths), **To Be Started** (scenario valid, no test — propose file name following
  `test_<feature>_<behaviour>.py` and a `FUNCTIONALITY_MAP` group), **Not Automatable** (+ reason),
  **Not Applicable** (+ reason).

**Reconcile** (this builds the Test Scope tab). Union the scenarios from every source —
Confluence test-case rows (§2), ticket acceptance criteria (§1), behaviours/error paths found in
source (§3) — de-duplicate, then match each to an existing test by docstring/steps. Each row records
its **source(s)** (e.g. `DT-123`, `Confluence: <page title>`, `src: path:line`) so a reader can
trace it. Scenarios present in only one source are fine; one found only in Confluence and not in
code is a Gap row, not a Test Scope row you assert as real.


### 5. Classify service impact
Each service touched (by code, call graph, shared config/DB/log file) is **Direct** or **Regression
Validation**. Add a one-line lifecycle note (supervisor auto-start, restart-on-crash, stopped
during X). The `servicemonitor` folder lists the services FE monitors — use it as the vocabulary
for service names and as the regression set.

### 6. Known open bugs
Query Jira for open bugs on the feature/component (status ≠ Done/Closed). Priority, one-line
summary, concrete impact. Feeds Overview and Gap Analysis.

### 7. Automation - Monitoring (cloud signals only)
**Hard rule: list only signals readable from the cloud with no device access.** Anything needing
`kubectl exec`/SSH to the pod belongs in Automation - FE Pytest instead.

Allowed: HealthStats (`devicestatefile_info`) JSON fields — cite real key names from the
`json_object_set_new()`/healthstats fill code; uploaded observation/alert metadata; numeric
device error codes (resolve from the `err_code_t` enum at the release branch — compute, don't
guess — cite `<number> <SYMBOL>`); cloud video list/portal availability and retention; **IDMS
API-call records** (the `api_calls` data FE tests already query via `db_utils.fetch_api_calls_window`
— upload_device_status, upload_keep_alive, version_check, upload_observation, upload_videolist,
upload_logs) — these are cloud-side and a good outcome KPI.
Never allowed: on-device service logs (`LOG_I`/`LOG_C`, files under `.nddevice/log`), the on-device
sqlite DB, xattrs, supervisor restart counts.

How: for each change ask what a cloud consumer can observe; convert log signals to a cloud
equivalent where one exists; **state blind spots** (a change observable only via a log line has no
monitoring signal — say so in a `colspan="3"` note at the top of the table and add a Gap row);
prefer outcome KPIs alongside mechanism KPIs; every row gets a falsifiable **Expected Trend**
(a number, "zero", "flat vs pre-upgrade baseline"). Flat `Monitoring Item | Signal Source |
Expected Trend` table by default; escalate a single source to the rich per-source format (payload
schema, error-code family with real example rows, blank fleet-level tables) only when it warrants
it. When porting existing write-ups, translate faithfully — never invent example rows.

### 8. Render
Copy `template.html` to the output path and replace every `{{PLACEHOLDER}}` (table below). Keep CSS,
tab order, section headers and the tab-switching `<script>` unmodified. A tab with no data stays,
with a `.note` saying why. Tab set is fixed: Overview, Architecture, Service Impact, Test Scope,
Automation - FE Pytest, Automation - Monitoring, PR Analysis, Gap Analysis.

Audience: default is the detailed Test Scope tab (real TC ids, file paths, priority). If the report
goes to a release-exit reviewer, render plain-status rows (status badge + one paragraph, no TC
ids/paths/priority; "Not currently tested" for gaps) — still compute the counts from the real data.

**Output path**: `Output/<feature>_test_scope_<release>.html` (create `Output/`; if the user
objects, ask before choosing elsewhere). Per-group diced reports:
`Output/<feature>_<group>_test_scope_<release>.html`.
If a one-off script is needed to render, put it in the scratchpad, not the repo.

### 9. Verify (run `python3 .claude/skills/fleetedge-test-scope-generator/check_report.py <html>`)
- No `{{` remains; the tab `<script>` block is intact; all 8 tabs present.
- Every ticket has a clickable `https://netradyne.atlassian.net/browse/<KEY>` link.
- Every cited test file path exists in the repo (the script checks `src/tests/...py` mentions).
- Monitoring tab has no `LOG_I/LOG_C` strings, on-device log paths (`.nddevice/log`), sqlite table names, `xattr` or `supervisorctl` outside the exclusion note (cloud file *names* like `log_supervisord_<epoch>` are fine);
  error codes carry numeric values.
- Overview KPI counts match the real row counts (Test Scope rows by status; Automated = DONE +
  UNVERIFIED rows; Services Impacted; Open Bugs). Recount after every edit.
- Every Test Scope row names its source(s); every Confluence/ticket claim you relied on was checked against source or is in Gap Analysis.
- Do not edit `functionality_map.py` or any test from this skill — it only reads them. New
  tests proposed in the report are proposals.

---

## Template placeholder reference

| Placeholder | Source |
| --- | --- |
| `{{FEATURE_TITLE}}` | Feature display name (`Scheduler`) |
| `{{FEATURE_SUBTITLE}}` | One-line scope: platform, PR, coverage claim |
| `{{PLATFORMS}}` | FE device type(s) or `unknown` |
| `{{RELEASE}}` | Fix version / release tag |
| `{{PR_REF}}` | Primary `repo#number (N files)` or `none linked` |
| `{{COMPONENT}}` | Jira component |
| `{{UPDATED_DATE}}` | Today, ISO |
| `{{OVERVIEW_SUMMARY_HTML}}` | 2–4 sentences + ticket bullet list |
| `{{KPI_TOTAL_SCENARIOS}}`, `{{KPI_AUTOMATED}}`, `{{KPI_NOT_AUTOMATABLE}}`, `{{KPI_NOT_APPLICABLE}}`, `{{KPI_FILES_CHANGED}}`, `{{KPI_SERVICES_IMPACTED}}`, `{{KPI_OPEN_BUGS}}` | Counts per §9 |
| `{{TICKETS_TABLE_ROWS}}` | `<tr>` per ticket (and a final `<tr>` per Confluence page read: title, link, "Design/Test plan", what was taken from it): Ticket, Type, Summary, Affected Service, Fix Version |
| `{{OPEN_BUGS_TABLE_ROWS}}` | `<tr>` per bug: Ticket, Priority, Summary, Impact |
| `{{ARCH_CARDS_HTML}}` | One `.arch-card` per change group, Before/After inline SVG panes (`.arch-pane-h.before/.after`), `.arch-chip` metadata, badges `b-high/b-med/b-low/b-service`; each card has an id for `toggleArch(id)` |
| `{{SERVICE_IMPACT_ROWS}}`, `{{SERVICE_IMPACT_NOTE}}`, `{{HIGH_RISK_LIST}}` | §5 / diff- and source-derived risks |
| `{{TEST_SCOPE_INTRO}}`, `{{TEST_SCOPE_EXCLUSION_NOTE}}`, `{{TEST_SCOPE_ROWS}}`, `{{TEST_SCOPE_TOTALS_NOTE}}` | §4; rows grouped by `FUNCTIONALITY_MAP` group, each citing its source(s) in the scenario cell (`rowspan` on Category); exclusion note names FE-impossible items (reboot, config download, relay/ignition hardware, physical power-off) |
| `{{AUTOMATION_PYTEST_ROWS}}` | One row per `src/tests/<feature>/*.py`: #, file / TC id, description (from docstrings), functionality group, status (DONE/UNVERIFIED) |
| `{{AUTOMATION_PYTEST_SUMMARY_NOTE}}` | Counts DONE/UNVERIFIED + source/date reconciled against (e.g. `src/tests/<feature>/` at commit `<sha>`) |
| `{{AUTOMATION_MONITORING_BODY}}` | §7 — whole section body |
| `{{PR_FINDINGS_ROWS}}`, `{{PR_FINDINGS_NOTE}}`, `{{PR_SCOPE_NOTES_ROWS}}` | §3; severity classes `p0` high / `p1` medium / `p2` low |
| `{{GAP_ANALYSIS_ROWS}}` | Doc/code mismatches, Confluence claims not found in source, linked-but-unread pages, Unverified assumptions, blind spots, UNVERIFIED log strings, missing PRs, not-fetched tickets |

Pill convention (keep): `p0` red/high, `p1` amber/medium (inline-styled green for "Automated"),
`p2` blue/low or "Not Applicable".

---

## Rules carried over (apply these)

- **Every scenario gets a row.** A scenario with no automated counterpart is `To Be Started`,
  `Not Automatable` or `Not Applicable` with a reason — never silently dropped.
- **Normalize device_type comparisons** — if the diff shows a raw device_type string compare
  (no `.strip().lower()`), flag it in Gap Analysis.
- **A change with no cloud-visible signal is a finding**, not an omission (Monitoring note + Gap row).
- **"Not confirmed" is a real status** — say plainly what couldn't be established from code.
- **A supplied test-case list/design doc is evidence to check, not content to transcribe.** Verify
  each claim (mechanism, endpoint, enum, log string) against source; what doesn't resolve is
  reported as not found, never invented.
- **UNVERIFIED log strings/paths** noted in test docstrings are real gaps in
  confidence — surface them in the Automation tab status and Gap Analysis.
- Keep KPI totals and row counts in sync.

---

## Mode B — Logs-only scope

> Input is **only** what the user hands over: local log file(s)/dir. **Never** download from S3,
> connect to the device/VPN, SSH to the pod, or call AWS in this mode. If a path doesn't exist,
> say so and stop.

**Inputs**: feature name + local log path(s). Primary log = the service's own log; grep neighbours
only to learn cross-service interactions. Platform/release optional — infer from the logs or write
`unknown` + a Gap row.

**B1. Profile (mechanical)**
```bash
python3 .claude/skills/fleetedge-test-scope-generator/log_profile.py <log> [<log> ...] --out <scratch>/profile.json
```
Handles `epoch_ms: mono: TAG: LEVEL: pid: tid: msg`. **FE caveat**: `otacheck`, `keep_alive_manager`,
`scheduler_manager` logs use UTC-string timestamps and will come out *unparsed* — check
`window.unparsed_lines`; if most lines are unparsed, profile by hand with `grep -c`/`sort | uniq -c`
on the message text and say in Gap Analysis that the profiler didn't apply. Output per file: time
window, inferred restarts (distinct PIDs), tag/level counts, ranked message templates, `anomalies`
(E/W/C/F), `rare` (≤3 occurrences). Confirm every cited template against a raw `grep` line.

**B2. Derive scenarios** from evidence (tag, template, count, first timestamp), grouped by:
lifecycle (rare templates, PID changes) → steady-state flows → config-driven paths → cross-service
interactions → error paths. Use the feature's `FUNCTIONALITY_MAP` groups and test docstrings as the
grouping vocabulary and to identify flows that **did not appear**.

**B3. Map to automation** as in §4; tag rows **Automated (file / TC id)**, **Not Covered**, or
**Not Observed**. Never invent TC ids.

**B4. Render** `template.html` unchanged → `Output/<feature>_test_scope_<release>_logs.html`.
Overview states the scope is **derived from device logs** (device ids, window, line count,
restarts). Tickets table: one `.note` "No tickets supplied — Mode B". Test Scope rows are
"Observed in logs", never "required"; no Confluence reconciliation. Service Impact: Direct = the
profiled service, Regression Validation = services seen interacting in its log. Monitoring:
recurring templates/anomaly signatures with observed rate — label them clearly as device-log
observations (this is the one place device logs are allowed, since there are no tickets/cloud
contract to honour; do not present them as drive-monitoring KPIs). Architecture, PR Analysis, Open
Bugs: keep tabs with `.note` "Not derivable in logs-only mode". Error templates go in Gap Analysis
as **unverified candidates** (real defect vs expected noise), plus every Not Covered / Not Observed
row, plus the limit: only behaviour exercised in the window is represented; absence of a flow is
not evidence it is untested or broken.

**B5. Verify**: §9 checks that still apply, plus every cited template/count traces to
`profile.json` or a raw grep, and the paths/window in Overview match the files actually read.
