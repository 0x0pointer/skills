# Quick Start Guide

## 🚀 30-Second Start

```bash
# 1. Navigate to your project
cd /path/to/your/project

# 2. Start Claude
claude

# 3. Analyze a CVE
Use the CVE workflow from ~/security-workflows/cve-analysis/workflow.md to analyze:
Dependency: pymupdf
Version: 1.26.4
CVE: https://nvd.nist.gov/vuln/detail/CVE-2024-XXXXX
```

## 📋 Command Reference

### CVE Analysis Commands

```bash
# Format 1: Direct command
/analyze-cve <package> <version> <cve-link>

# Format 2: Natural language
analyze CVE-YYYY-XXXXX for <package> version <version>

# Format 3: Full context
Use the CVE workflow from ~/security-workflows/cve-analysis/workflow.md
Dependency: <package>
Version: <version>
CVE: <cve-link>
```

### Examples

```bash
# Python
/analyze-cve pymupdf 1.26.4 https://nvd.nist.gov/vuln/detail/CVE-2024-12345

# Node.js
analyze CVE-2024-5678 for express version 4.18.2

# Java
check vulnerability jackson-databind 2.15.0 https://github.com/advisories/GHSA-xxxx
```

## 📂 What You Get

After analysis, you'll receive:

```
CVE-YYYY-XXXXX-analysis.md
├── Executive Summary (Exploitability: HIGH/MEDIUM/LOW)
├── Complete Dataflow Analysis (source → sink)
├── Burp Suite HTTP Request (ready to test)
└── Remediation Recommendations
```

## 🔄 Team Setup

### First Time Setup

```bash
# Clone the repository
git clone <your-repo-url> ~/security-workflows

# Run setup script (optional)
cd ~/security-workflows
./setup.sh
```

### Stay Updated

```bash
cd ~/security-workflows
git pull
```

## 💡 Tips

1. **Always run from project root** - ensures dependency files are found
2. **Keep dependencies updated** - workflow reads actual installed versions
3. **Review auto-detection** - verify Claude detected your project correctly
4. **Test in Burp Suite** - validate the generated PoC works

## 🆘 Troubleshooting

| Problem | Solution |
|---------|----------|
| "Can't find workflow" | Use full path: `~/security-workflows/cve-analysis/workflow.md` |
| "Can't find dependencies" | Run from project root directory |
| "CVE link doesn't work" | Try alternative sources: NVD, GitHub Advisories, Snyk |
| "Workflow not triggering" | Explicitly mention the workflow path in your command |

## 📚 More Help

- **Full Documentation**: [README.md](./README.md)
- **CVE Analysis Details**: [cve-analysis/README.md](./cve-analysis/README.md)
- **Example Report**: [cve-analysis/examples/](./cve-analysis/examples/)

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────┐
│  Security Workflows - CVE Analysis              │
├─────────────────────────────────────────────────┤
│                                                 │
│  📍 Location:                                   │
│  ~/security-workflows/cve-analysis/workflow.md  │
│                                                 │
│  🎯 Command:                                    │
│  /analyze-cve <pkg> <ver> <cve-url>            │
│                                                 │
│  📊 Output:                                     │
│  CVE-YYYY-XXXXX-analysis.md                     │
│                                                 │
│  🔄 Update:                                     │
│  cd ~/security-workflows && git pull            │
│                                                 │
│  📖 Docs:                                       │
│  ~/security-workflows/README.md                 │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Happy Hunting! 🔒🔍**
