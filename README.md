# CVE Analysis Workflow for Claude Code

A structured workflow that guides Claude through analyzing whether a CVE in your dependencies is actually exploitable in your codebase.

## What It Does

This workflow performs a comprehensive 6-phase security analysis:

1. **Vulnerability Context** - Fetches CVE details and understands the vulnerability
2. **Code Path Analysis** - Finds if vulnerable code is used in your application
3. **User Input Trace** - Identifies how user input enters the system
4. **Dataflow Analysis** - Maps complete path from input to vulnerable function
5. **PoC Development** - Creates HTTP request ready for Burp Suite testing
6. **Report Generation** - Produces detailed markdown report with fixes

**Supports:** Python, Node.js, Java, Go, Ruby, PHP, and more

---

## Installation

### Install as Claude Code Skill (Recommended)

Run the installer to enable `/analyze-cve` command:

```bash
cd ~/Desktop/security-workflows
bash cve-analysis/install-skill.sh
```

Then **restart Claude Code**.

### What Gets Installed

```
~/.claude/skills/analyze-cve/
└── SKILL.md      # Skill configuration and workflow (official format)
```

---

## Usage

### With Skill Installed

```bash
cd /your/project
claude

# Simple command format
/analyze-cve <dependency> <version> <cve-url>
```

**Example:**
```bash
/analyze-cve pymupdf 1.26.4 https://nvd.nist.gov/vuln/detail/CVE-2024-12345
```

### Without Skill

```bash
cd /your/project
claude

# Reference skill file directly
Use the CVE workflow from ~/Desktop/security-workflows/cve-analysis/SKILL.md to analyze:
Dependency: pymupdf
Version: 1.26.4
CVE: https://nvd.nist.gov/vuln/detail/CVE-2024-12345
```

---

## Output

Generates a comprehensive report: `CVE-YYYY-XXXXX-analysis.md`

**Includes:**
- Executive summary with exploitability rating (HIGH/MEDIUM/LOW/NOT EXPLOITABLE)
- Complete dataflow analysis from user input to vulnerable function
- Burp Suite-ready HTTP request for testing
- Remediation recommendations
- Detection and monitoring suggestions

---

## Repository Structure

```
security-workflows/
├── README.md                    # This file
├── .gitignore                   # Git ignore rules
└── cve-analysis/
    ├── SKILL.md                 # Skill configuration and workflow
    └── install-skill.sh         # One-command installer
```

---

## Sharing with Your Team

### Push to Git

```bash
cd ~/Desktop/security-workflows
git remote add origin <your-repo-url>
git push -u origin main
```

### Team Installation

```bash
git clone <your-repo-url> ~/security-workflows
cd ~/security-workflows
bash cve-analysis/install-skill.sh
# Restart Claude Code
```

---

## Updating

Pull latest changes:
```bash
cd ~/Desktop/security-workflows
git pull
```

Reinstall skill:
```bash
bash cve-analysis/install-skill.sh
# Restart Claude Code
```

---

## Uninstalling

```bash
# Remove the skill
rm -rf ~/.claude/skills/analyze-cve

# Remove the repository
rm -rf ~/Desktop/security-workflows
```

---

## Security Notice

This workflow is for:
- ✅ Authorized security testing
- ✅ Defensive security analysis
- ✅ CTF challenges
- ✅ Educational purposes

**NOT for:**
- ❌ Unauthorized testing
- ❌ Malicious exploitation
- ❌ Testing without permission

---

## License

[Add your license - MIT, Apache 2.0, or Internal Use Only]

---

**Happy Hunting! 🔒🔍**
