# iOS remediation patterns (secure-code reference)

Per-MASVS secure-vs-insecure patterns for confirming findings and advising fixes. For patch
generation chain `/remediate` — this ref is the iOS-specific knowledge it lacks. Every fix pairs with
a MASTG verification test.

| MASVS | Insecure → Secure |
|---|---|
| STORAGE | Secrets in `UserDefaults`/plist → **Keychain** (`SecItemAdd`) with `kSecAttrAccessibleWhenUnlockedThisDeviceOnly`; files → `NSFileProtectionComplete`; mark sensitive files `isExcludedFromBackup`; obscure snapshot in `applicationDidEnterBackground`. |
| CRYPTO | `kCCAlgorithmDES`, ECB, `CC_MD5` → **AES-256-GCM** (`CryptoKit`), **SHA-256**, keys in Keychain/**Secure Enclave**; `SecRandomCopyBytes` for IV/keys; never hardcode. |
| AUTH | Local-only → **server-side enforcement**; `LAContext.evaluatePolicy` bound to a Keychain item with `kSecAccessControlBiometryCurrentSet` (invalidates on biometric change); check `evaluatedPolicyDomainState`; short-lived tokens. |
| NETWORK | Remove `NSAllowsArbitraryLoads`; TLS 1.2+; **cert/public-key pinning** in the `URLSession` delegate (Tier-3); validate `SecTrust`. |
| PLATFORM | Validate custom-URL-scheme + Universal-Link inputs; WKWebView: no unsafe `WKScriptMessageHandler` bridges, disable `allowFileAccessFromFileURLs`; guard pasteboard writes; `secureTextEntry` for sensitive fields. |
| CODE | Parameterized SQL; sanitize WKWebView input; strip `get-task-allow`/symbols + `NSLog` in release; update pods/SPM deps. |
| RESILIENCE (Tier-3) | Layered jailbreak + `PT_DENY_ATTACH` anti-debug + anti-hook + integrity checks; obfuscation — defense-in-depth, not one flippable check. |
| PRIVACY | Minimal purpose-strings; ATT before IDFA/tracking-SDK init; accurate `PrivacyInfo.xcprivacy` + App Store label; keep PII out of analytics. |

**Hard numbers:** AES-256-GCM · RSA ≥ 2048 (prefer EC P-256) · TLS 1.2+ · Keychain
`kSecAttrAccessibleWhenUnlockedThisDeviceOnly` (or biometry-bound) for secrets · Secure Enclave for keys where possible.
