#!/usr/bin/env bash
# skill-training/sleep.sh — repo-scoped, fully-isolated wrapper around skillopt-sleep.
#
# Guarantees:
#   * Config + state live under skill-training/.sleep-home — NEVER your real
#     ~/.skillopt-sleep or ~/.claude (HOME is redirected for the child process).
#   * Loads the repo-owned config (validation gate ON, evolve_memory OFF so only
#     the targeted SKILL.md is ever proposed — never a CLAUDE.md).
#   * Always scopes --project to this repo; runs from the repo root so relative
#     --target-skill-path / --tasks-file resolve as you'd expect.
#
# Examples:
#   ./skill-training/sleep.sh dry-run --backend mock \
#       --target-skill-path reporting/gh-export/SKILL.md \
#       --tasks-file skill-training/tasks/gh-export.json --progress
#   ./skill-training/sleep.sh status
#   ./skill-training/sleep.sh adopt        # applies the latest staged proposal (backs up first)
#
# Go live (spends Anthropic API): export ANTHROPIC_API_KEY, then use --backend claude.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
SLEEP_HOME="$HERE/.sleep-home"
BIN="$HERE/.venv/bin/skillopt-sleep"

[[ -x "$BIN" ]] || { echo "skillopt not installed — run: $HERE/setup.sh" >&2; exit 1; }

# Load ANTHROPIC_API_KEY (and friends) from skill-training/.env if present.
# With a key set, the claude backend uses --bare API-key auth, so the isolated
# HOME works without a logged-in CLI. .env is git-ignored — never commit it.
if [[ -f "$HERE/.env" ]]; then set -a; . "$HERE/.env"; set +a; fi

# Redirect HOME so config ($HOME/.skillopt-sleep/config.json) and state are
# repo-local. claude_home defaults to $HOME/.claude (empty here) — harmless
# because we drive tasks via --tasks-file, not transcript harvesting.
mkdir -p "$SLEEP_HOME/.skillopt-sleep" "$SLEEP_HOME/.claude/projects"
cp -f "$HERE/config/skillopt-sleep.config.json" "$SLEEP_HOME/.skillopt-sleep/config.json"

cd "$REPO"
exec env HOME="$SLEEP_HOME" "$BIN" "$@" --project "$REPO"
