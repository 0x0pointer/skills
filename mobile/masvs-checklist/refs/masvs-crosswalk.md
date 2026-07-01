# MASVS 2.0 control → MASTG test crosswalk (Android + iOS)

The reference table for the compliance matrix. 8 groups. `needs_dynamic` = the control's honest
verdict requires runtime proof (mark it so, don't claim compliant on static alone). MASTG test IDs
use the v1.7+ renumbered scheme where noted (0200-series) alongside legacy IDs.

| MASVS control | What it asserts | Android MASTG | iOS MASTG | dynamic? |
|---|---|---|---|:--:|
| **STORAGE-1** | Sensitive data stored securely (Keystore/Keychain, encrypted) | 0001/0200 | 0052/0200 | partial |
| **STORAGE-2** | No sensitive-data leakage (logs, backups, clipboard, snapshots, IPC) | 0003/0011/0201/0202 | 0053/0058/0201/0202 | partial |
| **CRYPTO-1** | Strong, current cryptography (no DES/RC4/ECB/MD5/SHA1) | 0013/0014 | 0060/0061 | no |
| **CRYPTO-2** | Sound key management/lifecycle (Keystore/Keychain, no hardcoded keys) | 0013 | 0060 | no |
| **AUTH-1** | Auth enforced server-side; secure local auth | 0017 | 0064 | needs_dynamic |
| **AUTH-2** | Sensitive ops need fresh auth (step-up / biometric bound to KeyStore) | 0018 | 0065 | needs_dynamic |
| **AUTH-3** | Secure session handling (invalidation, token storage) | 0019 | 0066 | partial |
| **NETWORK-1** | Encrypted transport; no cleartext; correct TLS config | 0020/0021 | 0067/0068 | needs_dynamic |
| **NETWORK-2** | Cert validation / pinning where warranted (no bypass) | 0022 | 0069 | **needs_dynamic** |
| **PLATFORM-1** | IPC secured (exported components, providers, PendingIntent) | 0029/0030 | 0075/0076 | partial |
| **PLATFORM-2** | WebView hardened (no unsafe JS bridge / file access) | 0031/0033 | 0077 | partial |
| **PLATFORM-3** | UI/sensitive-data exposure (deeplinks, keyboard, screenshots) | 0034 | 0078 | partial |
| **CODE-1** | Up-to-date platform / no known-vuln deps | 0035 | 0079 | no |
| **CODE-2** | Secure inputs / no injection sinks | 0036 | 0080 | no |
| **CODE-3** | Debugging symbols/flags removed in release | 0037 | 0081 | no |
| **CODE-4** | Exceptions handled; no sensitive info in errors | 0038 | 0082 | no |
| **RESILIENCE-1** | Anti-tamper / integrity + root/jailbreak detection | 0044/0045 | 0088/0089 | **needs_dynamic** |
| **RESILIENCE-2** | Anti-debug / anti-hooking / emulator detection | 0047/0048 | 0090/0091 | **needs_dynamic** |
| **RESILIENCE-3** | Code obfuscation | 0049 | 0092 | partial |
| **RESILIENCE-4** | Device-binding / no unauthorized instance | 0050 | 0093 | needs_dynamic |
| **PRIVACY-1** | Data minimization / justified permissions | 0003/manifest | 0053/plist | no |
| **PRIVACY-2** | Consent before tracking (ATT, AD_ID, SDK init gating) | manifest/SDK | NSUserTracking | partial |
| **PRIVACY-3** | Transparency (privacy manifest, data-safety) | data-safety | PrivacyInfo.xcprivacy | no |
| **PRIVACY-4** | User controls (delete/export, opt-out) | app-flow | app-flow | partial |

Notes:
- `needs_dynamic` controls (NETWORK-2 pinning, RESILIENCE-1/2/4, AUTH-1/2) — a Frida/objection artifact
  proving the control holds (or is bypassable) is required before a `compliant`/`non_compliant` verdict.
- Tier gating: STORAGE/CRYPTO/AUTH/PLATFORM/PRIVACY = Tier 2+; RESILIENCE + NETWORK-2 pinning = Tier 3.
- Confirm exact current MASTG IDs at mas.owasp.org/MASTG — the scheme is periodically renumbered.
