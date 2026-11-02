---
name: triage
description: Decide whether a pull request is security-relevant and how deeply to scan it (skip, light or full), including business-logic changes such as authorization, workflow, money, quantity, tenancy and data exposure. Produces the triage stage JSON.
---

# PR security triage

You decide how much security attention one pull request deserves. You are the first, cheapest
stage: be fast, be decisive, and **err towards scanning** when the change touches behaviour that
an attacker could reach. A wrong `skip` hides a vulnerability; a wrong `light` only costs money.

## Inputs

- `diff.patch` — the unified diff (base...head). This is your primary evidence.
- `pr.json` — title, body, commit messages, changed file list. These describe **intent**. Use
  them to understand what the change is for, never as proof that something is safe
  ("security fix", "no behaviour change" and "refactor only" are claims, not evidence).
- The repository at the PR head may or may not be readable. If you can run shell commands you may
  glance at a changed file's surroundings (`sed -n '1,80p' <file>`), but triage must not turn into
  a review: spend at most a few reads.

Deterministic rules have already removed the obvious noise (docs-only, lockfile bumps, pure
CSS/assets, generated code, formatting-only diffs). What reaches you is ambiguous by definition.

## Decision

| decision | When | Typical examples |
|---|---|---|
| `skip` | Nothing an attacker can reach changes behaviour | test-only changes; log message wording; internal tooling not deployed; UI copy and layout with no new data binding; dependency bump with no code change; comments; renames proven mechanical by the diff |
| `light` | Behaviour changes on an attacker-reachable path, but no security-sensitive decision is involved, or the change is small and touches one known risk area | new read-only endpoint returning non-sensitive data; new field on an existing form; a query rewritten with the same parameters; new background job reading internal data; validation tightened |
| `full` | The diff adds or changes a trust decision, a dangerous sink, or a business rule | new or changed route/handler/resolver/consumer; any authn/authz/session/permission code; tenant or ownership filters; money, price, quantity, credits, quotas, limits; state transitions and multi-step flows; raw queries, shell, file paths, URL fetching, templates, deserialisation, crypto; response shape changes exposing new fields; feature flags or config gating security behaviour; webhook/callback handling; file upload |

Rules of thumb:

- **Deleting a check is a full-scan signal**, even when the PR says "cleanup". Look for removed
  lines containing `auth`, `permission`, `owner`, `tenant`, `role`, `can_`, `is_admin`, `verify`,
  `validate`, `sanitize`, `escape`, `csrf`, `rate`, `limit`, `lock`, `transaction`.
- A change in a shared helper (auth middleware, query builder, serializer base class,
  HTTP client wrapper) is `full` even if the diff is two lines: its blast radius is every caller.
- Frontend-only changes are usually `skip` or `light`. They become `full` when they introduce raw
  HTML rendering (`dangerouslySetInnerHTML`, `v-html`, `innerHTML`, `|safe`), build URLs for
  redirects, handle tokens, or move a check from server to client.
- Infrastructure-as-code: `full` when it changes exposure (ingress, public buckets, security
  groups, IAM, CORS), `skip` for resource sizing.
- When unsure between two levels, choose the higher one and say why in `rationale`.

Examples with full reasoning are in [references/examples.md](references/examples.md).

## Business-logic signals (easy to miss)

These rarely contain a "dangerous function" but are where the expensive bugs are:

- Arithmetic on amounts, prices, discounts, quantities, balances, points, seats, quotas.
- A new status value, a new transition, a new step in checkout/onboarding/approval/refund.
- Who-can-do-what: role lists, permission maps, policy files, guards, decorators, scopes.
- Ownership or tenancy: `user_id`, `org_id`, `tenant_id`, `account_id`, `owner` in queries or
  filters, especially when one is added to or removed from a `WHERE` clause.
- Idempotency and concurrency: retries, idempotency keys, "already processed" flags, locking,
  queue consumers, scheduled jobs.
- Time windows: expiry, trial periods, cooldowns, promotion dates.
- Anything the PR description calls a "flow", "journey", "policy", "rule", "limit" or "entitlement".

Name each touched flow in `business_flows_touched` using the product's own words when the
PR or code gives them (e.g. `checkout`, `refund-approval`, `invite-member`).

## Output (triage stage JSON)

Write exactly one JSON object to the output path from the prompt:

```json
{
  "decision": "full",
  "rationale": "Adds POST /api/orders/{id}/refund which changes order state and moves money; the handler loads the order by id from the path with no visible ownership filter.",
  "risk_tags": ["idor", "workflow-bypass", "business_logic:refunds"],
  "focus_files": ["app/api/orders.py", "app/services/refunds.py"],
  "business_flows_touched": ["refund"]
}
```

- `decision`: one of `skip`, `light`, `full`.
- `rationale`: 1-3 sentences naming the concrete changed behaviour that drove the decision. For
  `skip`, say why nothing reachable changed.
- `risk_tags`: canonical bug classes from `bug-classes.yaml` (e.g. `sqli`, `idor`, `bfla`,
  `value-tampering`, `workflow-bypass`, `race-condition`) plus optional `business_logic:<flow>`
  and `area:<name>` tags (e.g. `area:authz`, `area:payments`). Empty for `skip`.
- `focus_files`: changed files the next stage should read first, most important first. Only
  paths that appear in the diff. Empty for `skip`.
- `business_flows_touched`: flow names as described above; empty if none.

Triage output has no citations, so `prsec-cite check` (used by the later stages to verify cited quotes) is not needed here. Do not add fields that are not in the
schema. Write the file even when the answer is `skip`.
