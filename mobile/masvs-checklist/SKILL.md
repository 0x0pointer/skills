---
name: masvs-checklist
description: |
  Generate an OWASP MASVS 2.0 compliance matrix for a mobile app, mapped to MASTG test IDs and tagged
  by NowSecure risk tier. Produces a control-by-control table across all 8 MASVS groups (STORAGE,
  CRYPTO, AUTH, NETWORK, PLATFORM, CODE, RESILIENCE, PRIVACY) with a constrained status enum
  (compliant / non_compliant / not_applicable / needs_dynamic), file:line evidence per control, and an
  anti-overclaim rule (a control needing runtime proof cannot be marked compliant on static evidence
  alone). The mobile analog of /compliance (which covers ASVS). Chains from /mobile-pentest-plan,
  /android-security, /ios-security to turn their findings into an audit-grade deliverable.
argument-hint: "<app-or-source-path> [platform=android|ios|both] [tier=1|2|3]"
user-invocable: true
---

# MASVS 2.0 Compliance Matrix

You are a mobile security compliance expert. Produce an audit-grade MASVS v2 compliance matrix:
control-by-control, MASTG-mapped, tier-scoped, with evidence and an honest status — never overclaim.

**Request:** $ARGUMENTS

---

## CHAIN COMMITMENTS

| Trigger | Chain | Mandatory? |
| --- | --- | --- |
| Need to gather the evidence first (not yet assessed) | `/android-security` / `/ios-security` | **MANDATORY** (run before matrixing) |
| After matrix | `/remediate` for NON_COMPLIANT controls | OPTIONAL |

> **Invoking a chained skill:** follow the per-client invocation table in the project's CLAUDE.md / AGENTS.md — do not hard-code client-specific syntax here.

**Reuse:** this mirrors `/compliance` (ASVS) — reuse its matrix mechanics and evidence discipline; do
not reinvent a report format. **Logging:** `session(action="set_skill", ...)` before chaining.

## Workflow

### Step 1 — Classify (scope the matrix)
- Platform: android / ios / both (a control gets a per-platform row when the MASTG test differs).
- **Risk tier** (NowSecure 1/2/3 — see `/mobile-pentest-plan`): tags each control **Required** vs
  **Tier-3-only**, so a Tier 1 app isn't graded against RESILIENCE it never needed.

### Step 2 — Build the control matrix
For each MASVS control in each of the 8 groups (see `refs/masvs-crosswalk.md` for the control →
MASTG-test-ID crosswalk, per platform), emit a row:

| Field | Rule |
|---|---|
| `masvs_control` | e.g. MASVS-STORAGE-1 |
| `mastg_tests` | the mapped MASTG-TEST IDs (platform-specific) |
| `required` | Required (by tier) / Tier-3 / N/A-for-tier |
| `status` | **closed enum** → `compliant` \| `non_compliant` \| `not_applicable` \| `needs_dynamic` |
| `evidence` | file:line (static) or artifact_id (dynamic) — REQUIRED for compliant/non_compliant |
| `finding_id` | link to the report(action='finding') entry for non_compliant |

### Step 3 — Anti-overclaim rule (the integrity gate)
- A control whose MASTG test **requires runtime proof** (e.g. cert-pinning effectiveness,
  root-detection bypass-resistance, Keychain/Keystore behavior) **cannot be `compliant` on static
  evidence alone** → mark `needs_dynamic` until a dynamic artifact proves it. This mirrors Smith's
  "probe over trust" discipline.
- Never mark `compliant` without evidence. `not_applicable` requires a one-line reason.

### Step 4 — Emit
- The full matrix (all 8 groups) + a per-group Pass/Fail/Needs-Dynamic summary + overall posture.
- Every `non_compliant` control should have a filed `report(action='finding')` with the MASVS control
  in the title and file:line/artifact evidence; chain `/remediate` for fixes.

See `refs/masvs-crosswalk.md` for the authoritative MASVS-control → MASTG-test crosswalk (Android + iOS).
