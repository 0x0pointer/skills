---
name: analyze-cve
description: >-
  Analyzes CVE vulnerabilities in project dependencies with code path tracing and PoC generation for Burp Suite. Traces vulnerable code from user input to sink, assesses exploitability, and generates HTTP requests for testing.

  Use when the user asks to investigate a CVE, check whether a dependency vulnerability is exploitable in this codebase, trace a known exploit's code path through the project, or generate a Burp Repeater PoC for a CVE.
argument-hint: "[dependency] [version] [cve-link]"
user-invocable: true
---

# CVE Vulnerability Analysis Workflow

## Purpose

This workflow provides a structured methodology for analyzing whether a CVE affecting a project dependency poses a real security risk. It:
- Traces vulnerable code paths in your application
- Analyzes dataflow from user input to vulnerable functions
- Creates proof-of-concept HTTP requests for Burp Suite validation

**Language/Framework Agnostic**: Works with Python, Node.js, Java, Go, Ruby, PHP, and more.

## Important Assumptions

The user has already vetted the CVE, dependency name, and version through SCA tools (Snyk, Dependabot, GitHub Security, etc.) before invoking this skill. Trust that input — do not re-verify, do not require dependency files to exist, do not stop if the package isn't installed locally (private artifactories and complex build processes are common). Your job is **code usage analysis**: prove (or disprove) that the vulnerable code path is reachable from user input in this specific codebase.

---

## CHAIN COMMITMENTS — DECLARE BEFORE STARTING

Read this before executing any workflow phase. Commit to MANDATORY chains before your first tool call.

| Trigger | Chain | Mandatory? | Claude Code |
|------|------|------|------|
| After `Write("pentest/summary.md", "<summary>")` (confirmed exploitable finding) | `/gh-export` | **MANDATORY** | `Skill(skill="gh-export")` |
| Exploitable CVE confirmed + live target available | `/web-exploit` | OPTIONAL | `Skill(skill="web-exploit")` |
| Exploitable CVE confirmed + Metasploit module available | `/metasploit` | OPTIONAL | `Skill(skill="metasploit")` |

**You WILL invoke `/gh-export` after completing the analysis if a confirmed exploitable finding was produced.**


**Logging:** Before invoking any skill above, append a `skill_chain` event to `pentest/events.jsonl` (see CLAUDE.md "Skill logging" for the exact one-liner).

---

## Analysis Workflow

### Phase 1: Vulnerability Context Gathering

1. **Read CVE Details**
   - Fetch and analyze CVE from provided link
   - Identify vulnerable function/method/class
   - Understand attack vector and vulnerability type
   - Note affected version range
   - Document any PoC or exploit details
   - Search Exploit-DB for existing exploits: `Bash("searchsploit <product> <version>")`

2. **Trust User-Provided Version Information**
   - **IMPORTANT**: Trust the user's input about dependency version and CVE applicability
   - User has already verified this information through SCA tools (Snyk, Dependabot, etc.)
   - **Optional**: If dependency files are available, you MAY verify the version:
     - Python: `pyproject.toml`, `requirements.txt`, `Pipfile`
     - Node.js: `package.json`, `package-lock.json`
     - Java: `pom.xml`, `build.gradle`, `build.gradle.kts`
     - Go: `go.mod`
     - Ruby: `Gemfile`, `Gemfile.lock`
     - PHP: `composer.json`
   - **DO NOT stop analysis** if:
     - Dependency files are missing or inaccessible
     - The package is not found in lock files
     - Private artifactories require authentication
     - Dependencies are not locally installed
   - **Always proceed to Phase 2** - focus on analyzing whether the vulnerable code is actually used

### Phase 2: Code Path Analysis

3. **Understand Vulnerable Function from CVE**
   - **Primary source**: Use the CVE description to identify the vulnerable function/method/class
   - Document the vulnerable component (e.g., `jackson-databind.readValue()`, `pymupdf.Document.open()`)
   - Note: You typically **won't have access** to the dependency source code
   - **Optional**: If dependency is installed locally, you may inspect it for additional context
   - Key information needed:
     - Vulnerable module/package name
     - Vulnerable function/method/class name
     - Basic understanding of what triggers the vulnerability

4. **Trace Usage in Application**
   - Search codebase for:
     - **Imports of vulnerable module** (document these as evidence)
     - Instantiation of vulnerable classes
     - Calls to vulnerable functions
   - Document all usage locations with file:line references
   - **IMPORTANT**: For each file using the vulnerable code, capture:
     - The exact import statement(s) showing how the package is imported
     - The import location (file:line)
     - Import type (direct import, aliased, selective import, etc.)
   - This import evidence proves the vulnerable package is actually loaded in the application
   - If NOT used → stop analysis (not exploitable)
   - If used → proceed to Phase 3

### Phase 3: User Input Trace

5. **Identify Entry Points**
   - Map HTTP endpoints that interact with vulnerable code paths
   - Document each endpoint:
     - Route path
     - HTTP method
     - Request parameters (query, body, headers, files)
     - File location

6. **Trace User Input Flow**
   - For each endpoint, trace how user data flows:
     - Request parameter extraction
     - Validation/sanitization steps
     - Data transformations
     - Function calls toward vulnerable code
   - Document complete call chain

### Phase 4: Dataflow Analysis

7. **Construct Dataflow Graph**
   - Show path from SOURCE to SINK:
     - **SOURCE**: User input entry point
     - **INTERMEDIATE**: Each function in the chain
     - **SINK**: Vulnerable function call
   - For each node document:
     - Function name and file location
     - Input parameters
     - Validation/sanitization applied
     - Data transformations
     - Output to next function

8. **Exploitability Assessment**
   - Determine if user input reaches sink without proper sanitization
   - Identify security controls:
     - Input validation
     - Encoding/escaping
     - Authentication/authorization
     - Rate limiting
     - Content-type restrictions
   - Rate exploitability: **HIGH** / **MEDIUM** / **LOW** / **NOT EXPLOITABLE**

### Phase 5: Proof of Concept Development

9. **Craft HTTP Request**
   - Create complete HTTP request for Burp Suite:
     - Target vulnerable endpoint
     - Malicious payload to trigger vulnerability
     - Bypass security controls if possible
   - Format as raw HTTP request

10. **Document Expected Behavior**
    - Describe expected results when request is sent
    - Explain verification steps
    - Provide exploitation indicators

#### Running a downloaded PoC script

When a PoC is a Python script (from `searchsploit -m`, GitHub clone, exploit-db link, or any script you author yourself), run it via `uv` — never plain `python3`:

1. **`Read` the PoC first** — confirm what it does and identify imports.
2. **Spot non-stdlib imports** — `requests`, `impacket`, `pycryptodome`, `paramiko`, `cryptography`, `lxml`, `pwntools`, etc. Anything not in the Python standard library.
3. **Run it via `uv run`:**
   - Stdlib-only PoC: `Bash("uv run python /tmp/<poc>.py --target TARGET …")`
   - Has third-party deps: `Bash("uv run --with requests --with impacket python /tmp/<poc>.py --target TARGET …")`
   - PoC ships PEP 723 inline metadata (`# /// script` block at the top): `Bash("uv run --script /tmp/<poc>.py --target TARGET …")` resolves declared deps automatically.
4. **If you author your own PoC mid-session** — `Write` it with a PEP 723 header so future runs (yours or the user's) don't have to re-discover the deps:
   ```python
   # /// script
   # requires-python = ">=3.11"
   # dependencies = ["requests"]
   # ///
   import requests
   …
   ```
   then `Bash("uv run --script /tmp/<your-poc>.py …")`.

This rule does **not** apply to pre-installed external tools at fixed paths (`/opt/jwt_tool/jwt_tool.py`, `/opt/sqlmap/sqlmap.py`, etc.) — those keep their own dependency setup.

### Phase 5b: Persist to pentest/ artifacts (when running inside an engagement)

When chained from `/pentester` (or any time a `pentest/` directory exists in the working dir), persist findings alongside the rest of the run:

11. **Log confirmed vulnerabilities**
    - Append a `finding`/`add` event to `pentest/events.jsonl` with the CVE ID, affected component, exploitability rating, and raw evidence (dataflow trace, code snippets). See [pentester/EVENTS.md](../pentester/EVENTS.md) form 5 for the canonical one-liner.

12. **Save a Burp-ready PoC**
    - `Write("pocs/<title>.http", ...)` with a descriptive title (e.g. `cve-2024-xxxxx-rce-upload`) — include a leading `# notes: ...` line with the vulnerability description. The `.http` file can be pasted directly into Burp Repeater.

> **Skip this phase** for standalone analysis (no `pentest/` directory). The markdown report is always produced regardless.

### Phase 6: Report Generation

11. **Compile Findings into a markdown report.** Copy the template at [analyze-cve/TEMPLATE.md](TEMPLATE.md), save as `CVE-YYYY-XXXXX-analysis.md`, fill every bracketed placeholder. Code snippets must preserve original line numbers. The mandatory "Tracking Tool Summary" section at the end of the template is the issue-tracker handoff — never omit it.

---

## Output Report Template

The full markdown template lives at [analyze-cve/TEMPLATE.md](TEMPLATE.md). Copy it, save the result as `CVE-YYYY-XXXXX-analysis.md`, and fill every bracketed placeholder. Preserve original source line numbers in all code snippets. The mandatory "Tracking Tool Summary" at the end of the template is the issue-tracker handoff — never omit it.

---

## Operational notes

- **Vulnerability presence ≠ exploitability** — proving the import is not enough; the dataflow trace must reach the sink without effective sanitization.
- **Focus is code usage analysis, not dependency verification.** User has already vetted CVE info through SCA tools (Snyk, Dependabot, etc.) — see Important Assumptions above.
- **Consider deployment environment and network exposure** when rating exploitability.
- Works across multiple languages and frameworks; works even when dependency files or installed packages are absent (assumptions section explains why).
