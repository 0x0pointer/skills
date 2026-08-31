# Category Map Reference

Lazy-loaded reference for Phase 2 of `/aikido-triage`. Maps every Aikido `issue_type` to one of the
four triage categories (or Unmapped) and gives the judgment-call procedure for Unmapped findings.

---

## The full `issue_type` enum

```
open_source, leaked_secret, cloud, sast, iac, surface_monitoring, malware, eol,
mobile, docker_container, cloud_instance, scm_security, license, ai_pentest, ai_code_analysis
```

Every value above must land in exactly one row below. If Aikido returns a value not in this list,
see "New/unrecognized `issue_type`" at the bottom — do not error, do not skip it.

---

## Mapping table

| Category | `issue_type` values | Rationale |
|---|---|---|
| SCA | `open_source`, `license`, `eol` | All three are third-party component risk, not app-source risk — but they don't get identical treatment. `open_source` findings carry a CVE, so they chain to `/analyze-cve` for a real dataflow/reachability trace. `license` and `eol` findings have no CVE and nothing for `/analyze-cve` to trace — they get a lightweight native check instead (is the package actually used, is it end-of-life/incompatible-license in a way that matters to this deployment). |
| SAST | `sast`, `ai_code_analysis` | Both are static analysis of the application's own source code — a rule engine flagging a pattern in first-party code. They differ only in which engine produced the finding (traditional SAST rules vs. an AI-based code reviewer), not in what kind of verification is needed. Both use the same source-to-sink taint trace in `sast-taint-playbook.md`. |
| Application Secrets | `leaked_secret` | Single `issue_type`, single playbook — a credential/token/key detected in source, history, or config. Verification is removal-check + usage-estimate + opt-in liveness probe, never automatic. |
| Misconfiguration | `cloud`, `iac`, `docker_container`, `cloud_instance`, `scm_security`, `surface_monitoring` | All six are infrastructure, configuration, or exposure findings — none of them point at a line of application source code the way SAST does. They share a blast-radius reasoning method (what does this misconfiguration expose, to whom, and does it chain to something worse) with an optional live-chain confirmation via `/cloud-security`, `/container-k8s-security`, `/api-security`, `/ssl-tls-audit`, or `/cloud-identity-federation` depending on resource type. |
| Unmapped | `malware`, `mobile`, `ai_pentest` | None of these fit the four requested lenses (SCA / SAST / Secrets / Misconfiguration) at all. `malware` is a detected malicious-code signature — not a reachability or exploitability question, it's a "is this actually malicious code in the tree" question. `mobile` is MASVS-domain risk that belongs to `/android-security` or `/ios-security`, not a source-code taint trace. `ai_pentest` is a dynamic AI red-team result — evidence from live probing, not something a static file read can confirm or refute. |

---

## Unmapped handling — never silently drop these

Unmapped findings do not get a rich category-specific playbook, but they are **not exempt** from
the finding-record contract. Every Unmapped finding still gets a full record — `technical_verdict`,
`close_category` (if CLOSE), `exploitability_rating`, `verification_method`, `evidence` — populated
by whichever lightweight procedure below applies, then business-impact scoring in Phase 4 like
everything else. What they don't get is a deep taint trace, a CVE chain, or a live-chain
confirmation — those require the specialist skill.

### `malware`

This is a detected malicious-code signature (webshell pattern, known malware hash, obfuscated
dropper, etc.) — treat it as a real security event, not a code-quality finding.

1. Confirm the flagged file/pattern is still present at the reported `file`/`line`. If the file was
   deleted or the pattern no longer matches, that's your evidence for a CLOSE.
2. If present, read enough surrounding code to form a judgment: does this look like a genuine
   malicious signature (obfuscated payload, suspicious network callout, credential exfiltration,
   backdoor logic) or a benign false match (a security tool's own test fixture, a string that
   coincidentally matches a malware signature, a vendored file containing a YARA-rule test sample)?
3. **Any real hit is an immediate `KEEP OPEN` with `exploitability_rating: HIGH` and
   `business_severity` escalated to Critical**, regardless of Aikido's raw severity. This is not a
   category to be lenient on — do not downgrade a plausible malware hit on the basis of "I don't
   see it being called anywhere" the way you might for a SAST finding; unreachable malicious code
   in the tree is still malicious code in the tree.
4. Only close on a clean, specific removal/false-match reason (file deleted, or the match is
   provably a test fixture / vendored sample with no execution path in this codebase) — never on
   "looks unlikely to be exploited."

### `mobile`

This is MASVS-domain risk (insecure storage, exported components, weak crypto, etc. in a mobile
app) — a real assessment needs the structured MASVS/MASTG methodology, not an ad hoc read.

1. If the flagged file is small and self-contained — app config, `AndroidManifest.xml`, `Info.plist`,
   a build/signing config, a hardcoded-secret-in-source case — read it directly and render a
   best-effort verdict the same way you would for a simple secret or misconfig.
2. Otherwise, don't attempt to substitute for a real MASVS review. Record
   `verification_method: "static assessment only — needs MASVS-structured review"`, give your best
   `exploitability_rating` from what little static context is available, and set the suggested next
   step to `/android-security` or `/ios-security` (pick by file path / platform signal) in the Phase
   7 summary.

### `ai_pentest`

This is a dynamic finding — the output of a live AI red-team probe (jailbreak, prompt injection,
data exfiltration via the model, etc.), not a static code property.

1. A static read of the flagged file (system prompt, agent config, tool definition) can add context
   but **cannot confirm or refute** a dynamic finding — the underlying question is "does this model
   actually produce the unsafe behavior when probed," which only live testing answers.
2. Default the verdict to `KEEP OPEN` with `verification_method: "dynamic finding — static
   assessment only, not live-confirmed"`. Do not close an `ai_pentest` finding on static reasoning
   alone (e.g. "the system prompt looks fine to me") — that is exactly the class of finding static
   review is unequipped to rule out.
3. Suggest `/ai-redteam` in the Phase 7 summary as the way to actually confirm or close it.

---

## New/unrecognized `issue_type`

If a future Aikido response includes an `issue_type` not in the enum at the top of this file:

- Default it to **Unmapped** — never error, skip, or silently drop the finding.
- Still produce a full finding record for it using the general Unmapped procedure (read what you
  can, render a conservative verdict, flag if a live/specialist check would be needed to close it).
- Explicitly flag it to the user in the Phase 2 category counts and again in Phase 7 as:
  `"<issue_type> — new/unrecognized type — categorized as Unmapped by default."`
