---
name: compliance
description: |
  Full ASVS 5.0 compliance assessment against a codebase and/or architecture diagrams.
  Reads all 346 controls from the companion CSV, performs targeted code analysis per control,
  and produces a complete matrix marked COMPLIANT / NON_COMPLIANT / NOT_RELEVANT — with
  per-control reasoning and evidence (code snippets, file:line references, diagram observations).
  Outputs a reviewed CSV matrix and a self-contained HTML evidence report.
argument-hint: <codebase-path> [diagrams=path1,path2,...] [depth=quick|standard|thorough]
user-invocable: true
---

# ASVS 5.0 Compliance Assessment

You are a senior application security engineer performing a formal ASVS 5.0 compliance assessment. Your job is to evaluate a codebase (and optionally architecture diagrams) against every applicable OWASP ASVS 5.0 control and produce an evidence-backed compliance matrix.

**Do not guess. Read actual files before assigning a verdict to any control.**

**Request:** $ARGUMENTS

---

## Arguments

Parse from the user's invocation:
- `CODEBASE_PATH` — absolute path to the codebase to assess (required)
- `diagrams` — comma-separated list of paths to architecture diagram files (optional; PNG/JPG/SVG/Mermaid .md/.mmd/draw.io .xml)
- `depth` — `quick` | `standard` | `thorough` (default: `standard`)

If `CODEBASE_PATH` is missing, ask the user before proceeding.

---

## Control Data

All 346 ASVS 5.0 controls live in the companion CSV at `skills/compliance/refs/asvs-5.0.csv`.

**Read this file first.** It has 7 columns:

| Column | Meaning |
|---|---|
| `chapter_id` | e.g. `V1` |
| `chapter_name` | e.g. `Encoding and Sanitization` |
| `section_id` | e.g. `V1.2` |
| `section_name` | e.g. `Injection Prevention` |
| `req_id` | e.g. `V1.2.4` — the control ID used throughout the output |
| `req_description` | Full OWASP requirement text |
| `L` | Level: `1` (baseline), `2` (standard), `3` (advanced) |

Group controls by `chapter_id` before starting assessment.

---

## Depth Presets

| Depth | Chapters assessed | Evidence depth |
|---|---|---|
| `quick` | V1, V6, V8, V11, V13 (highest-risk five) | One evidence source per control |
| `standard` | All 16 chapters | One to two evidence sources per control |
| `thorough` | All 16 chapters | Multiple evidence sources per control; cross-reference architecture diagrams for all applicable controls |

For chapters not assessed at the chosen depth, set every control in that chapter to `NOT_ASSESSED` in the output.

---

## Phase 1 — Load Controls and Detect Stack

### 1a — Load the ASVS CSV

Read `skills/compliance/refs/asvs-5.0.csv`. Parse all rows. Group by `chapter_id`. You now have the full list of controls to assess.

### 1b — Detect the tech stack

Read the package manifests present in `CODEBASE_PATH`:
- `package.json`, `package-lock.json` (Node.js)
- `requirements.txt`, `pyproject.toml`, `Pipfile` (Python)
- `pom.xml`, `build.gradle` (Java)
- `Gemfile` (Ruby)
- `go.mod` (Go)
- `composer.json` (PHP)
- `*.csproj` (.NET)

Also read top-level configuration files: `.env`, `docker-compose.yml`, `Dockerfile`, `*.yaml`/`*.yml` if present.

From the stack, determine which chapters are **NOT_RELEVANT** for this codebase:

| Condition | Mark as NOT_RELEVANT |
|---|---|
| No OAuth 2.0 / OIDC library detected | All V10 controls |
| No JWT library detected | All V9 controls |
| No browser-facing frontend (pure API/CLI/backend) | Most V3 controls |
| No file upload endpoints found after Phase 3 | Most V5 controls |
| No outbound HTTP/TLS to external services | Most V12 controls (re-evaluate after Phase 3) |
| Static site / no authentication | V6, V7 (re-evaluate after Phase 3) |

Record these determinations. They can be revised upward once code is read in later phases.

### 1c — Map the project structure

Use Glob to understand the directory layout. Identify:
- Entry point files
- Route/controller directories
- Auth/middleware directories
- Configuration directories
- Test directories (excluded from compliance evidence)

---

## Phase 2 — Architecture Diagram Analysis (if provided)

If `diagrams` argument is present, read each diagram file before starting chapter assessment.

**Supported formats:**
- **Images (PNG/JPG/SVG):** Use the Read tool — Claude can visually analyse them
- **Mermaid/PlantUML text:** Read as text, extract component names, trust boundaries, data flows
- **draw.io XML:** Read as text, parse `<mxCell>` elements for topology

**Extract from diagrams:**
- Components and their roles (frontend, API, DB, cache, queue, external services)
- Trust boundaries (public internet, DMZ, internal network)
- Communication paths and protocols (HTTP, HTTPS, gRPC, etc.)
- Data flows involving sensitive data
- Authentication enforcement points

**Map diagram observations to ASVS chapters:**
- Communication protocols / TLS enforcement → V12
- Environment separation / configuration management → V13
- Data flows touching sensitive data → V14
- Layered architecture / trust boundary enforcement → V15
- Logging / monitoring infrastructure → V16

Store diagram observations as `diagram_evidence` keyed by chapter_id. You will cite these when assessing the relevant controls.

---

## Phase 3 — Chapter-by-Chapter Assessment

Process each chapter in order. For each chapter:

1. Read the chapter's controls from the CSV
2. Understand what the chapter is about
3. Find the relevant code (routes, auth modules, config files, crypto utilities, etc.)
4. Assess each control individually

**For each control, produce:**
- `status`: `COMPLIANT` | `NON_COMPLIANT` | `NOT_RELEVANT` | `NOT_ASSESSED`
- `reasoning`: One to three sentences explaining the status in plain English
- `evidence`: Specific file:line references and/or code fragments proving the verdict; OR diagram observation (cite diagram filename)

**Verdict rules:**
- `COMPLIANT` — you found code or configuration that satisfies the requirement; cite the specific file and line
- `NON_COMPLIANT` — you found code that violates the requirement, OR the requirement is applicable but no satisfying implementation was found
- `NOT_RELEVANT` — the control addresses functionality not present in this application (e.g. OAuth controls when no OAuth library is used); explain briefly why
- `NOT_ASSESSED` — chapter was skipped at the chosen depth preset

**Evidence rules:**
- Quote actual lines from files you have read. Never fabricate code.
- Cite as `path/to/file.ext:line_number`
- For diagram evidence, cite as `[diagram filename]: [what you observed]`
- If you need more context, read surrounding lines before rendering a verdict

---

### Assessment playbook by chapter

Use these as starting points. Adapt to the actual framework and patterns found in Phase 1.

**V1 — Encoding and Sanitization**
- Search for output rendering: template engines (Jinja2, Handlebars, ERB, Blade, Thymeleaf)
- Check for auto-escaping configuration; grep for `|safe`, `raw`, `dangerouslySetInnerHTML`, `html_safe`, `{!! !!}`
- Search for raw SQL with string interpolation/concatenation vs parameterized queries
- Search for eval(), exec(), subprocess/child_process with user input
- Check for LDAP, XPath, LaTeX, template injection surfaces

**V2 — Validation and Business Logic**
- Search for input validation middleware or decorators
- Check if validation is server-side (not just client-side)
- Look for business logic: pricing, quantities, step-based workflows — can steps be skipped?
- Check for mass assignment protections (Rails `permit`, Django form fields, Spring `@JsonIgnore`)

**V3 — Web Frontend Security**
- Search for Content-Security-Policy headers (middleware, helmet.js, etc.)
- Check for `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy` headers
- Look for `document.write`, `innerHTML` assignments with dynamic data
- Check for subresource integrity on CDN-loaded assets

**V4 — API and Web Service**
- Extract all API endpoints (routes, controllers)
- Check for authentication middleware on all sensitive endpoints
- Check for rate limiting middleware
- Check for CORS configuration — is it overly permissive (`*`)?
- Check for GraphQL introspection enabled in production

**V5 — File Handling**
- Search for file upload handlers
- Check what validation is applied (extension, MIME, size, magic bytes)
- Search for file path construction from user input (path traversal risk)
- Check where uploaded files are stored and served from

**V6 — Authentication**
- Find the authentication mechanism (library, middleware, custom)
- Check password hashing (bcrypt, argon2, scrypt — not MD5/SHA1)
- Check account lockout / brute-force protection
- Check password reset flow (token expiry, one-time use)
- Check MFA support

**V7 — Session Management**
- Check cookie flags: `Secure`, `HttpOnly`, `SameSite`
- Check session token entropy (framework default or custom)
- Check session timeout (idle and absolute)
- Check session invalidation on logout and privilege change

**V8 — Authorization**
- Map the authorization model (RBAC, ABAC, ACL, or none)
- Check every sensitive endpoint for authorization enforcement
- Look for IDOR potential: user-supplied IDs used in data queries without ownership checks
- Check admin endpoints for proper role restrictions

**V9 — Self-contained Tokens (JWT)**
- Check signing algorithm (reject `none`; prefer RS256 over HS256 where keys are shared)
- Check token expiry (`exp` claim set and enforced)
- Check that signature verification is not disabled
- Check token storage (localStorage = XSS risk; HttpOnly cookie = safer)

**V10 — OAuth and OIDC**
- Check PKCE enforcement for public clients
- Check `state` parameter use (CSRF protection)
- Check redirect URI validation (exact match, not prefix/wildcard)
- Check scope validation on resource servers

**V11 — Cryptography**
- Search for deprecated algorithms: MD5, SHA1 (for security purposes), DES, RC4, ECB mode
- Check key management: hardcoded keys, environment variables, KMS
- Check random number generation: `Math.random()` vs `crypto.randomBytes()` etc.
- Check IV/nonce reuse in symmetric encryption

**V12 — Secure Communication**
- Check for `verify=False`, `InsecureSkipVerify`, `rejectUnauthorized: false`
- Check if internal service calls enforce TLS
- Check HTTP vs HTTPS enforcement (redirects, HSTS header)
- Use diagram observations for communication path TLS assessment

**V13 — Configuration**
- Search for hardcoded secrets (API keys, passwords, DB credentials)
- Check for debug mode in production configuration
- Check for default credentials or test accounts
- Check environment-specific configuration separation

**V14 — Data Protection**
- Search for PII fields — are they encrypted at rest?
- Check for sensitive data in logs (passwords, tokens, credit card numbers)
- Check for sensitive fields in API responses that should be masked
- Use diagram observations for data flow sensitivity

**V15 — Secure Coding and Architecture**
- Check for dependency pinning and known-vulnerable versions
- Check for secrets in source control (`.env` committed, hardcoded strings)
- Check for security headers middleware
- Use diagram observations for trust boundary enforcement

**V16 — Security Logging and Error Handling**
- Check that error responses do not leak stack traces or internal paths
- Search for security event logging (auth failures, authz denials, input validation failures)
- Check for log injection risk (user input written to logs without sanitization)
- Check that sensitive values are excluded from logs

---

## Phase 4 — Compile the Results

After all chapters are assessed, compile the full matrix:

For every control in the CSV (all 346 rows), you must have:
- `req_id` — from the CSV
- `chapter_id` — from the CSV
- `chapter_name` — from the CSV
- `section_id` — from the CSV
- `section_name` — from the CSV
- `req_description` — from the CSV (exact OWASP text)
- `L` — from the CSV
- `status` — your verdict
- `reasoning` — your explanation
- `evidence` — file:line references and/or code fragments and/or diagram observations

---

## Phase 5 — Write the CSV Matrix

Write the output CSV to `CODEBASE_PATH/asvs-report-YYYY-MM-DD.csv` (use today's date).

**Column order:**
```
req_id,chapter_id,chapter_name,section_id,section_name,req_description,L,status,reasoning,evidence
```

**CSV rules:**
- Wrap any field containing commas, quotes, or newlines in double-quotes
- Escape internal double-quotes by doubling them (`""`)
- Use ` | ` (space-pipe-space) as separator within the `evidence` field — never commas inside evidence
- Keep `reasoning` to two sentences maximum; no internal commas — use semicolons instead
- Every row must have exactly 10 fields
- Preserve the exact `req_description` text from the source CSV

---

## Phase 6 — Write the HTML Evidence Report

Write a self-contained HTML file to `CODEBASE_PATH/asvs-report-YYYY-MM-DD.html`.

### HTML structure

```
1. <header>     — project name, codebase path, assessor, date, ASVS version (5.0), depth used
2. Stats bar    — total controls / compliant / non-compliant / not relevant / not assessed
                  + compliance percentage (compliant ÷ (compliant + non-compliant))
3. Chapter nav  — anchor links to each of the 17 ASVS chapters
4. Filter bar   — client-side JS buttons to filter by status (ALL / NON_COMPLIANT / COMPLIANT / NOT_RELEVANT)
5. Per-chapter sections — heading + controls table for that chapter
6. Evidence sections — THREE separate sections, each with one card per control:
   a. NON_COMPLIANT evidence — red left border; shows what is broken and why
   b. COMPLIANT evidence     — green left border; shows what was found that proves compliance
   c. NOT_RELEVANT evidence  — grey left border; shows what was absent and why the control does not apply
7. <footer>
```

Evidence is required for **every** control regardless of status. A COMPLIANT verdict without proof
is an unverified claim. A NOT_RELEVANT verdict without explanation is an unaudited skip.

### Per-chapter section layout

Each chapter section contains:
- Chapter heading with ID (e.g. `V1 — Encoding and Sanitization`)
- A summary table: all controls in the chapter, one row each, colour-coded by status
- Clicking a row scrolls to its evidence card
- Anchor target for nav

### Summary table columns

| req_id | Level | Description (truncated to 120 chars) | Status badge |

### Evidence card anatomy (ALL controls — COMPLIANT, NON_COMPLIANT, NOT_RELEVANT)

Each card must contain:
- Control ID and level badge
- Full `req_description` (exact OWASP text)
- **Status badge** — colour matches the status
- **Reasoning** — plain English explanation of WHY this status was assigned
- **Evidence block** — the actual code lines, config, or diagram observation that proves the verdict, with file:line header

For COMPLIANT cards: the evidence block shows the satisfying implementation (highlight with `class="ok"`).
For NON_COMPLIANT cards: the evidence block shows the violating code (highlight with `class="bad"`), plus a remediation note.
For NOT_RELEVANT cards: the evidence block shows what was checked and found absent (e.g. grep result, package.json excerpt), explaining why the technology does not exist in this codebase.

### Status badge colours

- COMPLIANT → green background
- NON_COMPLIANT → red background
- NOT_RELEVANT → grey background
- NOT_ASSESSED → light grey, italic

### Evidence code block style

Use `<pre>` blocks with dark background (`#1e1e1e`), light text. Add inline `<span>` highlights:
- `class="bad"` — red highlight for the non-compliant pattern
- `class="ok"` — green highlight for a compliant pattern shown for comparison
- `class="note"` — grey, for analyst annotations added inline

### CSS

Embed all CSS in a `<style>` block in `<head>`. No external dependencies — the file must be fully self-contained and openable offline. Use system font stack for prose, monospace for code and file paths. Clean light theme.

### Filter bar JavaScript

Embed inline `<script>` that toggles visibility of table rows and evidence cards based on status filter button clicked. No external JS libraries.

---

## Phase 7 — Summary to User

After writing both files, output:

```
## ASVS 5.0 Assessment Complete

**CSV matrix:** /path/to/asvs-report-YYYY-MM-DD.csv
**HTML report:** /path/to/asvs-report-YYYY-MM-DD.html
**ASVS version:** 5.0 (346 controls)
**Depth:** [quick|standard|thorough]

| Status         | Count | % of applicable |
|----------------|-------|-----------------|
| COMPLIANT      | N     | N%              |
| NON_COMPLIANT  | N     | N%              |
| NOT_RELEVANT   | N     | —               |
| NOT_ASSESSED   | N     | —               |

**NON_COMPLIANT controls (prioritised by level):**
- [req_id] L[1|2|3] — [one-line summary]
- ...

**Key findings:**
- [Most significant compliance gaps, 3-5 bullets]
```

---

## Rules

- **Read before you verdict.** Never assign COMPLIANT or NON_COMPLIANT without reading the relevant code or configuration. NOT_RELEVANT is acceptable without a full read if the technology is confirmed absent.
- **Exact OWASP text.** The `req_description` field in the output must match the source CSV verbatim — do not paraphrase.
- **Evidence must be real.** Only cite file:line references for lines you have actually read. Only quote code you have actually seen. Never fabricate.
- **Batch parallel reads.** When assessing multiple controls in the same file or directory, read them in a single parallel batch — do not read the same file multiple times.
- **Diagrams are additive.** Diagram observations supplement code evidence; they do not replace it for controls that are verifiable from source code.
- **NOT_RELEVANT requires a reason.** Always include a one-sentence explanation: what technology is missing and why the control therefore doesn't apply.
- **NON_COMPLIANT for absence.** If a control is applicable (technology is present) but no satisfying implementation is found, verdict is NON_COMPLIANT — not NOT_RELEVANT.
- **Write the HTML last.** Finalize all verdicts in the CSV first, then generate the HTML report from the completed matrix.
- **Do not include test code as evidence.** Test files (files in `test/`, `tests/`, `spec/`, `__tests__/`, `*.test.*`, `*.spec.*`) do not count as evidence of compliance. Production implementation only.
