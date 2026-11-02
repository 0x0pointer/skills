# Business-logic invariants: value-tampering, workflow-bypass, mass-assignment, race-condition

## What proves it
The server ends up in a state that breaks the invariant the hypothesis states, observed through
the app's **own server-computed data**: a negative total, a quantity below one, a status reached
without its prerequisite, a field the client must not set. `json_compare` checks the invariant
directly on a JSON response.

## Negative quantity / value tampering

```yaml
kind: http
hypothesis_id: H10
description: >
  POST /api/cart/items accepts a client quantity with no lower bound. Adding a product with
  quantity -1 makes the server-computed cart total negative (invariant: total >= 0).
users:
  alice:
    vars: {username: alice, password: alice-dev-pw}
    login:
      - name: alice_login
        method: POST
        path: /api/login
        json: {username: "${USER.username}", password: "${USER.password}"}
        expect_status: [200]
steps:
  - name: add_negative
    as: alice
    method: POST
    path: /api/cart/items
    json: {product_id: 2, quantity: -1}
  - name: view_cart
    as: alice
    path: /api/cart
    expect_status: [200]
oracles:
  - type: response_status
    step: add_negative
    status: [200, 201]
  - type: json_compare
    step: view_cart
    path: total
    op: lt
    value: 0
```

Read the invariant back from a **separate** step (the cart, the order, the balance), not only
from the tampering request's own response, so the oracle sees persisted state.

## Client-supplied price

Send a price the catalogue does not have and compare the persisted total with it:
`json_compare` `path: total`, `op: eq`, `value: 1` after posting `{"product_id": 2, "price": 1}`.
Use a value the real price can never equal.

## Workflow bypass

```yaml
kind: http
hypothesis_id: H11
description: >
  The new ship endpoint does not check the order was paid. alice creates an order and ships it
  without paying; the order then reports status shipped.
users:
  alice:
    vars: {username: alice, password: alice-dev-pw}
    login:
      - name: alice_login
        method: POST
        path: /api/login
        json: {username: "${USER.username}", password: "${USER.password}"}
        expect_status: [200]
steps:
  - name: create_order
    as: alice
    method: POST
    path: /api/orders
    json: {product_id: 1, quantity: 1}
    expect_status: [200, 201]
    extract:
      order_id: {json: id}
  - name: check_unpaid
    as: alice
    path: /api/orders/${USER.order_id}
  - name: ship
    as: alice
    method: POST
    path: /api/orders/${USER.order_id}/ship
  - name: check_shipped
    as: alice
    path: /api/orders/${USER.order_id}
oracles:
  - type: json_compare
    step: check_unpaid
    path: paid
    op: eq
    value: false
  - type: json_compare
    step: check_shipped
    path: status
    op: eq
    value: shipped
```

One-time tokens: redeem the same voucher twice; the second redeem must be refused, so the
oracle is `response_status` `[200, 201]` on the second step **plus** a `json_compare` on the
balance showing the credit twice.

## Mass assignment
Control step reads the protected field (`role eq user`), the update sends it
(`{"name": "x", "role": "admin"}`), a read-back step shows the new value (`role eq admin`).
Same shape as the `bfla` reference.

## Race conditions
PoC steps run one after another, so a check-then-act race usually cannot be shown. Report
`not_reproduced` with that explanation, or `blocked` when only concurrency can show it; do not
substitute a `script` loop for an HTTP proof.

## Pitfalls
- Compare like with like: `value: 0` for numbers, `value: false` for booleans, quoted strings
  for strings. A number returned as a string (`"-1200"`) needs a string comparison or a
  different field.
- A rejected request (`400`, `422`) followed by a read-back that shows nothing changed is a
  correct, safe app: make sure the control and the read-back cannot both pass on it.
