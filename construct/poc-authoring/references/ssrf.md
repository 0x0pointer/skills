# ssrf: proving server-side request forgery

## What proves it
The **server** sends a request to a destination the attacker chose. In the workbench every
unknown hostname resolves to the sink, so fetching `${CANARY.url}` lands there and is recorded
with the token in host and path. A `canary_hit` oracle then proves the server made the call,
even when the response is never shown to the attacker (blind SSRF).

## Steps
Send the canary URL in the parameter the hypothesis names (`url`, `webhook`, `avatar_url`,
`callback`, an XML/SVG reference, a redirect target the server follows).

```yaml
kind: http
hypothesis_id: H4
description: >
  POST /api/webhooks/test fetches the user-supplied url without an allowlist. The server
  requests the canary URL, which the sink records.
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
  - name: trigger
    as: alice
    method: POST
    path: /api/webhooks/test
    json: {url: "${CANARY.url}"}
oracles:
  - type: canary_hit
    value: ${CANARY.token}
```

## Variants
- **Scheme or host restrictions**: if the code requires `https`, use
  `https://${CANARY.host}/`; the sink records the TLS SNI host (which contains the token) before
  closing, so `canary_hit` still fires.
- **Host allowlist with a suffix check** (`endswith("example.com")`): try
  `http://${CANARY.host}/?x=example.com` or `http://example.com.${CANARY.host}/` only if the
  static analysis showed that exact flawed check.
- **Path-only control on a fixed internal host**: the request goes to that host, not the canary;
  stub the internal host and match the injected path with `canary_hit` (`value` = a path
  segment carrying `${CANARY.token}`).

## Pitfalls
- The sink records **everything** the app sends. An app that forwards request bodies to an error
  tracker or analytics host makes `canary_hit` on the token fire without SSRF. Check
  `prsec-canary hits --contains <token>` while authoring: the hit must be a request **to** the
  canary host, not a body that mentions it. If the app forwards bodies, put the token only in
  the canary host and also check the response shows the fetch happened.
- Do not target metadata services, internal admin ports or anything else real: the canary proves
  the primitive.
