# idor: proving missing object-level authorization

## What proves it
User **A** reads or changes an object that belongs to user **B** (or to another tenant)
through the new or changed endpoint, and the same data is **not** visible to A through the
legitimate path.

## Setup
- Two principals with the **same role**, each owning at least one object: `alice` and `bob`
  (different tenants in a multi-tenant app). Seed them in the EnvSpec or sign them up in their
  `login` steps; see the mocking skill.
- B's object should carry a distinctive value (a seeded note, or one B writes in a PoC step with
  `${CANARY.token}` in it) so the oracle matches B's data and nothing else.

## Steps
1. B lists or creates his object and `extract`s its id and the distinctive value.
2. Control: A's own listing does **not** contain B's value (`negate: true`).
3. Exploit: A requests B's object by id; it returns B's value (read) or changes it (write).

```yaml
kind: http
hypothesis_id: H2
description: >
  bob creates a note containing a canary; alice cannot see it in her own list, but
  GET /api/notes/<bob's id> as alice returns it.
users:
  alice:
    vars: {username: alice, password: alice-dev-pw}
    login:
      - name: alice_login
        method: POST
        path: /api/login
        json: {username: "${USER.username}", password: "${USER.password}"}
        expect_status: [200]
  bob:
    vars: {username: bob, password: bob-dev-pw}
    login:
      - name: bob_login
        method: POST
        path: /api/login
        json: {username: "${USER.username}", password: "${USER.password}"}
        expect_status: [200]
steps:
  - name: bob_creates
    as: bob
    method: POST
    path: /api/notes
    json: {text: "bob-private-${CANARY.token}"}
    expect_status: [200, 201]
    extract:
      note_id: {json: id}
  - name: alice_own_list
    as: alice
    path: /api/notes
    expect_status: [200]
  - name: alice_reads_bob
    as: alice
    path: /api/notes/${USERS.bob.note_id}
oracles:
  - type: response_contains
    step: alice_own_list
    value: bob-private-${CANARY.token}
    negate: true
  - type: response_contains
    step: alice_reads_bob
    value: bob-private-${CANARY.token}
```

## Write variants
For `PUT` / `PATCH` / `DELETE` on B's object, A changes it to a canary value (or deletes it) and
a **final step as B** reads the object back; the oracle runs on B's step. Only touch objects the
PoC or the seed created.

## Pitfalls
- Both users being admins, or the endpoint being intentionally public, proves nothing.
- A 200 alone is not proof: many apps answer 200 with an empty body or with A's own object.
  Always match B's distinctive value.
- An empty extracted value matches every response; the negative control on A's own list catches
  that, keep it.
