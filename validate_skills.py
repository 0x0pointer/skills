#!/usr/bin/env python3
"""Validate skill SKILL.md frontmatter before release.

Enforces the rules that have broken skill loading in the past:

  1. Frontmatter must exist and be closed with a `---` line.
  2. Frontmatter must be valid YAML.
  3. `name` must be present and a non-empty string.
  4. `description` must be present, a string, and at most 1024 characters
     (the harness rejects anything longer).
  5. `argument-hint`, when present, must be a quoted string -- never a bare
     value containing YAML flow characters like `[`, `]`, `:` or `#`, which
     YAML parses as a list (or fails on outright).

Run from anywhere; it scans the repository the script lives in.
Exit code is 0 when everything passes, 1 when any skill fails.

    python3 validate_skills.py
"""
from __future__ import annotations

import os
import re
import sys

DESCRIPTION_MAX = 1024

try:
    import yaml
except ImportError:  # pragma: no cover - surfaced clearly in CI
    sys.stderr.write(
        "error: PyYAML is required. Install with `pip install pyyaml`.\n"
    )
    sys.exit(2)

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
# Top-level markdown files that are NOT skills and should be skipped.
NON_SKILL_MD = {"README.md", "MEMORY.md", "LICENSE.md", "CONTRIBUTING.md", "CHANGELOG.md"}

FRONTMATTER_RE = re.compile(r"^---[ \t]*\n(.*?)\n---[ \t]*\n", re.DOTALL)


def find_skill_files(root: str) -> list[str]:
    """Every `*/SKILL.md`, plus any top-level `*.md` carrying YAML frontmatter."""
    skills: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # don't descend into VCS / tooling / hidden dirs (e.g. .git, .github,
        # .venv, .sleep-home, .skillopt-sleep staging+backups)
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != "node_modules"]
        for name in filenames:
            if name == "SKILL.md":
                skills.append(os.path.join(dirpath, name))
            elif dirpath == root and name.endswith(".md") and name not in NON_SKILL_MD:
                # a top-level skill like pentester.md -- only if it has frontmatter
                with open(os.path.join(dirpath, name), encoding="utf-8") as fh:
                    if fh.read(3) == "---":
                        skills.append(os.path.join(dirpath, name))
    return sorted(skills)


def frontmatter_lines(fm: str) -> list[tuple[str, str]]:
    """Return (key, raw_value) for each top-level `key: value` line."""
    out = []
    for line in fm.splitlines():
        if line and line[0] not in " \t":
            m = re.match(r"^([A-Za-z0-9_-]+):[ \t]*(.*)$", line)
            if m:
                out.append((m.group(1), m.group(2)))
    return out


# ── anti-drift: chaining tables must stay client-neutral ───────────────────────
# Per-client "how to invoke a skill" belongs in ONE place (the project's
# CLAUDE.md / AGENTS.md), never duplicated into every skill — that duplication
# rots (skills drifted to a deprecated opencode `cat` invocation while CLAUDE.md
# had moved on). These markers flag a SKILL.md that reintroduces client-specific
# invocation syntax. The `pentester*` orchestrators are the intentional
# per-client entrypoints and are exempt.
_CLIENT_SYNTAX_MARKERS = (
    ("| Claude Code | opencode |", "per-client chaining-table columns"),
    ("cat ~/.config/opencode/commands/", "deprecated opencode `cat` invocation"),
    ("Skill(skill=", "Claude-specific Skill() invocation"),
    ("Skill(name=", "Claude-specific Skill() invocation"),
    ("skill({", "opencode-specific skill() invocation"),
)


def _client_neutral_errors(rel: str, text: str) -> list[str]:
    if "pentester" in rel:  # intentional per-client orchestrator entrypoints
        return []
    errs: list[str] = []
    for marker, why in _CLIENT_SYNTAX_MARKERS:
        if marker in text:
            errs.append(
                f"{rel}: client-specific invocation syntax found ({why}) — keep "
                "chaining client-neutral; put per-client invocation in CLAUDE.md / AGENTS.md"
            )
    return errs


def validate_file(path: str) -> list[str]:
    rel = os.path.relpath(path, REPO_ROOT)
    errors: list[str] = []
    with open(path, encoding="utf-8") as fh:
        text = fh.read()

    errors.extend(_client_neutral_errors(rel, text))

    if not text.startswith("---"):
        return [f"{rel}: missing YAML frontmatter (must start with '---')"]

    m = FRONTMATTER_RE.match(text)
    if not m:
        return [f"{rel}: unterminated frontmatter (no closing '---' line)"]
    fm = m.group(1)

    try:
        data = yaml.safe_load(fm)
    except yaml.YAMLError as exc:
        detail = str(exc).splitlines()[0]
        return [f"{rel}: frontmatter is not valid YAML -> {detail}"]

    if not isinstance(data, dict):
        return [f"{rel}: frontmatter did not parse to a mapping"]

    # name
    name = data.get("name")
    if not name or not isinstance(name, str):
        errors.append(f"{rel}: `name` is required and must be a non-empty string")

    # description
    desc = data.get("description")
    if desc is None:
        errors.append(f"{rel}: `description` is required")
    elif not isinstance(desc, str):
        errors.append(f"{rel}: `description` must be a string, got {type(desc).__name__}")
    elif len(desc) > DESCRIPTION_MAX:
        errors.append(
            f"{rel}: `description` is {len(desc)} chars (max {DESCRIPTION_MAX})"
        )

    # argument-hint: must be a quoted string when present
    if "argument-hint" in data:
        if not isinstance(data["argument-hint"], str):
            errors.append(
                f"{rel}: `argument-hint` must be a quoted string "
                f"(parsed as {type(data['argument-hint']).__name__} -- add quotes)"
            )
        else:
            # even when YAML tolerates it, require explicit quoting whenever the
            # value carries flow characters, so future edits can't silently break.
            for key, raw in frontmatter_lines(fm):
                if key != "argument-hint":
                    continue
                quoted = len(raw) >= 2 and raw[0] in "\"'" and raw[-1] == raw[0]
                if not quoted and re.search(r"[\[\]#]|:\s", raw):
                    errors.append(
                        f"{rel}: `argument-hint` value must be wrapped in quotes "
                        f"(contains YAML special characters): {raw}"
                    )
    return errors


def main() -> int:
    files = find_skill_files(REPO_ROOT)
    if not files:
        sys.stderr.write("error: no SKILL.md files found\n")
        return 2

    all_errors: list[str] = []
    for path in files:
        all_errors.extend(validate_file(path))

    # Leaf skill-dir names must be globally unique: skills install to a FLAT target
    # (~/.claude/skills/<leaf>/), so two skills with the same leaf name in different
    # domain folders (e.g. web/foo and infra/foo) would clobber each other and break
    # by-name invocation. Enforce it now that skills are organised into /domain/ dirs.
    _seen: dict[str, str] = {}
    for path in files:
        if os.path.basename(path) != "SKILL.md":
            continue  # top-level *.md skills (e.g. pentester.md) have no dir to collide
        leaf = os.path.basename(os.path.dirname(path))
        if leaf in _seen:
            all_errors.append(
                f"duplicate skill name '{leaf}': {os.path.relpath(path, REPO_ROOT)} "
                f"collides with {os.path.relpath(_seen[leaf], REPO_ROOT)} "
                f"(both install to ~/.claude/skills/{leaf}/)"
            )
        else:
            _seen[leaf] = path

    print(f"Validated {len(files)} skill file(s).")
    if all_errors:
        print(f"\n{len(all_errors)} problem(s) found:\n")
        for err in all_errors:
            print(f"  ✗ {err}")
        return 1
    print("All skill frontmatter is valid. ✓")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
