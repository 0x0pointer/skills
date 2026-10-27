---
name: taint-analysis
description: Find technical vulnerabilities introduced or changed by a PR by tracing attacker-controlled data from sources through propagation to dangerous sinks, across trust boundaries, for Node/Express/Nest, Python/Django/Flask/FastAPI, Java/Spring, Go, .NET and PHP. Produces cited hypotheses for the hypothesise stage JSON.
---

# Taint analysis for PR review

Goal: turn the diff into a short, ranked list of **evidence-backed hypotheses** of the form
"attacker-controlled X reaches dangerous Y through Z, and nothing on the way neutralises it".
Every hypothesis must be specific enough that a separate reviewer with fresh context can confirm
or refute it from the citations alone.

## Inputs

- `diff.patch`, `pr.json` (intent: title, body, commits), optionally `repo_profile.json`
  (stack, routes, auth model) and `prior_findings.json` (findings from earlier pushes; re-check
  each one and keep it only if it still holds at this head).
- The repository at the PR head in the working directory. Read it freely with shell commands
  (`grep -rn`, `sed -n 'A,Bp' file`, `find`). Read; do not guess.

## Method

Work **diff-first, then outwards**. The PR is the unit of review; pre-existing code matters only
where the diff interacts with it.

1. **Map what changed.** For each changed hunk, note: new or modified entry points (routes,
   handlers, resolvers, consumers, CLI commands, scheduled jobs), new sinks, removed or modified
   guards, changed helpers with many callers.
2. **Sinks first.** For every dangerous operation in or reachable from changed code, confirm it
   is a real sink: executable code, not a comment, string, test fixture or dead branch. Use the
   per-language tables in the references to recognise sinks and their safe variants.
3. **Walk backwards to the source.** From each real sink, read every caller hop until the value
   originates. Record each hop as a citation in `path[]`. Classify the origin:
   - *attacker-controlled*: request params/body/headers/cookies, path segments, uploaded file
     content and names, message-queue payloads, webhook bodies, third-party API responses,
     values stored earlier by another user (second-order);
   - *trusted*: literals, server config and env vars, values only set by privileged internal code.
   A trusted-only origin ends the trace: no hypothesis.
4. **Check every transformation on the way.** Does it neutralise *this* payload shape for *this*
   sink? Parameter binding neutralises SQL injection; `strip()`, length caps and `escape()` for
   the wrong context do not. An allowlist of hosts neutralises SSRF; a denylist of strings usually
   does not. See the propagation and sanitiser notes per language.
5. **Map trust boundaries.** For each boundary the value crosses (gateway, auth middleware,
   signature check, schema validator, ORM layer), name the control and say whether it stops this
   payload. "There is probably a WAF" is not evidence. If no control is visible in the repo, say so
   and treat the path as unmitigated. Record controls you relied on in `assumed_guards`.
6. **Decide `introduced_by_diff`.** `true` if the diff adds the sink, adds the source-to-sink
   path, or removes/weakens a guard on it. `false` if the vulnerable path exists unchanged at base
   and the diff only touches nearby code. Pre-existing bugs are still worth reporting when the
   diff touches the same function, but rank them below introduced ones.
7. **Rank and cap.** Keep at most the number of hypotheses the prompt allows (default 8), ordered
   by likelihood x impact. Fewer, better hypotheses beat a long speculative list. An empty list is
   a valid answer for a PR with no reachable risk.

Language and framework specifics:
[Node / Express / Nest](references/node.md) ·
[Python / Django / Flask / FastAPI](references/python.md) ·
[Java / Spring](references/java.md) ·
[Go](references/go.md) ·
[.NET / ASP.NET Core](references/dotnet.md) ·
[PHP / Laravel / Symfony](references/php.md) ·
[Trust boundaries](references/trust-boundaries.md)

## How to cite

A citation is `{ "file": "...", "line": N, "end_line": M, "quote": "..." }`.

- `file` is repo-relative (`app/api/orders.py`, not `/work/src/app/api/orders.py`).
- `line` is the 1-based line number in the file **at the PR head**, not the diff hunk offset.
  Get it from `grep -n` or `sed -n` output, never by counting diff lines.
- `quote` is copied **verbatim** from those lines: at least one full line, ideally 1-3 lines,
  whitespace may differ but nothing else. No paraphrase, no `...` elisions, no added comments.
  For a multi-line quote set `end_line`.
- `source` cites where the attacker value enters (e.g. the `request.args.get` line), `sink`
  cites the dangerous call itself, `path[]` cites each hop in order from source to sink.
- Cite only code you have read in this session.

When a shell is available, run `prsec-cite check <your output file>` after writing the output
and fix every reported citation before finishing. Citations that fail the check after the stage
ends cause the hypothesis to be dropped.

## Output (hypothesise stage JSON)

```json
{
  "summary": "Adds an order search endpoint. Intent: let support staff search notes. The handler interpolates the q parameter into SQL and is reachable by any logged-in user.",
  "hypotheses": [
    {
      "id": "H1",
      "vuln_class": "technical",
      "bug_class": "sqli",
      "title": "SQL injection in GET /api/orders/search via q",
      "description": "q from the query string is interpolated into a LIKE clause with an f-string and executed with db().execute; no binding or escaping on the path.",
      "entry_point": "GET /api/orders/search",
      "source": {"file": "app.py", "line": 34, "quote": "q = request.args.get(\"q\", \"\")"},
      "sink": {"file": "app.py", "line": 36, "quote": "f\"SELECT id, note, total FROM orders WHERE user_id = {g.user_id} AND note LIKE '%{q}%'\""},
      "path": [],
      "assumed_guards": ["login_required on the route (authenticated users only)"],
      "impact": "Read or modify any table the app's DB user can access.",
      "severity_guess": "high",
      "introduced_by_diff": true
    }
  ]
}
```

- `vuln_class` is `technical` for taint findings (use the business-logic skill for invariants).
- `bug_class` is a canonical name from `bug-classes.yaml` (`sqli`, `nosqli`, `xss`, `ssrf`,
  `path-traversal`, `cmdi`, `code-injection`, `ssti`, `deserialization`, `open-redirect`, `xxe`,
  `header-injection`, `crypto-misuse`, `authn-session`, `idor`, `bfla`, `mass-assignment`,
  `data-exposure`, ...). Never invent a new name; use `other` and explain if nothing fits.
- `entry_point` is how an attacker reaches it: `METHOD /path`, `GraphQL mutation x`,
  `queue topic y`, `webhook z`.
- `severity_guess` is one of `critical`, `high`, `medium`, `low`, `info`; base it on impact
  and on the preconditions the attacker needs (anonymous > any user > specific role > admin).
- `id` values are `H1`, `H2`, ... in ranked order and stay stable within the output.
