# iOS static analysis — MASTG checklist (no Apple hardware needed)

MobSF report is the spine; confirm heuristics against the binary/plist before filing.

## Extract & read
`unzip <app>.ipa` → `Payload/<App>.app/`. Key artifacts: `Info.plist`, the Mach-O binary
(`<App>.app/<App>`), embedded `.framework`/`PlugIns`, `embedded.mobileprovision`.

## Info.plist (MASVS-NETWORK / PLATFORM)
- **ATS**: `NSAppTransportSecurity` → `NSAllowsArbitraryLoads=true` (HTTP everywhere), per-domain
  `NSExceptionAllowsInsecureHTTPLoads`, `NSExceptionMinimumTLSVersion` downgrades → MASVS-NETWORK.
- **Custom URL schemes**: `CFBundleURLTypes[].CFBundleURLSchemes` → hijackable / unvalidated deeplink
  entry points → MASVS-PLATFORM.
- **Universal Links**: `com.apple.developer.associated-domains` + the server's `apple-app-site-association`
  — check link validation.
- Usage-description strings hint at sensitive capabilities (camera, location, contacts).

## Binary (MASVS-CODE / CRYPTO / RESILIENCE)
- `class-dump <binary>` → Obj-C class/method surface (auth, crypto, storage classes worth hooking).
- `otool -L <binary>` → linked frameworks/dylibs → vulnerable third-party pods.
- `otool -hv <binary>` → `PIE` flag (ASLR); `nm`/`strings` → hardcoded secrets, endpoints, debug strings.
- Encryption: `otool -l | grep -A4 LC_ENCRYPTION_INFO` → `cryptid 1` = FairPlay-encrypted (App Store IPA);
  full static analysis needs a **decrypted** IPA (device-gated via frida-ios-dump).
- `LocalAuthentication`/`SecItem*` usage → biometric/Keychain review.

## Storage (MASVS-STORAGE)
- `NSUserDefaults` / `*.plist` in the bundle or container holding secrets.
- Keychain accessibility class in code: `kSecAttrAccessibleAlways`/`...AfterFirstUnlock` = weaker than
  `...WhenUnlockedThisDeviceOnly`.
- `UIPasteboard.general` writes of sensitive data; missing snapshot protection on backgrounding.

## Source mode (when available)
`scan(tool="mobsfscan", target=<src>)` + `scan(tool="trufflehog", target=<src>)`; chain `/codebase`.
Pin with `session(action="set_codebase")` so trace citations resolve.

## Grep batteries by MASVS category (iOS)
Run AFTER the sensitive-data inventory (classify-first). Each hit → mitigation gate → MASTG ID → finding.

### MASVS-CRYPTO (0060/0061) — inventory then adjudicate
- Sinks: `CCCrypt`, `SecKeyCreateEncryptedData`, `CryptoKit` (`AES.GCM`, `SHA256`), `CommonCrypto`, `SecRandomCopyBytes`.
- **Weak (CRITICAL):** `kCCAlgorithmDES/3DES`, `kCCOptionECBMode`, `CC_MD5`, `CC_SHA1`, hardcoded keys/IVs, `arc4random`-for-keys, RSA < 2048.
- **Acceptable (verify):** `AES.GCM` (256-bit), `SHA-256/512`, `SecRandomCopyBytes` for IV/keys, keys in Keychain/Secure Enclave.

### MASVS-NETWORK (0067/0068/0069)
- ATS: `NSAppTransportSecurity` → `NSAllowsArbitraryLoads=true`, per-domain `NSExceptionAllowsInsecureHTTPLoads`, `NSExceptionMinimumTLSVersion` downgrades.
- Pinning bypass sinks (HIGH): `URLSession(...delegate)` `urlSession(_:didReceive:completionHandler:)` calling `.useCredential` unconditionally, `SecTrustEvaluate` ignored, trust-all `URLCredential(trust:)`. Pinning appropriateness = Tier-3 gate.

### MASVS-CODE (0079-0082)
- Injection/sinks (mitigation gate): `sqlite3_exec`/string-built SQL, `WKWebView.evaluateJavaScript` with untrusted input, `loadHTMLString`, `NSExpression`/`objc_msgSend` dynamic dispatch on input, format-string `%@`/`String(format:)` with user data.
- Deps: CocoaPods/SPM/Carthage manifests → known-CVE check. Release hygiene: `get-task-allow` (debug), `#if DEBUG` guards, `NSLog` in release, symbols not stripped.

### MASVS-RESILIENCE (0088-0093) — detection signatures (confirm dynamically!)
- Jailbreak detection: checks for `/Applications/Cydia.app`, `/bin/bash`, `/etc/apt`, `fork()` success, `canOpenURL:cydia://`, suspicious dylibs.
- Anti-debug: `ptrace(PT_DENY_ATTACH)`, `sysctl` `P_TRACED`, `isatty`. Anti-hook: Frida/Substrate string checks.
- Obfuscation: symbol mangling / control-flow flattening vs plain Obj-C selectors.
- **Never credit on static presence alone** — Phase 2 proves whether it holds (SKILL Phase 2 rubric).

## MASTG test-ID crosswalk
Tag each finding with its MASTG ID (see `../../masvs-checklist/refs/masvs-crosswalk.md` for the full
per-control Android+iOS table) — audit-grade, standards-traceable results.

## Filing
MASVS category in the title, e.g. `MASVS-NETWORK: ATS disabled via NSAllowsArbitraryLoads`. Cite the
plist key or class-dump/binary evidence.
