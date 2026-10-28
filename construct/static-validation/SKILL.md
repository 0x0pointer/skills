---
name: static-validation
description: Verify or refute one security hypothesis about a PR from source alone, refute-first - check the sink is real, the source is attacker-controlled, the path is reachable from the entry point, and that no guard, sanitiser, framework protection or enforcement elsewhere neutralises it. One reference per bug class. Produces the static_verify (or skeptic) stage JSON.
---

# Static validation (refute-first)

You receive **one** hypothesis produced by an earlier stage. Your job is to try hard to prove it
**wrong**. Only when every attempt to refute it fails, and every link is backed by code you read,
does it survive. Earlier stages over-report on purpose; you are the filter. A false positive
costs developer trust; a false negative is caught by the next scan or the eval corpus.

## Inputs

- The hypothesis (in the prompt or in the input directory): `id`, `vuln_class`, `bug_class`,
  `entry_point`, `source`, `sink`, `path[]`, `assumed_guards`, `description`.
- `diff.patch`, `pr.json`, and the repository at the PR head (working directory).
- The bug-class reference: `references/<bug_class>.md`. Read it **before** you start. If the
  `bug_class` has no reference, use the generic method below.

Treat the hypothesis citations as claims. Re-read every cited line yourself; earlier stages can
be wrong about line numbers, callers and what a helper does.

## Method

Answer each question with evidence (file and line you read). Stop as soon as one answer refutes.

1. **Is the sink real?** The cited line exists, is executable production code (not a test,
   fixture, comment, string, dead branch, disabled feature), and is the dangerous variant (raw
   query, not parameterised; shell string, not argv; unscoped load, not scoped).
2. **Is the source attacker-controlled?** Trace the value back. Literals, server config, and
   values only written by privileged code refute. Second-order sources (stored by another user)
   count as attacker-controlled.
3. **Is the path reachable from the entry point?** Find the route/handler registration that
   exposes the code. Check the call chain actually connects (read each caller). Check
   preconditions: authentication, role, feature flag, environment-specific registration.
   Unregistered handlers, admin-only internal tools, and code behind a permanently-off flag
   refute or lower severity.
4. **Do guards on the path neutralise this payload?** For each check between source and sink
   (validation, type coercion, sanitiser, authorization, ownership filter, transaction, lock),
   decide whether it is *effective for this bug class and this payload*. Use the reference's
   "Refute if" and "Framework protections" sections.
5. **For business-logic hypotheses: is the invariant enforced elsewhere?** Look beyond the
   handler: service layer, model hooks/validators, ORM global scopes, DB constraints
   (`CHECK`, `UNIQUE`, foreign keys, row-level security), shared middleware, the `org` skill's
   known-safe wrappers. Enforcement on *every* path refutes.
6. **Does the diff matter?** Note in `reasoning` whether the PR introduced, changed or merely
   touched the path.

Generic method for bug classes without a reference: steps 1-6 above, with "dangerous" meaning
"the specific behaviour the `bug_class` describes in `bug-classes.yaml`".

### Choosing the verdict

| verdict | Use when | `reachable` |
|---|---|---|
| `refuted` | Any step above refutes, with a citation of the refuting code (the guard, the parameter binding, the scoped query, the missing route registration) | usually `no`; `yes` if reachable but neutralised |
| `plausible` | No refutation found and the main path is cited, but at least one link could not be verified from the repository (dynamic dispatch, config outside the repo, external gateway, unclear caller) | `yes` or `unknown` |
| `confirmed_static` | Every link from entry point through source and path to sink is cited, the route is registered and reachable by the stated attacker, and every guard on the path was examined and is ineffective | `yes` |

Never use `confirmed_static` with `reachable` other than `yes`. When torn between two verdicts,
choose the more conservative one (`refuted` over `plausible` only with evidence; otherwise
`plausible` over `confirmed_static`).

### Severity

Re-assess `severity` (`critical`, `high`, `medium`, `low`, `info`) from what you verified, not
from `severity_guess`: impact of the bug class here x who can reach it (anonymous > any user >
specific role > admin) x data sensitivity. For `refuted`, use `info`.

## Citations

`citations[]` needs at least one entry and should contain the decisive evidence: for
`confirmed_static`, the entry point registration, the source, the sink and the ineffective
guard; for `refuted`, the line that refutes. Each guard in `guards[]` should carry its own
`citation`.

A citation is `{ "file", "line", "end_line"?, "quote" }`: repo-relative path, 1-based line at the
PR head (from `grep -n` / `sed -n` output), and a **verbatim** quote of 1-3 full lines. No
paraphrase, no `...`, no line-number prefixes inside `quote`. Cite only what you read in this
session. When a shell is available, run `prsec-cite check <your output file>` after writing the
output and fix every reported citation; unverifiable citations invalidate the result.

## Output (static_verify stage JSON)

```json
{
  "hypothesis_id": "H1",
  "verdict": "confirmed_static",
  "reachable": "yes",
  "reasoning": "Route GET /api/orders/search is registered on the app with login_required only. q comes from request.args and is interpolated into the SQL string; db().execute receives a single string, no bind parameters. No validation of q exists on the path. Introduced by this PR.",
  "guards": [
    {"description": "login_required: requires a session, does not constrain q", "effective": false,
     "citation": {"file": "app.py", "line": 32, "quote": "@login_required"}}
  ],
  "citations": [
    {"file": "app.py", "line": 31, "quote": "@app.get(\"/api/orders/search\")"},
    {"file": "app.py", "line": 34, "quote": "q = request.args.get(\"q\", \"\")"},
    {"file": "app.py", "line": 36, "quote": "f\"SELECT id, note, total FROM orders WHERE user_id = {g.user_id} AND note LIKE '%{q}%'\""}
  ],
  "severity": "high",
  "remediation": "Bind q as a parameter: db().execute(\"SELECT id, note, total FROM orders WHERE user_id = ? AND note LIKE ?\", (g.user_id, f\"%{q}%\"))."
}
```

`hypothesis_id` must equal the input hypothesis `id`. `remediation` is a short, concrete fix
(one or two sentences, code allowed), or `null` for `refuted`.

## Skeptic stage

When the prompt asks for a **skeptic** review of an already verified finding, apply the same
refute-first method with fresh eyes and write the skeptic JSON instead:
`{ "hypothesis_id", "refuted": true|false, "confidence": "low"|"medium"|"high", "reasoning" }`.
Set `refuted: true` only when you can name the specific code, configuration or framework
behaviour that defeats the finding. The skeptic can only downgrade; disagreement about severity
alone is not a refutation.

## Bug-class references

[sqli](references/sqli.md) · [nosqli](references/nosqli.md) · [xss](references/xss.md) ·
[ssrf](references/ssrf.md) · [idor](references/idor.md) · [bfla](references/bfla.md) ·
[mass-assignment](references/mass-assignment.md) · [path-traversal](references/path-traversal.md) ·
[cmdi](references/cmdi.md) · [ssti](references/ssti.md) ·
[deserialization](references/deserialization.md) · [open-redirect](references/open-redirect.md) ·
[crypto-misuse](references/crypto-misuse.md) · [authn-session](references/authn-session.md) ·
[race-condition](references/race-condition.md) · [workflow-bypass](references/workflow-bypass.md) ·
[value-tampering](references/value-tampering.md) · [data-exposure](references/data-exposure.md)
