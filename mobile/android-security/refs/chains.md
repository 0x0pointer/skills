# Android exploit chains — turn isolated findings into impact

A single high-severity chain beats three isolated lows. File the compound finding at terminal
blast-radius severity and record the chain with `report(action="chain", ...)` when each step is
backed by an artifact.

## Static → backend (no device)
- Decompiled code leaks a backend base URL + an API key → hit the API with `http()` → chain `/api-security`
  (BOLA/BFLA) → `/web-exploit` if a parameter is injectable. Mobile apps are just another API client;
  the backend is often the real prize.
- Firebase URL in resources → `<url>/.json` open read/write → data exposure.

## Exported component → data theft (often no root)
- Exported `ContentProvider` without permission → `content query --uri content://<auth>/...` → if it
  concatenates the selection, SQLi into the app's private DB → dump credentials/PII.
- Exported `Activity`/`Receiver` → `am start`/`am broadcast` with crafted extras → state change, auth
  bypass, or intent redirection to an internal WebView (→ XSS/JS-bridge RCE).

## Deeplink → WebView JS bridge → RCE
- Unvalidated deeplink loads an attacker URL into a WebView that exposes `addJavascriptInterface` →
  JS calls the bridged Java method → device-side code execution → chain `/post-exploit`.

## Dynamic pin bypass → traffic → backend
- `objection ... android sslpinning disable` → proxy captures the full API surface → feed endpoints to
  `/api-security`; recovered tokens land in `known_assets.auth_tokens` for authenticated deeper testing.

## Storage → credential reuse
- Runtime dump of SharedPreferences/SQLite/KeyStore → recovered session tokens/credentials → replay
  against the backend (authenticated BOLA) or other org assets.

## Embedded LLM
- The app calls an LLM endpoint (on-device or remote) → chain `/ai-redteam` (prompt injection, system-
  prompt leak, excessive agency).
