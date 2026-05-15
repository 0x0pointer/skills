---
name: retrospective
description: >-
  End-of-engagement retrospective. Mines pentest/events.jsonl for time-wasters, fast wins, abandoned techniques, and dead-end skill chains; writes a per-engagement archive; merges cross-applicable heuristics into a global lessons store; appends topical lessons under specific/. Loaded automatically by /pentester after summary.md is written. Loaded by future engagements at startup so the agent gets better over time.
argument-hint: <engagement_name> [pentest_dir=pentest]
user-invocable: true
---

# Engagement Retrospective

You are running the post-engagement retrospective. The engagement is finished — `pentest/summary.md` already exists, `verify.py` has been run, all findings have PoCs. Your job now is to capture what should be remembered for next time.

**Request:** $ARGUMENTS

---

## Where lessons live

```
~/.claude/lessons/pentester/
    general.md                     # always loaded by /pentester at startup; capped ~200 lines
    index.md                       # always loaded; one line per specific file
    specific/
        by-tech/<topic>.md         # WordPress, Cloudflare-WAF, Spring Boot, ...
        by-tool/<topic>.md         # sqlmap, hydra, nuclei, ...
        by-target-class/<topic>.md # internal-AD, public-saas, ctf-machine, ...
    archive/<engagement-name>.md   # raw retrospective for this engagement; never auto-loaded
```

The store lives **outside** the skills repo so it survives re-clones. Create any missing files/directories as you go.

---

## Workflow

### 1. Mine the event log

```
Bash("mkdir -p ~/.claude/lessons/pentester/{specific/by-tech,specific/by-tool,specific/by-target-class,archive}")
Bash("uv run ~/.claude/skills/retrospective/mine.py pentest/events.jsonl pentest/scope.json > pentest/retrospective-stats.json")
Read("pentest/retrospective-stats.json")
Read("pentest/scope.json")
Read("pentest/summary.md")
Read("pentest/findings.json")
```

`mine.py` derives durations from existing event timestamps — no schema change needed. It reports:

- `cells.top_time_spend` — top-5 cells by total span between first `cell_status` and last
- `cells.fast_wins` — vulnerable cells confirmed in under 5 minutes
- `cells.abandoned` — cells with no terminal status (in-progress when the engagement ended)
- `tools.heavy_no_finding` — tools that ran 3+ times in `tested_by` but never produced a vulnerable cell
- `skill_chains.chains_to_dead_ends` — sub-skills invoked that produced no findings
- `findings_summary` — totals by severity

### 2. Write the per-engagement archive

Pick `<engagement-name>` (the engagement directory name). Write the full retrospective to `~/.claude/lessons/pentester/archive/<engagement-name>.md`. Include:

- Header: target, depth, date, finding count by severity
- The full `retrospective-stats.json` content as a fenced code block
- A free-form reflection (2–6 short paragraphs) anchored to the stats. Examples of the kind of observation worth writing:
  - *"hydra SSH brute on `staging.acme.com:22` ran 2h12m, zero creds — login form had account lockout after 5 attempts that wasn't visible in initial recon; should have probed lockout policy first"*
  - *"nuclei produced 4 of 7 findings in the first 90 seconds; everything after that was deep manual work — keep nuclei as the always-first pass"*
  - *"chained into `/cloud-security` based on a 169.254.169.254 hit but the host blocked IMDS — wasted 20 min; check `curl -m2 169.254.169.254/latest/meta-data/` returns 200 before chaining"*

The archive is the source-of-truth for traceability. If a future general lesson looks wrong, you can find which engagement it came from.

### 3. Propose general lessons

For each candidate that is **cross-applicable** (would apply to engagements against unrelated targets):

1. `Read ~/.claude/lessons/pentester/general.md` (create from the template below if missing).
2. For each candidate, scan the existing entries for near-duplicates. If found: `Edit` the existing entry to bump the `seen:` counter and append the current engagement to the `engagements:` line. Do **not** rewrite the rule unless the new evidence sharpens it.
3. If genuinely new: append a new entry. Use the format below.
4. If the file would exceed 200 lines after the edit, consolidate first — combine related entries, drop the weakest, and keep the file under cap. Bloat kills usefulness.

**General-lesson format** (each entry 1-3 lines):

```markdown
- **<rule, leading with the verb>** — <one-line elaboration if needed>.
  Why: <evidence — incident, stats, or short reasoning>.
  When to apply: <target signature where this kicks in>.
  seen: <N>; engagements: <comma-separated names>.
```

**Starter file template** (write only if `general.md` does not exist):

```markdown
# General lessons — cross-engagement heuristics

Loaded automatically by `/pentester` at engagement start. Keep under 200 lines — consolidate when full.

Each entry: rule on the first line, then `Why:`, `When to apply:`, and `seen:`/`engagements:`.

---

```

### 4. Propose specific lessons

For each candidate scoped to a tech/tool/target class:

1. Decide the right file: `specific/by-tech/<topic>.md`, `specific/by-tool/<topic>.md`, or `specific/by-target-class/<topic>.md`. Use kebab-case topic names (`wordpress.md`, `cloudflare-waf.md`, `sqlmap.md`).
2. Create or `Edit` the file. Same entry format as `general.md`.
3. If a new file was created, add a one-line entry to `~/.claude/lessons/pentester/index.md`:
   ```
   - by-tech/wordpress.md — WordPress targets: enum users first; hydra last (lockout common).
   ```
4. Keep `index.md` under ~150 lines. If a topic has fewer than 2 lessons after a year, consider folding it back into a parent topic.

**Starter file template** (write only if `index.md` does not exist):

```markdown
# Specific lessons — index

Loaded automatically by `/pentester` at engagement start so the agent knows which topical lesson files exist. The agent reads the matching file lazily before invoking long-running techniques.

One line per file, format: `- <relative path> — <one-line summary>`.

---

```

### 5. Audit-trail event

Append a `note` event to `pentest/events.jsonl` recording exactly which lesson files were touched:

```
Bash("jq -nc --arg ts \"$(date -Iseconds)\" --arg msg '<message>' --arg files '<comma-separated paths>' '{ts:$ts,type:\"note\",kind:\"lesson_capture\",msg:$msg,files:$files}' >> pentest/events.jsonl")
```

The `kind:"lesson_capture"` marker makes these events grep-able later.

---

## Hard rules

- **Do not blindly append to `general.md`.** Always read first, dedupe, merge counters. The point is a curated file, not an audit log.
- **Never write secrets or target-specific sensitive values into the lessons store.** `general.md` and `index.md` are loaded into every future engagement's context; if scope.json had credentials or PII, scrub them. Use generic placeholders (`<target>`, `<creds-from-prior-step>`) instead of raw values.
- **Use `Edit`, not `Write`, on existing lesson files.** `Write` overwrites the whole file and will destroy unrelated entries.
- **The archive file is write-once.** If `~/.claude/lessons/pentester/archive/<engagement-name>.md` already exists (engagement was retrospected before), append a new section dated today rather than overwriting.
- **Cap enforcement is on you.** If `general.md` would exceed 200 lines after your proposed edits, consolidate before committing. Same for `index.md` at 150 lines.
- **No new event types.** Reuse `note` with a `kind:` marker (`lesson_capture`, `lessons_loaded`, `lesson_lookup`). Keeps the existing `refresh.py` fold untouched.

---

## When this skill runs

- **Mandatory** at the end of every engagement. `/pentester` invokes it as a step after `Write("pentest/summary.md", ...)` and `verify.py`, before exit. See pentester.md for the chain.
- May also be invoked manually mid-engagement if the user wants an interim retrospective (e.g. before a long pause).
