# Android static analysis — MASTG checklist (no device needed)

The MobSF report is the spine; confirm its heuristics against decompiled source before filing
(MobSF is high-recall, low-precision — bulk-importing produces noise).

## Manifest (apktool d → AndroidManifest.xml)
- **Exported components** (`android:exported="true"` or an `<intent-filter>` with no permission):
  activities, services, providers, receivers. Each is an IPC entry point — MASVS-PLATFORM.
- `android:allowBackup="true"` → `adb backup` can exfiltrate app data (MASVS-STORAGE).
- `android:debuggable="true"` → attach a debugger, dump memory (MASVS-RESILIENCE/CODE).
- `usesCleartextTraffic="true"` or missing → HTTP allowed (MASVS-NETWORK).
- `<network-security-config>` (res/xml): `cleartextTrafficPermitted`, `trust-anchors` (user CAs = pin bypass), pin-set presence.
- Deeplinks: `<intent-filter>` with `<data android:scheme=.../>` — candidate for intent redirection / unvalidated navigation.
- `minSdkVersion` low → legacy platform weaknesses in scope.

## Code (jadx -d) — MASTG data flows
- **Secrets**: API keys, tokens, cloud creds in `strings.xml`, `BuildConfig`, or decompiled code → cross-check with `scan(tool="trufflehog")`.
- **Crypto**: `Cipher.getInstance("DES"|"AES/ECB"|...)`, `MessageDigest MD5/SHA1`, hardcoded `SecretKeySpec`/IV, `Random` for key material → MASVS-CRYPTO.
- **Storage**: `MODE_WORLD_READABLE/WRITEABLE`, `getExternalStorage*` for sensitive data, `SharedPreferences` holding secrets, verbose `Log.*` of PII → MASVS-STORAGE.
- **WebView**: `setJavaScriptEnabled(true)` + `addJavascriptInterface(...)` (RCE bridge < API 17; still risky), `setAllowFileAccess`/`AllowUniversalAccessFromFileURLs`, `onReceivedSslError → proceed()` → MASVS-PLATFORM.
- **Injection sinks**: raw `SQLiteDatabase.rawQuery`/`execSQL` with concatenation, `Runtime.exec`, dynamic `Class.forName`/`DexClassLoader`.
- **Firebase**: a `*.firebaseio.com` URL → test `<url>/.json` for open read (MASVS-CODE/NETWORK).

## Source mode (when available)
`scan(tool="mobsfscan", target=<src>)` + `scan(tool="trufflehog", target=<src>)`, and chain `/codebase`
for ASVS-depth source review. Pin the decompiled/source tree with `session(action="set_codebase")`
so trace citations resolve.

## Filing
Put the MASVS category in the finding title, e.g. `MASVS-STORAGE: sensitive data in world-readable
SharedPreferences`. Include the manifest/smali/java `file:line` evidence.

## Grep batteries by MASVS category (Android)
Run these AFTER the sensitive-data inventory (classify-first). Each hit → mitigation gate → MASTG ID → file finding.

### MASVS-CRYPTO (0013/0014) — inventory then adjudicate
Enumerate every crypto op, then classify against two lists (deprecated = auto-CRITICAL; acceptable = verify params):
- Sinks: `Cipher.getInstance`, `MessageDigest.getInstance`, `KeyGenerator`, `KeyPairGenerator`, `SecretKeySpec`, `IvParameterSpec`, `KeyGenParameterSpec`, `MessageDigest`, `Mac`.
- **Deprecated/weak (CRITICAL):** `DES`, `3DES/DESede`, `RC4`, `Blowfish`, `AES/ECB`, `MD5`, `SHA-1`, `RSA/…/NoPadding` or `PKCS1`, hardcoded `SecretKeySpec`/IV, `new Random()` for key/IV, PBKDF2 iterations < 600k.
- **Acceptable (verify):** `AES/GCM/NoPadding` (256-bit, random 12-byte IV), `SHA-256/512`, `RSA-OAEP` ≥ 2048, `EC` P-256+, keys in `AndroidKeyStore` with `setUserAuthenticationRequired` where warranted.

### MASVS-NETWORK (0020/0021/0022) — cert-validation-bypass sinks
- Bypass sinks (all HIGH): empty `checkServerTrusted`/`checkClientTrusted` body, `X509TrustManager` accepting all, `HostnameVerifier` returning `true`, `ALLOW_ALL_HOSTNAME_VERIFIER`, `SSLSocketFactory` with a trust-all `TrustManager`, `setHostnameVerifier`, `@SuppressLint("TrustAllX509TrustManager")`, `WebViewClient.onReceivedSslError → handler.proceed()`.
- Config: `usesCleartextTraffic`, `network_security_config` (`cleartextTrafficPermitted="true"`, user `trust-anchors`, missing `<pin-set>`). Pinning appropriateness = Tier-3 gate.

### MASVS-CODE (0035-0038) — injection sinks + hygiene
- Injection (mitigation gate = parameterized/sanitized): `rawQuery`/`execSQL` with concatenation, `loadUrl("javascript:")`/`evaluateJavascript`, `Runtime.exec`, dynamic `Class.forName`/`DexClassLoader`, `ObjectInputStream`/`readObject` (deserialization), unvalidated `Intent` extras used as sinks.
- Deps: `build.gradle` third-party versions → known-CVE check. Debug: `android:debuggable`, `BuildConfig.DEBUG` guards, verbose logging in release.

### MASVS-RESILIENCE (0044-0050) — detection signatures (confirm dynamically!)
- Root detection: `RootBeer`, `isRooted`, `su`/`Superuser.apk`/`Magisk`/`busybox`, `Build.TAGS`/`test-keys`, `SafetyNet`/`PlayIntegrity`.
- Anti-debug/hook: `Debug.isDebuggerConnected`, `TracerPid`, Frida/Xposed string checks, `ptrace`.
- Obfuscation: presence of ProGuard/R8/DexGuard mapping vs plain class names.
- **Never credit on static presence alone** — Phase 2 must prove whether it holds (see SKILL Phase 2 rubric).

## MASTG test-ID crosswalk
Tag each finding with its MASTG ID (see `../../masvs-checklist/refs/masvs-crosswalk.md` for the full
per-control Android+iOS table). This turns observations into standards-traceable, audit-grade results.
