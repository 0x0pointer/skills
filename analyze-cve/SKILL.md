---
name: analyze-cve
description: Analyzes CVE vulnerabilities in project dependencies with code path tracing and PoC generation for Burp Suite. Traces vulnerable code from user input to sink, assesses exploitability, and generates HTTP requests for testing.
argument-hint: [dependency] [version] [cve-link]
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

### Trust User-Provided Information
- **The user has already verified the CVE and version through SCA tools** (Snyk, Dependabot, GitHub Security, etc.)
- **Trust the dependency name, version, and CVE information provided** - do not require verification
- **Do not fail if dependency files are missing or incomplete** - focus on code analysis
- **Do not stop if packages aren't installed locally** - many projects use private artifactories or complex build processes
- **Your job is to analyze CODE USAGE**, not verify dependency versions

### What This Means
- If the user says "analyze CVE-X in package Y version Z", proceed with the analysis
- Look for usage of the vulnerable code in the application
- If you can't find dependency files, document this but continue the analysis
- If the package isn't locally installed, work with the CVE description to understand what to look for

---

## Analysis Workflow

### Phase 1: Vulnerability Context Gathering

1. **Read CVE Details**
   - Fetch and analyze CVE from provided link
   - Identify vulnerable function/method/class
   - Understand attack vector and vulnerability type
   - Note affected version range
   - Document any PoC or exploit details

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

### Phase 5b: Report to Dashboard (when MCP tools are available)

If pentest-agent MCP tools are available (e.g. when chained from `/pentester`), report findings to the live dashboard:

11. **Log confirmed vulnerabilities**
    - Call `report_finding` with the CVE ID, affected component, exploitability rating, and raw evidence (dataflow trace, code snippets)
    - This makes the finding visible in the live dashboard at localhost:5000

12. **Route PoC through Burp Suite**
    - Call `http_request(poc=True)` with the crafted exploit request — this lands it in Burp HTTP History
    - Call `save_poc` with a descriptive title (e.g. `cve-2024-xxxxx-rce-upload`) and include the vulnerability description in `notes`
    - This produces a `.http` file in `pocs/` that can be pasted directly into Burp Repeater

> **Skip this phase** if MCP tools are not available (standalone analysis). The markdown report is always produced regardless.

### Phase 6: Report Generation

11. **Compile Findings**
    - Generate comprehensive markdown report
    - Save as: `CVE-YYYY-XXXXX-analysis.md`
    - Include all sections (see template below)
    - **IMPORTANT**: All code snippets must preserve original line numbers from source files
    - **MANDATORY - NEVER SKIP**: The report MUST end with "## Tracking Tool Summary" containing:
      - Concise 1-2 sentence explanation of exploitability or false positive
      - **ALL relevant file paths and line numbers** (imports, usage, entry points, sinks)
      - Format: `[Explanation]. Found in: file.ext:line, file.ext:line`
      - This summary should be copy-paste ready for issue tracking tools
      - **THE REPORT IS INCOMPLETE WITHOUT THIS SECTION**

---

## Output Report Template

⚠️ **CRITICAL**: Every report MUST include the "Tracking Tool Summary" section at the end with file paths and line numbers. This section is MANDATORY and should NEVER be omitted.

```markdown
# CVE-YYYY-XXXXX Analysis Report

## Executive Summary
**Exploitability**: [HIGH/MEDIUM/LOW/NOT EXPLOITABLE]
**Impact**: [Brief description]
**Recommendation**: [Immediate action needed]

## Vulnerability Information
- **CVE ID**: CVE-YYYY-XXXXX
- **Dependency**: [name]
- **Installed Version**: [version]
- **Vulnerable Versions**: [range]
- **Vulnerability Type**: [RCE/XSS/SQLi/etc.]
- **CVSS Score**: [if available]

## Vulnerability Description
[Detailed description from CVE source]

## Code Path Analysis

### Vulnerable Function
- **Location in Dependency**: [module.function]
- **Function Signature**: `[signature]`
- **Vulnerability Mechanism**: [how it works]

### Import Evidence
[Show where and how the vulnerable package is imported - this proves the dependency is loaded]

1. `file.ext:line` - Import statement:
   ```[language]
   [line_number] [actual import statement from code with line numbers preserved]
   ```

2. `file.ext:line` - Import statement:
   ```[language]
   [line_number] [actual import statement from code with line numbers preserved]
   ```

**Note**: Include line numbers in all code snippets to show exact locations in source files.

### Usage in Application
[List all locations where vulnerable code is used]

1. `file.ext:line` - [context]
   ```[language]
   [line_number] [code snippet showing vulnerable function call with line numbers]
   ```

2. `file.ext:line` - [context]
   ```[language]
   [line_number] [code snippet showing vulnerable function call with line numbers]
   ```

## Dataflow Analysis

### Source (User Input Entry Point)
- **Endpoint**: `[METHOD] /api/path`
- **Parameter**: [parameter_name]
- **Location**: `file.ext:line`

### Flow Path
1. **Entry**: `file.ext:line` - [description]
   ```[language]
   [line_number] [code snippet with line numbers preserved]
   ```

2. **Step 2**: `file.ext:line` - [description]
   ```[language]
   [line_number] [code snippet with line numbers preserved]
   ```

[...continue for each step...]

N. **Sink**: `file.ext:line` - Vulnerable function called
   ```[language]
   [line_number] [code snippet with line numbers preserved]
   ```

**Note**: All code snippets must include line numbers from the original source files for precise traceability.

## Security Controls Analysis
- [Input validation present/absent]
- [Authentication/authorization]
- [Other relevant controls]
- [Bypass techniques if applicable]

## Exploitability Assessment
- **Verdict**: [HIGH/MEDIUM/LOW/NOT EXPLOITABLE]
- **Reasoning**: [detailed explanation]
- **Attack Complexity**: [Low/Medium/High]
- **Prerequisites**: [what attacker needs]

## Proof of Concept

### HTTP Request for Burp Suite
```http
POST /api/endpoint HTTP/1.1
Host: localhost:PORT
Content-Type: application/json
Content-Length: XXX

[payload]
```

### Reproduction Steps
1. [Step 1]
2. [Step 2]
3. [Step 3]

### Expected Results
- [What happens on successful exploitation]
- [Observable indicators]

### Verification
- Response code: [expected]
- Response body: [expected patterns]
- Log entries: [what to look for]
- Side effects: [file creation, code execution, etc.]

## Recommendations

### Immediate Actions
- [ ] Upgrade [dependency] to version [safe version]
- [ ] Apply workaround: [if available]
- [ ] Monitor for exploitation attempts

### Long-term Fixes
- [ ] Update dependency management policy
- [ ] Implement additional input validation
- [ ] Add security controls: [specific recommendations]

### Detection & Monitoring
- Monitor for requests to: [endpoint]
- Watch for patterns: [attack signatures]
- Alert on: [specific conditions]

## References
- [CVE Link]
- [GitHub Advisory]
- [Vendor Security Bulletin]
- [PoC/Exploit References]

---

## Tracking Tool Summary
⚠️ **MANDATORY SECTION - NEVER OMIT THIS**

**Quick Copy-Paste Summary** (1-2 sentences + file locations):
[Concise explanation of exploitability or why it's a false positive, followed by all relevant file:line references]

**Required Format**: [Explanation]. Found in: `file.ext:line`, `file.ext:line`, `file.ext:line`

**This section MUST always be included at the end of every report**

**Examples**:
- *False Positive*: "The vulnerable function is never called with user-controlled input; all usage is with hardcoded internal configuration values only. Found in: `config/settings.py:45`, `utils/loader.py:123`"
- *False Positive*: "Package is imported but the vulnerable code path is unreachable due to authentication requirements and input validation that prevents exploitation. Import at `api/routes.py:12`, usage at `api/handlers.py:89`"
- *Exploitable*: "User-controlled file uploads directly reach the vulnerable parser without sanitization, enabling remote code execution. Entry point: `api/upload.py:34`, sink: `parsers/document.py:156`"

---
**Analysis Date**: [date]
**Analyst**: Claude (Anthropic)
**Project**: [project name]
```

---

## Project Auto-Detection

When you run the workflow, the following will be automatically detected:

### Framework Detection
- **Python**: FastAPI, Django, Flask (checks for imports, config files)
- **Node.js**: Express, NestJS, Koa (checks package.json dependencies)
- **Java**: Spring Boot, Jakarta EE (checks pom.xml/build.gradle)
- **Go**: Gin, Echo, Chi (checks import statements in main.go)
- **Ruby**: Rails, Sinatra (checks Gemfile)
- **PHP**: Laravel, Symfony (checks composer.json)

### Entry Point Detection
- API route definitions
- Controller files
- Request handlers
- Middleware configuration

### Dependency File Location
- Automatically searches for dependency manifests
- Reads installed versions
- Checks for lock files for exact versions

### Import Statement Examples (By Language)
When documenting import evidence, look for patterns like:
- **Python**: `import package`, `from package import module`, `from package.submodule import function`
- **Node.js**: `const pkg = require('package')`, `import { function } from 'package'`
- **Java**: `import com.example.package.Class;`, `import com.example.package.*;`
- **Go**: `import "github.com/user/package"`, `import ( ... )`
- **Ruby**: `require 'package'`, `require_relative 'package'`
- **PHP**: `use Vendor\Package\Class;`, `require 'vendor/autoload.php'`

---

## Best Practices

1. **Be Thorough**: Check all code paths, even indirect ones
2. **Document Everything**: Include file:line references for traceability
3. **Show Import Evidence**: Always capture and display how vulnerable packages are imported as proof they're loaded
4. **Preserve Line Numbers**: All code snippets must include original line numbers from source files for precise traceability
5. **Test Assumptions**: Verify dataflow actually reaches the sink
6. **Consider Context**: Security controls might mitigate vulnerability
7. **Realistic PoC**: Create exploits that work in real application context
8. **Actionable Output**: Provide clear, specific recommendations
9. **Tracking Summary**: Always include a concise 1-2 sentence summary at the end with ALL relevant file:line references for easy copy-paste into tracking tools

## Important Notes

- ✅ Works across multiple languages and frameworks
- ✅ Automatically detects project structure
- ✅ Generates ready-to-use Burp Suite requests
- ✅ **Trusts user-provided CVE and version information** (no verification required)
- ✅ **Works even without dependency files or installed packages**
- 🚨 **CRITICAL**: Every report MUST end with "Tracking Tool Summary" containing a copy-paste ready summary with all file:line references
- ⚠️ Vulnerability presence ≠ exploitability (thorough analysis required)
- ⚠️ Focus is on **code usage analysis**, not dependency verification
- ⚠️ User has already vetted CVE info through SCA tools (Snyk, Dependabot, etc.)
- ⚠️ Consider deployment environment and network exposure

---

**Version**: 1.0
**Last Updated**: 2024
**Supported Languages**: Python, Node.js, Java, Go, Ruby, PHP, and more
