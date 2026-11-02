# race-condition: proving a check-then-act race

## What proves it
Several identical requests sent at the **same moment** all pass a check that should allow only
one (coupon redeemed once, balance never below zero, one vote per user). A step with
`parallel: N` sends N copies released together; a later, single read step shows the broken
invariant.

```yaml
kind: http
hypothesis_id: H8
description: >
  redeem() reads coupon.used, then sets it in a separate statement without a lock; concurrent
  redemptions all succeed and the account is credited several times.
users:
  alice:
    vars: {username: alice, password: "alice-pw"}
    login:
      - name: alice_login
        method: POST
        path: /login
        form: {username: "${USER.username}", password: "${USER.password}"}
        expect_status: [200, 302]
steps:
  - name: redeem
    as: alice
    method: POST
    path: /api/coupons/WELCOME10/redeem
    parallel: 10
    expect_status: [200, 409]
  - name: balance
    as: alice
    path: /api/account
oracles:
  - type: json_compare
    step: balance
    path: credit
    op: gt
    value: 10
```

## Pitfalls
- The oracle goes on the read-back step, not on the parallel step: ten `200`s may just mean the
  endpoint is idempotent.
- Races are timing dependent. If it fires only sometimes with `prsec-poc run`, raise `parallel`
  (up to 50). The replay must fire on every head run, so a flaky race ends `not_reproduced`;
  say what you saw in `reasoning`.
