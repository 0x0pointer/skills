# open-redirect: proving an open redirect

## What proves it
The app answers a request carrying an attacker-chosen URL with a redirect **to that URL**. The
replay never follows redirects, so the `3xx` and its `Location` header are the step's own
response. Use the canary host as the target: it is fresh per run, so a fixed app that redirects
to a constant can never match it.

```yaml
kind: http
hypothesis_id: H4
description: >
  /login?next= is passed to redirect() without checking that it is a local path; an anonymous
  attacker sends the victim to an external host.
steps:
  - name: login_next
    path: /login
    query:
      next: http://${CANARY.host}/landing
oracles:
  - type: response_status
    step: login_next
    status: [301, 302, 303, 307, 308]
  - type: response_header
    step: login_next
    name: Location
    op: starts_with
    value: http://${CANARY.host}
```

## Variants
- Protocol-relative `//${CANARY.host}/x` and backslash `/\${CANARY.host}` bypass naive
  "starts with /" checks: keep the same oracle (`Location` `contains` `${CANARY.host}`).
- If the redirect only happens after login, add the user and its `login` steps.
- A redirect that only happens in client JavaScript cannot be proven without a browser:
  report `blocked`.

## Pitfalls
- `Location: /landing` or a redirect to the app's own host is not the bug: the oracle must
  name the canary host.
