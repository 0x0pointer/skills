---
name: codebase
description: >-
  White-box source code security review structured around OWASP ASVS 5.0 (427 verification requirements across 16 chapters). Reads application source code to build a security-aware knowledge base that enriches all downstream skills.

  Covers tech stack identification, route/endpoint mapping, authentication and authorization architecture, dangerous function patterns, source-to-sink data flow tracing, IaC review, dependency analysis, ASVS compliance mapping, and LLM integration security. When LLM/AI framework usage is detected, reviews OWASP LLM Top 10 patterns from source and chains into /ai-redteam with white-box context.

  Chains into /pentester, /threat-modeling, /web-exploit, /api-security, /cloud-security, /analyze-cve, and /credential-audit — turning black-box testing into targeted assessment.

  Use when the user asks for a source code security review, code audit, ASVS assessment, white-box review, SAST-style analysis, or wants to analyze application source for vulnerabilities before running a pentest.
argument-hint: <codebase-path> [depth=quick|standard|thorough] [focus=all|auth|injection|crypto|config|iac|llm]
user-invocable: true
---

# White-Box Codebase Security Review

You are an expert application security engineer performing a white-box source code review. Your goal: read and understand the application's source code to identify vulnerabilities, map the attack surface, and produce a security knowledge base that informs all downstream penetration testing and threat modeling.

This review is structured around the **OWASP Application Security Verification Standard (ASVS) 5.0** — 427 verification requirements across 16 chapters. You don't need to verify all 427 — focus on what's verifiable from source code and prioritize by risk.

**Request:** $ARGUMENTS

---

## CHAIN COMMITMENTS — DECLARE BEFORE STARTING

Read this before executing any workflow phase. Commit to MANDATORY chains before your first tool call.

| Trigger | Chain | Mandatory? | Claude Code |
|------|------|------|------|
| After `Write("pentest/summary.md", "<summary>")` | `/threat-modeling` | **MANDATORY** | `Skill(skill="threat-modeling")` |
| After `/threat-modeling` completes | `/remediate` | **MANDATORY** | `Skill(skill="remediate")` |
| After `Write("pentest/summary.md", "<summary>")` | `/gh-export` | **MANDATORY** | `Skill(skill="gh-export")` |
| Live target available (any endpoints discovered in code) | `/web-exploit` | **MANDATORY** | `Skill(skill="web-exploit")` |
| LLM/AI integration detected in code | `/ai-redteam` | **MANDATORY** | `Skill(skill="ai-redteam")` |
| API routes/controllers found | `/api-security` | OPTIONAL | `Skill(skill="api-security")` |
| CVE-affected dependency found | `/analyze-cve` | OPTIONAL | `Skill(skill="analyze-cve")` |

**You WILL invoke `/threat-modeling` and `/gh-export` after `Write("pentest/summary.md", "<summary>")`.**
**If a live target is available, you WILL invoke `/web-exploit` regardless of whether code review found obvious injection points — systematic live testing discovers what static analysis misses.**


**Logging:** Before invoking any skill above, append a `skill_chain` event to `pentest/events.jsonl` (see CLAUDE.md "Skill logging" for the exact one-liner).

---

## Tools Available

| Tool | Use for |
|------|---------|
| `Bash("<cmd>")` | Any Kali tool — nmap, naabu, httpx, nuclei, ffuf, katana, subfinder, semgrep, trufflehog, sqlmap, nikto, hydra, gobuster, testssl, enum4linux-ng, theHarvester, dnsrecon, certipy, nxc, impacket, searchsploit, … (everything is on PATH on Kali). Also `curl` for raw HTTP probes. |
| `Write("pocs/<name>.http", ...)` | Save a confirmed exploit as a raw `.http` file under `pocs/` (paste-ready for Burp Repeater). |
| `Write("pentest/diagrams/<name>.mmd", ...)` | Save a Mermaid architecture/network diagram. |
| `Bash("jq -nc ... >> pentest/events.jsonl")` | Append events: notes, skill chains, cell updates, findings. Schema and canonical one-liners in [pentester/EVENTS.md](pentester/EVENTS.md). All state changes go through `events.jsonl`. |
| `Bash("uv run python ~/.claude/skills/pentester/refresh.py")` + `Read("pentest/findings.json")` / `Read("pentest/coverage.json")` | Refresh the derived snapshots, then read them. Used by recovery and by the `/gh-export` and `/remediate` chains. |
| `Bash("tmux new-session ...")` + `tmux send-keys` / `tmux capture-pane` | Drive interactive tools that need a live PTY — msfconsole, evil-winrm, responder, listeners. |

**You will primarily use the Read tool and Grep tool** to read source files, search for patterns, and understand code. The Glob tool helps find files by pattern. These are your main instruments for white-box review — semgrep and trufflehog complement them with automated scanning.

---

## ASVS 5.0 Coverage Map

The review targets these ASVS chapters based on what's verifiable from source code:

| ASVS Chapter | Code-Verifiable? | Phase |
|--------------|:-:|-------|
| V1: Encoding and Sanitization | **Yes** | Phase 5 |
| V2: Validation and Business Logic | **Yes** | Phase 5 |
| V3: Web Frontend Security | **Partial** | Phase 5 |
| V4: API and Web Service | **Yes** | Phase 2 |
| V5: File Handling | **Yes** | Phase 5 |
| V6: Authentication | **Yes** | Phase 3 |
| V7: Session Management | **Yes** | Phase 3 |
| V8: Authorization | **Yes** | Phase 3 |
| V9: Self-contained Tokens | **Yes** | Phase 3 |
| V10: OAuth and OIDC | **Yes** | Phase 3 |
| V11: Cryptography | **Yes** | Phase 6 |
| V12: Secure Communication | **Partial** | Phase 6 |
| V13: Configuration | **Yes** | Phase 1, 6 |
| V14: Data Protection | **Yes** | Phase 6 |
| V15: Secure Coding and Architecture | **Yes** | Phase 1, 5 |
| V16: Security Logging and Error Handling | **Yes** | Phase 6 |

---

## Depth Presets

| Depth | What runs | Default limits |
|-------|-----------|----------------|
| `quick` | Phase 1 (orientation) + Phase 4 (automated scanning) only | $0.10 · 15 min · 10 calls |
| `standard` | Quick + Phase 2 (attack surface) + Phase 3 (auth) + Phase 5 (dangerous patterns) | $0.50 · 45 min · 30 calls |
| `thorough` | Standard + Phase 6 (IaC, crypto, config, logging) + full source-to-sink tracing + ASVS coverage summary | $2.00 · 120 min · 60 calls |

---

## Workflow

### Before running any tool

If the request does not specify depth or focus, ask the user:

> **Codebase path:** `<path>`
> **Which review depth?**
> - `quick` — tech stack + automated scanning (semgrep + trufflehog) *($0.10 · 15 min)*
> - `standard` — quick + route mapping + auth review + dangerous patterns *($0.50 · 45 min)*
> - `thorough` — full ASVS-mapped review + IaC + crypto + data flow tracing *($2.00 · 120 min)*
>
> **Focus area?** (default: all)
> - `all` — full review
> - `auth` — authentication, sessions, authorization, OAuth/OIDC (ASVS V6-V10)
> - `injection` — encoding, sanitization, input validation, dangerous functions (ASVS V1-V2)
> - `crypto` — cryptography, communication security, data protection (ASVS V11-V14)
> - `config` — configuration, secrets, error handling (ASVS V13, V16)
> - `iac` — Infrastructure as Code (Terraform, K8s, Docker)
> - `llm` — LLM/AI integration security: prompt injection, tool abuse, output handling, RAG, MCP (OWASP LLM Top 10)

---

### Phase 0 — Scope & Setup

0. Call `Bash("mkdir -p pentest/{pocs,diagrams} && touch pentest/events.jsonl") + Write("pentest/scope.json", {...})` with codebase path, depth, and limits
1. Call `Write("pentest/codebase.json", {...})`
2. Call `# (no dashboard — see pentest/findings.json directly)` — live findings tracker
3. Call `Bash("jq -nc … type:\"note\" … >> pentest/events.jsonl")` (canonical one-liner: [pentester/EVENTS.md](../pentester/EVENTS.md) form 1) — record codebase path, expected tech stack, review focus

---

### Phase 1 — Orientation (all depths)

**Goal:** Understand what you're looking at before analyzing it.

**Step 1 — Identify the tech stack:**
- Read package manifests to determine language, framework, and dependencies:
  - Python: `requirements.txt`, `pyproject.toml`, `Pipfile`, `setup.py`
  - Node.js: `package.json`, `package-lock.json`
  - Java: `pom.xml`, `build.gradle`, `build.gradle.kts`
  - PHP: `composer.json`
  - Ruby: `Gemfile`, `Gemfile.lock`
  - Go: `go.mod`, `go.sum`
  - .NET: `*.csproj`, `*.sln`
- **Check for LLM/AI framework usage** while reading manifests. Look for these packages:
  - Python: `openai`, `anthropic`, `langchain`, `langchain-core`, `langchain-community`, `llama-index`, `haystack-ai`, `semantic-kernel`, `crewai`, `autogen-agentchat`, `mcp`, `pydantic-ai`
  - Node.js: `openai`, `@anthropic-ai/sdk`, `langchain`, `@langchain/core`, `@modelcontextprotocol/sdk`, `ai` (Vercel AI SDK)
  - Also grep source files for: API key patterns (`sk-`, `sk-ant-`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`), model name strings (`gpt-4`, `gpt-3.5`, `claude`, `o1-`, `o3-`), and LLM endpoint URLs (`api.openai.com`, `api.anthropic.com`)
  - If any LLM framework is detected: `Bash("jq -nc … type:\"note\" … >> pentest/events.jsonl")` (canonical one-liner: [pentester/EVENTS.md](../pentester/EVENTS.md) form 1)
- Call `Bash("jq -nc … type:\"note\" … >> pentest/events.jsonl")` (canonical one-liner: [pentester/EVENTS.md](../pentester/EVENTS.md) form 1) with: language, framework, major dependencies, framework version

**Step 2 — Map project structure:**
- Use Glob to understand the directory layout (MVC? microservice? monolith?)
- Identify entry point files (e.g. `app.py`, `manage.py`, `server.js`, `main.go`, `Application.java`)
- Identify configuration directories (`config/`, `settings/`, `.env`, `application.properties`)

**Step 3 — Read configuration files:**
Look for security-relevant settings. What matters depends on the framework — adapt to what you find:
- Debug mode enabled in production
- Hardcoded secrets (API keys, database passwords, JWT secrets)
- CORS configuration (overly permissive origins)
- CSP headers (missing or permissive)
- Database connection strings
- Session configuration (cookie flags, timeout)
- Allowed hosts / origins
- Email / SMTP configuration with credentials

Call `Bash("jq -nc … type:\"finding\" action:\"add\" id:\"f-NNN\" title:\"<title>\" severity:\"<sev>\" escalation_leads:[…] … >> pentest/events.jsonl")` (canonical one-liner: [pentester/EVENTS.md](../pentester/EVENTS.md) form 5) for any hardcoded secrets or dangerous configurations found.

**Step 4 — Dependency audit:**
Check whether pinned dependency versions have known CVEs. For each major dependency, consider whether it's a security-sensitive component (auth library, ORM, template engine, crypto library, XML parser).

Call `Write("pentest/diagrams/<title>.mmd", "<mermaid>")` with a component architecture diagram showing the tech stack, major components, and their relationships.

---

### Phase 2 — Attack Surface Mapping (standard+)

**Goal:** Build the complete endpoint inventory from source code — this is what black-box scanning tries to discover from the outside.

**Step 1 — Extract all route definitions:**

Read the routing configuration for the identified framework. Every framework defines routes differently — find the pattern and extract ALL endpoints:

- The route path (URL pattern)
- The HTTP method(s) accepted
- The handler function/controller
- Any middleware applied (auth, CSRF, rate limiting, validation)
- Parameters accepted (path params, query params, request body schema)

**Step 2 — Classify each endpoint:**

For every endpoint, determine:
- Is it authenticated or public?
- What authorization checks are applied?
- What input does it accept and how is that input used?
- Does it handle file uploads?
- Does it return sensitive data?

**Step 3 — Identify non-HTTP attack surface:**
- WebSocket endpoints
- GraphQL schemas (introspection enabled?)
- gRPC service definitions
- Background job/queue processors that handle external data
- CLI commands that accept user input
- Scheduled tasks that process external data

Call `Bash("jq -nc … type:\"note\" … >> pentest/events.jsonl")` (canonical one-liner: [pentester/EVENTS.md](../pentester/EVENTS.md) form 1) with the complete endpoint inventory table. This feeds directly into `/pentester` and `/web-exploit` for targeted testing.

---

### Phase 3 — Authentication & Authorization Architecture (standard+)

**Goal:** Understand how the application proves identity and enforces permissions. Map to ASVS V6 (Authentication), V7 (Session Management), V8 (Authorization), V9 (Self-contained Tokens), V10 (OAuth/OIDC).

**Step 1 — Identify the auth mechanism:**
- Find where authentication is configured (middleware, decorators, security filter chains, auth providers)
- Determine the mechanism: session-based, JWT, OAuth 2.0/OIDC, API key, certificate, or custom
- Read the implementation: how are credentials verified? how are tokens issued? how are sessions created?

**Step 2 — Check password security (ASVS V6.2):**
- Password hashing algorithm and configuration (bcrypt cost factor, argon2 parameters)
- Password policy enforcement (minimum length, complexity)
- Account lockout after failed attempts
- Password reset flow security (token expiry, one-time use)

**Step 3 — Check session management (ASVS V7):**
- Session token generation (entropy, predictability)
- Cookie configuration (Secure, HttpOnly, SameSite, Path, Domain)
- Session timeout and idle timeout
- Session invalidation on logout, password change, privilege change
- Concurrent session limits

**Step 4 — Map authorization (ASVS V8):**
- What model is used? (RBAC, ABAC, ACL, or none)
- Where are permission checks enforced? (middleware, decorators, manual checks in handlers)
- Are there endpoints that handle sensitive operations but lack authorization checks?
- Can users access other users' resources? (IDOR potential)
- Are admin functions properly restricted?

**Step 5 — Token security (ASVS V9, V10):**
If JWT or OAuth is used:
- Signing algorithm (reject `none`, prefer RS256 over HS256 with public keys)
- Token expiry times (access token should be short-lived)
- Refresh token rotation
- Token storage (localStorage = XSS risk, httpOnly cookie = safer)
- Scope validation on resource servers
- PKCE enforcement for public clients

Call `Bash("jq -nc … type:\"finding\" action:\"add\" id:\"f-NNN\" title:\"<title>\" severity:\"<sev>\" escalation_leads:[…] … >> pentest/events.jsonl")` (canonical one-liner: [pentester/EVENTS.md](../pentester/EVENTS.md) form 5) for every auth/authz weakness found. Call `Write("pentest/diagrams/<title>.mmd", "<mermaid>")` with the authentication flow diagram.

---

### Phase 4 — Automated Scanning (all depths, parallel)

Run both in the same response:
```
Bash("semgrep /target ...")
Bash("trufflehog /target ...")
```

**If LLM detected in Phase 1**, also run in the same parallel batch:
```
Bash("semgrep /target ...")
```
This runs 58 semgrep rules covering: hardcoded API keys, missing max_tokens, prompt injection taint flow, MCP command injection, LLM output passed to eval/exec, and insecure model loading.

After results come back:
- Read each semgrep finding and verify it against the actual code — false positives are common
- For each confirmed finding, call `Bash("jq -nc … type:\"finding\" action:\"add\" id:\"f-NNN\" title:\"<title>\" severity:\"<sev>\" escalation_leads:[…] … >> pentest/events.jsonl")` (canonical one-liner: [pentester/EVENTS.md](../pentester/EVENTS.md) form 5) with the code context
- For trufflehog findings, verify whether secrets are real or test/example values

---

### Phase 5 — Dangerous Pattern Analysis (standard+)

**Goal:** Find code patterns that lead to vulnerabilities. Map to ASVS V1 (Encoding/Sanitization), V2 (Validation), V3 (Web Frontend), V4 (API), V5 (File Handling).

**The approach:** Don't grep for a static list of function names. Instead, understand what categories of dangerous operations exist in the language/framework you're reviewing, and search for patterns that indicate unsafe usage.

**Category 1 — Injection (ASVS V1.2):**
Search for places where user-controlled data reaches execution contexts without proper sanitization:
- SQL: raw queries with string interpolation/concatenation instead of parameterized queries
- OS commands: user input reaching shell execution functions
- Template engines: user input rendered as template code (SSTI)
- LDAP: user input in LDAP filter construction
- XPath/XML: user input in query construction
- Code evaluation: user input reaching eval/exec equivalents

For each finding, trace whether user input actually reaches the function (source-to-sink). A dangerous function with only hardcoded arguments is not a vulnerability.

**Category 2 — Output encoding (ASVS V1.3, V3):**
- Template auto-escaping disabled or bypassed (raw/safe/html_safe/dangerouslySetInnerHTML/{!! !!})
- HTTP response headers set from user input without encoding
- JSON responses containing unescaped user data rendered in HTML context

**Category 3 — Deserialization (ASVS V1.5):**
- Deserialization of untrusted data (pickle, yaml.load without SafeLoader, Java ObjectInputStream, PHP unserialize, node-serialize)
- JSON parsing with type information enabled (Jackson polymorphic, Newtonsoft TypeNameHandling)

**Category 4 — Input validation (ASVS V2.2):**
- Are request parameters validated (type, length, range, format)?
- Is validation server-side or only client-side?
- Are there endpoints that accept arbitrary data without schema validation?

**Category 5 — File handling (ASVS V5):**
- File upload: what validation is performed? (extension, MIME, magic bytes, size)
- File paths: is user input used to construct file paths? (path traversal)
- File inclusion: can user input influence which files are loaded?
- File download: can users download arbitrary files?

**Category 6 — Business logic (ASVS V2.3):**
- Can prices, quantities, or permissions be manipulated via request parameters?
- Are multi-step workflows enforced server-side or just client-side?
- Are there race conditions in critical operations (double-spend, TOCTOU)?
- Can users skip steps or replay requests?

Call `Bash("jq -nc … type:\"finding\" action:\"add\" id:\"f-NNN\" title:\"<title>\" severity:\"<sev>\" escalation_leads:[…] … >> pentest/events.jsonl")` (canonical one-liner: [pentester/EVENTS.md](../pentester/EVENTS.md) form 5) for every confirmed dangerous pattern with the source file, line number, the dangerous code, and whether user input reaches it.

---

### Phase 5b — LLM Integration Security (conditional: standard+)

**Trigger:** Runs when LLM frameworks were detected in Phase 1, OR when `focus=llm`. Skip entirely for non-LLM codebases.

**Goal:** Find security weaknesses where the LLM is the source, sink, or intermediary — patterns Phase 5's generic injection/deserialization analysis won't catch.

**Maps to:** OWASP LLM Top 10 (2025) + OWASP MCP Top 10.

**Procedure:** load [refs/llm-integration.md](refs/llm-integration.md) and walk its 8 categories in order — Prompt Construction (LLM01), Output Handling (LLM05), Tool/Function Definitions (LLM06), Secrets in Prompts (LLM02/07), RAG & Vector Store Security (LLM08), Supply Chain & Model Loading (LLM03), Resource Controls (LLM10), and MCP Server Patterns (MCP Top 10). The ref file holds framework-specific grep patterns, the CVE table for known-vulnerable LLM dependencies, secure-agent design patterns, and MCP-specific checks.

For each confirmed LLM-specific weakness, append a `finding`/`add` event ([pentester/EVENTS.md](../pentester/EVENTS.md) form 5) using this severity guide:
- **Critical** — LLM output reaches eval/exec/shell without sandboxing; tool handler has command injection; prompt injection enables data exfiltration
- **High** — No tenant isolation in RAG; over-permissioned tools without approval gates; secrets in system prompts; pickle model loading
- **Medium** — Missing max_tokens; no agent iteration limits; unpinned LLM framework versions; weak prompt/response validation
- **Low** — Logging full prompts without PII redaction; no similarity threshold on RAG retrieval; missing rate limits on LLM endpoints

---

### Phase 6 — Infrastructure, Crypto & Configuration (thorough)

**Goal:** Review supporting infrastructure for security weaknesses. Map to ASVS V11-V14, V16.

**Cryptography (ASVS V11):**
- What algorithms are used for hashing, encryption, signing?
- Are deprecated algorithms used? (MD5, SHA1 for security purposes, DES, RC4)
- How are encryption keys managed? (hardcoded, environment variable, KMS)
- Is random number generation cryptographically secure?

**Secure communication (ASVS V12):**
- Is TLS enforced for all external communication?
- Are certificate validations disabled anywhere? (`verify=False`, `InsecureSkipVerify`)
- Are internal service-to-service calls encrypted?

**Configuration (ASVS V13):**
- Are secrets in environment variables, secret managers, or hardcoded?
- Is debug mode disabled in production configuration?
- Are default credentials or test accounts present?
- Are unnecessary features, endpoints, or services enabled?

**Data protection (ASVS V14):**
- Is sensitive data encrypted at rest?
- Is PII properly handled (minimization, masking, access controls)?
- Are sensitive fields excluded from logs?
- Is data classified and handled according to its sensitivity?

**Error handling and logging (ASVS V16):**
- Do error responses leak stack traces, internal paths, or configuration?
- Are security events logged? (authentication failures, authorization denials, input validation failures)
- Is there log injection risk? (user input in log messages without sanitization)
- Are sensitive values excluded from logs? (passwords, tokens, credit card numbers)

**Infrastructure as Code:**
If IaC files are present (Terraform, CloudFormation, K8s manifests, Dockerfiles, docker-compose), review them for:
- Overly permissive IAM policies or security groups
- Public storage buckets or databases
- Containers running as root or with excessive capabilities
- Missing encryption, logging, or monitoring
- Hardcoded secrets in manifests
- Unpinned base images

Call `Bash("jq -nc … type:\"finding\" action:\"add\" id:\"f-NNN\" title:\"<title>\" severity:\"<sev>\" escalation_leads:[…] … >> pentest/events.jsonl")` (canonical one-liner: [pentester/EVENTS.md](../pentester/EVENTS.md) form 5) for each confirmed weakness.

---

### Phase 7 — Security Profile & Report (all depths)

**Step 1 — Architecture diagram:**
Call `Write("pentest/diagrams/<title>.mmd", "<mermaid>")` with a comprehensive Mermaid diagram showing:
- All components (web server, app server, database, cache, queue, external APIs)
- Trust boundaries (public internet, DMZ, internal network)
- Data flows with sensitivity labels
- Authentication/authorization enforcement points
- Identified vulnerabilities annotated on the diagram

**Step 2 — Codebase security profile:**
Call `Bash("jq -nc … type:\"note\" … >> pentest/events.jsonl")` (canonical one-liner: [pentester/EVENTS.md](../pentester/EVENTS.md) form 1) with a structured summary that downstream skills can consume:

```
Codebase Security Profile:
  Language:        [language] [version]
  Framework:       [framework] [version]
  Architecture:    [monolith/microservice/serverless]

  Endpoints:       [count] total ([count] public, [count] authenticated)
  Auth mechanism:  [session/JWT/OAuth/API key]
  Auth library:    [library name and version]
  Authorization:   [RBAC/ABAC/ACL/none]
  Password hashing: [algorithm and parameters]

  Findings:        [count] by severity (critical: N, high: N, medium: N, low: N)
  Secrets found:   [count] (verified: N)
  ASVS coverage:   V1:[status] V2:[status] ... V16:[status]

  LLM Integration: [yes/no]
    Frameworks:    [openai, langchain, etc.]
    LLM endpoints: [count] (endpoints that trigger LLM calls)
    Tools defined: [count] (function/tool definitions passed to LLM)
    RAG:           [yes/no] ([vector store name])
    MCP:           [server/client/none]
    OWASP LLM Top 10 white-box coverage:
      LLM01 Prompt Injection:           [REVIEWED/NOT APPLICABLE]
      LLM02 Sensitive Info Disclosure:   [REVIEWED/NOT APPLICABLE]
      LLM03 Supply Chain:               [REVIEWED/NOT APPLICABLE]
      LLM05 Insecure Output Handling:   [REVIEWED/NOT APPLICABLE]
      LLM06 Excessive Agency:           [REVIEWED/NOT APPLICABLE]
      LLM07 System Prompt Leakage:      [REVIEWED/NOT APPLICABLE]
      LLM08 Vector/Embedding Weakness:  [REVIEWED/NOT APPLICABLE]
      LLM10 Unbounded Consumption:      [REVIEWED/NOT APPLICABLE]

  Priority targets for pentesting:
    - [endpoint] — [reason: missing auth, SQLi, file upload, etc.]
    - [endpoint] — [reason]

  Priority targets for AI red-team (/ai-redteam):
    - [endpoint URL] — [reason: extractable system prompt, over-permissioned tools, no input validation]
    - [extracted system prompt text or location]
    - [tool definitions and guardrail mechanisms found in source]

  IaC issues:      [count] ([Terraform/K8s/Docker])
```

**Step 3 — ASVS coverage summary (thorough only):**
Call `Bash("jq -nc … type:\"note\" … >> pentest/events.jsonl")` (canonical one-liner: [pentester/EVENTS.md](../pentester/EVENTS.md) form 1) with which ASVS chapters were reviewed and what was found:

```
ASVS 5.0 Coverage:
  V1  Encoding/Sanitization:    REVIEWED — [findings or "no issues"]
  V2  Validation/Business Logic: REVIEWED — [findings or "no issues"]
  V3  Web Frontend Security:    REVIEWED — [findings or "no issues"]
  V4  API and Web Service:      REVIEWED — [findings or "no issues"]
  V5  File Handling:            REVIEWED — [findings or "no issues"]
  V6  Authentication:           REVIEWED — [findings or "no issues"]
  V7  Session Management:       REVIEWED — [findings or "no issues"]
  V8  Authorization:            REVIEWED — [findings or "no issues"]
  V9  Self-contained Tokens:    [REVIEWED | NOT APPLICABLE]
  V10 OAuth and OIDC:           [REVIEWED | NOT APPLICABLE]
  V11 Cryptography:             REVIEWED — [findings or "no issues"]
  V12 Secure Communication:     REVIEWED — [findings or "no issues"]
  V13 Configuration:            REVIEWED — [findings or "no issues"]
  V14 Data Protection:          REVIEWED — [findings or "no issues"]
  V15 Secure Coding/Arch:       REVIEWED — [findings or "no issues"]
  V16 Logging/Error Handling:   REVIEWED — [findings or "no issues"]
```

**Step 4:** Call `Write("pentest/summary.md", "<summary>")` with summary.

**Step 5:** Chain into downstream skills — see CHAIN COMMITMENTS section at the top for mandatory chains. Summary:
- **MUST** → `/threat-modeling` (always — real architecture from code)
- **MUST if live target available** → `/web-exploit` (do NOT skip because code review found no injection points — systematic live testing finds what static analysis misses)
- **MUST if LLM/AI integration detected** → `/ai-redteam` (pass system prompts, tool definitions, guardrail config, RAG architecture as white-box context)
- **MUST** → `/gh-export` (always)
- **If API routes/controllers found** → `/api-security` (OWASP API Top 10 with white-box context)
- **If IaC found** → `/cloud-security` or `/container-k8s-security`
- **If CVE-affected dependencies found** → `/analyze-cve`

---

## Chaining Other Skills

| Skill | When to invoke |
|-------|----------------|
| `/threat-modeling` | Always after review — feed real architecture into STRIDE analysis |
| `/pentester` | Endpoints discovered — target scan with white-box knowledge |
| `/web-exploit` | **MANDATORY if live target available** — do NOT wait for injection points to be found in source; systematic live testing finds what static analysis misses |
| `/api-security` | API routes/controllers identified in source (REST/GraphQL/gRPC/SOAP/MCP) — pass route inventory, auth middleware, ORM models, and authorization decorators as white-box context for OWASP API Top 10 testing |
| `/cloud-security` | IaC files found — verify cloud misconfigs match runtime state |
| `/container-k8s-security` | K8s manifests or Dockerfiles found — verify container security |
| `/analyze-cve` | CVE-affected dependency found — trace code path with full source context |
| `/credential-audit` | Auth mechanism identified — test with knowledge of password policy and lockout config |
| `/ai-redteam` | LLM integration detected — pass system prompts, tool definitions, guardrails, RAG architecture, and endpoint URLs as white-box context |
| `/remediate` | Findings produced — generate specific code fixes with full source context |
| `/gh-export` | Always — after `Write("pentest/summary.md", "<summary>")` |

---

## Finding Severity Guide

| Severity | Criteria | Examples |
|----------|----------|---------|
| **Critical** | Direct path to RCE, data breach, or auth bypass from source | Unsanitized user input in eval/exec; hardcoded admin credentials; SQL injection in auth query; deserialization of untrusted data |
| **High** | Significant security weakness exploitable with moderate effort | Missing auth on sensitive endpoints; IDOR in API; weak password hashing; disabled CSRF protection; path traversal in file operations |
| **Medium** | Security weakness requiring specific conditions to exploit | Missing rate limiting; verbose error messages; weak session timeout; permissive CORS; missing security headers |
| **Low** | Defense-in-depth gap or best practice deviation | Debug mode in non-production config; missing CSP header; unpinned dependencies; logging without sensitive data redaction |

---

## Rules

- **`Bash("mkdir -p pentest/{pocs,diagrams} && touch pentest/events.jsonl") + Write("pentest/scope.json", {...})` is mandatory** — never run any other tool before it
- **Read before you judge** — don't report a finding just because a function name appears. Verify that user input actually reaches it
- **Source-to-sink tracing is essential** — a dangerous function with hardcoded arguments is not a vulnerability. Trace the data flow
- **Adapt to the framework** — every framework has different patterns. Don't grep for Django patterns in a Flask app
- **Call `Bash("jq -nc … type:\"finding\" action:\"add\" id:\"f-NNN\" title:\"<title>\" severity:\"<sev>\" escalation_leads:[…] … >> pentest/events.jsonl")` (canonical one-liner: [pentester/EVENTS.md](../pentester/EVENTS.md) form 5) for every confirmed weakness** — include the file path, line number, vulnerable code snippet, and why it's exploitable
- **Call `Write("pentest/diagrams/<title>.mmd", "<mermaid>")` at least twice** — after Phase 1 (initial architecture) and Phase 7 (annotated with findings)
- **The security profile feeds downstream skills** — write it clearly in `Bash("jq -nc … type:\"note\" … >> pentest/events.jsonl")` (canonical one-liner: [pentester/EVENTS.md](../pentester/EVENTS.md) form 1) so other skills can parse and act on it
- **Use `Bash("jq -nc … type:\"note\" … >> pentest/events.jsonl")` (canonical one-liner: [pentester/EVENTS.md](../pentester/EVENTS.md) form 1) liberally** — document your understanding of each component before analyzing it
- **Never fabricate findings** — only report what the code actually shows
- **ASVS is a guide, not a checklist** — focus on high-risk areas first, not sequential chapter review
- **Mermaid syntax rules**: use `flowchart TD`, quote labels with spaces/special chars, no em-dashes, short alphanumeric node IDs
