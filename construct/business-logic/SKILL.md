---
name: business-logic
description: Find business-logic flaws a PR introduces by mapping the intended workflow from the PR description and code, stating the invariants it must keep (ownership, tenancy, state transitions, value/quantity/limits, idempotency, concurrency, time windows) and generating abuse cases. Produces cited business_logic hypotheses whose sink is where the invariant should be enforced.
---

# Business-logic review for PRs

Business-logic bugs have no dangerous function. The code does exactly what it says; it just
fails to enforce a rule the business depends on. To find them you must first know the rule.
Work **understanding first**: intended behaviour, then invariants, then abuse cases, then the
code that should enforce each invariant.

## Inputs

- `pr.json`: the title, body and commit messages are your best statement of **intent** ("users
  can now cancel an order before it ships", "admins can approve refunds over 500").
- `diff.patch` and the repository at the PR head (read with shell commands).
- `repo_profile.json` if present: roles, tenancy model, domain glossary. The `org` skill, if
  available, describes internal auth libraries and domain terms.
- `prior_findings.json` if present: re-check each earlier finding at this head.

## Step 1: Model the intended workflow

From the PR text and the changed code, write down for yourself (briefly, this is not output):

- **Actors and roles**: anonymous, user, member of org/tenant, owner, admin, support, service,
  webhook sender.
- **Objects**: what records are created, read, changed or deleted, and who owns them.
- **Flow**: the steps of the business process the PR touches, in order, and which endpoint or
  function implements each step.
- **States**: the lifecycle of the main object (`draft -> submitted -> approved -> paid`), and
  which transitions the PR adds or changes.
- **Values**: amounts, prices, quantities, discounts, balances, credits, seats, quotas and limits
  the flow reads or writes, and who supplies each one (server-computed vs client-supplied).

## Step 2: State the invariants

Turn the model into rules that must always hold. Each invariant names **where it should be
enforced** (server-side code, DB constraint, service layer). Typical families, with what to read
in [references/source-patterns.md](references/source-patterns.md):

| Family | Example invariant | bug_class when violated |
|---|---|---|
| Ownership | "A user can only read/modify orders where `order.user_id == current_user.id`" | `idor` |
| Tenancy | "Every query on tenant data filters by the caller's `tenant_id`" | `idor` |
| Role / function | "Only `approver` role may move an invoice to `approved`" | `bfla` |
| Writable fields | "Clients may set `name`, never `role`, `price`, `status`, `owner_id`" | `mass-assignment` |
| State machine | "`refunded` is only reachable from `paid` or `shipped`, never from `pending`" | `workflow-bypass` |
| Step order | "An order cannot be confirmed before payment is captured" | `workflow-bypass` |
| One-time use | "A reset/invite/voucher token is consumed exactly once" | `workflow-bypass` |
| Value | "Quantity >= 1; total is computed server-side from catalogue prices" | `value-tampering` |
| Limits / quotas | "An org on the free plan has at most 3 seats" | `value-tampering` |
| Atomicity | "Balance never goes negative even under concurrent withdrawals" | `race-condition` |
| Idempotency | "Retrying a payment webhook does not credit twice" | `race-condition` |
| Time | "Expiry is evaluated against a server-stored timestamp" | `workflow-bypass` |
| Exposure | "The response never includes other users' email or internal flags" | `data-exposure` |
| Fail-safe | "If the entitlement service errors, access is denied" | `bfla` (or `workflow-bypass` for skipped steps) |

## Step 3: Generate abuse cases

For each invariant, ask how an attacker (a normal user, a member of another tenant, or a
replaying client) could break it with requests the API accepts. Use
[references/abuse-cases.md](references/abuse-cases.md) as a checklist. Good abuse cases are
concrete: "user B sends `POST /api/orders/{A's id}/cancel`", "send `quantity: -3`", "call
`/confirm` without `/pay`", "send the same `redeem` request twice in parallel".

## Step 4: Find (or fail to find) the enforcement

For each abuse case, locate the code that should stop it:

- Read the handler, the service it calls and the query it runs. Follow the object load: is the
  lookup scoped (`WHERE id = ? AND owner_id = ?`) or unscoped (`get(id)`) followed by a check?
- Look for the check in middleware, decorators, policy classes, model hooks, DB constraints
  (`CHECK (quantity > 0)`, unique indexes for idempotency keys), and in `org` safe wrappers.
- A check in the UI, in an API client, or in a comment is not enforcement.
- If enforcement exists somewhere reachable on every path, there is no hypothesis. If it exists
  on some paths (e.g. the old endpoint) but not the new one, that is the hypothesis.

Only keep abuse cases where enforcement is **absent, partial, or bypassable** on a path the PR
adds or changes.

## Step 5: Express the hypothesis

A business-logic hypothesis is a claim that an invariant is not enforced. Express it with the
same fields as a technical one:

- `vuln_class`: `business_logic`.
- `bug_class`: one of `idor`, `bfla`, `mass-assignment`, `workflow-bypass`, `value-tampering`,
  `race-condition`, `data-exposure` (from `bug-classes.yaml`; never `negative-quantity`,
  `price-tampering` etc., which are aliases of `value-tampering`).
- `title`: the broken invariant in one line ("Any user can refund another user's order").
- `description`: the invariant, the abuse case, and why the code does not enforce it.
- `entry_point`: the request or event that starts the abuse case.
- `source`: where the attacker-chosen value enters (the path id, the `quantity` field), if any.
- `sink`: **the line where the invariant should be enforced but is not**, usually the
  unscoped load, the write that persists the tampered value, the state assignment without a
  transition check, or the read-then-write pair. It must be real code you can quote.
- `path[]`: the hops from entry point to sink, plus the place a sibling path *does* enforce the
  rule when that contrast is the evidence.
- `assumed_guards`: checks that exist but you believe are insufficient, or checks that exist
  outside the repository and that you could not see.
- `introduced_by_diff`: `true` when the PR adds the flow, the field, the transition, or removes
  the check.

Ranking: missing ownership/tenancy or role checks on state-changing or sensitive-read endpoints,
and client-controlled money/quantity, rank highest. Theoretical races on low-value counters rank
lowest.

## How to cite

Citations are `{ "file", "line", "end_line"?, "quote" }`: repo-relative path, 1-based line at the
PR head (from `grep -n` / `sed -n`, never from diff offsets), and a **verbatim** 1-3 line quote of
the code. Do not paraphrase or elide. Cite only code you have read in this session. When a shell
is available run `prsec-cite check <your output file>` after writing the output and fix every
reported problem.

## Output (hypothesise stage JSON)

```json
{
  "summary": "Adds order cancellation for customers. Intent: customers cancel their own unshipped orders. The new handler loads the order by id without an owner filter and does not check the current status.",
  "hypotheses": [
    {
      "id": "H1",
      "vuln_class": "business_logic",
      "bug_class": "idor",
      "title": "Any authenticated user can cancel any order",
      "description": "Invariant: only the order owner may cancel. The handler loads Order by the path id with no user_id filter and no ownership check before setting status to cancelled; the existing GET /orders/<id> handler does filter by user_id.",
      "entry_point": "POST /api/orders/<id>/cancel",
      "source": {"file": "app/orders.py", "line": 58, "quote": "def cancel_order(order_id):"},
      "sink": {"file": "app/orders.py", "line": 60, "quote": "order = Order.query.get_or_404(order_id)"},
      "path": [
        {"file": "app/orders.py", "line": 61, "quote": "order.status = \"cancelled\""},
        {"file": "app/orders.py", "line": 31, "quote": "order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()"}
      ],
      "assumed_guards": ["login_required on the blueprint"],
      "impact": "Cancel other customers' orders (disruption, refund abuse).",
      "severity_guess": "high",
      "introduced_by_diff": true
    }
  ]
}
```

Write the combined hypotheses (technical and business-logic) into the single output file the
prompt names, ids `H1..Hn` in ranked order, within the hypothesis cap.
