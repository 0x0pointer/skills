# CVE Analysis Report Template

Routing: copy this template into a new file named `CVE-YYYY-XXXXX-analysis.md` (or whatever the CVE ID is) when you reach Phase 6 of `/analyze-cve`. Fill in every bracketed `[...]` placeholder. The "Tracking Tool Summary" at the end is **mandatory** — it is the copy-paste-ready handoff for issue trackers.

---

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
**Quick Copy-Paste Summary** (1-2 sentences + file locations):
[Concise explanation of exploitability or why it's a false positive, followed by all relevant file:line references]

**Required Format**: `[Explanation]. Found in: file.ext:line, file.ext:line, file.ext:line`

**Examples**:
- *False Positive*: "The vulnerable function is never called with user-controlled input; all usage is with hardcoded internal configuration values only. Found in: `config/settings.py:45`, `utils/loader.py:123`"
- *False Positive*: "Package is imported but the vulnerable code path is unreachable due to authentication requirements and input validation that prevents exploitation. Import at `api/routes.py:12`, usage at `api/handlers.py:89`"
- *Exploitable*: "User-controlled file uploads directly reach the vulnerable parser without sanitization, enabling remote code execution. Entry point: `api/upload.py:34`, sink: `parsers/document.py:156`"

---
**Analysis Date**: [date]
**Project**: [project name]
```
