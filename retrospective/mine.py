#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Mine pentest/events.jsonl for retrospective signals.

Emits a single JSON object on stdout with:
- target / depth / engagement_name (from scope.json)
- event_counts (totals by type)
- cells:
    - top_time_spend: cells sorted by (last_ts - first_ts), longest first
    - fast_wins: vulnerable cells whose total span was under 5 minutes
    - abandoned: cells with no terminal status
- tools:
    - heavy_no_finding: tools that appeared in >=3 cell_status events without
      ever producing a vulnerable cell
- skill_chains:
    - chains_to_dead_ends: sub-skills that ran but produced no findings
- findings_summary: count by severity

No new event-schema fields needed; durations are derived from existing `ts`.

Usage:
    uv run mine.py [pentest/events.jsonl] [pentest/scope.json]

Defaults: pentest/events.jsonl and pentest/scope.json relative to cwd.
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime


TERMINAL_STATUSES = {"tested_clean", "vulnerable", "not_applicable"}
FAST_WIN_SECONDS = 5 * 60


def parse_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def load_events(path: str) -> list[dict]:
    events = []
    if not os.path.exists(path):
        return events
    with open(path) as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def load_scope(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def mine(events: list[dict], scope: dict) -> dict:
    counts: dict[str, int] = defaultdict(int)
    cell_events: dict[str, list[dict]] = defaultdict(list)
    tool_appearances: dict[str, int] = defaultdict(int)
    tool_findings: dict[str, int] = defaultdict(int)
    skill_chains: list[dict] = []
    findings: list[dict] = []
    findings_by_id: dict[str, dict] = {}

    for ev in events:
        t = ev.get("type", "")
        counts[t] += 1
        if t == "cell_status":
            cid = ev.get("cell_id")
            if cid:
                cell_events[cid].append(ev)
            tool = ev.get("tested_by")
            if tool:
                tool_appearances[tool] += 1
                if ev.get("status") == "vulnerable":
                    tool_findings[tool] += 1
        elif t == "skill_chain":
            skill_chains.append(ev)
        elif t == "finding" and ev.get("action") == "add":
            findings.append(ev)
            findings_by_id[ev.get("id", "")] = ev
        elif t == "finding" and ev.get("action") == "update":
            target = findings_by_id.get(ev.get("id", ""))
            if target and ev.get("field"):
                target[ev["field"]] = ev.get("value")

    cells_summary: list[dict] = []
    abandoned: list[dict] = []
    for cid, evs in cell_events.items():
        evs_sorted = sorted(evs, key=lambda e: e.get("ts", ""))
        first = parse_ts(evs_sorted[0].get("ts"))
        last = parse_ts(evs_sorted[-1].get("ts"))
        terminal_status = next(
            (e.get("status") for e in reversed(evs_sorted) if e.get("status") in TERMINAL_STATUSES),
            None,
        )
        techniques = sorted({e.get("technique") for e in evs_sorted if e.get("technique")})
        tools = sorted({e.get("tested_by") for e in evs_sorted if e.get("tested_by")})
        duration = int((last - first).total_seconds()) if first and last else 0
        entry = {
            "cell_id": cid,
            "duration_seconds": duration,
            "techniques_tried": techniques,
            "tools_used": tools,
            "final_status": terminal_status or evs_sorted[-1].get("status"),
            "events": len(evs_sorted),
            "last_notes": evs_sorted[-1].get("notes"),
        }
        cells_summary.append(entry)
        if terminal_status is None:
            abandoned.append(entry)

    cells_summary.sort(key=lambda c: c["duration_seconds"], reverse=True)
    top_time_spend = cells_summary[:5]
    fast_wins = sorted(
        [c for c in cells_summary if c["final_status"] == "vulnerable" and c["duration_seconds"] <= FAST_WIN_SECONDS],
        key=lambda c: c["duration_seconds"],
    )[:5]

    heavy_no_finding = [
        {"tool": tool, "appearances": appearances}
        for tool, appearances in sorted(tool_appearances.items(), key=lambda kv: -kv[1])
        if appearances >= 3 and tool_findings.get(tool, 0) == 0
    ]

    chained_skills = {c.get("skill") for c in skill_chains if c.get("skill")}
    chains_to_dead_ends = []
    for skill_name in sorted(chained_skills):
        produced_finding = any(
            (f.get("tool_used") == skill_name) or skill_name in (f.get("description") or "")
            for f in findings
        )
        if not produced_finding:
            reasons = [c.get("reason", "") for c in skill_chains if c.get("skill") == skill_name]
            chains_to_dead_ends.append({"skill": skill_name, "reasons": reasons})

    severity_counts: dict[str, int] = defaultdict(int)
    for f in findings:
        severity_counts[f.get("severity", "unknown")] += 1

    return {
        "target": scope.get("target"),
        "depth": scope.get("depth"),
        "engagement_name": scope.get("name") or scope.get("engagement_name"),
        "event_counts": dict(counts),
        "cells": {
            "total": len(cells_summary),
            "top_time_spend": top_time_spend,
            "fast_wins": fast_wins,
            "abandoned": abandoned,
        },
        "tools": {
            "heavy_no_finding": heavy_no_finding,
        },
        "skill_chains": {
            "chains_to_dead_ends": chains_to_dead_ends,
        },
        "findings_summary": {
            "total": len(findings),
            "by_severity": dict(severity_counts),
        },
    }


def main() -> int:
    events_path = sys.argv[1] if len(sys.argv) > 1 else "pentest/events.jsonl"
    scope_path = sys.argv[2] if len(sys.argv) > 2 else "pentest/scope.json"
    events = load_events(events_path)
    scope = load_scope(scope_path)
    result = mine(events, scope)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
