# skill-training — improving skills with SkillOpt-Sleep

This directory wires [microsoft/SkillOpt](https://github.com/microsoft/SkillOpt)'s
**Sleep** engine into this repo so we can *iteratively improve our `SKILL.md`
documents from a validation-gated feedback loop* — the way you'd tune a model,
but the "weights" are the skill's prose.

**Mental model:** for a skill, you give it a handful of representative **tasks**
with a **checkable pass/fail signal**. SkillOpt-Sleep runs the skill on those
tasks, proposes small edits to the skill, and **keeps an edit only if it raises
the score on a held-out slice of your tasks**. Proposals are staged for review;
nothing changes until you `adopt`.

---

## Why this is safe for our repo

- **Frontmatter is never touched.** Edits are confined to a marked
  `<!-- SKILLOPT-SLEEP:LEARNED -->` block appended to the skill body. `name`,
  `description`, `argument-hint`, `user-invocable` — and everything you hand-wrote
  — are left byte-for-byte intact. (Verified: an adopted proposal passes
  `validate_skills.py`, our CI frontmatter gate.)
- **Skills only, never CLAUDE.md.** The repo-owned config sets `evolve_memory:false`,
  so a run only ever proposes changes to the single `--target-skill-path` you name.
- **Stage → review → adopt.** Runs stage a proposal + diff + report under
  `.skillopt-sleep/staging/` at the repo root (git-ignored); `adopt` applies it
  and backs up the original first. `--auto-adopt` exists but we don't use it.
- **Fully isolated.** The wrapper redirects `HOME` so config and state live under
  `skill-training/.sleep-home/` — never your real `~/.skillopt-sleep` or `~/.claude`.
- **Validation gate on.** An edit that doesn't improve the held-out score is
  rejected and the skill is unchanged (we saw exactly this with the mock backend).

---

## Setup (once)

```bash
./skill-training/setup.sh
```

Creates `skill-training/.venv` and installs the pinned `skillopt` package (the
`skillopt-sleep` CLI). Both `.venv/` and `.sleep-home/` are git-ignored.

## Verify with the mock backend (no API cost)

```bash
./skill-training/sleep.sh dry-run --backend mock \
  --target-skill-path reporting/gh-export/SKILL.md \
  --tasks-file skill-training/tasks/gh-export.json --progress
```

The `mock` backend is deterministic and free — it proves the pipeline runs, but
it can't actually improve a skill. Real gains require `--backend claude`.

---

## The real work: a tasks file per skill

SkillOpt-Sleep only improves a skill when its tasks carry a **correctness signal**.
Harvesting past Claude Code sessions alone yields "no reference" and flat, no-op
nights. The durable, shareable asset is a **reviewed tasks file** checked into
`skill-training/tasks/<skill>.json` — a small eval set the whole team benefits from.

Start from [`tasks/_TEMPLATE.json`](tasks/_TEMPLATE.json); the worked example is
[`tasks/gh-export.json`](tasks/gh-export.json).

Each task is one `TaskRecord`:

| field | meaning |
|---|---|
| `id` | unique task id |
| `intent` | the prompt the skill runs against |
| `context_excerpt` | minimal, secret-free input the skill needs (e.g. a `findings.json` snippet) |
| `reference_kind` | `rule` (local checks, recommended) · `rubric` (optimizer LLM judges vs `reference`) · `exact` (must equal `reference`) |
| `judge` | for `rule`: `{"kind":"rule","checks":[…]}` |
| `split` | `train` (drives edits) · `val` (the gate scores candidates here) · `test` |

Author **≥3 tasks** so the 0.34 holdout leaves a non-empty `val` split, or set
`split` explicitly (the example pins 3 `train` / 2 `val`).

### Local rule-judge ops (no API)

A `rule` judge passes (`hard=1.0`) iff **all** checks pass; the gate reads the
soft score (fraction passed), so partial progress still registers.

| op | passes when |
|---|---|
| `section_present <heading>` | a markdown heading (or `Name:` label) containing the substring exists |
| `contains <substring>` | case-insensitive substring present |
| `regex <python regex>` | pattern matches the response |
| `min_chars <n>` / `max_chars <n>` | length bound |
| `tool_called <name>` | a tool by that name was invoked |

Example (from `gh-export.json` — checks the produced GitHub issue is well-formed):

```json
{"kind": "rule", "checks": [
  {"op": "contains", "arg": "**Summary:**"},
  {"op": "section_present", "arg": "Steps To Reproduce"},
  {"op": "section_present", "arg": "Remediation"},
  {"op": "regex", "arg": "(?i)severity level:\\*\\*\\s*critical"}
]}
```

> **Invest in the scorer, not the prompts.** SkillOpt's own guidance: *noisy
> scoring kills the optimizer.* A crisp, deterministic rule judge is worth more
> than any number of training tasks.

`reviewed: true` is required at the top of the file — `--backend claude` refuses
to replay an unreviewed tasks file (a privacy guard, since tasks may otherwise
come from real transcripts). Only flip it after you've confirmed no secrets/client
data are embedded.

---

## Go live (spends Anthropic API)

The `claude` backend shells out to the local `claude` CLI. It needs an **API
key**, not a subscription login — the isolated `--bare` auth requires
`ANTHROPIC_API_KEY` (subscription-token auth breaks `--bare`, upstream issue #68).
Put your key in a git-ignored env file (created for you by `setup.sh`):

```bash
# skill-training/.env  (never committed)
ANTHROPIC_API_KEY=sk-ant-...
```

`sleep.sh` auto-loads it. Then:

```bash
# 1. Dry run: see what it would propose, change nothing.
./skill-training/sleep.sh dry-run --backend claude \
  --target-skill-path reporting/gh-export/SKILL.md \
  --tasks-file skill-training/tasks/gh-export.json --progress

# 2. Real run: stage a proposal (still nothing adopted).
./skill-training/sleep.sh run --backend claude \
  --target-skill-path reporting/gh-export/SKILL.md \
  --tasks-file skill-training/tasks/gh-export.json --edit-budget 4

# 3. Review the staged diff.
./skill-training/sleep.sh status

# 4. Adopt (backs up the original first), then re-validate frontmatter.
./skill-training/sleep.sh adopt
python validate_skills.py
```

Always run `python validate_skills.py` after `adopt` — it's the same gate CI runs.

## Improving many skills

One run targets one skill. Loop over the ones you've written tasks for:

```bash
for f in skill-training/tasks/*.json; do
  [ "$(basename "$f")" = "_TEMPLATE.json" ] && continue
  skill="$(python -c "import json,sys; print(json.load(open('$f'))['target_skill_path'])")"
  ./skill-training/sleep.sh run --backend claude \
    --target-skill-path "$skill" --tasks-file "$f" --edit-budget 4
done
./skill-training/sleep.sh status   # review everything staged, then adopt per skill
python validate_skills.py
```

---

## Running skills WITH tools (agentic skills)

The default `sleep.sh` runs each rollout as a single **tool-disabled** text turn.
That's correct for text-generation skills, but **agentic** skills (threat-modeling,
api-security, …) are built to call `session()`/`http()`/`scan()`/`report()` and
produce nothing useful without them — run tool-disabled they return empty output
and can't be optimized.

`sleep-tools.sh` is a drop-in variant that runs the rollout with **tools enabled**:
built-in `Bash`/`Read`/`Edit` plus the reused **agent-smith `pentest-agent` MCP
server** (`session`/`http`/`scan`/`report`/`kali`). Same isolation, gate, and
stage→adopt flow; only the rollout changes.

```bash
# point at your agent-smith checkout if it isn't the default location
echo 'AGENT_SMITH_DIR=/path/to/agent-smith' >> skill-training/.env   # optional

./skill-training/sleep-tools.sh run \
  --target-skill-path appsec/threat-modeling/SKILL.md \
  --tasks-file skill-training/tasks/threat-modeling.json --progress
```

How it works: `tools_runner.py` monkeypatches skillopt-sleep's `ClaudeCliBackend`
with `tools_backend.py`'s tool-enabled subclass (drops `--disallowedTools '*'`,
adds `--allowedTools`/`--mcp-config`, parses `stream-json` for the result + which
tools fired), then hands off to the stock CLI. Only the **rollout** gets tools —
the judge/reflect calls stay lean.

Author **tool-aware** checks with the `tool_called` op to score real tool use:
`{"op":"tool_called","arg":"report"}` passes only if the skill actually invoked
`report()`. Combine with `contains`/`section_present` on the produced write-up.

Tunables (env / `.env`): `AGENT_SMITH_DIR`, `SKILLOPT_TOOLS_MCP=0` (built-ins only,
no MCP), `SKILLOPT_TOOLS_BUILTIN` (default `Bash,Read,Edit`), `SKILLOPT_TOOLS_TIMEOUT`
(default 600s — agentic rollouts are slow).

**Tiers of tool use:**
- **Tier 1 — `session`/`report`/`http`(local)** — pure Python, no Docker. Runnable now.
- **Tier 2 — `scan`(semgrep/trufflehog)** — static analysis, needs Docker (images present).
- **Tier 3 — `kali()` / network `scan()`** — needs a **live target lab** + the Kali
  container. agent-smith ships the runtime but **no target fixtures**, so you must
  supply a vulnerable target (e.g. Juice Shop) and a ground-truth scorer. Out of scope here.

Verified: the MCP server connects and the model executes real tools (e.g. `session()`);
full agentic optimization runs are slow and API-costly, so budget accordingly.

---

## Honest scope

- Sleep **augments** a skill — it appends learned rules to the LEARNED block. It
  does not restructure the body or rewrite the description. For a holistic rewrite
  you'd need SkillOpt's heavier research training loop (a scored env per skill);
  we deliberately deferred that.
- **Text skills** optimize cleanly with `sleep.sh`; **agentic skills** need
  `sleep-tools.sh` (tools enabled) or they return empty output. Fully exercising
  the offensive ones (real `scan`/`kali`) additionally needs a target lab (Tier 3).
- No tasks file ⇒ no signal ⇒ no improvement. The leverage is in authoring good
  tasks with sharp rule judges. Treat `tasks/*.json` as first-class repo assets and
  grow them over time.
- `mock` backend never produces real edits; it's for wiring/CI only.

## What's tracked vs generated

```
skill-training/
├── README.md                          # this guide
├── requirements.txt                   # pinned skillopt==0.2.0
├── setup.sh                           # bootstraps .venv
├── sleep.sh                           # isolated wrapper — tool-DISABLED (text skills)
├── sleep-tools.sh                     # isolated wrapper — tools ENABLED (agentic skills)
├── tools_backend.py                   # tool-enabled ClaudeCliBackend subclass
├── tools_runner.py                    # monkeypatch injector → stock skillopt-sleep CLI
├── config/skillopt-sleep.config.json  # gate on, evolve_memory off
├── tasks/
│   ├── _TEMPLATE.json                 # start here for a new skill
│   ├── gh-export.json                 # worked example (5 tasks) — proven live: val 0.388→1.000
│   ├── remediate.json                 # 4 tasks (diff + verification + effort)
│   ├── ssl-tls-audit.json             # 3 tasks (findings + severity + PCI/NIST)
│   ├── threat-modeling.json           # 4 tasks (Mermaid + STRIDE + RTM)
│   └── api-security.json              # 3 tasks (OWASP API cat + PoC + impact)
├── .env            (git-ignored)      # your ANTHROPIC_API_KEY (for --backend claude)
├── .venv/          (git-ignored)      # toolchain
└── .sleep-home/    (git-ignored)      # isolated config copy + state

# also git-ignored, written at the repo root by a run:
.skillopt-sleep/staging/<ts>/          # proposed_SKILL.md + diff + report.md — review, then adopt
```
