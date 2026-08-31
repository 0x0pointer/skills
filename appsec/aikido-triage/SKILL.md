---
name: aikido-triage
description: |
  Triages Aikido security findings live via the Aikido MCP — no CSV. Splits findings into SCA, SAST, Application Secrets, and Misconfiguration, applies a category-specific verification playbook to each (source-to-sink taint analysis with trust-boundary/reachability assessment for SAST, /analyze-cve chaining for SCA, usage + opt-in liveness checks for secrets, blast-radius reasoning with optional live-chain confirmation for misconfiguration), scores every finding's business impact and severity, then closes confirmed non-issues directly in Aikido after a single review checkpoint.
argument-hint: "<codebase-path> [repo=<name>] [team=<name>] [workspace=<name>] [severity=critical,high,medium,low]"
user-invocable: true
---

# Aikido Findings Triage Workflow

You are triaging Aikido's live security feed against a local codebase, using the Aikido MCP for
both reading and closing findings — **there is no CSV in this workflow**. For each finding, read
the flagged file, run the verification playbook for its category, score its business impact, and
render a verdict. Confirmed non-issues get closed directly in Aikido with a specific reason;
everything else is reported back to the user ranked by business severity.

**Do not guess. Read the actual files before rendering a verdict. Never call
`aikido_ignore_issue` before the user has confirmed the batch in Phase 5.**

---

## Arguments

Parse from the user's invocation:
- `CODEBASE_PATH` — absolute path to the local codebase to investigate. **Required** — Aikido's
  feed gives you file/line/type/severity/remediation text, never source code, so every category
  still needs a local read. Ask the user if missing.
- Optional scoping filters, passed straight through to `aikido_issues_list`: `repo`, `team`,
  `workspace`, `severity` (one or more of `critical|high|medium|low`), `labels`,
  `out_of_sla`/`sla_due_soon`. Ask only if the user's Aikido workspace spans multiple
  repos/teams and it's ambiguous which one `CODEBASE_PATH` corresponds to.

---

## CHAIN COMMITMENTS — declare before starting

| Trigger | Chain | Mandatory? |
| --- | --- | --- |
| `open_source` finding where the package is imported and reachability can't be resolved from a quick grep alone | `/analyze-cve` | **MANDATORY** |
| Misconfiguration finding (`cloud`, `iac`, `docker_container`, `cloud_instance`, `surface_monitoring`) AND the user has already provided/authorized live target access | `/cloud-security`, `/container-k8s-security`, `/api-security`, or `/ssl-tls-audit` (pick by resource type — see `references/misconfig-playbook.md`) | OPTIONAL — only with authorized live access |
| `scm_security` finding that is specifically a CI/CD OIDC trust misconfiguration | `/cloud-identity-federation` | OPTIONAL |
| Unmapped `mobile` finding | `/android-security` or `/ios-security` | OPTIONAL — suggest, don't run automatically |
| Unmapped `ai_pentest` finding | `/ai-redteam` | OPTIONAL — suggest, don't run automatically |

`/analyze-cve` is the one mandatory chain — reuse it exactly as documented in
`references/sca-playbook.md` rather than re-deriving a dataflow trace inline.

---

## Phase 0 — Auth check

Call `mcp__aikido__aikido_issues_list` once with no filters as a probe. If the response signals
sign-in is required, call `mcp__aikido__aikido_login` and wait for the user to complete the
browser flow before continuing. Do not proceed to Phase 1 until issues can actually be listed.

---

## Phase 1 — Ingest (Aikido MCP only)

1. Call `mcp__aikido__aikido_issues_list`, applying any scoping filters the user gave
   (`repo_name`/`team_name`/`workspace_name`/`severity`/`labels`/`out_of_sla`/`sla_due_soon`).
2. Paginate: increment `page` (zero-based) until a page comes back with no issues. **Do not stop
   after page 0** — a truncated first page silently under-triages the workspace.
3. Collect every issue's full field set (`issue_id`, `issue_title`, `issue_type`,
   `issue_severity`, `issue_remediation`, and whichever extra fields the tool surfaces for that
   issue — `issue_file`/`issue_start_line`, `location`, `issue_link`,
   `issue_remediate_by_date`, package/version fields for `open_source`, a liveness field for
   `leaked_secret` if Aikido already reports one).
4. **Optional supplement**: if `CODEBASE_PATH` has local changes not yet reflected in the Aikido
   dashboard (`git -C CODEBASE_PATH diff --name-only`, plus untracked files), offer to run
   `mcp__aikido__aikido_full_scan` on those changed files (max 50 per call — batch if more) so
   new SAST/secrets issues are caught before they even land in the feed. This is additive, not a
   replacement for Phase 1 step 1 — mention it's available, don't force it.

---

## Phase 2 — Categorize

Bucket every issue by its `issue_type` into one of five categories. Full rationale and Unmapped
handling: `references/category-map.md`.

| Category | `issue_type` values |
|---|---|
| SCA | `open_source`, `license`, `eol` |
| SAST | `sast`, `ai_code_analysis` |
| Application Secrets | `leaked_secret` |
| Misconfiguration | `cloud`, `iac`, `docker_container`, `cloud_instance`, `scm_security`, `surface_monitoring` |
| Unmapped | `malware`, `mobile`, `ai_pentest` |

Print the counts per category to the user before investigating anything — **never silently drop a
finding**, including Unmapped ones.

---

## Phase 3 — Dispatch & investigate

For each category, load the matching reference file and run its playbook against every finding in
that bucket, reading `CODEBASE_PATH` as needed. Each playbook produces a **finding record**:

```
{
  issue_id, issue_title, category, issue_type, aikido_severity,
  file, line,
  technical_verdict:      "KEEP OPEN" | "CLOSE",
  close_category:         "False Positive" | "File Removed" | "Not Exploitable" | "Real Finding",
  exploitability_rating:  "HIGH" | "MEDIUM" | "LOW" | "NOT EXPLOITABLE",
  verification_method:    <free text — how the verdict was reached, e.g. "static taint trace",
                            "/analyze-cve dataflow trace", "live-confirmed via /cloud-security",
                            "static assessment only — not live-confirmed">,
  evidence:                <file:line references + the specific detail that proves the verdict>
}
```

| Category | Reference file | Core method |
|---|---|---|
| SCA | `references/sca-playbook.md` | Package-usage check → `/analyze-cve` chain for `open_source`; native EOL/license check otherwise |
| SAST | `references/sast-taint-playbook.md` | Verify sink → taint trace → identify source → trust-boundary/proxy crossing → reachability |
| Application Secrets | `references/secrets-playbook.md` | Removal check → static usage estimate → opt-in liveness probe |
| Misconfiguration | `references/misconfig-playbook.md` | Static blast-radius reasoning → optional live-chain confirmation |
| Unmapped | `references/category-map.md` | Lightweight judgment call + suggested chain-out, per finding |

---

## Phase 4 — Business impact & severity

For **every** finding record from every category (Unmapped included), apply
`references/business-impact-rubric.md` to add:

```
business_severity:      "Critical" | "High" | "Medium" | "Low"
business_justification: <required only when business_severity != aikido_severity — one line>
```

`business_severity`, not Aikido's raw `aikido_severity`, is what drives ranking in Phase 5 and 7.

---

## Phase 5 — Review & confirm

Before writing anything to Aikido, present one categorized table to the user:

```
## Proposed triage — review before I close anything

| Category | ID | Business Severity | Verdict | Reason |
|---|---|---|---|---|
| SAST | AIK-1234 | Low | CLOSE — Not Exploitable | ... |
| Secrets | AIK-5678 | Critical | KEEP OPEN | ... |
...

N proposed closures, M kept open. Confirm closures before I call aikido_ignore_issue?
```

Wait for explicit confirmation. This is a real, shared-state write against the team's Aikido
workspace — do not skip this checkpoint even under an otherwise autonomous invocation.

---

## Phase 6 — Execute closures

For every confirmed `CLOSE` verdict, call:

```
mcp__aikido__aikido_ignore_issue(issue_id=<id>, reason=<one-line, specific — reuse the finding
  record's evidence/verification_method, not a generic "not exploitable">)
```

Report per-call success/failure. If a call fails, do not retry silently — surface it in the Phase
7 summary so the user knows which issues are still open in Aikido despite the intended verdict.

---

## Phase 7 — Final summary

Chat-facing only — **no file is generated**. Include:
- Category counts (found / closed / kept open), including the Unmapped bucket.
- Every closed issue with its ID and the reason sent to Aikido.
- Every kept-open finding, ranked by `business_severity` (Critical first), with its
  `exploitability_rating` and one-line evidence.
- For Unmapped findings, or KEEP OPEN findings whose verdict is "static assessment only — not
  live-confirmed," a one-line suggested next skill (see CHAIN COMMITMENTS).

---

## Rules

- **Read every flagged file before rendering a verdict.** Never close a finding based on the rule
  name or Aikido's remediation text alone.
- **Batch independent reads in parallel** — read multiple files in one response when they don't
  depend on each other.
- **`/analyze-cve` is mandatory** for `open_source` findings where a quick grep can't settle
  reachability. Do not skip it to save time.
- **Never call `aikido_ignore_issue` before Phase 5's confirmation.** Batch confirmation once,
  then execute — don't re-confirm per issue, and don't fire early either.
- **Never auto-probe a secret's liveness.** `references/secrets-playbook.md` requires asking
  first, every time, even for an allowlisted provider.
- **Label unconfirmed misconfiguration verdicts as such** — "static assessment only" is a valid,
  honest result. Never present reasoning as if it were live-confirmed.
- **Never silently drop a finding type.** Anything that isn't SCA/SAST/Secrets/Misconfiguration
  goes in Unmapped and still gets a verdict and a business-severity score.
- **Preserve line numbers** in all evidence — use the actual line numbers from the source file.
- **Do not fabricate code or evidence.** Only cite lines you have actually read.
