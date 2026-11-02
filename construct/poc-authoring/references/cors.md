# cors: proving a credentialed CORS misconfiguration

## What proves it
A request with an attacker `Origin` gets that origin back in `Access-Control-Allow-Origin`
**and** `Access-Control-Allow-Credentials: true`, on a route that returns the victim's data.
Then any site can read the victim's data with the victim's cookies.

```yaml
kind: http
hypothesis_id: H6
description: >
  The new CORS middleware reflects any Origin and allows credentials; /api/me returns the
  logged-in user's profile to any site.
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
  - name: cross_origin_read
    as: alice
    path: /api/me
    headers:
      Origin: http://${CANARY.host}
oracles:
  - type: response_header
    step: cross_origin_read
    name: Access-Control-Allow-Origin
    op: equals
    value: http://${CANARY.host}
  - type: response_header
    step: cross_origin_read
    name: Access-Control-Allow-Credentials
    op: equals
    value: "true"
  - type: response_contains
    step: cross_origin_read
    value: alice
```

## Pitfalls
- `Access-Control-Allow-Origin: *` without credentials is not this bug (browsers do not send
  cookies then).
- The route must return something private; a public endpoint with permissive CORS is fine.
