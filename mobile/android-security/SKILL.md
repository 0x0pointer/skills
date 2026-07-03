---
name: android-security
description: |
  Android app security assessment structured on OWASP MASVS 2.0 / MASTG. Static analysis of an APK
  (MobSF, jadx, apktool, dex2jar, mobsfscan): hardcoded secrets, weak/broken crypto, insecure data
  storage, exported activities/services/providers/receivers, android:allowBackup, cleartext traffic
  & network-security-config, WebView addJavascriptInterface bridges, insecure deeplinks/intent
  redirection, missing FLAG_SECURE, tapjacking, root/anti-Frida detection, vulnerable third-party
  SDKs, Firebase/cloud-config leaks. Dynamic analysis (opt-in, needs a device) via Frida/objection:
  SSL-pinning bypass, runtime keystore/shared-prefs/SQLite dumps, traffic capture, deeplink & IPC
  abuse. Chains from /pentester and /codebase; into /api-security for backend endpoints,
  /web-exploit for injection, /post-exploit on device RCE, /ai-redteam on an embedded LLM.
argument-hint: "<app.apk | package-name | source-path> [depth=quick|standard|thorough]"
user-invocable: true
---

# Android App Security Assessment (MASVS / MASTG)

You are a mobile application security expert. Your goal: take an Android app (an `.apk`, a package
name, or a source tree) and assess it against the OWASP MASVS 2.0 categories using MASTG techniques.
**Static analysis is the 80% deliverable and needs no device** — do it first and completely. Dynamic
analysis is opt-in and needs an operator-provided device; it never blocks completion.

**Request:** $ARGUMENTS

---

## CHAIN COMMITMENTS — DECLARE BEFORE STARTING

Read this before executing any workflow phase. Commit to MANDATORY chains before your first tool call.

| Trigger | Chain | Mandatory? |
| --- | --- | --- |
| Backend API endpoints discovered (from static strings or captured traffic) | `/api-security` | **MANDATORY** |
| Injection reachable in an API/WebView parameter | `/web-exploit` | **MANDATORY** |
| Command execution / device RCE achieved | `/post-exploit` | **MANDATORY** |
| Embedded LLM / AI endpoint discovered | `/ai-redteam` | **MANDATORY** |
| App source tree available | `/codebase` | OPTIONAL (white-box enrich) |
| After `session(action="complete")` | `/gh-export` | OPTIONAL — user request only |

> **Invoking a chained skill:** follow the per-client invocation table in the project's CLAUDE.md / AGENTS.md — do not hard-code client-specific syntax here.

**Logging:** Before invoking any skill above, call `session(action="set_skill", options={"skill":"<name>","reason":"<why>","chained_from":"android-security"})`.

**Authorization:** Testing a third-party APK can implicate app-store ToS and (for repackaging/decryption)
DMCA §1201. Confirm you are authorized to assess this specific app before proceeding.

## Tools Available

| Tool | Use for |
|------|---------|
| `session(action="start", options={...})` | Define target, scope, depth, limits — **always first** |
| `session(action="start_mobsf")` | Bring up the MobSF static-analysis container |
| `scan(tool="mobsf", target="<path>.apk")` | **Primary static engine** — MASVS-mapped report for the APK |
| `scan(tool="mobsfscan", target="<src>")` | Source-tree SAST (when source is available) |
| `scan(tool="trufflehog", target="<path>")` | Secret scanning over the decompiled/source tree |
| `kali(command=...)` | jadx / apktool / dex2jar decompile; frida / objection / adb for dynamic |
| `session(action="setup_gate", options={...})` | Gate + verify the dynamic prerequisite (a hooked device) |
| `http(action="request", ...)` | Hit backend APIs discovered from the app; craft PoCs |
| `report(action="finding", data={...})` | Log a confirmed finding (with MASVS category in the title) |
| `report(action="note", data={...})` | Record MASVS-category coverage progress |
| `session(action="wishlist_add", ...)` | Non-blocking ask for a device when none is available |

---

## MASVS 2.0 coverage map

| MASVS category | What to check | Static signal | Dynamic |
|---|---|---|---|
| **STORAGE** | shared-prefs / SQLite / files / logs / clipboard, `android:allowBackup`, screenshot cache | MobSF + jadx; manifest `allowBackup` | objection `android keystore/prefs`, `run-as` file dump |
| **CRYPTO** | weak algs (DES/ECB/MD5), hardcoded keys/IVs, insecure RNG | MobSF code_analysis + mobsfscan | Frida hook `javax.crypto.Cipher` |
| **AUTH** | local auth bypass, biometric misuse, session/token handling | jadx auth flow read | Frida hook auth checks |
| **NETWORK** | cleartext traffic, `network_security_config`, missing/weak cert pinning | manifest + res/xml; MobSF | objection `android sslpinning disable` + proxy capture |
| **PLATFORM** | exported activities/services/providers/receivers, deeplinks/intent redirection, WebView `addJavascriptInterface`, `FLAG_SECURE`, tapjacking, pending-intent | manifest + jadx | `adb shell am start`/`am broadcast` IPC probing |
| **CODE** | vulnerable 3rd-party SDKs, debug flags, injection sinks, hardcoded secrets, Firebase config | MobSF + mobsfscan + trufflehog | — |
| **RESILIENCE** | root/emulator/anti-Frida detection, obfuscation, integrity/repackaging checks | MobSF | attempt bypass via objection/Frida |

---

## Depth Presets

| Depth | What runs | Default limits |
|-------|-----------|----------------|
| `quick` | MobSF static scan + manifest/permissions triage | $0.10 | 15 min | 10 calls |
| `standard` | Static (MobSF + jadx spot-checks + mobsfscan/trufflehog on source) + full MASVS checklist | $0.50 | 45 min | 25 calls |
| `thorough` | Standard + dynamic (Frida/objection: pin bypass, storage/keystore dumps, IPC/deeplink abuse, traffic capture) when a device is provided + backend API chaining | unlimited | unlimited | unlimited |

---

## Workflow

### Phase 0 — Scope, acquisition & setup
1. `session(action="start", options={target, depth, scope})` and `session(action="set_skill", options={"skill":"android-security","reason":"..."})`.
2. **Acquisition** — obtain the APK: an operator-provided path/upload (default), or pull an installed app: `kali(command="adb shell pm path <package>")` then `adb pull <apk-path>`. Split APKs: pull every `base/split_*.apk`.
3. `session(action="start_mobsf")`; `report(action="dashboard")`.

### Phase 1 — Static analysis (the 80%, no device)
Work the MASVS categories with this **orchestration discipline** (distilled from the MASTG skill set;
full per-category grep dictionaries in `refs/static.md`):

1. **Classify FIRST, then map sinks.** Before grepping storage/crypto/network sinks, do a
   **sensitive-data inventory** (creds/tokens/keys, PII, financial, health, session state) so every
   later sink hit is correlated to a concrete sensitive datum — not blind-flagged.
2. `scan(tool="mobsf", target="<app>.apk")` — MASVS-mapped report; triage `high`/`warning` buckets.
   `jadx -d /tmp/out <app>.apk` + `apktool d <app>.apk -o /tmp/apk`. **Manifest is the
   source-of-exposure-truth** — read `AndroidManifest.xml` for exported components, `allowBackup`,
   `usesCleartextTraffic`, deeplink `<intent-filter>`, `network_security_config`.
3. **Walk the fixed per-category checklist** (STORAGE→CRYPTO→AUTH→NETWORK→PLATFORM→CODE→PRIVACY→
   RESILIENCE) via `refs/static.md`'s grep batteries. Two gates per hit:
   - **Anti-FP mitigation gate** — a raw grep hit is NEVER a finding until it survives a mitigation
     check (EncryptedSharedPreferences? parameterized query? pinning present? sanitized WebView?).
     Confirm against decompiled source; MobSF is high-recall/low-precision — don't bulk-import.
   - **Appropriateness gate** — judge whether the control applies to the app's risk tier before
     flagging its absence (pinning is warranted for Tier-3, optional for Tier-1).
4. If a **source tree** is available: `scan(tool="mobsfscan", target="<src>")` + `scan(tool="trufflehog", target="<src>")`, `set_codebase`, chain `/codebase`.
5. **File each confirmed issue** with the MASVS category in the title (e.g. "MASVS-NETWORK: cleartext
   traffic permitted"), the `file:line` evidence, and the MASTG test ID. Record coverage with `report(action="note")`.
6. Extract backend API endpoints (strings/resources/decompiled) → each chains `/api-security`.
7. Deep-dive: `refs/static.md` (grep dicts + MASTG IDs), `refs/privacy.md` (per-SDK consent/tracking fan-out), `refs/reversing.md`, `refs/remediation.md`.

### Phase 2 — Dynamic analysis (opt-in; needs a device; non-blocking)
This skill declares an `android-dynamic` prerequisite in its `capabilities.yaml`, so invoking the
skill opens a **setup gate** for a hooked device (surfaced as "MANUAL SETUP REQUIRED").
1. **Elect:** interactive → ask the operator whether to set up a device now; headless → default `defer`
   (`session(action="setup_gate", options={"action":"elect","id":"android-dynamic","choice":"now|defer|skip"})`).
   If no device is available, also `session(action="wishlist_add", category="environment", need="ADB-reachable rooted emulator/device with frida-server")` and **keep filing static findings** — never stall.
2. **Verify:** `session(action="setup_gate", options={"action":"check","id":"android-dynamic"})` runs the readiness probe (`frida-ps -U`). Only proceed when it passes.
3. **Test** via `kali(...)`: `objection -g <package> explore` → `android sslpinning disable`, `android keystore list`, dump shared-prefs/SQLite; capture traffic through the proxy; probe IPC/deeplinks with `adb shell am start/broadcast`. See `refs/dynamic.md`.
4. **Static→dynamic confirmation & bypass-resistance rubric** (harvested): when static evidence for a
   control is ambiguous (pinning present? does it hold?), escalate to **prove effectiveness at runtime**
   before verdicting — the ladder is Frida hook → r2frida → radare2. For RESILIENCE controls (root/anti-debug
   detection), never credit a control for merely being present: instrument the live process and document
   the exact **bypass path** (hooks + preconditions) as the artifact. A one-boolean-flip bypass = finding.
5. Hybrid/WebView apps: drive the WebView via Playwright-Android over adb (`refs/dynamic.md`).

### Phase 3 — Chain & report
- Backend endpoints → `/api-security`; injection → `/web-exploit`; device RCE → `/post-exploit`; embedded LLM → `/ai-redteam`.
- Summarize MASVS-category coverage in the final notes. Chain exploits where possible (e.g. exported provider → SQLi → data theft) — `refs/chains.md`.

**Coverage-matrix note:** the coverage matrix auto-fans *web-injection* cells and does not model
MASVS categories. Track MASVS coverage as a checklist via `report(action="note")` and file findings
normally; backend endpoints get real coverage cells when you chain into `/api-security`.
