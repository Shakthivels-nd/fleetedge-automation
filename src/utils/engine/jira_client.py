"""
jira_client.py — JIRA integration for Known/Unknown issue classification.

Ported from the pytest_device_validator reference framework's jira_client.py,
adapted to this repo's test naming convention and credential handling:

  - Test names here are test_<description>_itn<NNNN> (not TC_<service>_<num>),
    so ticket-key extraction maps itn<NNNN> -> ITN-<NNNN> instead of TC-<NNNN>.
  - Credentials: environment variables (JIRA_SERVER, JIRA_USERNAME,
    JIRA_API_TOKEN) take priority; jira_config.ini (repo root, [JIRA]
    section) is a fallback for whichever of the three env vars aren't set.
    jira_config.ini is gitignored -- never commit it with real values filled
    in. Prefer .env over it when possible; it exists only for parity with
    the reference framework's config style for people who prefer a file.

Pre-fetch strategy (same as the reference):
  1. At session start, collect all test node IDs (itn numbers) that will run.
  2. Batch-fetch linked issues for ALL of them in one go (single JIRA connection).
  3. Store in a JiraCache dict: {ITN_ticket -> [(key, status, link), ...]}.
  4. When a test fails, just look up the cache -- zero API calls at report time.

Classification logic:
  - If any linked issue is NOT an ITN ticket, NOT 'NA', and NOT in a resolved
    state -> KNOWN_ISSUE (active bug)
  - If linked issues exist but all are resolved/ITN self-refs -> UNKNOWN_ISSUE
  - If no JIRA data available -> NO_JIRA

Configuration:
  JIRA_SERVER, JIRA_USERNAME, JIRA_API_TOKEN via .env, or the matching keys
  in jira_config.ini's [JIRA] section (env vars win if both are set).

Requires the optional `jira` package (pip install jira). If it isn't
installed, or credentials aren't set, JiraCache.prefetch() no-ops and every
test classifies as NO_JIRA -- the report still works, it just shows no
known/unknown-issue badges.
"""

from __future__ import annotations

import logging
import os
import re
from configparser import ConfigParser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("fleetedge.jira_client")

# Resolved statuses — issues in these states are considered fixed
RESOLVED_STATUSES = frozenset([
    "done", "resolved", "closed", "cancelled", "won't fix", "wontfix",
    "duplicate", "cannot reproduce",
])

# Repo root (fleetedge-automation/) -- src/utils/engine/jira_client.py is three levels down.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_CONFIG_FILE = _PROJECT_ROOT / "jira_config.ini"


def _load_config() -> Dict[str, str]:
    """Load JIRA config: env vars first, jira_config.ini as fallback."""
    config = {
        "server": os.environ.get("JIRA_SERVER", ""),
        "username": os.environ.get("JIRA_USERNAME", ""),
        "api_token": os.environ.get("JIRA_API_TOKEN", ""),
    }

    if _CONFIG_FILE.exists():
        parser = ConfigParser()
        parser.read(_CONFIG_FILE)
        if parser.has_section("JIRA"):
            config["server"] = config["server"] or parser.get("JIRA", "server", fallback="")
            config["username"] = config["username"] or parser.get("JIRA", "username", fallback="")
            config["api_token"] = config["api_token"] or parser.get("JIRA", "api_token", fallback="")

    return config


def _get_jira_connection():
    """Create a JIRA connection. Returns None if jira package not installed or config missing."""
    try:
        from jira import JIRA
    except ImportError:
        logger.warning("jira package not installed. Run: pip install jira")
        return None

    config = _load_config()
    if not all([config["server"], config["username"], config["api_token"]]):
        logger.warning(
            "JIRA credentials not configured. Set JIRA_SERVER, JIRA_USERNAME, "
            "JIRA_API_TOKEN in .env to enable known/unknown-issue classification."
        )
        return None

    try:
        return JIRA(server=config["server"], basic_auth=(config["username"], config["api_token"]))
    except Exception as exc:
        logger.error("Failed to connect to JIRA: %s", exc)
        return None


def _extract_jira_ticket(test_id: str) -> str:
    """Convert a test node id (or name) to its JIRA ticket ID.

    test_connection_success_itn2426        -> ITN-2426
    test_api_call_upload_keep_alive_itn2639 -> ITN-2639
    itn2426                                 -> ITN-2426
    """
    m = re.search(r"itn(\d+)", test_id, re.IGNORECASE)
    if m:
        return f"ITN-{m.group(1)}"
    return ""


def _classify_linked_issues(linked_issues: List[Tuple[str, str, str]]) -> Dict[str, Any]:
    """Classify a test based on its pre-fetched linked issues."""
    if linked_issues == [("NA", "NA", "NA")]:
        return {"classification": "NO_JIRA", "linked_issues": [], "active_bugs": []}

    if not linked_issues:
        return {"classification": "UNKNOWN_ISSUE", "linked_issues": [], "active_bugs": []}

    active_bugs = []
    for issue_key, status, link in linked_issues:
        if issue_key.startswith("ITN"):
            continue
        if issue_key == "NA":
            continue
        if status.lower() not in RESOLVED_STATUSES:
            active_bugs.append((issue_key, status, link))

    classification = "KNOWN_ISSUE" if active_bugs else "UNKNOWN_ISSUE"
    return {
        "classification": classification,
        "linked_issues": linked_issues,
        "active_bugs": active_bugs,
    }


class JiraCache:
    """Pre-fetches all JIRA linked issues once, provides instant lookups.

    Usage:
        cache = JiraCache()
        cache.prefetch(["test_x_itn2426", "test_y_itn2639"])  # one-time JIRA call
        ...
        info = cache.classify("test_x_itn2426")  # instant local lookup
        # -> {"classification": "KNOWN_ISSUE", "linked_issues": [...], "active_bugs": [...]}
    """

    def __init__(self):
        # {jira_ticket_id: [(key, status, link), ...]}
        self._linked_issues: Dict[str, List[Tuple[str, str, str]]] = {}
        # {test_id: jira_ticket_id}
        self._test_to_jira: Dict[str, str] = {}
        self._prefetched = False

    @property
    def available(self) -> bool:
        return self._prefetched

    def prefetch(self, test_ids: List[str]) -> int:
        """Batch-fetch linked issues for all test IDs. Single JIRA connection."""
        jira = _get_jira_connection()
        if jira is None:
            logger.info("JIRA prefetch skipped — connection unavailable")
            return 0

        config = _load_config()
        server = config["server"].rstrip("/")

        jira_tickets: Dict[str, List[str]] = {}
        for test_id in test_ids:
            ticket = _extract_jira_ticket(test_id)
            if not ticket:
                continue
            self._test_to_jira[test_id] = ticket
            jira_tickets.setdefault(ticket, []).append(test_id)

        logger.info("JIRA prefetch: %d unique tickets from %d test IDs", len(jira_tickets), len(test_ids))

        fetched = 0
        for ticket_id in jira_tickets:
            if ticket_id in self._linked_issues:
                fetched += 1
                continue
            try:
                issue = jira.issue(ticket_id)
                linked = []
                for link in issue.fields.issuelinks:
                    linked_ref = getattr(link, "outwardIssue", None) or getattr(link, "inwardIssue", None)
                    if linked_ref is None:
                        continue
                    linked_issue = jira.issue(linked_ref.key)
                    jira_link = f"{server}/browse/{linked_issue.key}"
                    linked.append((linked_issue.key, linked_issue.fields.status.name, jira_link))
                self._linked_issues[ticket_id] = linked
                fetched += 1
            except Exception as exc:
                logger.warning("  %s -> FETCH_FAILED: %s", ticket_id, exc)
                self._linked_issues[ticket_id] = [("NA", "NA", "NA")]

        self._prefetched = True
        logger.info("JIRA prefetch complete: %d/%d tickets fetched", fetched, len(jira_tickets))
        return fetched

    def classify(self, test_id: str) -> Dict[str, Any]:
        """Classify a test using the pre-fetched cache. Zero API calls."""
        ticket = self._test_to_jira.get(test_id) or _extract_jira_ticket(test_id)
        if not ticket:
            return {"classification": "NO_JIRA", "linked_issues": [], "active_bugs": []}

        linked = self._linked_issues.get(ticket)
        if linked is None:
            return {"classification": "NO_JIRA", "linked_issues": [], "active_bugs": []}

        return _classify_linked_issues(linked)

    def to_json_cache(self) -> Dict[str, Any]:
        """Serialize cache to a JSON-safe dict (e.g. to persist across a run)."""
        return {
            "linked_issues": {k: [list(t) for t in v] for k, v in self._linked_issues.items()},
            "test_to_jira": dict(self._test_to_jira),
        }

    @classmethod
    def from_json_cache(cls, data: Dict[str, Any]) -> "JiraCache":
        """Restore cache from a JSON dict written by to_json_cache()."""
        cache = cls()
        for k, v in data.get("linked_issues", {}).items():
            cache._linked_issues[k] = [tuple(t) for t in v]
        cache._test_to_jira = data.get("test_to_jira", {})
        cache._prefetched = True
        return cache
