# open-redirect: Open redirect

## Claim to verify
The server redirects the browser to an attacker-chosen absolute URL, enabling phishing or
token theft (OAuth `redirect_uri`, post-login `next`).

## Refute if
- Only relative paths are accepted and the check rejects `//host`, `/\host`, `\\host`,
  `https:` and other schemes (`url_has_allowed_host_and_scheme`, `Url.IsLocalUrl`,
  `LocalRedirect`, a parsed-URL check that host is empty **and** path starts with a single `/`
  not followed by `/` or `\`).
- The destination is chosen from a server-side allowlist or map.
- The value is a route name, not a URL (`redirect()->route($name)` with a fixed set).

## Framework protections to check
- `startsWith("/")` alone is bypassable (`//evil.com`, `/\evil.com`).
- `startsWith("https://good.com")` is bypassable (`https://good.com.evil.com`,
  `https://good.com@evil.com`).
- Regex without anchors or with unescaped dots.
- Parsing with one library and redirecting with another.

## confirmed_static when
A cited request value reaches a cited redirect sink on a reachable path with no effective check.

## Common false positives
- Redirects to a URL stored by an admin in config.

## Severity
Usually `low`/`medium`. `high` when it leaks OAuth codes or tokens (redirect after auth with
token in URL or fragment), or bypasses an allowlisted `redirect_uri`.

## Remediation
Accept only relative paths validated with the framework's safe helper, or map to an allowlist.
