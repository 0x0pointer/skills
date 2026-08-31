# SAST Taint Analysis Playbook

Lazy-loaded reference for Phase 3 of `/aikido-triage`, covering `issue_type` values `sast` and
`ai_code_analysis`. Run this 5-step sequence against every finding in the SAST bucket — verify the
sink, trace the taint, identify the true source, map every trust boundary the tainted value
crosses, then render a reachability verdict. Each step is a separate, deliberate check. Do not
collapse sink-verification and taint-tracing into a single "does this look bad" read, and do not
skip the trust-boundary step because a control exists somewhere upstream in the architecture —
"somewhere in the architecture" is not evidence for a specific finding.

---

## Step 1 — Verify the sink is real

Read the flagged `file:line`, plus roughly 10 lines of surrounding context on each side. Confirm
that the dangerous pattern Aikido's rule name claims is actually present in **executable** code.

Rule out, specifically:
- The match is inside a comment, docstring, or commented-out code.
- The match is inside a string literal (e.g. a log message that mentions `exec(` as text, not a
  call to it).
- The match is in a test file, test fixture, or mock/stub used only in tests — confirm by checking
  whether the file lives under a `test`/`spec`/`__tests__`/`fixtures` path and whether it's excluded
  from the production build.
- The match is in dead or unreachable code — a function that is never called, a branch guarded by a
  condition that can never be true, code behind a feature flag permanently off, or a file excluded
  from the build/deploy artifact.

This step alone resolves a meaningful fraction of SAST findings. Rule engines pattern-match on
syntax, not semantics — a rule name like "SQL injection" or "command injection" tells you what
*shape* of code triggered it, not that a vulnerability exists. If the sink isn't real, stop here:
`CLOSE — False Positive`, `exploitability_rating: NOT EXPLOITABLE`, and do not proceed to Step 2.

### Rule-specific checks (still part of Step 1)

A few Aikido rules have a fast, specific disqualifier or confirmation that's worth checking before
you invest in a full taint trace. Run the matching check below when the rule name matches; for
everything else, do the general check above and move on to Step 2 — don't skip the full sequence
just because there's no dedicated sub-playbook for the rule.

**NoSQL injection** (`NoSQL injection attack possible`)
Trace what the flagged call actually does. Does it call a NoSQL driver — a MongoDB query
(`.find(`, `.findOne(`, `$where`), a Redis command, an Elasticsearch query DSL call, a Mongoose
model method — or does it call something unrelated that merely matched the rule's syntax pattern,
such as an HTTP client (`axios.get`, `fetch`, `HTTParty.get`)? Cross-check `package.json` /
`Gemfile` / `requirements.txt` for an actual NoSQL driver dependency in the stack. If there's no
NoSQL driver in the project at all, the finding cannot be a NoSQL injection regardless of what the
flagged line looks like — `CLOSE — False Positive` immediately, skip Steps 2-5.

**SQL injection** (`SQL injection`, `string-based query concatenation`)
Confirm there is actual string interpolation or concatenation building a raw SQL string. Then check
the type of the interpolated variable — a strictly-typed value (`Date`, `Integer`, an enum, a
boolean) removes the injection vector even with naive string interpolation, because there's no
attacker-controlled string content that can break out of the query. Confirm how the string is
executed: `select_all`, `execute`, `connection.exec`, a raw `cursor.execute(f"...")`, string-built
`.query()` calls all count; a parameterized/bound-variable call using the same string does not, even
if it superficially resembles concatenation. This determines whether Step 2's trace needs to go any
further — a `Date`-typed interpolation into raw SQL is a real construct but not an injectable one,
so it still gets a full record, just with the type-safety fact as the decisive evidence.

**Unpinned GitHub Actions** (`3rd party Github Actions should be pinned`)
Read the actual workflow file at the flagged line. SHA-pinned (`uses: owner/action@<40-char-sha>`)
→ `CLOSE — False Positive` immediately — skip Steps 2-5 entirely, there's no data-flow concept here.
Tag- or branch-pinned (`@v2`, `@main`, `@master`) → `KEEP OPEN`, `close_category` not applicable
(it stays open), treat as `Real Finding` — supply-chain risk (a tag can be moved, a branch can be
force-pushed), not a taint-flow question. Do not run a taint trace on this rule; the verdict is
fully determined by reading the pin format.

**`NODE_AUTH_TOKEN` usage**
Read the flagged line directly. If the value comes from `${{ secrets.* }}` (or an equivalent
secrets-manager reference) → `CLOSE — False Positive`. If it's a hardcoded literal token value →
this is a secrets-shaped finding wearing a SAST label — `KEEP OPEN`, `close_category: Real Finding`,
and note explicitly in `evidence` that it should also be run through
`references/secrets-playbook.md`'s opt-in liveness-check option, since the real question ("is this
credential still valid") belongs to that playbook, not this one.

---

## Step 2 — Taint analysis: build the source-to-sink propagation chain

Once the sink is confirmed real, walk **backward** from it. For every hop between the sink and
wherever the value first enters the codebase, document: what calls this function, what the tainted
value looks like at that point, and what — if anything — transforms, validates, or sanitizes it
along the way. Read each intermediate file; don't infer a hop from a function name alone.

Record the trace in this shape — the same source/propagation/sink structure used by `/codebase`'s
`trace[]` and `/analyze-cve`'s dataflow graph, so evidence reads consistently across every skill in
this repo that does taint analysis:

```
SOURCE:       api/orders.py:42  get_order()      — order_id taken from query string, unvalidated
PROPAGATION:  db/query.py:88    build_filter()   — order_id concatenated into SQL string, no escaping
SINK:         db/query.py:91    execute_raw()    — raw query executed against the DB
```

Add as many `PROPAGATION` rows as there are real hops — don't compress a three-hop chain into one
row because the middle hop "obviously" does nothing. If a hop applies a transformation (escaping,
type coercion, an allowlist check, truncation), record it explicitly and note whether it actually
neutralizes the payload shape the sink is vulnerable to — a `.strip()` or a length cap does not
neutralize SQL injection; a parameterized rebind or an allowlist match usually does.

If the trace terminates without ever reaching an external entry point (the value is fully
constructed from constants and internal state at every hop you can find), that is itself a finding
for Step 3 — don't force a SOURCE row that isn't real.

---

## Step 3 — Identify the true source

Classify the origin found in Step 2:

- **Externally controllable** — an HTTP request parameter, header, body field, cookie, a
  message-queue payload, a webhook payload, a third-party API response consumed by the app,
  uploaded file content/metadata, a query string, anything an outside party can set the value of
  directly or indirectly.
- **Internal/trusted only** — a hardcoded literal, a value read from a config file or environment
  variable the application controls, an admin-only CLI argument, a value that is only ever set by
  other trusted internal code with no path from any external input.

If the source is internal/trusted only, and you cannot construct any path — direct or
multi-hop — by which external input could reach it, **short-circuit here**: `CLOSE — Not
Exploitable`, `exploitability_rating: NOT EXPLOITABLE`. There is no taint path from anything an
attacker controls, so Steps 4-5 have nothing to evaluate. State explicitly in `evidence` what you
checked to rule out an external path (e.g. "grepped all callers of `build_filter()`; every call site
passes a hardcoded internal constant, none derive from request data").

If the source is externally controllable, continue to Step 4.

---

## Step 4 — Trust boundary / proxy crossing

This is the step generic SAST tooling — and a purely source-to-sink trace — skips, and it is the
reason this playbook exists as a separate step rather than folded into Step 2. A tainted value can
be externally controllable and still never reach the sink in an exploitable form, because it
crosses one or more boundaries on the way that neutralize or gate it. Conversely, teams often
*assume* a boundary control exists ("the gateway validates that") without the codebase actually
proving it. Your job here is to map the real boundaries and check each one specifically against
this payload — not to note that boundaries exist in general.

Enumerate every boundary the tainted value crosses between the source identified in Step 3 and the
sink identified in Step 2. Concrete boundaries to look for, adapted to what this codebase actually
has:
- Public internet → WAF/CDN → reverse proxy / API gateway → application service → internal service
  mesh → database.
- External webhook → signature-verification middleware → handler.
- Public endpoint → authentication middleware → authorization check → business logic → sink.
- Message-queue consumer → schema validation → handler.

For each boundary actually crossed, do two things:
1. **State what control exists there** — auth middleware, an input-validation gateway, a WAF rule,
   a network ACL, mTLS between services, a signature check, a schema validator — and point to the
   file/config that implements it (middleware registration, gateway config, WAF ruleset, ingress
   annotation).
2. **Reason about whether that control would neutralize *this specific* payload/pattern** — not
   just whether a control exists. An auth middleware that requires a valid session says nothing
   about whether the session-holder's input is then injectable; a WAF rule tuned for classic
   `' OR 1=1` patterns may not catch a blind time-based payload; input validation on one field
   doesn't cover a different field feeding the same sink. Say explicitly which specific
   payload shape the control would or wouldn't stop.

If you cannot find evidence of a boundary or control in the codebase — no gateway config in the
repo, no middleware file, no WAF/ingress rule checked into IaC — **say so explicitly** rather than
assuming a control exists because "there's probably a WAF in front of this in production." An
unverified assumption is not evidence; record it as `verification_method: "static assessment only —
no evidence of a mitigating boundary control found in the codebase"` and treat the path as
unmitigated for the purposes of Step 5.

---

## Step 5 — Reachability verdict, then roll into exploitability_rating

Classify reachability using what Steps 2-4 established:

- **Directly reachable** — no authentication is required, and no boundary control found in Step 4
  blocks or meaningfully hinders this specific payload.
- **Reachable-with-preconditions** — reaching the sink requires something beyond an anonymous
  request: a valid authenticated session, network-level access (VPN, internal-only network), a
  specific role or permission, or a multi-step setup (e.g. must first create a resource you then
  attack).
- **Not reachable** — the code path is dead/unreachable (should have been caught in Step 1, but
  reconfirm here if Step 2's trace revealed it), or a Step 4 boundary control does neutralize this
  specific payload, or the path is unauthenticated-internal-only (e.g. an internal admin socket)
  with no route from any external input.

Combine the reachability verdict with the mitigation picture from Steps 2-4 into the final
`exploitability_rating` — the same four-value scale `/analyze-cve` uses, so severity read-outs are
comparable across every category in the Phase 5 review table:

- **HIGH** — directly reachable, and no mitigating control was found that would stop this payload.
- **MEDIUM** — reachable-with-preconditions, **or** a mitigating control exists but is weak,
  partial, or plausibly bypassable for this payload shape (e.g. the WAF rule covers a different
  encoding than the one that reaches the sink).
- **LOW** — reachable only under unlikely or edge conditions (a rare configuration, a race window,
  a precondition that's technically possible but operationally improbable).
- **NOT EXPLOITABLE** — not reachable, or Step 3 already closed the finding because there is no
  external source at all.

---

## Finding-record mapping

Use this table to translate the Step 5 outcome directly into the finding-record fields defined in
`SKILL.md`'s Phase 3 (`technical_verdict`, `close_category`, `exploitability_rating`). Every SAST
finding record must have a `verification_method` that names which step ended the analysis (e.g.
`"Step 1 — sink not present in executable code"`, `"Step 3 — source is internal/trusted only"`,
`"full 5-step static taint trace"`) so a reviewer can see how deep the check actually went.

| Outcome | `technical_verdict` | `close_category` | `exploitability_rating` |
|---|---|---|---|
| Step 1: sink not real (comment/string/test/dead code) | CLOSE | False Positive | NOT EXPLOITABLE |
| Step 1: NoSQL rule, no NoSQL driver in stack | CLOSE | False Positive | NOT EXPLOITABLE |
| Step 1: GitHub Action is SHA-pinned | CLOSE | False Positive | NOT EXPLOITABLE |
| Step 1: `NODE_AUTH_TOKEN` sourced from `secrets.*` | CLOSE | False Positive | NOT EXPLOITABLE |
| Step 1: GitHub Action tag/branch-pinned | KEEP OPEN | Real Finding | MEDIUM (supply-chain risk — rate per rubric, not a data-flow score) |
| Step 1: hardcoded `NODE_AUTH_TOKEN` value | KEEP OPEN | Real Finding | escalate — also cross-check `secrets-playbook.md` |
| Step 3: source is internal/trusted only, no external path | CLOSE | Not Exploitable | NOT EXPLOITABLE |
| Step 5: Not reachable (dead path, or Step 4 control neutralizes payload) | CLOSE | Not Exploitable | NOT EXPLOITABLE |
| Step 5: Directly reachable, no mitigating control | KEEP OPEN | Real Finding | HIGH |
| Step 5: Reachable-with-preconditions, or a weak/bypassable control | KEEP OPEN | Real Finding | MEDIUM |
| Step 5: Reachable only under unlikely/edge conditions | KEEP OPEN | Real Finding | LOW |

`close_category: "File Removed"` (from the shared enum in `SKILL.md`) applies to SAST findings only
in the rare case where the flagged file itself no longer exists in the codebase at all — check for
this before Step 1's line-level read; if the file is gone, it's a straight `CLOSE — File Removed`
without running the sequence.
