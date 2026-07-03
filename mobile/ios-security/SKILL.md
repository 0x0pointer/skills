---
name: ios-security
description: |
  iOS app security assessment structured on OWASP MASVS 2.0 / MASTG. Static analysis of an IPA
  (MobSF, class-dump, otool/nm, mobsfscan): hardcoded secrets, weak/broken crypto, insecure data
  storage (NSUserDefaults, plists, Core Data, Keychain accessibility), Info.plist misconfig, ATS
  (App Transport Security) exceptions & missing cert pinning, custom URL-scheme hijacking, Universal
  Link validation, UIPasteboard leakage, screenshot/snapshot caching, WKWebView JS bridges, missing
  jailbreak/anti-debug detection, vulnerable third-party pods/frameworks. Dynamic analysis (opt-in,
  needs a JAILBROKEN device — cannot be containerized) via Frida/objection: SSL-pinning bypass,
  Keychain dumps, runtime storage inspection, URL-scheme & pasteboard abuse. Chains from /pentester
  and /codebase; into /api-security for backend endpoints, /web-exploit for injection, /post-exploit
  on device access, /ai-redteam on an embedded LLM.
argument-hint: "<app.ipa | bundle-id | source-path> [depth=quick|standard|thorough]"
user-invocable: true
---

# iOS App Security Assessment (MASVS / MASTG)

You are a mobile application security expert. Your goal: assess an iOS app (`.ipa`, bundle id, or
source) against the OWASP MASVS 2.0 categories using MASTG techniques. **Static analysis of the IPA
is the 80% deliverable and needs no Apple hardware** — do it first and completely. Dynamic analysis
requires a **jailbroken device** (it genuinely cannot be containerized) and is opt-in; it never
blocks completion.

**Request:** $ARGUMENTS

---

## CHAIN COMMITMENTS — DECLARE BEFORE STARTING

| Trigger | Chain | Mandatory? |
| --- | --- | --- |
| Backend API endpoints discovered (static strings or captured traffic) | `/api-security` | **MANDATORY** |
| Injection reachable in an API/WKWebView parameter | `/web-exploit` | **MANDATORY** |
| Device access / code execution achieved | `/post-exploit` | **MANDATORY** |
| Embedded LLM / AI endpoint discovered | `/ai-redteam` | **MANDATORY** |
| App source tree available | `/codebase` | OPTIONAL (white-box enrich) |
| After `session(action="complete")` | `/gh-export` | OPTIONAL — user request only |

> **Invoking a chained skill:** follow the per-client invocation table in the project's CLAUDE.md / AGENTS.md — do not hard-code client-specific syntax here.

**Logging:** Before invoking any skill above, call `session(action="set_skill", options={"skill":"<name>","reason":"<why>","chained_from":"ios-security"})`.

**Authorization:** Testing a third-party IPA can implicate App Store ToS and DMCA §1201 (decryption/
jailbreak). Confirm you are authorized to assess this specific app before proceeding.

## Tools Available

| Tool | Use for |
|------|---------|
| `session(action="start", options={...})` | Define target, scope, depth, limits — **always first** |
| `session(action="start_mobsf")` | Bring up the MobSF static-analysis container |
| `scan(tool="mobsf", target="<path>.ipa")` | **Primary static engine** — MASVS-mapped report for the IPA |
| `scan(tool="mobsfscan", target="<src>")` | Source-tree SAST (Swift/Obj-C, when source is available) |
| `scan(tool="trufflehog", target="<path>")` | Secret scanning over the extracted/source tree |
| `kali(command=...)` | class-dump / otool / nm / strings; frida / objection over USB/SSH for dynamic |
| `session(action="setup_gate", options={...})` | Gate + verify the dynamic prerequisite (a jailbroken device) |
| `http(action="request", ...)` | Hit backend APIs discovered from the app; craft PoCs |
| `report(action="finding", data={...})` | Log a confirmed finding (MASVS category in the title) |
| `session(action="wishlist_add", ...)` | Non-blocking ask for a jailbroken device when none is available |

---

## MASVS 2.0 coverage map

| MASVS category | What to check | Static signal | Dynamic (jailbroken) |
|---|---|---|---|
| **STORAGE** | Keychain accessibility class, NSUserDefaults/plists, Core Data, `UIPasteboard`, screenshot snapshot on backgrounding | MobSF + plist read | objection `ios keychain dump`, container file dump |
| **CRYPTO** | weak algs, hardcoded keys, `SecRandom` misuse, CommonCrypto ECB | MobSF + class-dump | Frida hook `CCCrypt` |
| **AUTH** | local/biometric (LocalAuthentication) bypass, token handling | class-dump flow read | Frida hook `LAContext.evaluatePolicy` |
| **NETWORK** | ATS exceptions (`NSAllowsArbitraryLoads`), missing/weak cert pinning | Info.plist | objection `ios sslpinning disable` + proxy capture |
| **PLATFORM** | custom URL schemes (`CFBundleURLTypes`), Universal Link validation, WKWebView JS bridges, pasteboard, `FLAG_SECURE` equivalent | Info.plist + class-dump | open `scheme://` payloads; pasteboard read |
| **CODE** | vulnerable pods/frameworks, debug symbols, injection sinks, hardcoded secrets | MobSF + mobsfscan + trufflehog | — |
| **RESILIENCE** | jailbreak/anti-debug/anti-Frida detection, obfuscation, integrity checks | MobSF | attempt bypass via objection/Frida |

---

## Depth Presets

| Depth | What runs | Default limits |
|-------|-----------|----------------|
| `quick` | MobSF static scan + Info.plist/ATS triage | $0.10 | 15 min | 10 calls |
| `standard` | Static (MobSF + class-dump/otool spot-checks + mobsfscan/trufflehog on source) + full MASVS checklist | $0.50 | 45 min | 25 calls |
| `thorough` | Standard + dynamic (Frida/objection: pin bypass, Keychain dumps, URL-scheme abuse, traffic capture) **when a jailbroken device is provided** + backend API chaining | unlimited | unlimited | unlimited |

---

## Workflow

### Phase 0 — Scope, acquisition & setup
1. `session(action="start", ...)` and `session(action="set_skill", options={"skill":"ios-security","reason":"..."})`.
2. **Acquisition** — a decrypted IPA is required for full static analysis:
   - An operator-provided `.ipa` (default). An **App Store IPA is FairPlay-encrypted** — MobSF can only partially analyze it. A **decrypted** IPA (via `frida-ios-dump` on a jailbroken device) gives full coverage — so App Store decryption is itself device-gated. State this assumption explicitly in findings.
3. `session(action="start_mobsf")`; `report(action="dashboard")`.

### Phase 1 — Static analysis (the 80%, no Apple hardware)
Work the MASVS categories with this **orchestration discipline** (distilled from the MASTG skill set;
full per-category grep dictionaries in `refs/static.md`):
1. **Classify FIRST, then map sinks** — build a sensitive-data inventory (creds/tokens/keys, PII,
   financial, health) before grepping sinks, so each hit correlates to a concrete datum.
2. `scan(tool="mobsf", target="<app>.ipa")` — MASVS-mapped report; triage `high`/`warning`. Confirm via
   `kali()`: `unzip` → `Payload/<App>.app/`; **Info.plist is the source-of-exposure-truth** (ATS
   `NSAppTransportSecurity`, `CFBundleURLTypes`, `NS*UsageDescription`); `class-dump`/`otool -L`/`nm`/`strings` on the Mach-O.
3. **Walk the fixed per-category checklist** (STORAGE→CRYPTO→AUTH→NETWORK→PLATFORM→CODE→PRIVACY→
   RESILIENCE) via `refs/static.md`. Two gates per hit: **anti-FP mitigation gate** (a raw hit is not a
   finding until it fails a mitigation check — Keychain w/ correct accessibility? pinning present?) and
   **appropriateness gate** (does the control apply at this app's risk tier?). MobSF is high-recall/low-precision — confirm before filing.
4. If a **source tree** is available: `scan(tool="mobsfscan", target="<src>")` + `scan(tool="trufflehog", target="<src>")`, `set_codebase`, chain `/codebase`.
5. **File each confirmed issue** with the MASVS category in the title + `file:line`/plist-key evidence + MASTG test ID. Record coverage via `report(action="note")`.
6. Backend endpoints from strings/code → chain `/api-security`.
7. Deep-dive: `refs/static.md` (grep dicts + MASTG IDs), `refs/privacy.md`, `refs/reversing.md`, `refs/remediation.md`.

### Phase 2 — Dynamic analysis (opt-in; needs a JAILBROKEN device; non-blocking)
This skill declares an `ios-dynamic` prerequisite in its `capabilities.yaml`, so invoking it opens a
**setup gate** ("MANUAL SETUP REQUIRED"). iOS dynamic cannot be containerized — it needs a real
jailbroken device with Frida installed.
1. **Elect** now/defer/skip (`session(action="setup_gate", options={"action":"elect","id":"ios-dynamic",...})`). No device → `session(action="wishlist_add", category="environment", need="jailbroken iOS device with Frida over USB/SSH")` and **keep filing static findings**.
2. **Verify:** `session(action="setup_gate", options={"action":"check","id":"ios-dynamic"})` (probe `frida-ps -U`). Proceed only on pass.
3. **Test** via `kali(...)`: `objection -g <bundle-id> explore` → `ios sslpinning disable`, `ios keychain dump`, dump the app container, read `UIPasteboard`; capture traffic through the proxy; abuse custom URL schemes (`uiopen "scheme://..."`). See `refs/dynamic.md`.
4. **Static→dynamic confirmation & bypass rubric** (harvested): when static evidence is ambiguous
   (pinning/jailbreak-detection present? does it hold?), escalate to prove effectiveness at runtime
   before verdicting — Frida hook → r2frida → radare2. For RESILIENCE, never credit a control for merely
   existing: hook the live process and document the exact bypass path (hooks + preconditions) as the artifact.

### Phase 3 — Chain & report
- Backend endpoints → `/api-security`; injection → `/web-exploit`; device access → `/post-exploit`; embedded LLM → `/ai-redteam`.
- Summarize MASVS-category coverage in the final notes; chain exploits where possible — `refs/chains.md`.

**Coverage-matrix note:** the coverage matrix models *web-injection* cells, not MASVS categories.
Track MASVS coverage as a checklist via `report(action="note")`; backend endpoints get real coverage
cells when you chain into `/api-security`.

**iOS caveat:** ~80% of value lands from static (IPA) alone with no hardware; the dynamic phase and
full App-Store-app decryption both require a jailbroken device (or Corellium).
