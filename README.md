# skills

A library of offensive-security skills for **Claude Code** and **Codex CLI** on Kali.

> 🍴 **Fork of [`0x0pointer/skills`](https://github.com/0x0pointer/skills).** The upstream project routes everything through an MCP server ([`0x0pointer/agent-smith`](https://github.com/0x0pointer/agent-smith)) with a Docker bundle. This fork rewrites every skill to run **natively on Kali** using the agent's built-in `Bash`, `Read`, `Write`, and `Edit` tools — no MCP server, no Docker.

> ⚠️ **Authorized testing only.** Use these skills against systems you own or have explicit written permission to test.

## Setup

### Claude Code

```bash
git clone <this-fork> ~/skills
ln -s ~/skills ~/.claude/skills
```

### Codex CLI

```bash
git clone <this-fork> ~/skills
cd ~/skills && uv run python migrate_codex.py    # builds codex-build/
ln -s ~/skills/codex-build ~/.codex/skills
```

Both symlinks can coexist on the same machine. The source tree is canonically Claude-Code-native; `migrate_codex.py` produces a parallel Codex-shaped mirror under `codex-build/` (regenerated, not committed). See [migrate_codex.py](migrate_codex.py) for what it rewrites — chiefly: `Skill(...)` chain calls → `/skill-name` textual handoffs, `~/.claude/` → `~/.codex/` paths, `CLAUDE.md` → `AGENTS.md`.

Each skill becomes a slash command (`/pentester`, `/web-exploit`, `/api-security`, …). Start the agent from the directory where you want artifacts written, then invoke a skill.

## Requirements

- Kali Linux with the standard offensive toolchain on `PATH` (`kali-linux-default` or `kali-linux-large`)
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) **or** [Codex CLI](https://developers.openai.com/codex/cli) with the matching API key
- [`uv`](https://docs.astral.sh/uv/) — every Python invocation goes through `uv run` / `uvx`
- `tmux` and `jq`

> **Codex tmux note.** Codex sandbox modes restrict PTY access. For tmux-driven workflows (msfconsole, evil-winrm, responder, interactive listeners), run Codex in Full Auto mode.

## Migrating from upstream

If you have a copy of the upstream MCP-based skills, run [migrate_native.py](migrate_native.py) once to rewrite them to native form:

```bash
uv run python migrate_native.py --dry-run   # preview
uv run python migrate_native.py             # apply
```

Both migration scripts (`migrate_native.py`, `migrate_codex.py`) are idempotent. After pulling upstream changes: re-run `migrate_native.py` against the source tree, then `migrate_codex.py` to refresh `codex-build/`.

## License

GNU Affero General Public License v3.0 — see [LICENSE](LICENSE).
