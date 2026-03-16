# Agent Smith — Skills

The skill library for [Agent Smith](https://github.com/0x0pointer/agent-smith), an AI-powered penetration testing tool built on [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

Agent Smith turns Claude into an autonomous security engineer. These skills teach it how to perform structured pentests, analyze vulnerabilities, model threats, red-team AI systems, and produce professional reports — all from your terminal.

## Skills

| Skill | Command | What it does |
|-------|---------|--------------|
| **Pentester** | `/pentester` | Full penetration test — recon, scanning, exploitation, and reporting. Chains into other skills automatically. |
| **Threat Modeling** | `/threat-modeling` | PASTA + Shostack 4-question framework. Produces component maps, data flow diagrams, attack trees, STRIDE tables, and mitigation plans. |
| **CVE Analysis** | `/analyze-cve` | Traces a CVE through your dependency tree to determine real exploitability. Generates Burp Suite-ready PoC requests. |
| **AI Red Team** | `/ai-redteam` | OWASP LLM Top 10 (2025) assessment using FuzzyAI, PyRIT, Garak, and promptfoo. |
| **Aikido Triage** | `/aikido-triage` | Triages Aikido security findings against your codebase. Verdicts each as KEEP OPEN or CLOSE with evidence. |
| **GH Export** | `/gh-export` | Formats confirmed findings into GitHub issue markdown, ready to paste or file. |

## Installation

Copy skills into your Claude Code skills directory:

```bash
# Clone the repo
git clone https://github.com/0x0pointer/skills.git
cd skills

# Copy all skills
cp -r ai-redteam aikido-triage analyze-cve gh-export threat-modeling ~/.claude/skills/
cp pentester.md ~/.claude/skills/pentester/SKILL.md
```

Restart Claude Code. Skills are now available as slash commands.

## Usage

```bash
cd /your/target/project
claude

# Run a full pentest
/pentester scan https://target.example.com depth=standard

# Threat model the current codebase
/threat-modeling

# Analyze a specific CVE
/analyze-cve express 4.17.1 https://nvd.nist.gov/vuln/detail/CVE-2024-XXXXX

# Red-team an AI/LLM endpoint
/ai-redteam https://api.example.com/chat

# Triage Aikido findings
/aikido-triage findings.csv ./src

# Export findings to GitHub issues
/gh-export findings.json
```

## Security Notice

These skills are for **authorized security testing only** — pentests with written scope, CTF challenges, security research, and defensive analysis. Do not use them against systems you don't have permission to test.

## License

MIT
