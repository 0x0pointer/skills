#!/usr/bin/env bash
# One-time bootstrap for the SkillOpt-Sleep toolchain.
# Creates a self-contained venv under skill-training/.venv and installs the
# pinned `skillopt` package (gives the `skillopt-sleep` CLI). No global installs.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$HERE/.venv"
PY="${PYTHON:-python3}"

echo "==> Creating venv: $VENV"
"$PY" -m venv "$VENV"
"$VENV/bin/python" -m pip install -q --upgrade pip

echo "==> Installing: $(grep -v '^#' "$HERE/requirements.txt" | tr -d '[:space:]')"
"$VENV/bin/pip" install -q -r "$HERE/requirements.txt"

"$VENV/bin/skillopt-sleep" --help >/dev/null
echo "==> OK: skillopt-sleep installed."

# Seed a git-ignored .env for the API key (needed only for --backend claude).
if [[ ! -f "$HERE/.env" ]]; then
  cp "$HERE/.env.example" "$HERE/.env"
  echo "==> Created skill-training/.env — paste your ANTHROPIC_API_KEY there to go live."
fi
cat <<EOF

Verify with the free mock backend (no API cost):

  ./skill-training/sleep.sh dry-run --backend mock \\
    --target-skill-path reporting/gh-export/SKILL.md \\
    --tasks-file skill-training/tasks/gh-export.json --progress

See skill-training/README.md for the full workflow and going live with --backend claude.
EOF
