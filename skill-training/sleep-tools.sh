#!/usr/bin/env bash
# sleep-tools.sh — like sleep.sh, but runs each rollout with TOOLS ENABLED:
# built-in Bash/Read/Edit + the reused agent-smith `pentest-agent` MCP server
# (session/http/kali/scan/report). Use this for AGENTIC skills whose value comes
# from calling tools (threat-modeling, api-security, …) rather than pure text.
#
# Everything else matches sleep.sh: isolated HOME (repo-local config/state),
# validation gate on, evolve_memory off, stage → review → adopt.
#
#   ./skill-training/sleep-tools.sh run --target-skill-path appsec/threat-modeling/SKILL.md \
#       --tasks-file skill-training/tasks/threat-modeling.json --progress
#
# Requires ANTHROPIC_API_KEY in skill-training/.env. Tier-1 MCP tools
# (session/report/http-local) need no Docker; scan()/kali() need a target lab.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
SLEEP_HOME="$HERE/.sleep-home"
PY="$HERE/.venv/bin/python"

[[ -x "$PY" ]] || { echo "skillopt not installed — run: $HERE/setup.sh" >&2; exit 1; }
if [[ -f "$HERE/.env" ]]; then set -a; . "$HERE/.env"; set +a; fi

mkdir -p "$SLEEP_HOME/.skillopt-sleep" "$SLEEP_HOME/.claude/projects"
cp -f "$HERE/config/skillopt-sleep.config.json" "$SLEEP_HOME/.skillopt-sleep/config.json"

# agent-smith supplies the pentest-agent MCP server; override the path if needed.
: "${AGENT_SMITH_DIR:=/Users/gibson/Desktop/development/agent-smith}"
export AGENT_SMITH_DIR
# Serial rollouts: the MCP server writes shared state (findings.json/session.json)
# under the agent-smith repo, so concurrent rollouts would race.
export SKILLOPT_SLEEP_WORKERS="${SKILLOPT_SLEEP_WORKERS:-1}"

cd "$REPO"
exec env HOME="$SLEEP_HOME" "$PY" "$HERE/tools_runner.py" "$@" --backend claude --project "$REPO"
