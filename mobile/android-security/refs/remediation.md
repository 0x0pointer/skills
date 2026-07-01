# Android remediation patterns (secure-code reference)

Per-MASVS-category secure-vs-insecure code patterns for confirming a finding is real and advising the
fix. For actual patch generation, chain `/remediate` (it owns diffs + verification) — this ref is the
mobile-specific knowledge it lacks. Every fix pairs with a MASTG verification test.

| MASVS | Insecure → Secure |
|---|---|
| STORAGE | `SharedPreferences` plaintext → **EncryptedSharedPreferences** (Jetpack Security); SQLite → **SQLCipher**; keys → **AndroidKeyStore**; exclude sensitive data from `allowBackup`/`dataExtractionRules`. |
| CRYPTO | `AES/ECB`, `DES`, `MD5` → **AES-256-GCM** (random 12-byte IV), **SHA-256**, **PBKDF2 ≥ 600k** / Argon2; keys generated+stored in `AndroidKeyStore`, never hardcoded. |
| AUTH | Local-only auth → **server-side enforcement**; bind biometric to a KeyStore key with `setUserAuthenticationRequired(true)` + `BiometricPrompt` + `CryptoObject`; short-lived tokens, proper logout invalidation. |
| NETWORK | Trust-all `TrustManager`/`HostnameVerifier` → remove; enforce TLS 1.2+; **cert/public-key pinning** via `network_security_config <pin-set>` (Tier-3); no `cleartextTrafficPermitted`. |
| PLATFORM | `exported=true` without permission → set `exported=false` or add a signature permission; `PendingIntent` → `FLAG_IMMUTABLE`; WebView → disable `addJavascriptInterface` (or gate < API 17), `setAllowFileAccess(false)`, validate deeplink inputs. |
| CODE | Parameterized queries; validate `Intent` extras; strip `debuggable`/verbose logs in release; update vulnerable deps. |
| RESILIENCE (Tier-3) | Layered root/anti-debug/anti-hook + integrity/signature checks; obfuscate (R8/DexGuard) — defense-in-depth, not a single flippable boolean. |
| PRIVACY | Request minimum perms; gate SDK init behind consent; keep PII out of analytics events; align with Play Data-Safety. |

**Hard numbers:** AES-256-GCM · RSA ≥ 2048 (prefer EC P-256) · PBKDF2 ≥ 600k iterations · TLS 1.2+ ·
`kSecAttrAccessibleWhenUnlockedThisDeviceOnly`-equivalent (KeyStore user-auth-bound) for secrets.
