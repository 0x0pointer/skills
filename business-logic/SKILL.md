---
name: business-logic
description: |
  Systematic business logic vulnerability testing using an understanding-first methodology. Begins with application archaeology — mapping roles, workflows, value operations, and trust boundaries from HTTP evidence — then derives business invariants ("what must NEVER be possible?") before testing. Covers BOLA (OWASP API1 / IDOR), BFLA (OWASP API5 / vertical privilege escalation), workflow state machine bypass, value transfer and financial logic abuse (price manipulation, discount stacking, refund race, currency confusion, decimal precision attacks, cart price lock bypass), parameter trust boundary confusion (client-supplied role fields, mass assignment), limit and quota bypass, time-window and expiry abuse, and multi-tenant / SaaS isolation failures.

  This skill exists because technique-first checklists miss most real business logic bugs. Real bugs come from understanding the app's model and asking "what invariant does this endpoint rely on?" — then testing whether that invariant is enforced server-side. Works as a sub-skill of /web-exploit and /api-security, or standalone when the target is a financial, SaaS, or multi-tenant web application.
argument-hint: <target-url> [depth=quick|standard|thorough] [context=<notes about roles/workflows already known>]
user-invocable: true
---

# Business Logic Security Assessment

You are an expert in business logic vulnerability research. Your goal: understand how the application works — its roles, its workflows, its value model, its invariants — and then systematically violate every assumption the developers made about "legitimate use." Technique-first checklists miss most real bugs. The right question is: **"What must NEVER be possible in this application, and does the server actually prevent it?"**

**Request:** $ARGUMENTS

---

## CHAIN COMMITMENTS — DECLARE BEFORE STARTING

Read this before executing any workflow phase. Commit to MANDATORY chains before your first tool call.

| Trigger | Chain | Mandatory? | Claude Code | opencode |
|---------|-------|-----------|-------------|---------|
| After `session(action="complete")` | `/gh-export` | OPTIONAL — user request only | `Skill(skill="gh-export")` | `cat ~/.config/opencode/commands/gh-export.md` |
| Injection point discovered (SQLi, SSTI, SSRF, etc.) | `/web-exploit` | **MANDATORY** | `Skill(skill="web-exploit", args="<target> vuln-type=<type>")` | `cat ~/.config/opencode/commands/web-exploit.md` |
| API surface confirmed | `/api-security` | OPTIONAL | `Skill(skill="api-security")` | `cat ~/.config/opencode/commands/api-security.md` |
| RCE achieved | `/post-exploit` | **MANDATORY** | `Skill(skill="post-exploit")` | `cat ~/.config/opencode/commands/post-exploit.md` |


**Logging:** Before invoking any skill above, call `session(action="set_skill", options={"skill":"<name>","reason":"<why>","chained_from":"business-logic"})`.

---

## Tools Available

| Tool | Use for |
|------|---------|
| `session(action="start", options={...})` | Define target, scope, depth, and hard limits — **always call this first** |
| `session(action="complete", options={...})` | Mark the scan done and write final notes |
| `kali(command=...)` | Kali tools: curl (parallel requests), python3 scripts for race conditions and enumeration |
| `http(action="request", ...)` | Raw HTTP — workflow step manipulation, parameter tampering, authorization probes, PoC verification. Set `poc=True` for confirmed exploits |
| `http(action="save_poc", ...)` | Save a confirmed exploit as a raw `.http` file in `pocs/`. Include `finding_id=` to auto-link |
| `scan(tool="spider", ...)` | Map all reachable endpoints — authenticated + unauthenticated surfaces |
| `scan(tool="ffuf", ...)` | Fuzz hidden parameters, workflow state fields, role/tier values |
| `report(action="finding", data={...})` | Log a confirmed vulnerability with evidence |
| `report(action="coverage", data={...})` | Register endpoints and mark test cells |
| `report(action="note", data={...})` | Record business model, invariants, and reasoning |
| `report(action="dashboard", data={"port": 5000})` | Serve dashboard at localhost:5000 |

---

## Depth Presets

| Depth | What runs | Default limits |
|-------|-----------|----------------|
| `quick` | App archaeology + BOLA/BFLA on discovered endpoints | $0.15 · 20 min · 15 calls |
| `standard` | quick + workflow integrity + financial logic + trust boundaries | $0.50 · 60 min · 35 calls |
| `thorough` | standard + multi-tenant isolation + limit bypass + time-window abuse + race conditions | $2.00 · 120 min · 75 calls |

---

## Workflow

### Before running any tool

If no context is provided about roles or workflows, ask:

> **Target:** `<extracted URL>`
>
> **Which depth?**
> - `quick` — archaeology + object authorization only *($0.15 · 20 min · 15 calls)*
> - `standard` — full business logic coverage *($0.50 · 60 min · 35 calls)*
> - `thorough` — standard + multi-tenant + races *($2.00 · 120 min · 75 calls)*
>
> Any known roles (e.g. admin/user/guest)? Auth tokens? Transaction flows you've already observed?

---

### Phase 0 — Scope & Setup

```
session(action="start", options={
  "target": "<target>",
  "depth": "<depth>",
  "scope": ["<target-domain>"]
})
report(action="dashboard", data={"port": 5000})
```

---

### Phase 0b — Coverage Matrix Gate (MANDATORY)

```
session(action="status")
```

| `coverage.total_cells` | Action |
|------------------------|--------|
| **> 0** | Matrix pre-built by caller. Skip to Phase 1b. |
| **== 0** | Empty. MUST build it now. Continue to Phase 1. |

---

### Phase 1 — Application Archaeology

**This phase is the core differentiator of this skill. Do NOT skip it. Do NOT jump straight to testing. You cannot derive business invariants without understanding what the application does.**

#### 1a — Map the surface

```
scan(tool="spider", target="<target>", options={"depth": 3, "mode": "fast"})
```

Then probe for API specs:
```
http(action="request", url="<target>/api/docs")
http(action="request", url="<target>/swagger.json")
http(action="request", url="<target>/openapi.json")
http(action="request", url="<target>/v3/api-docs")
http(action="request", url="<target>/graphql", method="POST", body={"query":"{__schema{types{name}}}"})
```

If OpenAPI/GraphQL spec found → chain into `/api-security` immediately (it handles spec-driven testing).

#### 1b — Register endpoints into the coverage matrix

For every discovered endpoint, register it with its parameters. Use `injection_type` hints that reflect the business logic category being tested:

```
# Example: order endpoint
report(action="coverage", data={
  "type": "endpoint",
  "path": "/api/orders/{id}",
  "method": "GET",
  "params": [{"name": "id", "type": "path", "value_hint": "integer"}],
  "discovered_by": "spider",
  "auth_context": "jwt"
})
# This auto-generates cells for: sqli, idor, traversal (path/integer)
# and: cors, csrf, security_headers, rate_limit, method_tampering, cache, jwt, race (endpoint/default)
```

#### 1c — Role and authentication inventory

For each distinct auth level (unauthenticated, basic user, premium user, admin, service account):

1. Identify which requests are gated to which role from spider output
2. Obtain or register test credentials for each level (note in session if not available)
3. Run an authenticated re-spider for each role level you have credentials for:
   ```
   scan(tool="spider", target="<target>", options={"depth": 3, "mode": "fast"}, flags="-H 'Cookie: session=ROLE_TOKEN'")
   ```
4. Register any role-specific endpoints discovered into the coverage matrix

#### 1d — Business model synthesis (MANDATORY OUTPUT)

Before ANY testing, write a note with your business model synthesis:

```
report(action="note", data={"message": """
BUSINESS MODEL SYNTHESIS
========================
App type: [e-commerce / SaaS subscription / banking / marketplace / social / other]

ROLES:
- [role_name]: can [do X], cannot [do Y], identified by [header/claim/row]
  ...

WORKFLOWS:
- [workflow_name]: [step1] → [step2] → [step3] (terminal state: [state])
  State transitions enforced by: [session / DB status field / JWT claim]
  ...

VALUE OPERATIONS (operations that move money, credits, permissions, or data ownership):
- [endpoint]: transfers/grants [what] from [actor] to [actor]
  ...

TRUST BOUNDARIES:
- Client supplies: [list of user-controlled fields that affect authorization/logic]
- Server derives: [list of fields that should NEVER come from client]
  ...

INVARIANTS (what must NEVER be possible):
- A [role_A] user must NEVER access [role_B]'s [resource]
- A [workflow] must NEVER skip [step] and go directly to [later_step]
- A user must NEVER [pay less than / redeem more than / exceed quota of] [X]
- [tenant_A] data must NEVER be readable by [tenant_B]
  ...
"""})
```

**The testing phases below are derived from these invariants. For each invariant, you will design and run a specific test case. Do not test what you didn't derive from the model.**

---

### Phase 2 — Object Authorization (BOLA + BFLA)

**BOLA (Broken Object Level Authorization / IDOR):** Can user A access user B's objects by changing an ID?
**BFLA (Broken Function Level Authorization):** Can a lower-privilege user invoke functions restricted to higher-privilege roles?

#### 2a — BOLA: Cross-user object access

For every endpoint with an object ID parameter (path or query integer/UUID):

```
# Step 1: Get your own object IDs (register as user_A, create objects)
http(action="request", method="POST", url="<target>/api/orders", headers={"Authorization": "Bearer TOKEN_A"}, body={"item": "test"})
# Note returned order ID: e.g., 1042

# Step 2: Access with a different user's session
http(action="request", method="GET", url="<target>/api/orders/1042", headers={"Authorization": "Bearer TOKEN_B"})
# BOLA confirmed if 200 + object data returned (not 403/404)

# Step 3: Mutate via B's session (BOLA on write)
http(action="request", method="PUT", url="<target>/api/orders/1042", headers={"Authorization": "Bearer TOKEN_B"}, body={"status": "cancelled"})

# Step 4: Also test indirect references — search, filter, include params
http(action="request", method="GET", url="<target>/api/search?user_id=USER_A_ID", headers={"Authorization": "Bearer TOKEN_B"})
```

For UUID-formatted IDs that can't be guessed, use the IDOR advanced techniques in `refs/idor-advanced.md`.

Mark cells:
```
report(action="coverage", data={"type": "tested", "cell_id": "<cell_id>", "status": "vulnerable|tested_clean", "notes": "<what was tested>", "tested_by": "http_manual"})
```

#### 2b — BFLA: Cross-role function invocation

For every admin/privileged endpoint discovered during authenticated re-spider:

```
# Identify admin-only endpoints from URL patterns: /admin/, /manage/, /internal/, /v1/admin/
# Test with lower-privilege token directly
http(action="request", method="GET", url="<target>/admin/users", headers={"Authorization": "Bearer USER_TOKEN"})
http(action="request", method="DELETE", url="<target>/api/users/OTHER_ID", headers={"Authorization": "Bearer USER_TOKEN"})
http(action="request", method="POST", url="<target>/api/admin/promote", headers={"Authorization": "Bearer USER_TOKEN"}, body={"user_id": "USER_ID", "role": "admin"})
```

Also test method switching on restricted endpoints:
```
# Endpoint allows GET for any role; test if POST (create/modify) is also accessible
http(action="request", method="POST", url="<target>/api/reports", headers={"Authorization": "Bearer USER_TOKEN"}, body={"type": "all_users"})
```

---

### Phase 3 — Workflow Integrity Testing

**Root pattern:** Application enforces multi-step workflows (checkout → payment → fulfillment) using a client-visible or DB-visible state field. Skipping a required step is possible if the state machine is checked only at submission, not at each transition.

#### 3a — Identify the workflow's state representation

Where is the current step tracked?
- URL: `/checkout/step2` — skip to `/checkout/step3` directly
- Session cookie: decode and inspect for `step`, `stage`, `status` fields
- Hidden form field: `<input type="hidden" name="wizard_step" value="2">`
- JWT claim: decode with `kali(command="echo JWT | cut -d. -f2 | base64 -d | python3 -m json.tool")`
- Database: returned in API responses as `order.status`, `application.state`

#### 3b — Prerequisite skip attack

For each multi-step workflow (checkout, onboarding, approval, application):

```
# Step 1: Start the workflow, note the terminal/completion URL or endpoint
http(action="request", method="POST", url="<target>/checkout/start", headers={"Cookie": "session=TOKEN"}, body={"cart_id": "CART_ID"})
# Returns: {"step": 1, "next": "/checkout/payment"}

# Step 2: Skip directly to completion WITHOUT payment
http(action="request", method="POST", url="<target>/checkout/complete", headers={"Cookie": "session=TOKEN"}, body={"cart_id": "CART_ID", "step": 3})
# VULNERABLE if: order created, items shipped, subscription activated
```

Variations to try:
```
# Try replaying the final step from a different (completed) session
# Try with step field set to final value in body/cookie
# Try accessing the order confirmation page directly before payment
# Try modifying the redirect URL on the payment page to skip callback
http(action="request", method="GET", url="<target>/order/confirm?order_id=NEW_ORDER_ID&status=paid")
```

#### 3c — Status field manipulation

When an object's status is returned in API responses, test direct mutation:

```
# If GET /api/orders/1042 returns {"status": "pending_payment", ...}
# Try updating the status field directly
http(action="request", method="PATCH", url="<target>/api/orders/1042", headers={"Authorization": "Bearer USER_TOKEN"}, body={"status": "paid"})
http(action="request", method="PATCH", url="<target>/api/orders/1042", headers={"Authorization": "Bearer USER_TOKEN"}, body={"status": "shipped"})

# Also test approval workflows
http(action="request", method="PATCH", url="<target>/api/applications/5", headers={"Authorization": "Bearer USER_TOKEN"}, body={"status": "approved", "reviewer_id": "SELF_ID"})
```

---

### Phase 4 — Value Transfer & Financial Logic

**This phase applies to any application that moves money, credits, subscription tiers, discount codes, or any scarce resource.**

#### 4a — Price parameter tampering

```
# Baseline: observe the purchase flow and find where price appears in client-side requests
# Check: POST body, hidden fields, query parameters, cookie values

# Test 1: Direct price manipulation
http(action="request", method="POST", url="<target>/api/checkout", headers={"Authorization": "Bearer TOKEN"}, body={"item_id": 5, "quantity": 1, "price": 0.01})
http(action="request", method="POST", url="<target>/api/checkout", headers={"Authorization": "Bearer TOKEN"}, body={"item_id": 5, "quantity": 1, "price": -100})

# Test 2: Currency confusion (different currency unit)
http(action="request", method="POST", url="<target>/api/checkout", headers={"Authorization": "Bearer TOKEN"}, body={"item_id": 5, "amount": 100, "currency": "JPY"})
# If app converts: $100 base price → 100 JPY = ~$0.67 → pays $0.67 for $100 item

# Test 3: Decimal precision (floating point truncation)
http(action="request", method="POST", url="<target>/api/checkout", headers={"Authorization": "Bearer TOKEN"}, body={"item_id": 5, "price": 0.000001})
```

#### 4b — Discount and coupon abuse

```
# Test 1: Multiple discount stacking
http(action="request", method="POST", url="<target>/api/cart/discount", body={"code": "SAVE10"})
http(action="request", method="POST", url="<target>/api/cart/discount", body={"code": "SAVE20"})
# Vulnerable if both applied cumulatively

# Test 2: Coupon reuse after "consumed" state
http(action="request", method="POST", url="<target>/api/redeem", headers={"Authorization": "Bearer TOKEN"}, body={"code": "GIFTCARD50"})
# Then try again immediately:
http(action="request", method="POST", url="<target>/api/redeem", headers={"Authorization": "Bearer TOKEN"}, body={"code": "GIFTCARD50"})

# Test 3: Coupon from a different user's cart
# Register as user_A, generate/obtain a coupon, use from user_B
http(action="request", method="POST", url="<target>/api/redeem", headers={"Authorization": "Bearer TOKEN_B"}, body={"code": "USER_A_COUPON"})

# Test 4: Negative quantity discount (coupon that adds money)
http(action="request", method="POST", url="<target>/api/cart/discount", body={"code": "SAVE10", "quantity": -5})
```

#### 4c — Race condition on balance operations

For any endpoint that checks a balance/quota then deducts it (see `refs/race-condition.md` for full technique):

```
# Identify endpoints: fund transfer, coupon redemption, credit spend, subscription activation
# Send N simultaneous requests targeting the same single-use resource

kali(command="seq 1 30 | xargs -P 30 -I {} curl -s -o /dev/null -w '%{http_code}\\n' -X POST '<target>/api/redeem' -H 'Authorization: Bearer TOKEN' -H 'Content-Type: application/json' -d '{\"code\":\"GIFT50\"}'")
# Count 200 responses — if > 1, the race succeeded
```

For HTTP/2 targets (tighter timing window), use the single-packet attack from `refs/race-condition.md`.

#### 4d — Refund and reversal abuse

```
# Test 1: Refund after consuming the benefit
# Buy product → download it → request refund
http(action="request", method="POST", url="<target>/api/orders/1042/refund")
# Check: can you keep the download access after refund?

# Test 2: Partial refund accumulation exceeding purchase price
http(action="request", method="POST", url="<target>/api/orders/1042/refund", body={"amount": 80})
http(action="request", method="POST", url="<target>/api/orders/1042/refund", body={"amount": 80})
# Total refunded: $160 on a $100 order

# Test 3: Refund after subscription cancellation
# Cancel subscription → immediately request refund for full billing period
```

#### 4e — Cart price lock bypass

```
# Add expensive items to cart when sale price applies, lock the cart, wait out the sale
# More directly: test whether price is re-validated at checkout or only at add-to-cart time

# Step 1: Add item at current price
http(action="request", method="POST", url="<target>/api/cart", body={"item_id": 5})
# Returns: {"cart_id": "CART123", "total": 50.00}

# Step 2: Use the cart token from step 1, but modify the price field
http(action="request", method="POST", url="<target>/api/checkout", body={"cart_id": "CART123", "total": 1.00})
```

---

### Phase 5 — Trust Boundary Confusion

**Root pattern:** The application trusts parameters it should derive server-side. Common cases: user sends their own `role`, `tier`, `org_id`, `account_type`, `is_admin`, or `price` in the request body.

#### 5a — Mass assignment / parameter pollution probe

```
# Try injecting privilege-escalation fields into registration and update endpoints
http(action="request", method="POST", url="<target>/api/register", body={"username": "test", "password": "test", "role": "admin"})
http(action="request", method="POST", url="<target>/api/register", body={"username": "test", "password": "test", "is_admin": true})
http(action="request", method="POST", url="<target>/api/register", body={"username": "test", "password": "test", "subscription_tier": "enterprise"})

# Try injecting on profile/account update
http(action="request", method="PUT", url="<target>/api/profile", headers={"Authorization": "Bearer TOKEN"}, body={"display_name": "test", "role": "admin"})
http(action="request", method="PATCH", url="<target>/api/account", headers={"Authorization": "Bearer TOKEN"}, body={"email": "new@test.com", "is_verified": true, "account_balance": 99999})
```

#### 5b — Hidden field discovery via ffuf

```
scan(tool="ffuf", target="<target>/api/register?FUZZ=1", options={"wordlist": "/usr/share/seclists/Discovery/Web-Content/burp-parameter-names.txt"})
scan(tool="ffuf", target="<target>/api/profile?FUZZ=1", options={"wordlist": "/usr/share/seclists/Discovery/Web-Content/burp-parameter-names.txt"})
```

Interesting parameter names to look for: `role`, `admin`, `superuser`, `tier`, `plan`, `is_verified`, `credit`, `balance`, `discount`, `group`, `org_id`, `tenant_id`

#### 5c — Account context switching

```
# Test whether the app enforces org/tenant context server-side or trusts a client-supplied field
http(action="request", method="GET", url="<target>/api/dashboard", headers={"Authorization": "Bearer TOKEN", "X-Org-ID": "TARGET_ORG_ID"})
http(action="request", method="GET", url="<target>/api/data", headers={"Authorization": "Bearer TOKEN"}, body={"org_id": "OTHER_ORG_ID"})

# Attempt to switch to admin context:
http(action="request", method="GET", url="<target>/api/dashboard", headers={"Authorization": "Bearer TOKEN", "X-User-Role": "admin"})
```

---

### Phase 6 — Limit & Quota Bypass

**Root pattern:** Application enforces usage limits (API calls/day, file upload size, message count, storage quota) with server-side checks that can be bypassed by changing the unit of measure, fragmenting the request, or exploiting stale quota checks.

#### 6a — Rate limit bypass

```
# Test common bypass techniques on rate-limited endpoints
# 1. Change the IP marker
http(action="request", url="<target>/api/endpoint", headers={"X-Forwarded-For": "1.2.3.4"})
http(action="request", url="<target>/api/endpoint", headers={"X-Real-IP": "1.2.3.5"})

# 2. Case variation on username (for per-user rate limits)
# login as "admin", "Admin", "ADMIN", "admin " (trailing space)

# 3. Null byte / encoding
http(action="request", url="<target>/api/endpoint", body={"username": "admin\x00"})
```

#### 6b — Upload size / quota bypass

```
# Test 1: Chunk upload to exceed total quota in chunks under the per-request limit
# Test 2: Content-Length mismatch (declare smaller than actual)
# Test 3: Compression bomb — upload a small .zip that expands to exceed quota
kali(command="python3 -c \"import zipfile,io; z=zipfile.ZipFile('/tmp/bomb.zip','w',zipfile.ZIP_DEFLATED); z.writestr('big.txt','A'*10_000_000); z.close()\"")
http(action="request", method="POST", url="<target>/api/upload", headers={"Authorization": "Bearer TOKEN"}, body={"file": "@/tmp/bomb.zip"})

# Test 4: Integer overflow on quantity field
http(action="request", method="POST", url="<target>/api/purchase", body={"item_id": 5, "quantity": 2147483647})
# Or wrap around: quantity=-1 may become MAX_INT after server-side unsigned cast
```

#### 6c — Subscription tier bypass

```
# If app gates features behind paid tier, test with free-tier token on paid endpoints
http(action="request", method="GET", url="<target>/api/premium/export", headers={"Authorization": "Bearer FREE_TIER_TOKEN"})

# Also test JWT claim tampering — if tier is in the JWT payload
kali(command="python3 /opt/jwt_tool/jwt_tool.py FREE_JWT -I -pc tier -pv premium")
http(action="request", method="GET", url="<target>/api/premium/export", headers={"Authorization": "Bearer TAMPERED_JWT"})
```

---

### Phase 7 — Time-Window & Expiry Logic

**Root pattern:** Application uses time-based validity (trial periods, password reset links, OTP windows, coupon expiry, session idle timeout) but checks the time at a different point than the resource is consumed, or reuses a timestamp from the client.

#### 7a — Token/link replay after expiry

```
# Test 1: Password reset link replay
# Request password reset → note the token → wait for it to expire → try again
http(action="request", method="POST", url="<target>/api/reset-password", body={"token": "EXPIRED_TOKEN", "new_password": "hacked123"})

# Test 2: Email verification link replay
# Verify email → use same link again → check if a second account can be verified with the same link

# Test 3: OTP replay in the same window
# Log in with OTP → copy the OTP → use it again within the validity window
```

#### 7b — Trial period bypass

```
# Test: Create new account → activate trial → cancel → create new account with same email +1 char trick
# Register: user@test.com, then user+1@test.com, then user+2@test.com
# Check if trials stack or if there's a per-card/per-IP check instead of per-email

# Test: Manipulate trial_ends_at or subscription_start date via mass assignment
http(action="request", method="PUT", url="<target>/api/account", headers={"Authorization": "Bearer TOKEN"}, body={"trial_ends_at": "2099-12-31T23:59:59Z"})
```

#### 7c — Session idle timeout bypass

```
# Background keep-alive to prevent session expiry during long-running attacks
kali(command="while true; do curl -s -o /dev/null -H 'Cookie: session=TOKEN' '<target>/api/ping'; sleep 60; done &")
```

---

### Phase 8 — Multi-Tenant / SaaS Isolation

**Root pattern (applies only to multi-tenant applications):** Each tenant's data should be completely invisible and inaccessible to other tenants. Isolation failures range from trivial ID-guessing (tenant_id in URL) to subtle context-injection (X-Org-ID header that the backend trusts without re-validating against the authenticated user's permitted orgs).

#### 8a — Tenant context injection

```
# Register two accounts in different organizations: org_A and org_B
# Authenticate as org_B user, attempt to inject org_A context

# Via header
http(action="request", method="GET", url="<target>/api/dashboard", headers={"Authorization": "Bearer ORG_B_TOKEN", "X-Tenant-ID": "ORG_A_ID"})

# Via query parameter
http(action="request", method="GET", url="<target>/api/reports?org_id=ORG_A_ID", headers={"Authorization": "Bearer ORG_B_TOKEN"})

# Via body field
http(action="request", method="POST", url="<target>/api/search", headers={"Authorization": "Bearer ORG_B_TOKEN"}, body={"query": "confidential", "tenant_id": "ORG_A_ID"})
```

#### 8b — Cross-tenant object access via BOLA

```
# Every BOLA test in Phase 2 should also be run cross-tenant (not just cross-user)
# Object IDs created by org_A should return 403/404 for org_B, not the object

# Use org_A user to create objects, note their IDs
# Authenticate as org_B user, attempt access on org_A object IDs
```

#### 8c — Shared resource disclosure

```
# Test for global/shared resources leaking cross-tenant
http(action="request", method="GET", url="<target>/api/templates", headers={"Authorization": "Bearer ORG_B_TOKEN"})
# Should only return org_B templates — check for org_A templates in response

http(action="request", method="GET", url="<target>/api/audit-log", headers={"Authorization": "Bearer ORG_B_TOKEN"})
# Audit log should be scoped to org_B only
```

---

### Phase 9 — Coverage Matrix Completion Gate

Before calling `session(action="complete")`:

1. All cells in `status: "pending"` or `status: "in_progress"` must be resolved
2. For each cell marked `not_applicable`, you must have a concrete reason from your business model synthesis
3. All `vulnerable` findings must have a PoC saved with `http(action="save_poc", ...)`

```
session(action="status")
```

For any remaining pending cells, either test them or justify N/A with evidence:
```
report(action="coverage", data={
  "type": "tested",
  "cell_id": "<cell_id>",
  "status": "not_applicable",
  "notes": "Endpoint does not exist in this app's domain model",
  "tested_by": "manual_review"
})
```

---

### Phase 10 — Complete & Chain

```
session(action="complete", options={"notes": "Business logic assessment complete. Key findings: <summary>"})
```

If the user asks to file findings as GitHub issues, invoke `/gh-export` at this point.

---

## Finding Templates

### BOLA finding template

```
report(action="finding", data={
  "title": "BOLA: [User A] can access [User B]'s [resource] via /api/[endpoint]",
  "severity": "high",
  "target": "<full URL>",
  "description": "User B's [resource type] is accessible by User A by substituting the [path/query] parameter. The server does not verify that the authenticated user owns the requested object. OWASP API Security Top 10 2023: API1:2023 Broken Object Level Authorization.",
  "evidence": "Request: [request details]. Response: [response excerpt showing victim's data].",
  "reproduction": "1. Authenticate as user_B\n2. Note resource ID [X]\n3. Authenticate as user_A\n4. Send GET /api/[endpoint]/[X] with user_A's token\n5. Observe: response contains user_B's data",
  "tool_used": "http_manual"
})
```

### BFLA finding template

```
report(action="finding", data={
  "title": "BFLA: [Low-privilege role] can invoke [admin function] at /api/[endpoint]",
  "severity": "high",
  "target": "<full URL>",
  "description": "A user with [role] can invoke [admin function] by sending a direct request to [endpoint]. The server performs no role check — only the UI hides the function. OWASP API Security Top 10 2023: API5:2023 Broken Function Level Authorization.",
  "evidence": "Request with [role] token to [endpoint] returned [response showing elevated action succeeded].",
  "reproduction": "1. Authenticate as [low-privilege role]\n2. Send [METHOD] /api/[admin-endpoint]\n3. Observe: action succeeds (HTTP 200, not 403)",
  "tool_used": "http_manual"
})
```

### Workflow bypass finding template

```
report(action="finding", data={
  "title": "Workflow bypass: [step] in [workflow] can be skipped without [prerequisite]",
  "severity": "high",
  "target": "<full URL>",
  "description": "The [workflow] enforces [step_A → step_B → step_C] but allows direct submission to [step_C] without completing [step_B]. The state transition is enforced only client-side.",
  "evidence": "Direct POST to /[completion-endpoint] without prior payment step returned HTTP 200 with order confirmed.",
  "reproduction": "1. Start checkout flow\n2. Skip payment step\n3. POST /checkout/complete directly\n4. Observe: order created and confirmed without payment",
  "tool_used": "http_manual"
})
```

### Financial logic finding template

```
report(action="finding", data={
  "title": "Price manipulation: [item] can be purchased for [injected_value] via parameter tampering",
  "severity": "critical",
  "target": "<full URL>",
  "description": "The checkout endpoint accepts a client-supplied [price/amount] parameter which overrides the server-stored price. An attacker can purchase any item for an arbitrary amount, including $0 or negative values.",
  "evidence": "POST /api/checkout with body {price: 0.01} completed successfully — order confirmed at $0.01 (server price: $99.00).",
  "reproduction": "1. Add item to cart\n2. Intercept checkout request\n3. Modify price parameter to 0.01\n4. Observe: order confirmed at modified price",
  "tool_used": "http_manual"
})
```
