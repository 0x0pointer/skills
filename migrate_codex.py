#!/usr/bin/env python3
"""
migrate_codex.py — build a Codex-CLI-compatible mirror of this Claude-Code
skills repo into a parallel tree at `codex-build/`. The source tree is not
modified — both runtimes can coexist:

    ln -s "$PWD"             ~/.claude/skills    # Claude Code
    ln -s "$PWD/codex-build" ~/.codex/skills     # Codex CLI

Run from the skills repo root:
    uv run python migrate_codex.py             # build codex-build/
    uv run python migrate_codex.py --dry-run   # list what would be written
    uv run python migrate_codex.py --verify    # post-build sanity check
    uv run python migrate_codex.py --out-dir DIR

The script is idempotent: re-running overwrites codex-build/ with the same
content. It mirrors `migrate_native.py`'s style — manual arg parsing, regex
transforms, one driver function.
"""

import re
import shutil
import sys
from pathlib import Path

DRY_RUN = "--dry-run" in sys.argv
VERIFY = "--verify" in sys.argv
OUT_DIR_NAME = "codex-build"
for i, a in enumerate(sys.argv):
    if a == "--out-dir" and i + 1 < len(sys.argv):
        OUT_DIR_NAME = sys.argv[i + 1]


# ── 1. Skill() call rewrites ──────────────────────────────────────────────────
#
# Five forms appear across the corpus. Apply specific → general so a broader
# regex doesn't gobble a more specific match.


def replace_skill_legacy_form(text: str) -> str:
    # pentester/SKILL.md:450 — only occurrence in the corpus.
    return re.sub(
        r'use the Skill tool — `skill: "([^"]+)", args: "([^"]*)"`',
        r'invoke the skill — `/\1 \2`',
        text,
    )


def replace_skill_syntax_meta(text: str) -> str:
    # The meta-syntax lines that document the calling convention.
    text = re.sub(
        r'\*\*Syntax:\*\*\s+`Skill\(skill="<name>", args="<arguments>"\)`',
        r'**Syntax:** `Invoke /<name> <arguments>`',
        text,
    )
    text = re.sub(
        r'### `Skill\(skill="<name>", args="\.\.\."\)`',
        r'### `Invoke /<name> <args>`',
        text,
    )
    return text


def replace_skill_bare_in_block(text: str) -> str:
    # Multi-line bare form inside code fences: indented `Skill(...)` on its
    # own line. Must run before the backticked patterns (which won't match
    # bare forms anyway, but order keeps intent clear).
    return re.sub(
        r'^(\s*)Skill\(skill="([^"]+)",\s*args="([^"]*)"\)\s*$',
        r'\1Invoke /\2 \3',
        text,
        flags=re.MULTILINE,
    )


def replace_skill_with_args_backtick(text: str) -> str:
    # `Skill(skill="X", args="Y")` — single-line backticked, with args.
    return re.sub(
        r'`Skill\(skill="([^"]+)",\s*args="([^"]*)"\)`',
        r'`Invoke /\1 \2`',
        text,
    )


def replace_skill_no_args_backtick(text: str) -> str:
    # `Skill(skill="X")` — single-line backticked, no args. Broadest; runs last.
    return re.sub(
        r'`Skill\(skill="([^"]+)"\)`',
        r'`Invoke /\1`',
        text,
    )


# ── 2. Path rewrites ──────────────────────────────────────────────────────────


def replace_paths(text: str) -> str:
    text = re.sub(r'~/\.claude/lessons/', '~/.codex/lessons/', text)
    text = re.sub(r'~/\.claude/skills/', '~/.codex/skills/', text)
    return text


# ── 3. Doc-name and structural rewrites ───────────────────────────────────────


def replace_table_column_header(text: str) -> str:
    return re.sub(r'\|\s*Claude Code\s*\|', '| Codex |', text)


def replace_claude_md_refs(text: str) -> str:
    return re.sub(r'\bCLAUDE\.md\b', 'AGENTS.md', text)


def replace_migrate_script_refs(text: str) -> str:
    return re.sub(r'\bmigrate_native\.py\b', 'migrate_codex.py', text)


# ── 4. Selective "Claude Code" → "Codex" rewrites ─────────────────────────────
#
# Narrow substring whitelist. Avoids rewriting fork-rationale paragraphs in
# CLAUDE.md L5 and README.md L5, which describe project lineage.

CLAUDE_CODE_REWRITES = [
    ("natively in Claude Code on a Kali host",
     "natively in Codex on a Kali host"),
    ("The skills speak Claude Code's standard tools.",
     "The skills speak Codex's standard tools."),
    ("# Install Claude Code on the same host and configure your Anthropic API key.",
     "# Install Codex on the same host and configure your OpenAI API key."),
    ("# Drop the skills into Claude Code's skills directory.",
     "# Drop the skills into Codex's skills directory."),
    ("Claude Code picks them up automatically.",
     "Codex picks them up automatically."),
    ("They just start Claude Code from a parent directory where engagements live",
     "They just start Codex from a parent directory where engagements live"),
    ("they just start Claude Code from a parent directory where engagements live",
     "they just start Codex from a parent directory where engagements live"),
    ("Inside Claude Code, the user will say something like",
     "Inside Codex, the user will say something like"),
    ("**Multi-client support (OpenCode / any MCP client)** — gone. Claude Code only.",
     "**Multi-client support** — gone. Codex only."),
    ("Claude Code is sequential. Tool calls do not run in parallel.",
     "Codex is sequential. Tool calls do not run in parallel."),
    ("- **Claude Code**: invoke the skill —",
     "- **Codex**: invoke the skill —"),
]


def replace_claude_code_selective(text: str) -> str:
    for old, new in CLAUDE_CODE_REWRITES:
        text = text.replace(old, new)
    return text


# ── 5. Cleanup: drop opencode leftover ────────────────────────────────────────


def drop_opencode_line(text: str) -> str:
    # pentester/SKILL.md:451 — the "opencode / other clients" recovery hint.
    # In the Codex tree, Codex IS the other client, and the line above it
    # (rewritten by replace_skill_legacy_form + replace_claude_code_selective)
    # already covers the recovery instruction.
    return re.sub(
        r'^[ \t]*-[ \t]+\*\*opencode / other clients\*\*:.*\n',
        '',
        text,
        flags=re.MULTILINE,
    )


# ── Pipelines ─────────────────────────────────────────────────────────────────


def transform_md(text: str) -> str:
    text = replace_skill_legacy_form(text)
    text = replace_skill_syntax_meta(text)
    text = replace_skill_bare_in_block(text)
    text = replace_skill_with_args_backtick(text)
    text = replace_skill_no_args_backtick(text)
    text = replace_paths(text)
    text = replace_table_column_header(text)
    text = replace_claude_md_refs(text)
    text = replace_claude_code_selective(text)
    text = replace_migrate_script_refs(text)
    text = drop_opencode_line(text)
    return text


def transform_py(text: str) -> str:
    # Python scripts (refresh.py, verify.py, mine.py) contain ~/.claude/ paths
    # in docstrings and error messages. Rewrite paths only — leave code alone.
    return replace_paths(text)


# ── AGENTS.md generation ──────────────────────────────────────────────────────

CODEX_HEADER = """<!-- Codex compatibility header — generated by migrate_codex.py -->

> **Codex CLI compatibility.** This file is the Codex equivalent of
> `CLAUDE.md` in the source repo. Codex discovers skills under
> `~/.codex/skills/**/SKILL.md`. Implicit invocation is on by default — the
> `description:` field in each SKILL.md's YAML frontmatter is the trigger
> surface, so write descriptions that name the conditions a skill applies to.
>
> **Skill chaining.** Codex sub-agents run at `agents.max_depth=1` by default,
> so the nested skill-invocation tool used in Claude Code does not exist here.
> The rewritten skills tell you to invoke `/skill-name <args>` as a textual
> handoff — Codex's implicit invocation picks it up, or the user types the
> slash command directly. The `skill_chain` event-logging boilerplate still
> applies; it is the audit trail.
>
> **tmux-driven workflows.** Codex sandbox modes restrict PTY access. For
> tmux-driven workflows (msfconsole, evil-winrm, responder, interactive
> listeners), run Codex in Full Auto mode.
>
> **Source of truth.** This file is generated. Do not edit by hand — edit
> `CLAUDE.md` in the source repo, then re-run `migrate_codex.py`.

---

"""


def build_agents_md(src_root: Path, out_dir: Path) -> int:
    src = src_root / "CLAUDE.md"
    text = transform_md(src.read_text(encoding='utf-8'))
    full = CODEX_HEADER + text
    dst = out_dir / "AGENTS.md"
    if not DRY_RUN:
        dst.write_text(full, encoding='utf-8')
    print(f"{'[dry-run] would write' if DRY_RUN else 'wrote'}: AGENTS.md ({len(full)} bytes)")
    return len(full)


# ── Driver ────────────────────────────────────────────────────────────────────

# Files that should never appear in codex-build/
SKIP_FILES = {
    "README.md",          # mirrors migrate_native.py's skip
    "CLAUDE.md",          # replaced by generated AGENTS.md
    "migrate_codex.py",   # this script
    "migrate_native.py",  # source-tree-only utility
}

SKIP_DIRS = {".git", ".github", ".claude", "__pycache__"}


def iter_source_files(src_root: Path, out_dir: Path):
    """Yield (src_path, kind) pairs. kind is 'md' or 'other'."""
    for p in src_root.rglob('*'):
        if not p.is_file():
            continue
        rel = p.relative_to(src_root)
        # Skip dot/build dirs
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        # Skip anything inside the chosen out_dir
        if rel.parts and rel.parts[0] == OUT_DIR_NAME:
            continue
        if p.name in SKIP_FILES:
            continue
        yield p, ('md' if p.suffix == '.md' else 'other')


def write_file(src_path: Path, out_dir: Path, src_root: Path, kind: str) -> bool:
    rel = src_path.relative_to(src_root)
    dst = out_dir / rel
    if kind == 'md':
        new_text = transform_md(src_path.read_text(encoding='utf-8'))
        write_bytes = new_text.encode('utf-8')
    elif src_path.suffix == '.py':
        new_text = transform_py(src_path.read_text(encoding='utf-8'))
        write_bytes = new_text.encode('utf-8')
    else:
        # Binary or non-Python: byte-copy
        write_bytes = src_path.read_bytes()

    if not DRY_RUN:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(write_bytes)
        # Preserve executable bit for shell/py scripts
        shutil.copymode(src_path, dst)

    return True


# ── Verification ──────────────────────────────────────────────────────────────

FORBIDDEN_PATTERNS = [
    (re.compile(r'Skill\(skill='), 'unrewritten Skill() call'),
    (re.compile(r'~/\.claude/skills/'), 'unrewritten ~/.claude/skills/ path'),
    (re.compile(r'~/\.claude/lessons/'), 'unrewritten ~/.claude/lessons/ path'),
    (re.compile(r'\|\s*Claude Code\s*\|'), 'unrewritten chain-table column header'),
]

# Substrings that legitimize a remaining "CLAUDE.md" mention (generation
# headers self-reference the upstream file).
CLAUDE_MD_ALLOW_CONTEXTS = [
    "edit `CLAUDE.md`",
    "generated by migrate_codex.py",
    "equivalent of `CLAUDE.md`",
    "equivalent of\n> `CLAUDE.md`",
]


def verify_output(out_dir: Path) -> int:
    if not out_dir.exists():
        print(f"VERIFY FAIL: {out_dir} does not exist. Run without --verify first.")
        return 1

    issues = []
    agents_md = out_dir / "AGENTS.md"
    if not agents_md.exists():
        issues.append((agents_md, 0, "AGENTS.md missing"))
    else:
        size = agents_md.stat().st_size
        if size >= 32768:
            issues.append((agents_md, 0, f"AGENTS.md is {size} bytes (Codex limit 32768)"))

    for p in sorted(out_dir.rglob('*.md')):
        text = p.read_text(encoding='utf-8')
        full_text_lower = text  # for multi-line context checks
        for i, line in enumerate(text.splitlines(), 1):
            for rx, desc in FORBIDDEN_PATTERNS:
                if rx.search(line):
                    issues.append((p, i, desc))
            if re.search(r'\bCLAUDE\.md\b', line):
                # Allow if the line itself or the file's allow-list context matches
                if not any(ctx in line for ctx in CLAUDE_MD_ALLOW_CONTEXTS) and \
                   not any(ctx in full_text_lower for ctx in CLAUDE_MD_ALLOW_CONTEXTS):
                    issues.append((p, i, 'unrewritten CLAUDE.md reference'))

    if not issues:
        print(f"VERIFY PASS: {out_dir} is Codex-clean.")
        return 0

    for path, lineno, desc in issues:
        try:
            rel = path.relative_to(Path.cwd())
        except ValueError:
            rel = path
        loc = f"{rel}:{lineno}" if lineno else str(rel)
        print(f"{loc}: {desc}")
    print(f"\nVERIFY FAIL: {len(issues)} issue(s).")
    return 1


# ── main ──────────────────────────────────────────────────────────────────────


def main() -> int:
    src_root = Path(__file__).resolve().parent
    out_dir = (src_root / OUT_DIR_NAME).resolve()

    if VERIFY:
        return verify_output(out_dir)

    if not DRY_RUN:
        out_dir.mkdir(exist_ok=True)

    md_count = 0
    other_count = 0
    for src_path, kind in iter_source_files(src_root, out_dir):
        rel = src_path.relative_to(src_root)
        write_file(src_path, out_dir, src_root, kind)
        if kind == 'md':
            md_count += 1
        else:
            other_count += 1
        if DRY_RUN:
            print(f"[dry-run] would write: {OUT_DIR_NAME}/{rel}")

    agents_size = build_agents_md(src_root, out_dir)

    print(f"\nDone. {'Would write' if DRY_RUN else 'Wrote'} {md_count} markdown file(s) + "
          f"{other_count} other file(s) + AGENTS.md ({agents_size} bytes).")
    print(f"Output: {out_dir}")

    if agents_size >= 32768:
        print(f"WARNING: AGENTS.md is {agents_size} bytes — Codex limit is 32 KiB.")
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
