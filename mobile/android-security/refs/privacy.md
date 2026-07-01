# MASVS-PRIVACY (Android) — permissions, tracking, consent, minimization

PRIVACY is the one MASVS category about data-handling/consent/tracking rather than exploitable
memory/crypto/network flaws — so the exploitation-oriented checks don't cover it. Distinct pass.

## Orchestration: presence → uniform sub-checklist fan-out
Enumerate the privacy-relevant units (permissions, tracking/analytics/ad SDKs, data-collection
points), then run the SAME fixed sub-checklist against EACH unit — don't do one flat pass.

**Per tracking/analytics/ad SDK found** (Firebase/Crashlytics, Facebook, AppsFlyer, Adjust, ad
networks), run this 4-point loop:
1. **Minimization** — does it collect more than the feature needs?
2. **PII in events** — are identifiers/PII passed into analytics events?
3. **Consent before init** — is the SDK initialized *before* the user consents (gating)?
4. **Sharing settings** — data-sharing/attribution flags, cross-app identifiers.

## Static signals
- `AndroidManifest.xml`: `<uses-permission>` inventory — flag dangerous/rarely-justified perms
  (LOCATION, CONTACTS, SMS, CAMERA, MIC, `AD_ID`, `QUERY_ALL_PACKAGES`, `READ_PHONE_STATE`).
- `Settings.Secure.ANDROID_ID`, `getImei`/`getSubscriberId`, advertising-ID usage → persistent identifiers.
- Data-safety alignment: does actual collection match the Play Data-Safety declaration?
- Consent flow present before any network/analytics call on first launch?

## MASVS-PRIVACY controls
- PRIVACY-1 minimization/justified perms · PRIVACY-2 consent-before-tracking (AD_ID gating) ·
  PRIVACY-3 transparency (data-safety) · PRIVACY-4 user controls (delete/export/opt-out).

File findings as `MASVS-PRIVACY: <issue>` with the manifest/code `file:line` and which SDK/permission.
