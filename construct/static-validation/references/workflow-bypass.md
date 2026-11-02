# workflow-bypass: Workflow, state-machine and one-time-token bypass

## Claim to verify
An attacker can skip a required step, force an illegal state transition, reuse a one-time token,
or act outside a time window, because the server does not check the current state, the
completion of the prior step, or the token's used/expired status.

## Refute if
- The transition goes through a state machine or explicit guard that rejects this source state
  (`django-fsm` `@transition(source=...)`, `transitions`, xstate, Spring State Machine, a
  transition table, `if order.status != "paid": raise`), and **all** endpoints that change the
  state use it.
- The later step checks a server-side marker of the earlier step (payment captured id, verified
  timestamp) stored by trusted code, not a client flag.
- The token is consumed atomically with the effect (deleted or marked used in the same
  transaction, unique constraint on use) and expiry is checked against a stored timestamp.
- A DB constraint or trigger rejects the illegal state.

## Framework protections to check
- Generic update endpoints that accept `status`/`state` in the body bypass any dedicated
  transition endpoint (`PATCH /orders/{id}` with `{"status": "shipped"}`).
- Bulk/import/admin APIs that set state directly.
- Checks performed in the frontend wizard only.
- Expiry compared with a client-supplied timestamp; time zone confusion.
- Token lookup that does not bind the token to the user or purpose (reset token usable as
  invite token).

## confirmed_static when
The cited handler performs a cited state change or step effect, is reachable by the attacker in
the wrong state or without the prior step, and no guard on the path (including model hooks and
DB constraints) rejects it.

## Common false positives
- Transitions that are harmless in any order (e.g. editing a draft's title).
- Admin-only state overrides that are intended.

## Severity
Skipping payment/approval/verification: `high`/`critical`. Reusable one-time token with access
impact: `high`. Reversible cosmetic states: `low`.

## Remediation
Route all state changes through one guarded transition function; check server-side completion
markers; consume tokens atomically.
