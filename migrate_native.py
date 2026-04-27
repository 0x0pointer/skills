#!/usr/bin/env python3
"""
migrate_native.py — convert all skill files from the 5-tool MCP API
(`session`, `scan`, `kali`, `http`, `report`) to native Claude Code tools
(`Bash`, `Read`, `Write`, `Edit`) for use on a Kali host where every
underlying CLI tool is already installed.

Run from the skills repo root:
    python3 migrate_native.py

Dry-run (show which files would change, no writes):
    python3 migrate_native.py --dry-run

Idempotent: re-running on already-migrated files is a no-op.
"""

import re
import sys
from pathlib import Path

DRY_RUN = "--dry-run" in sys.argv


# ── 1. Tool-call replacements ─────────────────────────────────────────────────
#
# Order matters: more specific patterns first, generic catch-alls last, so
# substitutions don't cascade. Each block handles three forms:
#   1. call form        kali(command="X")           → Bash("X")
#   2. backtick prose  `kali(command=...)`          → `Bash(...)`
#   3. plain prose      kali(command=...)           → Bash(...)


def replace_kali(text: str) -> str:
    # Call form with quoted string arg
    text = re.sub(r'\bkali\(command="([^"]*)"\)', r'Bash("\1")', text)
    text = re.sub(r"\bkali\(command='([^']*)'\)", r'Bash("\1")', text)
    # Call form with f-string
    text = re.sub(r'\bkali\(command=f"([^"]*)"\)', r'Bash(f"\1")', text)
    # Call form with bare variable / generic
    text = re.sub(r'\bkali\(command=([^)]+)\)', r'Bash(\1)', text)
    # Backtick prose
    text = re.sub(r'`kali\(command=\.\.\.\)`', '`Bash(...)`', text)
    text = re.sub(r'`kali_exec`', '`Bash`', text)
    text = re.sub(r'`kali`', '`Bash`', text)
    # Plain word references that survive
    text = re.sub(r'\bkali\(command=\.\.\.\)', 'Bash(...)', text)
    return text


# ── scan(tool="X", ...) ───────────────────────────────────────────────────────
# These call patterns vary too much to convert losslessly. We rewrite to
# Bash("<binary> ...") preserving any literal target= value when present so
# the prose still reads coherently.

SCAN_BINARIES = {
    "naabu": "naabu",
    "nmap": "nmap",
    "httpx": "httpx",
    "nuclei": "nuclei",
    "ffuf": "ffuf",
    "subfinder": "subfinder",
    "semgrep": "semgrep",
    "trufflehog": "trufflehog",
    "spider": "katana",  # fast mode → katana; deep mode mentioned in prose
    "metasploit": "msfconsole",
}


def replace_scan(text: str) -> str:
    # Backtick prose with explicit ellipsis: `scan(tool="X", ...)`
    def bt(m):
        tool = m.group(1)
        return f'`Bash("{SCAN_BINARIES.get(tool, tool)} ...")`'

    text = re.sub(r'`scan\(tool="([^"]+)",\s*\.\.\.\)`', bt, text)
    text = re.sub(r'`scan\(tool="([^"]+)"\)`', bt, text)

    # Call form with a literal target string and possibly more args
    def call_target(m):
        tool, target = m.group(1), m.group(2)
        return f'Bash("{SCAN_BINARIES.get(tool, tool)} {target} ...")'

    text = re.sub(
        r'\bscan\(tool="([^"]+)",\s*target="([^"]+)"[^)]*\)',
        call_target,
        text,
    )

    # Call form with no literal target
    def call_generic(m):
        tool = m.group(1)
        return f'Bash("{SCAN_BINARIES.get(tool, tool)} ...")'

    text = re.sub(r'\bscan\(tool="([^"]+)"[^)]*\)', call_generic, text)

    # Plain prose ellipsis form
    text = re.sub(
        r'\bscan\(tool="([^"]+)",\s*\.\.\.\)',
        lambda m: f'Bash("{SCAN_BINARIES.get(m.group(1), m.group(1))} ...")',
        text,
    )
    return text


# ── http(action="request"|"save_poc", ...) ────────────────────────────────────


def replace_http(text: str) -> str:
    # Backtick prose
    text = re.sub(
        r'`http\(action="request"[^`]*\)`',
        '`Bash("curl ...")`',
        text,
    )
    text = re.sub(
        r'`http\(action="save_poc"[^`]*\)`',
        '`Write("pocs/<title>.http", ...)`',
        text,
    )

    # Call form
    text = re.sub(
        r'\bhttp\(action="request"[^)]*\)',
        'Bash("curl ...")',
        text,
    )
    text = re.sub(
        r'\bhttp\(action="save_poc"[^)]*\)',
        'Write("pocs/<title>.http", ...)',
        text,
    )

    # Old prose names that survived from the 8-tool API (e.g. http_request)
    text = re.sub(r'`http_request`', '`Bash("curl ...")`', text)
    text = re.sub(r'\bhttp_request\b', 'Bash("curl ...")', text)
    text = re.sub(r'`save_poc`', '`Write("pocs/<title>.http", ...)`', text)
    text = re.sub(r'\bsave_poc\b', 'Write("pocs/<title>.http", ...)', text)
    return text


# ── report(action="X", data={...}) ────────────────────────────────────────────

REPORT_REPLACEMENTS = {
    "finding": '# Append finding to pentest/findings.json (Read → mutate JSON array → Write)',
    "note": 'Bash("echo \'<message>\' >> pentest/notes.log")',
    "diagram": 'Write("pentest/diagrams/<title>.mmd", "<mermaid>")',
    "coverage": '# Upsert into pentest/coverage.json (Read → update entry by cell_id/path+method → Write)',
}


def replace_report(text: str) -> str:
    # Strip dashboard entirely — paragraph-level cleanup happens later
    text = re.sub(
        r'`report\(action="dashboard"[^`]*\)`',
        '`# (no dashboard — see pentest/findings.json directly)`',
        text,
    )
    text = re.sub(
        r'\breport\(action="dashboard"[^)]*\)',
        '# (no dashboard — see pentest/findings.json directly)',
        text,
    )

    # Concrete actions
    for action, native in REPORT_REPLACEMENTS.items():
        # Backtick form `report(action="finding", data={...})` etc.
        text = re.sub(
            rf'`report\(action="{action}"[^`]*\)`',
            f'`{native}`',
            text,
        )
        # Call form
        text = re.sub(
            rf'\breport\(action="{action}"[^)]*\)',
            native,
            text,
        )

    # Old prose names that may survive from the 8-tool API
    text = re.sub(r'`report_finding`', '`# Append finding to pentest/findings.json`', text)
    text = re.sub(r'\breport_finding\b', '# Append finding to pentest/findings.json', text)
    text = re.sub(r'`report_diagram`', '`Write("pentest/diagrams/<title>.mmd", ...)`', text)
    text = re.sub(r'\breport_diagram\b', 'Write("pentest/diagrams/<title>.mmd", ...)', text)
    text = re.sub(r'`log_note`', '`Bash("echo ... >> pentest/notes.log")`', text)
    text = re.sub(r'\blog_note\b', 'Bash("echo ... >> pentest/notes.log")', text)
    text = re.sub(r'`start_dashboard`', '`# (no dashboard)`', text)
    text = re.sub(r'\bstart_dashboard\b', '# (no dashboard)', text)
    return text


# ── session(action="X", ...) ──────────────────────────────────────────────────

SESSION_REPLACEMENTS = {
    "start": 'Bash("mkdir -p pentest/{pocs,diagrams}") + Write("pentest/scope.json", {...})',
    "complete": 'Write("pentest/summary.md", "<summary>")',
    "recovery": '# Recover state: Read("pentest/coverage.json"), Read("pentest/findings.json"), Bash("tail -200 pentest/notes.log")',
    "set_skill": 'Bash("echo \'SKILL_CHAIN <skill> <reason> chained_from=<this>\' >> pentest/skill_chain.log")',
    "set_codebase": 'Write("pentest/codebase.json", {...})',
    "status": '# Read pentest/scope.json + tail pentest/notes.log',
}

# These three are no-ops in native mode (no Docker)
SESSION_DROPPED = {"start_kali", "stop_kali", "pull_images"}


def replace_session(text: str) -> str:
    # Drop Docker-only actions entirely
    for action in SESSION_DROPPED:
        text = re.sub(
            rf'`session\(action="{action}"\)`',
            '`# (no-op — tools native on Kali)`',
            text,
        )
        text = re.sub(
            rf'\bsession\(action="{action}"\)',
            '# (no-op — tools native on Kali)',
            text,
        )

    # Concrete actions
    for action, native in SESSION_REPLACEMENTS.items():
        text = re.sub(
            rf'`session\(action="{action}"[^`]*\)`',
            f'`{native}`',
            text,
        )
        text = re.sub(
            rf'\bsession\(action="{action}"[^)]*\)',
            native,
            text,
        )

    # Old prose names (8-tool API leftovers)
    text = re.sub(r'`start_scan`', '`# Init pentest/ + Write pentest/scope.json`', text)
    text = re.sub(r'\bstart_scan\b', '# Init pentest/ + Write pentest/scope.json', text)
    text = re.sub(r'`complete_scan`', '`Write("pentest/summary.md", ...)`', text)
    text = re.sub(r'\bcomplete_scan\b', 'Write("pentest/summary.md", ...)', text)
    text = re.sub(r'`start_kali`', '`# (no-op — tools native on Kali)`', text)
    text = re.sub(r'(?<!action=")\bstart_kali\b', '# (no-op — tools native on Kali)', text)
    text = re.sub(r'`stop_kali`', '`# (no-op — tools native on Kali)`', text)
    text = re.sub(r'(?<!action=")\bstop_kali\b', '# (no-op — tools native on Kali)', text)
    text = re.sub(r'`pull_images`', '`# (no-op — tools native on Kali)`', text)
    text = re.sub(r'(?<!action=")\bpull_images\b', '# (no-op — tools native on Kali)', text)
    return text


# ── 2. Tools-available table replacement ──────────────────────────────────────

OLD_TABLE_PATTERN = re.compile(
    r"(\| Tool \| Use for \|\n\|[-| ]+\|\n)"
    r"((?:\|[^\n]+\|\n)+)",
    re.MULTILINE,
)

NEW_TABLE = (
    "| Tool | Use for |\n"
    "|------|---------|\n"
    "| `Bash(\"<cmd>\")` | Any Kali tool — nmap, naabu, httpx, nuclei, ffuf, katana, subfinder, semgrep, trufflehog, sqlmap, nikto, hydra, gobuster, testssl, enum4linux-ng, theHarvester, dnsrecon, certipy, nxc, impacket, searchsploit, … (everything is on PATH on Kali). Also `curl` for raw HTTP probes. |\n"
    "| `Write(\"pocs/<name>.http\", ...)` | Save a confirmed exploit as a raw `.http` file under `pocs/` (paste-ready for Burp Repeater). |\n"
    "| `Write(\"pentest/diagrams/<name>.mmd\", ...)` | Save a Mermaid architecture/network diagram. |\n"
    "| `Read` + `Write` `pentest/findings.json` | Append a confirmed vulnerability (with evidence) to `pentest/findings.json` — read, mutate the JSON array, write back. |\n"
    "| `Read` + `Write` `pentest/coverage.json` | Upsert an endpoint/test cell in the coverage matrix. |\n"
    "| `Bash(\"echo ... >> pentest/notes.log\")` | Append a reasoning note or decision to the running session log. |\n"
    "| `Bash(\"tmux new-session ...\")` + `tmux send-keys` / `tmux capture-pane` | Drive interactive tools that need a live PTY — msfconsole, evil-winrm, responder, listeners. |\n"
)


def replace_tools_table(text: str) -> str:
    # Trigger when the table is *clearly* the old MCP "Tools available" table:
    # it contains either old-API markers OR has the post-rewrite stigmata of
    # being a converted MCP table — `# (no-op` rows from session_kali drops,
    # the empty-dashboard row, etc. We avoid touching unrelated tables that
    # happen to share the `| Tool | Use for |` header by also requiring the
    # row count to be >= 6 (real MCP tables have 10+ rows).
    old_markers = [
        "kali(command=", "scan(tool=", 'http(action="request"',
        'http(action="save_poc"', 'report(action="', 'session(action="',
        "kali_exec", "run_nmap", "report_finding", "start_scan",
    ]
    post_rewrite_markers = [
        '`# (no-op — tools native on Kali)`',
        '`# (no dashboard — see pentest/findings.json directly)`',
    ]
    match = OLD_TABLE_PATTERN.search(text)
    if not match:
        return text
    table_body = match.group(2)
    row_count = table_body.count('|\n')
    if row_count < 6:
        return text
    if not any(m in table_body for m in old_markers + post_rewrite_markers):
        return text
    return text[: match.start()] + NEW_TABLE + text[match.end():]


# ── 3. Dual-mode chain blocks → single Skill(...) call ────────────────────────

# 3-line block:
#   <indent># Claude Code: skill: "X", args: "..."
#   <indent># READ THIS FILE NOW (opencode / other clients): cat ~/.config/opencode/commands/X.md — then follow the workflow in that file
#   <indent>Invoke /X: ...

TRIPLE_BLOCK = re.compile(
    r'^(?P<indent>[ \t]*)# Claude Code: skill: "(?P<name>[^"]+)", args: "(?P<args>[^"]*)"\n'
    r'(?P=indent)# READ THIS FILE NOW \(opencode / other clients\):[^\n]*\n'
    r'(?P=indent)Invoke /[^:\n]+:[^\n]*',
    re.MULTILINE,
)


def replace_triple_block(text: str) -> str:
    def repl(m):
        indent, name, args = m.group('indent'), m.group('name'), m.group('args')
        # escape any embedded double-quotes
        safe_args = args.replace('"', '\\"')
        return f'{indent}Skill(skill="{name}", args="{safe_args}")'
    return TRIPLE_BLOCK.sub(repl, text)


# 2-line block (Claude Code header followed by READ-THIS-FILE-NOW, no
# trailing Invoke line — sometimes appears in older blocks).

DOUBLE_BLOCK = re.compile(
    r'^(?P<indent>[ \t]*)# Claude Code: skill: "(?P<name>[^"]+)", args: "(?P<args>[^"]*)"\n'
    r'(?P=indent)# READ THIS FILE NOW \(opencode / other clients\):[^\n]*',
    re.MULTILINE,
)


def replace_double_block(text: str) -> str:
    def repl(m):
        indent, name, args = m.group('indent'), m.group('name'), m.group('args')
        safe_args = args.replace('"', '\\"')
        return f'{indent}Skill(skill="{name}", args="{safe_args}")'
    return DOUBLE_BLOCK.sub(repl, text)


# Older single-line variant from migrate_api.py output:
#   skill: "X" / args: "..."  (two adjacent indented lines)
SKILL_BLOCK_PATTERN = re.compile(
    r'^(?P<indent>[ \t]*)skill: "(?P<name>[^"]+)"\n'
    r'(?P=indent)args: "(?P<args>[^"]*)"',
    re.MULTILINE,
)


def replace_skill_blocks(text: str) -> str:
    def repl(m):
        indent, name, args = m.group('indent'), m.group('name'), m.group('args')
        safe_args = args.replace('"', '\\"')
        return f'{indent}Skill(skill="{name}", args="{safe_args}")'
    return SKILL_BLOCK_PATTERN.sub(repl, text)


# Stray standalone `Invoke /X: ...` lines (left over after triple-block kill)
# Only kill them when they immediately follow a Skill(...) line we just emitted.
INVOKE_AFTER_SKILL = re.compile(
    r'(^[ \t]*Skill\(skill="[^"]+", args="[^"]*"\)\n)'
    r'(^[ \t]*Invoke /[^\n]+\n)',
    re.MULTILINE,
)


def drop_redundant_invoke(text: str) -> str:
    return INVOKE_AFTER_SKILL.sub(r'\1', text)


# ── 4. Chain-commitments tables: drop the opencode column ─────────────────────
#
# Pattern: a markdown table where one column header is "opencode" (or contains
# `~/.config/opencode`) — strip that column from every row including the header
# and the separator. We detect by scanning each table block.

TABLE_BLOCK = re.compile(
    r'(^\|[^\n]*\|\n)'        # header row
    r'(^\|[-:|\s]+\|\n)'       # separator row
    r'((?:^\|[^\n]*\|\n)+)',   # data rows
    re.MULTILINE,
)


def strip_opencode_column(text: str) -> str:
    def process(m):
        header, sep, body = m.group(1), m.group(2), m.group(3)
        # only act on tables that mention opencode
        if 'opencode' not in (header + body).lower() and '~/.config/opencode' not in body:
            return m.group(0)

        def split_row(row):
            # markdown rows start and end with |. Strip those, then split.
            inner = row.strip().strip('|')
            return [c.strip() for c in inner.split('|')]

        def join_row(cells):
            return '| ' + ' | '.join(cells) + ' |\n'

        h_cells = split_row(header)
        # find column index whose header is "opencode" (case-insensitive) or
        # contains the path
        drop_idx = None
        for i, cell in enumerate(h_cells):
            if cell.lower() == 'opencode' or '~/.config/opencode' in cell:
                drop_idx = i
                break
        if drop_idx is None:
            # fall back: detect by data cells
            for row in body.strip().split('\n'):
                cells = split_row(row)
                for i, cell in enumerate(cells):
                    if '~/.config/opencode' in cell:
                        drop_idx = i
                        break
                if drop_idx is not None:
                    break
        if drop_idx is None:
            return m.group(0)

        def drop(cells):
            return [c for i, c in enumerate(cells) if i != drop_idx]

        new_header = join_row(drop(h_cells))
        # rebuild separator with right number of dashes
        n = len(h_cells) - 1
        new_sep = '|' + '|'.join(['-' * 6] * n) + '|\n'
        new_body = ''.join(join_row(drop(split_row(r))) for r in body.strip().split('\n'))
        return new_header + new_sep + new_body

    return TABLE_BLOCK.sub(process, text)


# ── 5. Misc references to the old opencode/Docker setup ──────────────────────


def replace_misc(text: str) -> str:
    # Path: ~/.config/opencode/commands/X.md → ~/.claude/skills/X/SKILL.md
    text = re.sub(
        r'~/\.config/opencode/commands/([a-z0-9-]+)\.md',
        r'~/.claude/skills/\1/SKILL.md',
        text,
    )
    # "READ THIS FILE NOW (opencode / other clients):" lines that escaped
    # the dual-mode block matcher (e.g. when the trailing Invoke is missing)
    text = re.sub(
        r'^[ \t]*# READ THIS FILE NOW \(opencode / other clients\):[^\n]*\n',
        '',
        text,
        flags=re.MULTILINE,
    )
    # Burp routing references
    text = re.sub(
        r'Set `poc=True` for confirmed exploits to route through Burp HTTP History',
        'For confirmed exploits, also save a `.http` file under `pocs/` for Burp Repeater',
        text,
    )
    text = re.sub(
        r'\. Set `poc=True` for confirmed exploits[^.]*\.',
        '. Save confirmed exploits as `.http` files under `pocs/` for Burp Repeater.',
        text,
    )
    # Drop dashboard URL references
    text = re.sub(
        r'\bgives you a live URL to watch findings roll in\b',
        'creates the pentest/ artifact directory',
        text,
    )
    text = re.sub(r'localhost:5000', 'pentest/findings.json', text)
    return text


# ── 6. Footer "How to chain" / "How:" line ────────────────────────────────────

OLD_HOW_PATTERNS = [
    re.compile(
        r'\*\*How to chain:\*\*[^\n]*\n'
        r'- \*\*Claude Code\*\*:[^\n]*\n'
        r'- \*\*opencode[^\n]*\n'
        r'(?:- [^\n]*\n)?',
        re.MULTILINE,
    ),
    re.compile(
        r'\*\*How:\*\* Use the Skill tool \(e\.g\. `skill: "[^"]+", args: "[^"]*"`\)[^\n]*'
    ),
]

NEW_HOW = (
    '**How to chain:** At the trigger point, invoke the sub-skill with '
    '`Skill(skill="<name>", args="<arguments>")`, then resume this skill '
    'after it returns.\n'
)


def replace_how_line(text: str) -> str:
    for pat in OLD_HOW_PATTERNS:
        text = pat.sub(NEW_HOW, text)
    return text


# ── 7. Syntax-line under chain-commitments table ──────────────────────────────


def replace_syntax_line(text: str) -> str:
    text = re.sub(
        r'\*\*Syntax — Claude Code:\*\*[^\n]*\n'
        r'\*\*Syntax — opencode:\*\*[^\n]*\n',
        '**Syntax:** `Skill(skill="<name>", args="<arguments>")`\n',
        text,
    )
    return text


# ── Driver ─────────────────────────────────────────────────────────────────────


def migrate_file(path: Path) -> bool:
    original = path.read_text(encoding='utf-8')
    text = original

    # Order: tool calls first (so the tools table rewrite below sees clean text
    # and only the table itself contains old markers).
    text = replace_kali(text)
    text = replace_scan(text)
    text = replace_http(text)
    text = replace_report(text)
    text = replace_session(text)

    # Tools table — runs AFTER the call rewrites. The replacer's own marker
    # check now also looks for post-rewrite stigmata (`# (no-op ...)` rows
    # from session_kali drops) so it fires correctly on already-rewritten
    # cells.
    text = replace_tools_table(text)

    # Structural rewrites
    text = replace_triple_block(text)
    text = replace_double_block(text)
    text = replace_skill_blocks(text)
    text = drop_redundant_invoke(text)
    text = strip_opencode_column(text)
    text = replace_syntax_line(text)
    text = replace_how_line(text)
    text = replace_misc(text)

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
    changed = 0
    skipped = 0
    for p in md_files:
        if p.name == 'README.md':
            continue
        if migrate_file(p):
            changed += 1
        else:
            skipped += 1
    print(f"\nDone. {'Would update' if DRY_RUN else 'Updated'} {changed} file(s), {skipped} already clean.")


if __name__ == '__main__':
    main()
