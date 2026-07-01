# iOS exploit chains — turn isolated findings into impact

File the compound finding at terminal blast-radius severity; record with `report(action="chain", ...)`
when each step is artifact-backed.

## Static → backend (no device)
- `strings`/class-dump leak a backend base URL + API key/token → hit it with `http()` → chain
  `/api-security` (BOLA/BFLA) → `/web-exploit` if a parameter is injectable. The backend is usually the
  real prize; the app is just an API client.
- Embedded 3rd-party service keys (analytics, cloud storage) → test for over-privilege/exposure.

## URL scheme / Universal Link → WKWebView JS bridge → code exec
- Unvalidated custom scheme (`CFBundleURLTypes`) loads attacker content into a WKWebView exposing a JS
  ↔ native bridge (`WKScriptMessageHandler`) → JS invokes native handlers → sensitive action or logic
  bypass → chain `/post-exploit` if device-side execution follows.

## Pin bypass → traffic → backend
- `objection ... ios sslpinning disable` → proxy captures the full API surface → feed endpoints to
  `/api-security`; recovered session tokens → authenticated deeper testing (`known_assets.auth_tokens`).

## Keychain / storage → credential reuse
- `ios keychain dump` + container file dump → recovered credentials/tokens → replay against the backend
  (authenticated BOLA) or lateral to other org assets.

## ATS disabled → MITM
- `NSAllowsArbitraryLoads` + no pinning → on-path attacker reads/modifies traffic → account takeover /
  content injection. Confirm dynamically with the proxy capture.

## Embedded LLM
- App calls an on-device or remote LLM → chain `/ai-redteam` (prompt injection, system-prompt leak,
  excessive agency).
