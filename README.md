# skills

A collection of Claude Code skills for security assessments, penetration testing, and AI safety tooling. Each skill is a `/slash-command` that runs directly in Claude Code — no setup required beyond having the MCP tools configured.

## Skills

### Penetration Testing

| Skill | Description |
|-------|-------------|
| `/pentester` | Full penetration test — chains recon through exploitation and reporting |
| `/web-exploit` | Deep web exploitation: SQLi, XSS, SSRF, SSTI, deserialization, JWT, smuggling, and more |
| `/network-assess` | Internal network assessment: VLAN hopping, LLMNR/NBT-NS abuse, SNMP, segmentation |
| `/post-exploit` | Post-exploitation: privesc (Linux/Windows), persistence, credential harvesting, pivoting |
| `/lateral-movement` | AD lateral movement: PTH, PTT, Kerberoasting, NTLM relay, delegation abuse, cross-trust |
| `/metasploit` | Exploit validation with Metasploit — runs in an isolated Docker container |
| `/reverse-shell` | Generate and manage reverse shells across all major platforms and encodings |

### Cloud & Infrastructure

| Skill | Description |
|-------|-------------|
| `/cloud-security` | AWS, Azure, and GCP posture assessment: IAM escalation, storage exposure, serverless, logging |
| `/container-k8s-security` | Container escape, K8s RBAC misconfig, etcd access, service account abuse |
| `/ad-assessment` | Full Active Directory audit: ADCS (ESC1–ESC8), BloodHound, GPO, LAPS, forest trusts |
| `/email-security` | SPF/DKIM/DMARC, open relay, spoofing resilience, MTA-STS, SMTP security |
| `/ssl-tls-audit` | TLS protocol/cipher audit, certificate chain, known vulns (POODLE, BEAST, Heartbleed) |
| `/credential-audit` | Password policy, hash extraction, lockout, enumeration, lateral movement chains |

### Recon & Analysis

| Skill | Description |
|-------|-------------|
| `/osint` | Deep OSINT: subdomain takeover, certificate transparency, Shodan, cloud storage, leaked creds |
| `/threat-modeling` | PASTA + STRIDE threat modeling — outputs attack tree, risk register, mitigation plan |
| `/codebase` | White-box source code review against OWASP ASVS 5.0 (427 requirements, 16 chapters) |
| `/analyze-cve` | CVE analysis with code path tracing and Burp Suite PoC generation |
| `/aikido-triage` | Triage Aikido SAST/SCA/secret-scanning CSV exports against local code |

### Reporting & Remediation

| Skill | Description |
|-------|-------------|
| `/remediate` | Generate specific code patches and config fixes for every finding in `findings.json` |
| `/gh-export` | Export confirmed findings as copy-pasteable GitHub issue markdown blocks |

### AI Safety

| Skill | Description |
|-------|-------------|
| `/ai-redteam` | LLM red-team using OWASP LLM Top 10: prompt injection, jailbreaks, system prompt leakage |
| `/colang-gen` | Generate NeMo Guardrails Colang files and YAML config blocks from plain-language descriptions |

## Usage

Skills are invoked as slash commands inside Claude Code:

```
/web-exploit https://target.example.com depth=standard
/codebase path=./src
/threat-modeling
/colang-gen
```

Most skills support three depth presets: `quick`, `standard`, and `thorough`.

Skills chain automatically — `/pentester` will invoke `/web-exploit`, `/post-exploit`, `/remediate`, and others as findings emerge. `/codebase` enriches all downstream skills with source-level context.

## Requirements

- [Claude Code](https://claude.ai/code)
- MCP tools configured: `pentest-agent` (scan, http, kali, session, report)
- Kali Linux container accessible via MCP for active testing skills
- Docker (for `/metasploit`)

## License

GNU Affero General Public License v3.0 — see [LICENSE](LICENSE).
