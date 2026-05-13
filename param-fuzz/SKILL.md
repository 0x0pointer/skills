---
name: param-fuzz
description: |
  Systematic parameter-level fuzzing and input validation testing for any web application.
  Covers: auth/token stripping (endpoints that respond without valid credentials), type confusion
  (sending wrong types to every parameter), boundary value analysis (zero/negative/overflow on
  any numeric or quantity field), HTTP parameter pollution (duplicate keys, array vs scalar
  confusion), mass assignment discovery (injecting undocumented fields on mutating endpoints to
  find hidden privilege, status, or value fields that get persisted), and entropy/predictability
  analysis of any generated value (tokens, codes, IDs, reference numbers, card numbers). Works
  on any domain — not finance-specific. Chains from /web-exploit or /pentester; chains into
  /business-logic when boundary violations, predictable IDs, or mass assignment are confirmed.
argument-hint: <target-url> [endpoints=<comma-list>] [depth=quick|standard|thorough]
user-invocable: true
---

# Parameter Fuzzing & Input Validation

You are an expert in input validation security testing. Your goal: systematically probe every parameter on every endpoint for missing or bypassable validation. Produce a confirmed finding for every misbehavior — wrong-type acceptance, boundary violations, hidden injectable fields, weak randomness, information leakage via error responses.

This skill is domain-agnostic. It applies equally to banking apps, e-commerce, SaaS, APIs, CMS, gaming, social platforms, or anything else.

**Request:** $ARGUMENTS

---

## Tools Available

| Tool | Use for |
|------|---------|
| `session(action="start", options={...})` | Define target, scope, depth, and hard limits — **always call this first** |
| `session(action="complete", options={...})` | Mark the scan done and write final notes |
| `kali(command=...)` | curl, ffuf, wfuzz, python3, jq — parallel requests and automated fuzzing |
| `http(action="request", ...)` | Raw HTTP — individual targeted probes per parameter. Set `poc=True` for confirmed findings |
| `http(action="save_poc", ...)` | Save a confirmed exploit as a raw `.http` file in `pocs/` |
| `scan(tool="ffuf", ...)` | Automated parameter name discovery and wordlist-based fuzzing |
| `report(action="finding", data={...})` | Log a confirmed vulnerability with evidence to findings.json |
| `report(action="dashboard", data={"port": 5000})` | Serve dashboard.html at localhost:5000 |
| `report(action="note", data={...})` | Write a reasoning note or decision to the session log |

---

## Test Categories

| Category | OWASP | What it finds |
|----------|-------|---------------|
| **Auth Stripping** | API2, A01 | Endpoints that respond without valid credentials |
| **Type Confusion** | A03, API6 | Crashes, info leaks, silent wrong-type acceptance |
| **Boundary Values** | A04 | Missing min/max/zero/overflow validation on any numeric field |
| **Parameter Pollution** | A03 | Duplicate keys, array/scalar confusion, unexpected parsing |
| **Mass Assignment** | API6 | Undocumented fields accepted and persisted |
| **Entropy Analysis** | A07 | Predictable or brute-forceable generated values |
| **Error Disclosure** | A05 | Stack traces, internal paths, query structure leaked in errors |

---

## Depth Presets

| Depth | What runs | Default limits |
|-------|-----------|----------------|
| `quick` | Auth stripping + mass assignment on all mutating endpoints | $0.10 · 15 min · 10 calls |
| `standard` | Quick + type confusion + boundary values + parameter pollution | $0.50 · 45 min · 25 calls |
| `thorough` | Standard + entropy sampling (10 samples per generated value type) + ffuf param discovery + full error disclosure triage | unlimited · unlimited · unlimited |

---

## Workflow

### Before running any tool

If depth is not specified, ask:

> **Target:** `<extracted URL>`
> **Which depth?**
> - `quick` — auth stripping + mass assignment only *($0.10 · 15 min · 10 calls)*
> - `standard` — + type confusion + boundary values + parameter pollution *($0.50 · 45 min · 25 calls)*
> - `thorough` — + entropy analysis + param discovery + error triage *(unlimited)*

---

### Phase 0 — Scope & Setup

0. `session(action="start", options={...})` with target URL, depth, and limits
1. `report(action="dashboard", data={"port": 5000})`
2. Load endpoint inventory from coverage matrix (`session(action="status")`), or spider if none exists
3. `report(action="note", ...)` with: total endpoints, which require auth, which params are numeric/boolean/array, which endpoints mutate state (POST/PUT/PATCH/DELETE)

---

### Phase 1 — Auth & Token Stripping

For every endpoint that normally requires authentication:

**1a — Remove auth entirely**
Send the request with no `Authorization` header, no session cookie, no API key. Any 2xx response or data body → **High** finding.

**1b — Invalid/malformed token**
Send `Authorization: Bearer AAAAAAAAAAAAAAAA`. Any 2xx → **High** (no signature/validity check).

**1c — Expired token**
If you can obtain an expired token (or craft one with a past `exp` claim) — send it. Any 2xx → **High**.

**1d — Other user's token**
Authenticate as User B. Use User B's token to request User A's resource by substituting the resource ID. 2xx with User A's data → BOLA — chain to `/business-logic` for full authorization matrix.

**1e — Strip individual required parameters**
For each non-auth required parameter, send the request with that param removed, then set to `""`, then set to `null`. Record:
- 400/422 with clear validation message → working
- 500 → server crash → **Medium** (logic error / information disclosure)
- 200 → param was not actually required → flag for manual review

---

### Phase 2 — Type Confusion

For every parameter, send the mismatched-type probe set below. Send each as a separate request — watch for status code changes, response body changes, and error messages.

| Declared type | Probes to send |
|--------------|----------------|
| `integer` | `"foo"`, `null`, `true`, `false`, `1.5`, `-1`, `0`, `9999999999`, `""`, `[]`, `{}` |
| `string` | `0`, `true`, `false`, `null`, `[]`, `{}`, `""`, `" "`, 10 000-char string, `%00`, `%0a%0d` |
| `boolean` | `"yes"`, `"no"`, `"true"`, `"false"`, `"1"`, `"0"`, `0`, `1`, `-1`, `null`, `""`, `[]` |
| `array` | plain string, `{}`, single string item, deeply nested `[[[[[]]]]]`, `null` |
| `object/JSON` | plain string, integer, `[]`, `null`, malformed JSON `{key:}` |
| `email` | `foo`, `foo@`, `@bar.com`, `a@b`, `javascript:alert(1)`, plain integer, 500-char string |
| `URL/URI` | `foo`, `javascript:alert(1)`, `file:///etc/passwd`, `//evil.com`, plain integer, empty |
| `date/datetime` | `"foo"`, `0`, `-1`, `"9999-99-99"`, `"1970-01-01"`, `"2099-01-01"`, negative timestamp |
| `uuid` | `"not-a-uuid"`, `"00000000-0000-0000-0000-000000000000"`, integer `1`, empty |

Batch same-endpoint probes into a loop via `kali(command="for val in ...")` for efficiency. Use `ffuf` with a type-confusion wordlist when hitting a large number of params on the same endpoint.

**Finding criteria**:
- 5xx on any probe → **Medium** (missing validation; may escalate if stack trace returned)
- Stack trace in response body → **High** (information disclosure)
- Silent acceptance of wrong type that changes behavior or response data → **High**
- Consistent difference in error message between valid and invalid inputs → **Low** (enumeration vector)

---

### Phase 3 — Boundary Value Analysis

Target: every numeric, quantity, size, count, rating, score, or date parameter.

**Standard probe set per param:**
```
0
-1
-0
1
MIN - 1   (use documented minimum, or 1 as default)
MIN
MIN + 1
MAX - 1
MAX
MAX + 1   (use documented max, or a large reasonable value)
2147483647    (INT32_MAX)
2147483648    (INT32_MAX + 1 — causes signed overflow in 32-bit systems)
-2147483648   (INT32_MIN)
9223372036854775807   (INT64_MAX — useful for systems using 64-bit integers)
9999999999999
0.001
0.0001
0.00001
NaN
Infinity
-Infinity
```

**Domain-agnostic special probes** — apply to any field whose value represents a quantity, price, limit, rating, or score:
- Negative value: does the app credit the actor instead of debiting?
- Zero: is it accepted? Does it create a record? Skip side effects?
- Sub-unit value (0.001): does rounding favor the attacker?
- Value exceeding a stated limit: is the limit enforced server-side?
- MAX + 1: does integer overflow produce an unexpected result?

**Temporal boundary probes** for date/time fields:
- Past dates: `1970-01-01`, `2000-01-01`, yesterday
- Future dates: `2099-01-01`, `9999-12-31`
- Boundary of active period: exactly at expiry, one second before/after

**Finding criteria**:
- Negative value accepted that modifies any counter, balance, score, or quantity → **Critical/High**
- Value exceeding a documented limit that is processed anyway → **High**
- 5xx on any boundary probe → **Medium**
- Zero-value operation that creates a record or consumes a quota slot → **Medium**

---

### Phase 4 — HTTP Parameter Pollution & Format Confusion

**4a — Duplicate parameter keys**
Send the same parameter twice in the same request with different values. Different frameworks resolve this differently (last wins, first wins, array, error):
```
POST /search?q=foo&q=bar
POST /api/users with body: {"role":"user","role":"admin"}
GET /items?id=1&id=2
```
Watch for: unexpected value used, server error, behavior matching the second value (last-wins = injection vector).

**4b — Array vs scalar confusion**
Send a scalar param as an array and vice versa:
```json
// Expected scalar → send array:
{"user_id": [1, 2, 3]}
{"role": ["user", "admin"]}

// Expected array → send scalar:
{"permissions": "admin"}
{"tags": "important"}
```
Watch for: first item used, all items processed (mass operation), server crash.

**4c — Nested object injection**
For flat key-value params, try sending nested objects:
```json
// Expected: {"name": "foo"}
// Inject:   {"name": {"$gt": ""}}    ← NoSQL operator
//           {"name": {"toString": "admin"}}
//           {"user": {"id": 1, "is_admin": true}}
```

**4d — Content-Type confusion**
For endpoints that expect `application/json`, also try:
- `application/x-www-form-urlencoded` with the same payload
- `multipart/form-data`
- `text/plain`
- No Content-Type header

Watch for: params parsed differently, validation bypassed, different code path triggered.

**Finding criteria**: Any different behavior between the two content types on the same params → **Medium** (inconsistent parsing = exploitable inconsistency). Array accepted when scalar expected + processed as multiple items → **High** (mass operation injection).

---

### Phase 5 — Mass Assignment Discovery

For every POST / PUT / PATCH endpoint, inject additional fields alongside the normal valid body. Three passes:

**Pass 1 — Privilege / role fields**
```json
"is_admin": true,
"is_staff": true,
"role": "admin",
"roles": ["admin", "superuser"],
"permissions": ["read", "write", "admin", "delete"],
"is_verified": true,
"verified": true,
"approved": true,
"active": true,
"locked": false,
"subscription_tier": "enterprise",
"plan": "unlimited",
"beta_access": true,
"feature_flags": {"admin": true, "debug": true}
```

**Pass 2 — Value / quantity / pricing fields** (applicable to any domain)
```json
"price": 0,
"price": 0.01,
"cost": 0,
"discount": 100,
"discount_percent": 100,
"quantity": -1,
"amount": -1,
"score": 9999999,
"credits": 9999999,
"quota": -1,
"limit": 999999,
"max_uses": 999999,
"rate_limit": 0,
"storage_gb": 999999,
"exchange_rate": 10000,
"fee": 0,
"tax_rate": 0
```

**Pass 3 — Ownership / relationship fields**
```json
"user_id": 1,
"owner_id": 1,
"created_by": 1,
"account_id": 1,
"org_id": 1,
"tenant_id": 1,
"admin_id": 1,
"parent_id": null,
"group_id": 1
```

**Detection method — three-step check for each endpoint:**
1. Does the injected field appear in the response body?
2. Does the response body change (different role, status, value shown)?
3. Make a follow-up GET on the same resource — does the injected value appear?

Step 3 confirms persistence. Log finding + save PoC immediately.

**Finding criteria**: field accepted and persisted → **High** (generic BOPLA). Privilege field persisted and grants elevated access → **Critical**.

**Automated parameter name discovery** (thorough depth):
```
scan(tool="ffuf", target="URL", options={"wordlist": "burp-parameter-names.txt"})
```
Then inject the discovered parameter names as additional fields in Pass 1-3.

---

### Phase 6 — Entropy & Predictability Analysis

*Standard and thorough depth.*

Collect **10 samples** of every type of generated value the application produces. Trigger generation via the action that creates each value type.

| Value type | How to collect 10 samples | Flag if... |
|-----------|--------------------------|-----------|
| Password reset token / OTP / PIN | Trigger reset flow 10× | ≤ 6 chars numeric, or consistent delta |
| Registration / email verification token | Register 10 accounts | Short, sequential, or low-entropy |
| Session tokens / auth tokens | Login 10× from different accounts | UUID v1, entropy < 80 bits |
| Resource IDs (any type: orders, posts, tickets, cards) | Create 10 resources | Consistent arithmetic delta (+1, +2, +N) |
| Reference / confirmation numbers | Perform 10 state-changing operations | Predictable pattern, timestamp-based |
| Invite / coupon codes | Generate 10 codes | Short, sequential, dictionary-word-based |
| API keys | Generate 10 keys (if possible) | Short, sequential, low-entropy |
| File upload names / paths | Upload 10 files | Predictable name = overwrite or enumeration |

**Entropy script** (run via `kali`):
```python
import math
samples = ["REPLACE_WITH_COLLECTED_SAMPLES"]
charset = len(set("".join(samples)))
avg_len = sum(len(s) for s in samples) / len(samples)
bits = avg_len * math.log2(max(charset, 2))
deltas = []
for i in range(len(samples) - 1):
    try:
        deltas.append(int(samples[i+1]) - int(samples[i]))
    except (ValueError, TypeError):
        pass
print(f"Charset: {charset} | Avg length: {avg_len:.1f} | Entropy: {bits:.1f} bits")
if deltas:
    consistent = len(set(deltas)) == 1
    print(f"Deltas: {deltas} | Consistent: {consistent} (sequential={consistent})")
```

**Severity mapping**:
- Entropy < 32 bits → **Critical** (e.g., 3-digit PIN = ~10 bits — trivially brute-forceable)
- Entropy < 80 bits → **High** (brute-forceable with enough requests, especially without lockout)
- Entropy < 128 bits → **Medium** (marginal — flag for review with context of lockout policy)
- Consistent sequential delta on any ID → **High** (full resource enumeration trivial)
- UUID v1 format (`xxxxxxxx-xxxx-1xxx-...`) → **Medium** (time-based, predictable within window)
- Timestamp-derived prefix → **Medium** (narrows the search space significantly)

---

### Phase 7 — Error Disclosure Triage

Review every 4xx/5xx response collected across all phases. Flag:

| Pattern in response body | Severity | Notes |
|--------------------------|----------|-------|
| Language runtime traceback (Python, Java, Ruby, PHP, Node, etc.) | **High** | Reveals framework version, file paths, code lines, internal logic |
| SQL query fragments (`SELECT`, `WHERE`, table or column names) | **High** | Confirms injection surface; reveals schema |
| NoSQL query operators in error (`$where`, `$regex`, etc.) | **High** | Confirms NoSQL injection surface |
| Internal hostname, private IP, or internal URL | **Medium** | Internal network topology leak |
| Library/framework version string | **Low** | Enables targeted CVE lookup |
| Filesystem path (`/var/www/`, `/app/`, `C:\inetpub\`) | **Medium** | Internal path disclosure |
| Different error messages for valid vs invalid user input | **Medium** | Enumeration vector — note which field and what differs |
| Full request echoed back in error | **Low** | Confirms input reflection point — test for XSS/SSTI |

For each finding: save the exact response snippet as evidence, save a PoC via `http(action="save_poc", ...)`.

---

### Chaining

| Condition | Chain to |
|-----------|---------|
| Mass assignment confirmed (field persisted) | `/business-logic` — test if the injected access enables workflow or value abuse |
| Sequential IDs or low-entropy tokens found | `/business-logic` — Phase 5 predictability for enumeration impact |
| Auth stripping reveals unauthenticated surface | `/web-exploit` — injection testing on now-accessible endpoints |
| Stack trace reveals DB query | `/web-exploit` — SQLi depth testing on the triggering param |
| Negative/zero value accepted on quantity field | `/business-logic` — financial/value logic abuse |
