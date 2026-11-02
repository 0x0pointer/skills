# cookie-flags: proving a session cookie without HttpOnly / Secure / SameSite

## What proves it
The response that sets the **session** cookie sets it without the flag the hypothesis says is
missing. Check every `Set-Cookie` value with a regex anchored on the cookie name, so another
cookie that does carry the flag cannot satisfy or hide the check.

```yaml
kind: http
hypothesis_id: H7
description: >
  The new login handler sets the session cookie with set_cookie(..., httponly=False); script
  on any page of the origin can read the session id.
steps:
  - name: login
    method: POST
    path: /login
    form: {username: alice, password: "alice-pw"}
oracles:
  - type: response_header
    step: login
    name: Set-Cookie
    op: regex
    value: "^session=(?!.*;\\s*HttpOnly)"
```

## Pitfalls
- Name the real session cookie (read the code); a `theme=` cookie without flags is not a finding.
- `Secure` is only a finding for apps served over HTTPS in production; say so in `reasoning`.
