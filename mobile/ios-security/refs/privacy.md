# MASVS-PRIVACY (iOS) — permissions, tracking, consent, minimization

PRIVACY is about data-handling/consent/tracking, not exploitable flaws — a distinct pass the
exploitation-oriented checks don't cover.

## Orchestration: presence → uniform sub-checklist fan-out
Enumerate the privacy units (purpose-string permissions, tracking/analytics/ad SDKs, collection
points), then run the SAME 4-point loop against EACH tracking SDK (Firebase, Facebook, AppsFlyer,
Adjust, ad networks):
1. **Minimization** — collects more than the feature needs?
2. **PII in events** — identifiers/PII in analytics payloads?
3. **Consent before init / ATT** — is `ATTrackingManager.requestTrackingAuthorization` requested and
   honored *before* the SDK initializes / before IDFA access?
4. **Sharing settings** — attribution/cross-app identifiers, data-sharing flags.

## Static signals
- `Info.plist`: `NS*UsageDescription` strings (Camera/Location/Contacts/Mic/…) — flag broad/unjustified;
  `NSUserTrackingUsageDescription` present ⇢ tracking; `Privacy - *` keys.
- **PrivacyInfo.xcprivacy** (Apple Privacy Manifest): declared data types + "required reason" APIs —
  does actual usage match the manifest and the App Store privacy label?
- `ASIdentifierManager`/IDFA, `identifierForVendor`, pasteboard reads of identifiers.

## MASVS-PRIVACY controls
- PRIVACY-1 minimization/justified permissions · PRIVACY-2 consent-before-tracking (ATT) ·
  PRIVACY-3 transparency (PrivacyInfo.xcprivacy / App Store label) · PRIVACY-4 user controls.

File as `MASVS-PRIVACY: <issue>` with the plist key / manifest entry / code `file:line` and which SDK/permission.
