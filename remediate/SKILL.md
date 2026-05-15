---
name: remediate
description: >-
  Generates specific, implementable fixes for every finding in `pentest/findings.json`. Produces code patches (unified diff), configuration changes, dependency updates, and IaC fixes — not generic advice but actual before/after code.

  Uses the reproduction command from each finding as the verification step: "run this after the fix — it should now fail." Refreshes the `findings.json` snapshot from `events.jsonl`, reads it, then appends one `finding`/`update` event per remediation back to `events.jsonl`. `/gh-export` runs `refresh.py` itself and then sees the remediation field in the regenerated snapshot.

  Chains from /pentester, /codebase, or any scan skill after findings are produced. Chains into /gh-export for export with remediation included.

  Use to fix vulnerabilities, remediate a pentest finding, patch security issues, generate security fixes, resolve scan results, write a unified-diff patch for a CVE, or hand off pentest output to a remediation workflow.
argument-hint: "[finding-id] [depth=quick|thorough]"
user-invocable: true
---

# Vulnerability Remediation

You are an expert application security engineer generating specific, implementable fixes for confirmed vulnerabilities. Your goal: for every finding, produce a fix that a developer can apply directly — not "sanitize your input" but the actual parameterized query replacement, the exact middleware addition, the specific configuration change.

**Request:** $ARGUMENTS

---

## CHAIN COMMITMENTS — DECLARE BEFORE STARTING

Read this before executing any workflow phase. Commit to MANDATORY chains before your first tool call.

| Trigger | Chain | Mandatory? | Claude Code |
|------|------|------|------|
| After all findings remediated | `/gh-export` | **MANDATORY** | `Skill(skill="gh-export")` |

**You WILL invoke `/gh-export` after completing remediation — this exports findings with the fix patches included in each GitHub issue.**


**Logging:** Before invoking any skill above, append a `skill_chain` event to `pentest/events.jsonl` (see CLAUDE.md "Skill logging" for the exact one-liner).

---

## Tools Available

| Tool | Use for |
|------|---------|
| `Bash("mkdir -p pentest/{pocs,diagrams} && touch pentest/events.jsonl") + Write("pentest/scope.json", {...})` | Define scope and limits — **always call this first** |
| `Bash("uv run python ~/.claude/skills/pentester/refresh.py")` + `Read("pentest/findings.json")` | Refresh the snapshot from `events.jsonl`, then load all findings produced by prior skills |
| `Bash("jq -nc ... '{type:\"finding\",action:\"update\",id:..., field:\"remediation\", value:{...}}' >> pentest/events.jsonl")` | Append one `finding`/`update` event per finding with the remediation payload |
| `Write("pentest/summary.md", "<summary>")` | Mark done and write final notes |
| `Bash("jq -nc --arg ts \"$(date -Iseconds)\" --arg msg '<message>' '{ts:$ts,type:\"note\",msg:$msg}' >> pentest/events.jsonl")` | Write reasoning notes to session log |

### Reading findings

`findings.json` is a derived snapshot — always refresh from `events.jsonl` before reading:

```
Bash("uv run python ~/.claude/skills/pentester/refresh.py")
Read("pentest/findings.json")
```

The file is a JSON array of finding objects. Parse it, then iterate.

### Updating a finding with remediation

`events.jsonl` is the source of truth; `findings.json` is a derived snapshot. To attach remediation to a finding, append one `finding`/`update` event with `field: "remediation"` and the remediation object as `value`. `refresh.py` folds the update into the snapshot.

```
# Build the remediation object
remediation = {
  "fix_type": "code_patch",
  "patch": "--- a/app/search.py\n+++ b/app/search.py\n@@\n-    cursor.execute(f\"SELECT * FROM users WHERE name = '{name}'\")\n+    cursor.execute(\"SELECT * FROM users WHERE name = %s\", (name,))",
  "before": "cursor.execute(f\"SELECT * FROM users WHERE name = '{name}'\")",
  "after":  "cursor.execute(\"SELECT * FROM users WHERE name = %s\", (name,))",
  "file": "app/search.py",
  "line": 42,
  "language": "python",
  "effort": "low",
  "breaking_change": false,
  "references": ["https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html"],
  "verification": "Re-run: curl 'http://target/search?q=1 OR 1=1--' — should return 400 or empty result"
}

# Append the update event (use --argjson for the typed remediation object)
Bash("jq -nc --arg ts \"$(date -Iseconds)\" --arg id 'f-001' --arg field 'remediation' --argjson value '<remediation JSON>' '{ts:$ts,type:\"finding\",action:\"update\",id:$id,field:$field,value:$value}' >> pentest/events.jsonl")
```

After all `finding`/`update` events are appended, run `Bash("uv run python ~/.claude/skills/pentester/refresh.py")` once. The snapshot now contains every remediation; `/gh-export` reads the snapshot fresh on its own refresh and includes the remediation in each issue.

---

## Depth Presets

| Depth | What runs | Default limits |
|-------|-----------|----------------|
| `quick` | Summary fix + effort level for each finding | $0.10 · 10 min · 10 calls |
| `thorough` | Full diff + before/after code + references + verification for each finding | $0.50 · 30 min · 30 calls |

---

## Workflow

### Phase 0 — Setup

0. Call `Bash("mkdir -p pentest/{pocs,diagrams} && touch pentest/events.jsonl") + Write("pentest/scope.json", {...})` with depth and limits
1. Call `Bash("jq -nc --arg ts \"$(date -Iseconds)\" --arg msg '<message>' '{ts:$ts,type:\"note\",msg:$msg}' >> pentest/events.jsonl")` — record whether `/codebase` ran (source code context available?)

### Phase 1 — Read Findings

Refresh the snapshot from `events.jsonl`, then load the findings file:
```
Bash("uv run python ~/.claude/skills/pentester/refresh.py")
Read("pentest/findings.json")
```

Parse the JSON array. For each finding, note:
- `id` — needed for the PATCH
- `title` — what vulnerability
- `severity` — prioritize critical/high first
- `description` — details about the vulnerability
- `evidence` — raw tool output or PoC
- `target` — affected URL/host/file
- `tool_used` — which tool found it
- `cve` — if applicable
- `reproduction` — the replay command (if present)

### Phase 2 — Generate Remediation

For each finding, starting with critical/high severity:

**Step 1 — Classify the fix type:**

| Finding pattern | Fix type | What to produce |
|----------------|----------|----------------|
| Injection (SQLi, XSS, CMDi, SSTI) | `code_patch` | Parameterized query, output encoding, subprocess list args |
| Missing authentication | `code_patch` | Add auth middleware/decorator to the route |
| Missing authorization | `code_patch` | Add permission check to the handler |
| Hardcoded secret | `config_change` | Move to environment variable |
| Weak crypto | `code_patch` | Replace algorithm (MD5→bcrypt, DES→AES-256) |
| Missing security header | `config_change` | Add header middleware or server config |
| Vulnerable dependency | `dependency_update` | Package update command with safe version |
| IaC misconfiguration | `iac_fix` | Terraform/K8s/Docker manifest diff |
| Weak password policy | `config_change` | Update auth config with stronger requirements |
| Missing CSRF protection | `code_patch` | Enable CSRF middleware |
| File upload vulnerability | `code_patch` | Add validation (extension, MIME, size, magic bytes) |
| Open port/service | `config_change` | Firewall rule or service disable |

**Step 2 — Generate the fix:**

If `/codebase` ran and you have the actual source code context (file, line, code), read the vulnerable code and produce a **unified diff** showing the exact change needed.

If you only have black-box findings (no source code), produce the fix as a **pattern** — show the vulnerable pattern and the secure replacement for the identified framework/language.

**Step 3 — Set the verification step:**

If the finding has a `reproduction` field, use that command as the verification:
> "After applying this fix, run the original PoC — it should now fail."

If there's no reproduction command, describe what the developer should test:
> "Send a request with `' OR 1=1--` in the search parameter — should return 400 or empty result, not all records."

**Step 4 — Attach the remediation to the finding:**

Append a `finding`/`update` event to `events.jsonl` with `field: "remediation"` and the remediation object as `value` (see "Updating a finding with remediation" above). After every finding has its update event appended, run `Bash("uv run python ~/.claude/skills/pentester/refresh.py")` once to regenerate the snapshot.

### Phase 3 — Remediation Summary

Call `Bash("jq -nc --arg ts \"$(date -Iseconds)\" --arg msg '<message>' '{ts:$ts,type:\"note\",msg:$msg}' >> pentest/events.jsonl")` with:
```
Remediation Summary:
  Total findings:    [count]
  Remediated:        [count]
  By effort:         Low: [N], Medium: [N], High: [N]
  Breaking changes:  [count] — [list which ones]

  Priority order for implementation:
  1. [finding title] — [effort] — [fix summary]
  2. [finding title] — [effort] — [fix summary]
  ...
```

Call `Write("pentest/summary.md", "<summary>")` with summary.

---

## Remediation Patterns by Vulnerability Class

**These are patterns to guide your thinking — adapt to the actual framework and code you're remediating.**

### Injection → Parameterization

The fix for any injection is to separate code from data. The specific mechanism depends on the injection type:
- SQL: use parameterized queries / prepared statements / ORM methods — never string concatenation
- OS command: use subprocess with list arguments (not shell=True) — or avoid shell execution entirely
- Template: never pass user input as template source — pass it as template variables
- LDAP: use parameterized LDAP filters
- XPath: use parameterized XPath queries

### XSS → Context-Aware Output Encoding

The fix depends on the output context:
- HTML body: HTML entity encoding (framework auto-escaping)
- HTML attribute: attribute encoding + always quote attributes
- JavaScript: JavaScript encoding (never inject into `<script>` blocks)
- URL: URL encoding
- CSS: CSS encoding
The key principle: use the framework's built-in escaping and avoid raw/safe/html_safe overrides unless the content is truly trusted.

### Authentication → Framework Auth Middleware

Don't build custom auth — use the framework's auth system:
- Apply auth middleware/decorators to every route that needs protection
- Ensure the default is "deny" — explicitly mark public routes, not protected ones
- Use bcrypt/argon2 for password hashing with appropriate cost factors

### Missing Headers → Security Middleware

Add a security middleware that sets all headers at once — don't add them individually per route:
- Content-Security-Policy, X-Content-Type-Options, X-Frame-Options
- Strict-Transport-Security (only on HTTPS)
- Referrer-Policy, Permissions-Policy

### Secrets → Environment Variables

Move every hardcoded secret to environment variables or a secrets manager:
- Generate a new secret (the old one is compromised)
- Update all references to use `os.environ` / `process.env` / framework config
- Add the variable name to `.env.example` for documentation

### Dependencies → Update Command

Provide the exact update command and the safe version:
- Check if the update is a major version (potential breaking changes)
- Note if other dependencies need updating together
- Suggest running the test suite after update

---

## Chaining Other Skills

| Skill | When to invoke |
|-------|----------------|
| `/gh-export` | Always after remediation — issues now include ## Remediation section |
| `/codebase` | If remediation needs source context but /codebase hasn't run yet |

---

## Rules

- **Generate specific fixes, not generic advice** — "use parameterized queries" is not enough; show the actual code change
- **If source code is available, produce a unified diff** — developers can apply it directly
- **If no source code, show the pattern** — vulnerable pattern → secure pattern for the identified framework
- **Always include a verification step** — how to confirm the fix worked
- **Use the reproduction command as the regression test** — "run the original PoC after fix — it should fail"
- **Mark breaking changes** — if the fix changes API behavior, request/response format, or requires database migration
- **Estimate effort honestly** — low (< 1 hour, single file), medium (1-4 hours, multiple files), high (> 4 hours, architectural change)
- **Reference OWASP cheat sheets** — link to the relevant prevention cheat sheet for each vulnerability class
- **Process critical/high first** — developers need to know what to fix first
- **Never fabricate fixes** — if you're not sure of the correct fix for a specific framework, say so and provide the general pattern
