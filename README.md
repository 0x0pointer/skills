# skills

A library of offensive-security skills for Claude Code on Kali.

> 🍴 **Fork of [`0x0pointer/skills`](https://github.com/0x0pointer/skills).** The upstream project routes everything through an MCP server ([`0x0pointer/agent-smith`](https://github.com/0x0pointer/agent-smith)) with a Docker bundle. This fork rewrites every skill to run **natively in Claude Code on Kali** using the built-in `Bash`, `Read`, `Write`, and `Edit` tools — no MCP server, no Docker.

> ⚠️ **Authorized testing only.** Use these skills against systems you own or have explicit written permission to test.

## Setup

```bash
git clone <this-fork> ~/.claude/skills
```

Each skill becomes a slash command (`/pentester`, `/web-exploit`, `/api-security`, …). Start Claude Code from the directory where you want artifacts written, then invoke a skill.

## Requirements

- Kali Linux with the standard offensive toolchain on `PATH` (`kali-linux-default` or `kali-linux-large`)
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) with an Anthropic API key
- [`uv`](https://docs.astral.sh/uv/) — every Python invocation goes through `uv run` / `uvx`
- `tmux` and `jq`

## Migrating from upstream

If you have a copy of the upstream MCP-based skills, run [migrate_native.py](migrate_native.py) once to rewrite them:

```bash
uv run python migrate_native.py --dry-run   # preview
uv run python migrate_native.py             # apply
```

The script is idempotent.

## License

GNU Affero General Public License v3.0 — see [LICENSE](LICENSE).
