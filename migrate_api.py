#!/usr/bin/env python3
"""
migrate_api.py — update all skill files from the 8-tool API to the 5-tool API.

Run from the skills repo root:
    python3 migrate_api.py

Dry-run (print diffs, no writes):
    python3 migrate_api.py --dry-run
"""

import re
import sys
import os
from pathlib import Path

DRY_RUN = "--dry-run" in sys.argv

# ── Tools-table replacement ────────────────────────────────────────────────────
# The old table has many rows of individual tool names. We detect it by the
# presence of a | `start_scan` | row and replace the whole block.

OLD_TABLE_PATTERN = re.compile(
    r"(\| Tool \| Use for \|\n\|[-| ]+\|\n)"   # header rows
    r"((?:\|[^\n]+\|\n)+)",                    # all data rows
    re.MULTILINE,
)

NEW_TABLE = (
    "| Tool | Use for |\n"
    "|------|---------|\n"
    "| `session(action, options)` | Scan lifecycle — `action=\"start\"` · `action=\"complete\"` · `action=\"status\"` · `action=\"set_codebase\"` · `action=\"start_kali\"` · `action=\"stop_kali\"` |\n"
    "| `scan(tool, target, flags, options)` | Security scanners — tool: `nmap` · `naabu` · `httpx` · `nuclei` · `ffuf` · `spider` · `subfinder` · `semgrep` · `trufflehog` · `metasploit` |\n"
    "| `kali(command, timeout)` | Any Kali tool — sqlmap, nikto, gobuster, hydra, testssl, enum4linux-ng, wapiti, theHarvester, dnsrecon, certipy, nxc, impacket, searchsploit, ... |\n"
    "| `http(action, url, method, headers, body, options)` | Raw HTTP — `action=\"request\"` (probe/PoC; options: `poc=true` routes through Burp), `action=\"save_poc\"` (writes `.http` file) |\n"
    "| `report(action, data)` | Log output — `action=\"finding\"` · `action=\"diagram\"` · `action=\"note\"` · `action=\"dashboard\"` (data: `{\"port\":5000}`) · `action=\"coverage\"` |\n"
)


def replace_tools_table(text: str) -> str:
    """Replace the Tools table only when it contains old API rows."""
    # Only replace if the table has at least one old-API row
    old_api_markers = [
        "| `start_scan`", "| `run_nmap`", "| `kali_exec`",
        "| `http_request`", "| `start_dashboard`", "| `report_finding`",
    ]
    match = OLD_TABLE_PATTERN.search(text)
    if not match:
        return text
    table_body = match.group(2)
    if not any(m in table_body for m in old_api_markers):
        return text
    # Replace the matched header+body with the new table
    return text[: match.start()] + NEW_TABLE + text[match.end() :]


# ── Function-call replacements (order matters) ────────────────────────────────

def replace_function_calls(text: str) -> str:
    # ── kali_exec ──────────────────────────────────────────────────────────────
    # kali_exec("cmd")  →  kali(command="cmd")
    # kali_exec(f"cmd") →  kali(command=f"cmd")
    # kali_exec(`cmd`)  →  kali(command=`cmd`)  (backtick in markdown)
    # kali_exec(var)    →  kali(command=var)
    # Backtick prose reference first (must precede plain-word catch-all)
    text = re.sub(r'`kali_exec`', '`kali(command=...)`', text)
    # Call form: kali_exec(...) — replace name, keep parens + args
    text = re.sub(r'\bkali_exec\(', 'kali(command=', text)
    # Plain word / prose reference (e.g. "via kali_exec before invoking")
    text = re.sub(r'\bkali_exec\b', 'kali(command=...)', text)
    # kali(command=command=...) double-up guard (if someone already had keyword arg)
    text = re.sub(r'\bkali\(command=command=', 'kali(command=', text)

    # ── start_dashboard ────────────────────────────────────────────────────────
    text = text.replace(
        'start_dashboard()',
        'report(action="dashboard", data={"port": 5000})',
    )
    # Backtick prose reference
    text = re.sub(
        r'`start_dashboard`',
        '`report(action="dashboard", data={"port": 5000})`',
        text,
    )
    # Call `start_dashboard` → call `report(action="dashboard", ...)`
    text = re.sub(
        r'\bstart_dashboard\b',
        'report(action="dashboard", data={"port": 5000})',
        text,
    )

    # ── http_request ───────────────────────────────────────────────────────────
    # http_request(poc=True, ...) → http(action="request", ..., options={"poc": true})
    # We handle poc=True first before the generic rename so we can move it to options
    def fix_poc(m):
        inner = m.group(1)
        # Remove poc=True / poc=False from kwargs
        inner_no_poc = re.sub(r',?\s*poc\s*=\s*(True|False|true|false)\s*,?', '', inner).strip().strip(',').strip()
        poc_val = re.search(r'\bpoc\s*=\s*(True|true)', m.group(0))
        if poc_val:
            if inner_no_poc:
                return f'http(action="request", {inner_no_poc}, options={{"poc": true}})'
            else:
                return 'http(action="request", options={"poc": true})'
        else:
            if inner_no_poc:
                return f'http(action="request", {inner_no_poc})'
            else:
                return 'http(action="request")'

    text = re.sub(r'\bhttp_request\(([^)]*(?:poc\s*=)[^)]*)\)', fix_poc, text)

    # Generic http_request(...) → http(action="request", ...)
    text = re.sub(r'\bhttp_request\(', 'http(action="request", ', text)
    # Clean up empty trailing comma: http(action="request", )
    text = re.sub(r'http\(action="request",\s*\)', 'http(action="request")', text)

    # Backtick prose reference
    text = re.sub(r'`http_request`', '`http(action="request", ...)`', text)
    # Plain prose reference
    text = re.sub(r'\bhttp_request\b', 'http(action="request", ...)', text)

    # ── save_poc ───────────────────────────────────────────────────────────────
    # save_poc(title="x", method="GET", url="...", headers={}, body={}, notes="...")
    # → http(action="save_poc", url="...", method="GET", headers={}, body={},
    #        options={"title": "x", "notes": "..."})
    def fix_save_poc(m):
        inner = m.group(1)
        # Extract title and notes kwargs to move to options
        title_m = re.search(r'title\s*=\s*("[^"]*"|\'[^\']*\'|\S+)', inner)
        notes_m = re.search(r'notes\s*=\s*("[^"]*"|\'[^\']*\'|\S+)', inner)
        # Remove title= and notes= from inner
        inner2 = re.sub(r',?\s*title\s*=\s*(?:"[^"]*"|\'[^\']*\'|\S+)\s*,?', '', inner)
        inner2 = re.sub(r',?\s*notes\s*=\s*(?:"[^"]*"|\'[^\']*\'|\S+)\s*,?', '', inner2)
        inner2 = inner2.strip().strip(',').strip()
        opts_parts = []
        if title_m:
            opts_parts.append(f'"title": {title_m.group(1)}')
        if notes_m:
            opts_parts.append(f'"notes": {notes_m.group(1)}')
        opts_str = ', '.join(opts_parts)
        parts = []
        if inner2:
            parts.append(inner2)
        if opts_str:
            parts.append(f'options={{{opts_str}}}')
        args = ', '.join(parts)
        return f'http(action="save_poc", {args})' if args else 'http(action="save_poc")'

    text = re.sub(r'\bsave_poc\(([^)]*)\)', fix_save_poc, text)
    text = re.sub(r'`save_poc`', '`http(action="save_poc", ...)`', text)
    # Negative lookbehind: don't match when already inside action="save_poc"
    text = re.sub(r'(?<!action=")\bsave_poc\b', 'http(action="save_poc", ...)', text)

    # ── report_finding ─────────────────────────────────────────────────────────
    text = re.sub(r'\breport_finding\(', 'report(action="finding", data={', text)
    # Close the rewritten call: report(action="finding", data={...}) — the original
    # args become the data dict content; we can't auto-close perfectly but adding
    # a note is better than leaving stale name. For simple prose references:
    text = re.sub(r'`report_finding`', '`report(action="finding", data={...})`', text)
    text = re.sub(r'\breport_finding\b', 'report(action="finding", data={...})', text)

    # ── report_diagram ─────────────────────────────────────────────────────────
    text = re.sub(r'\breport_diagram\(', 'report(action="diagram", data={', text)
    text = re.sub(r'`report_diagram`', '`report(action="diagram", data={...})`', text)
    text = re.sub(r'\breport_diagram\b', 'report(action="diagram", data={...})', text)

    # ── log_note ───────────────────────────────────────────────────────────────
    text = re.sub(r'\blog_note\(', 'report(action="note", data={"message": ', text)
    text = re.sub(r'`log_note`', '`report(action="note", data={...})`', text)
    text = re.sub(r'\blog_note\b', 'report(action="note", data={...})', text)

    # ── start_scan ─────────────────────────────────────────────────────────────
    text = re.sub(r'\bstart_scan\(', 'session(action="start", options={', text)
    text = re.sub(r'`start_scan`', '`session(action="start", options={...})`', text)
    text = re.sub(r'\bstart_scan\b', 'session(action="start", options={...})', text)

    # ── complete_scan ──────────────────────────────────────────────────────────
    text = re.sub(r'\bcomplete_scan\(', 'session(action="complete", options={', text)
    text = re.sub(r'`complete_scan`', '`session(action="complete", options={...})`', text)
    text = re.sub(r'\bcomplete_scan\b', 'session(action="complete", options={...})', text)

    # ── start_kali / stop_kali / pull_images ───────────────────────────────────
    text = re.sub(r'\bstart_kali\(\)', 'session(action="start_kali")', text)
    text = re.sub(r'`start_kali`', '`session(action="start_kali")`', text)
    # Negative lookbehind: don't match when already inside action="start_kali"
    text = re.sub(r'(?<!action=")\bstart_kali\b', 'session(action="start_kali")', text)

    text = re.sub(r'\bstop_kali\(\)', 'session(action="stop_kali")', text)
    text = re.sub(r'`stop_kali`', '`session(action="stop_kali")`', text)
    # Negative lookbehind: don't match when already inside action="stop_kali"
    text = re.sub(r'(?<!action=")\bstop_kali\b', 'session(action="stop_kali")', text)

    text = re.sub(r'\bpull_images\(\)', 'session(action="pull_images")', text)
    text = re.sub(r'`pull_images`', '`session(action="pull_images")`', text)
    # Negative lookbehind: don't match when already inside action="pull_images"
    text = re.sub(r'(?<!action=")\bpull_images\b', 'session(action="pull_images")', text)

    # ── run_* scan tools ───────────────────────────────────────────────────────
    # These appear in prose as `run_nmap` or in code as run_nmap(...)
    # We replace the call form and the backtick prose form separately.
    scanner_map = {
        'run_nmap':       'scan(tool="nmap", ...)',
        'run_naabu':      'scan(tool="naabu", ...)',
        'run_httpx':      'scan(tool="httpx", ...)',
        'run_nuclei':     'scan(tool="nuclei", ...)',
        'run_ffuf':       'scan(tool="ffuf", ...)',
        'run_spider':     'scan(tool="spider", ...)',
        'run_subfinder':  'scan(tool="subfinder", ...)',
        'run_semgrep':    'scan(tool="semgrep", ...)',
        'run_trufflehog': 'scan(tool="trufflehog", ...)',
    }
    for old, new in scanner_map.items():
        # Backtick prose: `run_nmap`
        text = re.sub(rf'`{old}`', f'`{new}`', text)
        # Call form: run_nmap(...) — replace name, keep parens
        tool_name = re.search(r'tool="([^"]+)"', new).group(1)
        text = re.sub(
            rf'\b{old}\(',
            f'scan(tool="{tool_name}", target=',
            text,
        )
        # Plain word reference
        text = re.sub(rf'\b{old}\b', new, text)

    return text


# ── Claude-Code-only skill: "X" / args: "..." → dual-mode pattern ─────────────

# Matches a block like:
#   skill: "name"
#   args: "arguments"
# (with any leading whitespace, as long as both lines have the same indentation)

SKILL_BLOCK_PATTERN = re.compile(
    r'^(?P<indent>[ \t]*)skill: "(?P<name>[^"]+)"\n'
    r'(?P=indent)args: "(?P<args>[^"]*)"',
    re.MULTILINE,
)


def replace_skill_blocks(text: str) -> str:
    def repl(m):
        indent = m.group('indent')
        name = m.group('name')
        args = m.group('args')
        return (
            f'{indent}# Claude Code: skill: "{name}", args: "{args}"\n'
            f'{indent}# opencode / other clients: read the skill file at ~/.config/opencode/commands/{name}.md and follow its workflow\n'
            f'{indent}Invoke /{name}: {args}'
        )
    return SKILL_BLOCK_PATTERN.sub(repl, text)


# ── "How:" chaining line ──────────────────────────────────────────────────────

OLD_HOW_PATTERN = re.compile(
    r'\*\*How:\*\* Use the Skill tool \(e\.g\. `skill: "[^"]+", args: "[^"]*"`\)[^\n]*'
)

NEW_HOW = (
    '**How to chain:** At the trigger point, invoke the sub-skill then resume the pentest.\n'
    '- **Claude Code**: use the Skill tool — `skill: "<name>", args: "<arguments>"`\n'
    '- **opencode / other clients**: read the skill command file at '
    '`~/.config/opencode/commands/<name>.md` and follow its workflow inline with the provided arguments'
)


def replace_how_line(text: str) -> str:
    return OLD_HOW_PATTERN.sub(NEW_HOW, text)


# ── Main ───────────────────────────────────────────────────────────────────────

def migrate_file(path: Path) -> bool:
    """Return True if the file was (or would be) changed."""
    original = path.read_text(encoding='utf-8')
    text = original

    # function_calls runs first so it processes old tool names before the
    # tools table is replaced (new table description contains action= strings
    # that would otherwise be double-substituted).
    text = replace_function_calls(text)
    text = replace_tools_table(text)
    text = replace_skill_blocks(text)
    text = replace_how_line(text)

    if text == original:
        return False

    if DRY_RUN:
        print(f"[dry-run] would update: {path}")
    else:
        path.write_text(text, encoding='utf-8')
        print(f"updated: {path}")
    return True


def main():
    root = Path(__file__).parent
    md_files = sorted(root.rglob('*.md'))
    # Skip the migration script itself (not an .md but guard anyway)
    changed = 0
    skipped = 0
    for p in md_files:
        # Skip README
        if p.name == 'README.md':
            continue
        if migrate_file(p):
            changed += 1
        else:
            skipped += 1
    print(f"\nDone. {'Would update' if DRY_RUN else 'Updated'} {changed} file(s), {skipped} already clean.")


if __name__ == '__main__':
    main()
