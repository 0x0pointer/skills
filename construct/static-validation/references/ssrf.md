# ssrf: Server-side request forgery

## Claim to verify
The attacker controls the destination (scheme, host, port, or full URL) of a request the
**server** makes, so it can reach internal services, cloud metadata, or arbitrary hosts.

## Refute if
- The host is fixed by the server and the attacker controls only a path or query component that
  is encoded (`encodeURIComponent`, `urllib.parse.quote`) and cannot change the authority.
  (Path-only control is still a finding if the fixed host is internal and the path reaches
  sensitive internal APIs: rate `low`/`medium`.)
- The URL is validated against an **allowlist of hosts** after parsing, the check is on the
  same parsed URL that is fetched, and redirects are disabled or re-validated.
- The value only comes from trusted configuration.

## Framework protections to check
- Denylist checks (`if "169.254" in url`, `if host == "localhost"`) are bypassable: decimal/hex
  IPs, IPv6 (`[::ffff:127.0.0.1]`), DNS names resolving to private IPs, DNS rebinding,
  redirects. Treat them as **ineffective** unless they check the resolved address at connect
  time.
- Parser differentials: validating with one parser (`URL`, `urlparse`) and fetching with another
  library can disagree on `user@host`, backslashes, and fragments.
- Clients that follow redirects by default: `requests`, `axios`, `fetch` (Node), Go
  `http.Client`, Java `HttpClient` (`NEVER` by default in `java.net.http`).
- Non-HTTP schemes: `file://` (`urlopen`, curl), `gopher://` (curl), `jar:`, `netdoc:`.

## confirmed_static when
A cited request parameter flows to the URL or host of a cited outbound call, the route is
reachable, and validation is absent or a bypassable denylist.

## Common false positives
- Webhook delivery to user-registered URLs where the product intends arbitrary destinations,
  **and** delivery runs from an isolated egress network that is visible in the repo config.
  (Without that evidence, it is still `plausible`.)
- Fetching from a fixed third-party API with a user-chosen resource id.

## Severity
Full URL control from an internet-reachable endpoint in a cloud environment: `high`/`critical`
(metadata credentials). Blind SSRF with no response returned: lower by one.

## Remediation
Allowlist destinations; resolve and reject private/link-local ranges at connect time; disable
redirects; restrict schemes.
