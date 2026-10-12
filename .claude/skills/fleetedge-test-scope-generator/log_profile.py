#!/usr/bin/env python3
"""Profile one or more device service logs for test-scope derivation (Mode B).

Line format handled:  <epoch_ms>: <mono>: <TAG>: <LEVEL>: <pid>: <tid>: <message>
Lines that don't match (continuation lines) are folded into the previous entry's count
of "unparsed" and otherwise ignored.

Output (JSON to stdout, or --out FILE) per log file:
  window        first/last epoch_ms + ISO, line count
  pids          distinct PIDs in order of first appearance (a new PID mid-log == service restart)
  tags          TAG -> count
  levels        LEVEL -> count
  templates     message templates (digits/hex/paths-with-ids collapsed) ranked by frequency,
                each with count, first_ts, last_ts, level, tag, one raw example
  anomalies     ERROR/WARN/CRIT templates only (subset of templates)
  rare          templates seen <= --rare-max times (candidate one-shot lifecycle events)

Usage:
  python3 log_profile.py <log> [<log> ...] [--top 150] [--rare-max 3] [--out profile.json]
"""
import argparse
import json
import re
import sys
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from pathlib import Path

LINE_RE = re.compile(r"^(\d{13}):\s*(\d+):\s*([^:]+?):\s*([A-Z]):\s*(\d+):\s*(\d+):\s?(.*)$")
BAD_LEVELS = {"E", "W", "C", "F"}  # error, warn, critical, fatal

_SUBS = [
    (re.compile(r"0x[0-9a-fA-F]+"), "<HEX>"),
    (re.compile(r"\b[0-9a-fA-F]{8,}\b"), "<ID>"),
    (re.compile(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(\.\d+)?"), "<DATETIME>"),
    (re.compile(r"-?\d+\.\d+"), "<F>"),
    (re.compile(r"-?\d+"), "<N>"),
]


def templatize(msg: str) -> str:
    for rx, rep in _SUBS:
        msg = rx.sub(rep, msg)
    return re.sub(r"\s+", " ", msg).strip()[:220]


def iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def profile(path: Path, top: int, rare_max: int) -> dict:
    tags, levels = Counter(), Counter()
    pids: "OrderedDict[str, int]" = OrderedDict()
    tmpl = {}
    first = last = None
    lines = unparsed = 0
    with path.open("r", errors="replace") as fh:
        for raw in fh:
            lines += 1
            m = LINE_RE.match(raw.rstrip("\n"))
            if not m:
                unparsed += 1
                continue
            ts, _mono, tag, lvl, pid, _tid, msg = m.groups()
            ts = int(ts)
            first = ts if first is None else first
            last = ts
            tags[tag] += 1
            levels[lvl] += 1
            pids.setdefault(pid, ts)
            key = (tag, lvl, templatize(msg))
            t = tmpl.get(key)
            if t is None:
                tmpl[key] = {"tag": tag, "level": lvl, "template": key[2], "count": 1,
                             "first_ts": ts, "last_ts": ts, "example": msg[:300]}
            else:
                t["count"] += 1
                t["last_ts"] = ts
    ranked = sorted(tmpl.values(), key=lambda t: -t["count"])
    for t in ranked:
        t["first_iso"], t["last_iso"] = iso(t["first_ts"]), iso(t["last_ts"])
    return {
        "file": str(path),
        "window": {"first_ms": first, "last_ms": last,
                   "first_iso": iso(first) if first else None,
                   "last_iso": iso(last) if last else None,
                   "lines": lines, "unparsed_lines": unparsed},
        "pids": [{"pid": p, "first_seen_iso": iso(t)} for p, t in pids.items()],
        "restarts_inferred": max(len(pids) - 1, 0),
        "tags": dict(tags.most_common()),
        "levels": dict(levels.most_common()),
        "templates": ranked[:top],
        "anomalies": [t for t in ranked if t["level"] in BAD_LEVELS][:top],
        "rare": [t for t in ranked if t["count"] <= rare_max][:top],
        "distinct_templates": len(ranked),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("logs", nargs="+")
    ap.add_argument("--top", type=int, default=150)
    ap.add_argument("--rare-max", type=int, default=3)
    ap.add_argument("--out")
    a = ap.parse_args()
    res = []
    for p in a.logs:
        path = Path(p)
        if not path.is_file():
            print(f"skip (not a file): {p}", file=sys.stderr)
            continue
        res.append(profile(path, a.top, a.rare_max))
    out = json.dumps(res, indent=2)
    if a.out:
        Path(a.out).write_text(out)
        print(f"wrote {a.out} ({len(res)} log(s))")
    else:
        print(out)
    return 0 if res else 1


if __name__ == "__main__":
    sys.exit(main())
