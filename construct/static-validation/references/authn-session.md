# authn-session: Authentication and session weaknesses

## Claim to verify
An attacker can authenticate as someone else, or keep or obtain a session they should not have:
missing authentication on a route, a bypassable auth check, broken token validation, session
fixation, sessions not invalidated on logout/password change, account-recovery flaws, missing
brute-force protection on credential or OTP checks.

## Refute if
- The route is covered by authentication middleware/config on this exact path (check mount
  point, filter-chain order, `permitAll`/`AllowAnonymous`/`@Public` exceptions).
- Token validation checks signature, algorithm, expiry, issuer and audience with a vetted
  library.
- Session id is regenerated on login (framework default in Django, Rails, Spring Security,
  ASP.NET Core Identity, Laravel `session()->regenerate()`).
- Attempt limiting exists for the credential/OTP endpoint (middleware, decorator, gateway rule
  visible in the repo).

## Framework protections to check
- Middleware conditions inverted or short-circuited (`if token and not verify(token)` lets a
  missing token through).
- Auth errors that fall through (`catch` -> `next()`), optional-auth dependencies used on
  protected routes (`get_current_user_optional`).
- JWT: signature not verified, `alg` not pinned, `exp` ignored, `kid` used to load keys from
  attacker-chosen paths/URLs.
- Password reset: token not bound to the user, not single-use, not expiring, host header used to
  build the reset link, user enumeration that matters to the product.
- OAuth/OIDC login: `state` not checked, `email` claim used as identity without `email_verified`
  or issuer check, account linking by email.
- Cookie flags: missing `Secure`/`HttpOnly`/`SameSite` (usually `low` on their own).

## confirmed_static when
The cited flaw is on a reachable path and leads to a concrete impersonation, bypass, or
session-retention scenario you can describe step by step from the cited code.

## Common false positives
- Health and metrics endpoints intentionally public.
- Rate limiting done at the gateway when the gateway config is in the repo and covers the route.

## Severity
Authentication bypass or account takeover: `critical`. Brute-forceable OTP: `high`. Missing
session invalidation: `medium`. Cookie flags alone: `low`.

## Remediation
Apply the standard auth middleware to the route, validate tokens fully, regenerate sessions on
privilege change, and rate-limit credential checks.
