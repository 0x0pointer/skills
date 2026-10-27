# Abuse-case checklist

Run through the rows that apply to the flow the PR touches. Each row is a question to answer
from the code; keep only those where the answer is "nothing stops it".

## Who

- Can user B perform this action on user A's object by substituting an id (path, query, body,
  nested object id, GraphQL node id)?
- Can a member of tenant X reach tenant Y's object, or pass `tenant_id` / `org_id` explicitly?
- Can a lower role call the new action? Is the role check on the handler, or only on the page
  that links to it?
- Can the actor be chosen by the client (`from_user_id`, `created_by`)?
- What happens when the check itself fails (timeout, missing config, exception)? Allow or deny?

## What

- Which fields of the request end up persisted? Are any of them privileged (role, status,
  price, owner, tenant, verified)?
- Which fields of the response are new? Do any belong to other users or reveal internals?

## How much

- `quantity`, `amount`, `count`: what do `0`, `-1`, `0.001`, `1e9`, `2147483648`, `"1"`, `null`,
  `[1, 2]` do? Is the value bounded server-side?
- Is the price / total / discount / fee computed by the server or taken from the request?
- Can a discount be applied twice, stacked with another, or applied after the total is fixed?
- Can a limit (seats, quota, credits, file size) be exceeded via update, import, bulk or a second
  endpoint that skips the check?

## In what order

- Can step N be called without step N-1 (confirm without pay, ship without approve, activate
  without verify)?
- Can a terminal state be left (cancelled -> active, refunded -> paid)?
- Can the client set the state field directly through a generic update endpoint?
- Can a one-time token / code / link be used twice, after expiry, or by another account?

## How often and how fast

- What happens if the same request is sent twice in parallel? Twice in sequence?
- Is there a read-then-write gap on a balance, stock level, counter or quota?
- Does a retried webhook or message cause the side effect twice?
- Is a rate or attempt limit keyed on something the attacker can vary (IP header, username case)?

## When

- Is expiry evaluated against server-stored data?
- Can a promotion or trial be re-entered by cancelling and re-subscribing?
- Are scheduled jobs operating on objects whose state may have changed since they were queued?

## Expressing the result

For each surviving abuse case, the hypothesis `sink` is the line that should have enforced the
rule (the unscoped query, the persisted tampered field, the unchecked transition, the racy
write). If several lines share the blame, cite the one closest to the effect as `sink` and the
others in `path[]`.
