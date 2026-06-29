#!/usr/bin/env bash
#
# Regenerate per-skill SkillSpector baselines.
#
# A baseline records the findings that have been REVIEWED and accepted as false
# positives (this repo's skills intentionally contain offensive tooling, payloads
# and recon references). The CI workflow passes each skill's baseline to
# `skillspector scan --baseline`, so only NEW, un-accepted findings are reported.
#
# Baselines live centrally under .github/workflows/skillspector/FP/<skill>.yaml
# (NOT inside the skill folders). Run this after intentionally adding content that
# SkillSpector flags, then review the diff before committing. To re-surface a
# specific finding, delete its entry from that skill's FP file instead.
#
# Usage: scripts/gen-baselines.sh
#
set -uo pipefail

REASON="Reviewed: intended security-skill content (offensive tooling, payloads, recon). Accepted false positive."
SS_REF="git+https://github.com/NVIDIA/skillspector.git"
FP_DIR=".github/workflows/skillspector/FP"

mkdir -p "$FP_DIR"
created=0
skipped=0
while IFS= read -r skill; do
  name=$(basename "$skill")
  out="$FP_DIR/$name.yaml"
  # </dev/null: skillspector otherwise consumes this loop's stdin (the find list).
  uvx --from "$SS_REF" skillspector baseline "$skill" --no-llm \
    -o "$out" --reason "$REASON" </dev/null >/dev/null 2>&1

  if [ -f "$out" ] && grep -q "rule_id" "$out"; then
    n=$(grep -c "rule_id" "$out")
    printf '  %-26s %s findings accepted\n' "$name" "$n"
    created=$((created + 1))
  else
    # No findings: don't commit an empty baseline.
    rm -f "$out"
    skipped=$((skipped + 1))
  fi
done < <(find . -name SKILL.md -not -path './.git/*' -printf '%h\n' | sort -u)

echo "---"
echo "baselines: $created written, $skipped skills clean"
