# Trust boundaries

A tainted value can be attacker-controlled and still harmless because a control on the way
neutralises it. Equally, teams often *assume* a control exists that the code does not prove.
For each hypothesis, list the boundaries the value actually crosses and judge each one against
**this payload for this sink**.

## Typical boundaries

| Boundary | Control to look for | Where it lives in a repo |
|---|---|---|
| Internet -> edge | WAF, CDN rules, API gateway schema validation | IaC (`*.tf`, Helm values, ingress annotations), gateway config |
| Edge -> service | authentication middleware, mTLS, IP allowlists | middleware registration, security config, ingress |
| Authenticated -> authorised | role / permission / policy checks, ownership filters | guards, decorators, policy classes, query filters |
| Handler -> data layer | ORM parameter binding, repository methods, stored procedures | repositories, DAOs, query builders |
| Service -> service | signed internal tokens, network policy | service clients, mesh config |
| Webhook / queue -> handler | signature verification, schema validation, idempotency keys | webhook controllers, consumer setup |
| Server -> browser | output encoding, CSP, cookie flags | templates, response headers |

## Judging a control

Ask three questions and answer them with citations:

1. **Is the control on this path?** Middleware registered after the route, a guard on a sibling
   controller, a validator defined but not applied, or a policy only enforced in the UI does not
   count.
2. **Does it cover this field?** Schema validation of `amount` says nothing about `note`;
   authentication says nothing about whether the user may access *this* object.
3. **Does it neutralise this payload shape?** HTML escaping does not stop SQL injection; a
   blocklist of `127.0.0.1` does not stop `0x7f000001`, IPv6, DNS rebinding or redirects; a WAF
   signature for `' OR 1=1` does not stop time-based or JSON-encoded payloads.

If no control is visible in the repository, say "no control found in repository" in the
hypothesis `description` and do not list one in `assumed_guards`. Edge controls outside the repo
are unknown, not present.

## Preconditions and severity

| Who can reach the sink | Typical `severity_guess` ceiling (impact permitting) |
|---|---|
| Anonymous internet user | critical / high |
| Any authenticated user (self sign-up possible) | high |
| Authenticated user of a paying tenant, or a specific role | high / medium |
| Admin or internal-only network | medium / low |
| Nobody (dead code, trusted-only origin, neutralising control) | no hypothesis |
