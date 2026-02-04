# Security Workflows for Claude Code

A collection of reusable security analysis workflows for Claude Code that can be shared across your team.

## 🎯 Purpose

This repository contains structured workflows that guide Claude through complex security analysis tasks. These workflows are:
- **Reusable** across multiple projects and programming languages
- **Version controlled** for easy updates and collaboration
- **Shareable** with your entire team
- **Standardized** to ensure consistent analysis quality

## 📦 Available Workflows

### 1. CVE Vulnerability Analysis (`cve-analysis/`)
Comprehensive workflow for analyzing whether a CVE in a project dependency is actually exploitable.

**Features:**
- Traces vulnerable code paths in your application
- Analyzes dataflow from user input to vulnerable functions
- Generates Burp Suite-ready HTTP requests for testing
- Creates detailed reports with remediation steps

**Supports:** Python, Node.js, Java, Go, Ruby, PHP, and more

[→ See CVE Analysis Documentation](./cve-analysis/README.md)

---

## 🚀 Quick Start

### Installation (One-Time Setup)

```bash
# Clone this repository to your home directory
git clone <your-repo-url> ~/security-workflows

# That's it! The workflows are now available.
```

**Optional:** Run the setup script for convenience:
```bash
cd ~/security-workflows
chmod +x setup.sh
./setup.sh
```

### Usage

1. Navigate to any project you want to analyze
2. Open Claude Code
3. Reference the workflow you want to use

**Example:**
```
cd ~/my-project
claude

# In Claude, say:
Use the CVE workflow from ~/security-workflows/cve-analysis/workflow.md to analyze:
Dependency: fastapi
Version: 0.115.13
CVE: https://nvd.nist.gov/vuln/detail/CVE-2024-XXXXX
```

**Or use the shorter command format:**
```
/analyze-cve fastapi 0.115.13 https://nvd.nist.gov/vuln/detail/CVE-2024-XXXXX

(Make sure to mention using ~/security-workflows/cve-analysis/workflow.md first)
```

---

## 📋 Workflows Overview

| Workflow | Purpose | Status |
|----------|---------|--------|
| **CVE Analysis** | Analyze dependency vulnerabilities | ✅ Ready |
| Security Code Review | (Coming soon) | 🚧 Planned |
| Threat Modeling | (Coming soon) | 🚧 Planned |
| Penetration Test Report | (Coming soon) | 🚧 Planned |

---

## 🔄 Updating Workflows

Workflows are continuously improved. To get the latest version:

```bash
cd ~/security-workflows
git pull
```

All team members will instantly have access to updated workflows.

---

## 👥 Team Collaboration

### For Team Members

**First-time setup:**
1. Clone this repository: `git clone <repo-url> ~/security-workflows`
2. Start using workflows immediately

**Staying updated:**
- Run `git pull` in the `~/security-workflows` directory periodically
- Or set up a cron job for automatic updates

### For Workflow Contributors

**Adding a new workflow:**
1. Create a new directory: `mkdir new-workflow-name`
2. Add `workflow.md` with the workflow instructions
3. Add `README.md` with usage documentation
4. Add `examples/` directory with sample outputs
5. Submit a pull request

**Improving existing workflows:**
1. Edit the `workflow.md` file in the relevant directory
2. Update the workflow version number
3. Document changes in the workflow's README
4. Submit a pull request

---

## 📁 Repository Structure

```
security-workflows/
├── README.md                           # This file
├── setup.sh                            # Optional setup script
├── .gitignore                          # Git ignore rules
│
├── cve-analysis/                       # CVE vulnerability analysis
│   ├── workflow.md                     # Main workflow instructions
│   ├── README.md                       # Usage guide
│   └── examples/                       # Example reports
│       └── CVE-2024-XXXXX-example.md   # Sample analysis report
│
└── [future-workflows]/                 # Additional workflows coming soon
```

---

## 🛠️ Configuration

### Default Workflow Location

By default, workflows are stored in `~/security-workflows/`. If you prefer a different location:

1. Clone to your preferred location
2. Update references in your commands to use the correct path

### Project-Specific Customization

While workflows are designed to be generic, you can create project-specific overrides:

```bash
# In your project directory
cp ~/security-workflows/cve-analysis/workflow.md ./.claude/workflows/cve-analysis.md

# Customize the local copy for project-specific needs
```

---

## 🔒 Security Considerations

**Important:** These workflows are designed for:
- ✅ Authorized security testing
- ✅ Defensive security analysis
- ✅ CTF challenges and competitions
- ✅ Educational purposes
- ✅ Internal penetration testing with proper authorization

**NOT for:**
- ❌ Unauthorized access or testing
- ❌ Malicious exploitation
- ❌ Testing systems without permission

Always ensure you have proper authorization before conducting security testing.

---

## 📞 Support

### Getting Help

- **Documentation**: Check the README in each workflow directory
- **Examples**: Review the `examples/` directory for sample outputs
- **Issues**: Open an issue in this repository
- **Questions**: Ask in your team's security channel

### Troubleshooting

**Claude can't find the workflow:**
- Verify the path: `ls ~/security-workflows/cve-analysis/workflow.md`
- Use absolute path: `~/security-workflows/cve-analysis/workflow.md`
- Check you're referencing the correct file name

**Workflow not working as expected:**
- Make sure you're using the latest version: `git pull`
- Check if your project structure is supported
- Review the workflow's README for specific requirements

---

## 🤝 Contributing

We welcome contributions! To add or improve workflows:

1. Fork this repository
2. Create a feature branch: `git checkout -b new-workflow`
3. Make your changes
4. Test thoroughly with multiple project types
5. Submit a pull request

**Contribution Guidelines:**
- Workflows should be language/framework agnostic when possible
- Include clear documentation and examples
- Test with at least 2-3 different project types
- Follow the existing directory structure

---

## 📜 License

[Add your license here - e.g., MIT, Apache 2.0, or Internal Use Only]

---

## 🎖️ Credits

Created and maintained by the Security Team

**Contributors:**
- [Your name]
- [Team members]

---

## 📝 Changelog

### Version 1.0.0 (2024-02-04)
- ✨ Initial release
- ✅ CVE Analysis workflow
- 📚 Documentation and examples

---

## 🚀 Roadmap

**Coming Soon:**
- [ ] Security code review workflow
- [ ] Threat modeling workflow
- [ ] Automated CVE database integration
- [ ] MCP server version for native Claude integration
- [ ] VS Code extension
- [ ] Slack/Discord integration for team notifications

**Future Ideas:**
- [ ] API security testing workflow
- [ ] Container security analysis
- [ ] Secret scanning workflow
- [ ] Compliance checking (OWASP, PCI-DSS, etc.)

---

**Happy Hunting! 🔒🔍**

For questions or suggestions, reach out to the security team.
