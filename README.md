<p align="center">
  <img src="https://nullpointer.studio/design/FullLogo_Transparent.png" alt="nullpointer.studio" width="320">
</p>

# skills

**A library of offensive-security skills that teach your LLM how to think like a pentester.**
Drop them into Claude Code, OpenCode, or any MCP-capable agent and run end-to-end engagements with a single slash command.

> ⚠️ **Authorized testing only.** Use these skills against systems you own or have explicit written permission to test. Unauthorized access is illegal.

<p align="center">
  <img src="https://nullpointer.studio/design/FullLogo_Transparent.png" alt="skills hero" width="0" height="0">
  <!-- TODO: drop a hero gif of /pentester running end-to-end into the parent agent-smith repo's docs/gifs/ -->
</p>

---

## Why these skills

- 🧠 **Pattern teachings, not payload libraries.**


Each skill is a prompt that teaches a vulnerability *class* — the surface area, the verification logic, the chaining rules. The LLM invents the actual attacks. Two runs against the same target produce different attack paths.
- 🛠 **Bring your own LLM.**


Works with Claude Code, [OpenCode](https://opencode.ai) (any provider — OpenAI, Anthropic, Google, OpenRouter, Ollama, llama.cpp, vLLM), or any MCP-capable client. Skills are plain markdown — load them however your client expects.
- 🔗 **Skills chain themselves.**


`/pentester` discovers an API surface and pivots into `/api-security`; `/api-security` finds an LLM endpoint and pivots into `/ai-redteam`; `/codebase` finds an injection point and pivots into `/web-exploit`. The agent decides what to run next based on what it just found — you don't write the orchestration.
- 📚 **Methodology-first.**


Every skill is grounded in a public framework: OWASP Web/API/LLM Top 10, ASVS 5.0, AITG, MCP Top 10, MITRE ATT&CK, PASTA, STRIDE. The skills enforce *coverage*, not just *testing*.
- 📦 **End-to-end deliverables.**


Findings, PoCs (Burp-ready `.http` files), threat models, code patches, GitHub issues, and CVE submission packages — all generated for you.
- 🔌 **Engine-agnostic.**


The skills assume an MCP server providing five consolidated tools (`scan`, `kali`, `http`, `report`, `session`). Pair them with [agent-smith](https://github.com/0x0pointer/agent-smith) for a turnkey setup, or wire them into your own MCP server.

---

## The new way: skills as pattern teachings

Most pentest automation ships a giant payload library and runs it linearly. These skills do the opposite.

**A skill is not a script. A skill is a prompt that teaches the LLM a way of *thinking*.** It describes the vulnerability class, the surface area, the verification logic, and the chaining rules — but it leaves the actual attacks to the model. The LLM reads the skill, understands the *pattern*, and then finds its own paths through your target.

The skills are inspiration. The LLM is the operator.

---

## See it in action

<!-- TODO: drop gifs into agent-smith/docs/gifs/ — paths are wired up below relative to the agent-smith repo -->

<table>
  <tr>
    <td width="50%">
      <p align="center"><strong><code>/pentester</code> — full autonomous engagement</strong></p>
      <img src="https://raw.githubusercontent.com/0x0pointer/agent-smith/main/docs/gifs/pentester-full-run.gif" alt="pentester running from recon through reporting" width="100%">
      <p><sub>Recon → fingerprint → exploit → loot → report. The agent decides every step.</sub></p>
    </td>
    <td width="50%">
      <p align="center"><strong><code>/codebase</code> — white-box ASVS review</strong></p>
      <img src="https://raw.githubusercontent.com/0x0pointer/agent-smith/main/docs/gifs/codebase-review.gif" alt="codebase skill performing an ASVS 5.0 review" width="100%">
      <p><sub>Source → routes → sinks → ASVS chapters → enriched context for every downstream skill.</sub></p>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <p align="center"><strong><code>/api-security</code> — OWASP API Top 10 (2023)</strong></p>
      <img src="https://raw.githubusercontent.com/0x0pointer/agent-smith/main/docs/gifs/api-security.gif" alt="api-security skill testing BOLA, BFLA, mass assignment" width="100%">
      <p><sub>Spec hunt → BOLA two-account loop → BFLA → mass assignment → SSRF → inventory drift.</sub></p>
    </td>
    <td width="50%">
      <p align="center"><strong><code>/ai-redteam</code> — OWASP LLM Top 10 + AITG</strong></p>
      <img src="https://raw.githubusercontent.com/0x0pointer/agent-smith/main/docs/gifs/ai-redteam.gif" alt="ai-redteam executing prompt injection and jailbreak chains" width="100%">
      <p><sub>Prompt injection, jailbreaks, model extraction, MCP runtime attacks, post-access infra checks.</sub></p>
    </td>
  </tr>
</table>

---

## Use cases examples

Drop in any of these the moment you start your client/agent. Most skills run with a single slash command.

### 1. Run a full pentest, hands-off

```
/pentester scan https://staging.example.com depth=thorough
```

The agent runs OSINT → recon → web exploit → API exploit → post-exploit → reporting, deciding each pivot from the previous result. End state: `findings.json`, PoCs in `pocs/`, a topology diagram, a coverage matrix, and patch-ready code fixes.

### 2. Pre-prod secure code review

```
/codebase path=./src
```

White-box ASVS 5.0 review across 16 chapters and 427 requirements. Maps every route, every sink, every dangerous pattern, and feeds the result as white-box context into every downstream skill.

### 3. Audit an API surface against the OWASP API Top 10

```
/api-security https://api.example.com depth=thorough
```

Discovers your full API surface (spec, JS bundles, kiterunner, version drift), then runs the complete OWASP API Top 10 (2023) — BOLA with a two-account cross-tenant loop, BFLA, mass assignment, JWT/OAuth abuse, SSRF, business-flow abuse, and inventory drift. Works on REST, GraphQL, gRPC, SOAP, and MCP.

### 4. Triage a CVE in your dependency tree

```
/analyze-cve lodash 4.17.20 CVE-2021-23337
```

The agent reads your code, traces the vulnerable function from user input to sink, decides whether you're actually exploitable, and writes a Burp-ready PoC if you are.

### 5. AI / LLM red-team

```
/ai-redteam https://your-app.com/api/chat provider=openai depth=thorough
```

OWASP LLM Top 10 (2025), the OWASP AI Testing Guide (AITG v1, Nov 2025), and OWASP MCP Top 10 runtime attacks. Generates payloads on the fly using FuzzyAI, Garak, PyRIT, and promptfoo.

### 6. Internal AD assessment

```
/ad-assessment domain=corp.example.com
```

Full BloodHound enumeration, ADCS (ESC1–ESC8), Kerberoasting, AS-REP roasting, delegation abuse (constrained / unconstrained / RBCD), GPO/LAPS audit, and forest trust mapping. MITRE ATT&CK aligned.

### 7. Threat-model an architecture

```
/threat-modeling
```

PASTA + STRIDE + 4-question framework. Outputs component map, data flow diagram, attack tree, prioritized risk register, and a mitigation plan.

> 💡 **Pick a skill or let `/pentester` orchestrate.** Single-purpose skills give you laser focus; `/pentester` chains everything based on what it finds.

---

## Pick your LLM client

These skills are plain markdown — anything that speaks MCP can drive them.

<table>
  <tr>
    <th width="33%">Claude Code</th>
    <th width="33%">OpenCode (BYO LLM)</th>
    <th width="33%">Custom MCP client</th>
  </tr>
  <tr>
    <td>
      Anthropic's official CLI. Best UX, native skill support. Skills install into <code>~/.claude/skills/</code> and become slash commands automatically.
      <pre><code>git clone --recursive \
  https://github.com/0x0pointer/agent-smith
cd agent-smith
./installers/install.sh</code></pre>
      Requires <a href="https://docs.anthropic.com/en/docs/claude-code">Claude Code</a> + an Anthropic API key.
    </td>
    <td>
      Open-source coding agent that supports <strong>any</strong> provider — OpenAI, Anthropic, Google, OpenRouter, Ollama, llama.cpp, vLLM, your own endpoint. Skills install into <code>~/.config/opencode/commands/</code>.
      <pre><code>git clone --recursive \
  https://github.com/0x0pointer/agent-smith
cd agent-smith
./installers/install_opencode.sh</code></pre>
      Requires <a href="https://opencode.ai">OpenCode</a>. Configure your model in <code>~/.config/opencode/opencode.json</code>.
    </td>
    <td>
      Any MCP-capable client (Cursor, Continue, Zed, custom Agent SDK app, etc.). Skills are plain markdown — load them however your client expects prompts.
      <pre><code># wire the agent-smith MCP
# server into your client
poetry install
poetry run python -m mcp_server</code></pre>
      Five consolidated MCP tools: <code>scan</code>, <code>kali</code>, <code>http</code>, <code>report</code>, <code>session</code>.
    </td>
  </tr>
</table>

> 🧠 **The LLM is your choice.** These skills don't care if it's Claude Opus 4.6, GPT-5, Gemini 2.5, Llama-4, or a local Qwen3 — anything strong enough to follow tool-use instructions will work. Bigger / smarter models find more interesting attack paths.

---

## Catalog

<details>
<summary><strong>Penetration testing</strong> (9 skills)</summary>

| Skill | What it does |
|---|---|
| `/pentester` | Full autonomous engagement — chains everything else based on findings |
| `/web-exploit` | SQLi, XSS, SSRF, SSTI, deserialization, JWT, smuggling, race conditions, business logic |
| `/api-security` | OWASP API — BOLA, BFLA, mass assignment, JWT/OAuth abuse, SSRF, business-flow abuse, inventory drift. REST/GraphQL/gRPC/SOAP/MCP |
| `/network-assess` | VLAN hopping, LLMNR/NBT-NS abuse, SNMP enumeration, segmentation testing |
| `/post-exploit` | Linux/Windows privesc, persistence, credential harvesting, internal recon |
| `/lateral-movement` | PTH, PTT, Kerberoasting, NTLM relay, delegation abuse, cross-trust pivoting |
| `/metasploit` | Exploit validation in an isolated Docker container with msfconsole HTTP shim |
| `/reverse-shell` | Generates and manages reverse shells across all platforms with fallback chains |
| `/pivot-tunnel` | Chisel + SOCKS5 tunneling and ligolo-ng pivoting after RCE |
</details>

<details>
<summary><strong>Cloud, infra & identity</strong> (6 skills)</summary>

| Skill | What it does |
|---|---|
| `/cloud-security` | AWS / Azure / GCP IAM escalation, public storage, serverless, database exposure, logging gaps |
| `/container-k8s-security` | Container escape, K8s RBAC, etcd access, service account abuse, pod security |
| `/ad-assessment` | ADCS (ESC1–ESC8), BloodHound, GPO, LAPS, fine-grained password policies, forest trusts |
| `/email-security` | SPF / DKIM / DMARC, open relay, MTA-STS, TLS-RPT, SMTP security, S/MIME |
| `/ssl-tls-audit` | Protocol/cipher audit, cert chain (CT logs, OCSP, pinning), POODLE/BEAST/Heartbleed |
| `/credential-audit` | Brute force, password spraying, default creds, lockout, MFA bypass, OAuth/OIDC abuse |
</details>

<details>
<summary><strong>Recon & analysis</strong> (5 skills)</summary>

| Skill | What it does |
|---|---|
| `/osint` | Subdomain takeover, certificate transparency, Shodan/Censys, leaked creds, Wayback historical |
| `/threat-modeling` | PASTA + STRIDE + 4-question, attack tree, risk register, mitigation plan |
| `/codebase` | OWASP ASVS 5.0 white-box review (16 chapters, 427 requirements) |
| `/analyze-cve` | CVE code-path tracing from user input to sink, with Burp-ready PoC |
| `/aikido-triage` | Triage Aikido SAST/SCA/secret-scan CSV against your code, output reviewed CSV + HTML evidence |
| `/compliance` | Full ASVS 5.0 compliance matrix (346 controls) — COMPLIANT/NON_COMPLIANT/NOT_RELEVANT per control with code evidence, outputs CSV + HTML report |
</details>

<details>
<summary><strong>AI safety & red-team</strong> (2 skills)</summary>

| Skill | What it does |
|---|---|
| `/ai-redteam` | OWASP LLM Top 10 (2025) + AITG v1 + MCP Top 10 runtime attacks. Uses FuzzyAI, Garak, PyRIT, promptfoo |
| `/colang-gen` | Generate NeMo Guardrails Colang configs and YAML config blocks from plain language |
</details>

<details>
<summary><strong>Reporting & remediation</strong> (3 skills)</summary>

| Skill | What it does |
|---|---|
| `/remediate` | Writes specific code patches and config fixes for every confirmed finding |
| `/gh-export` | Formats confirmed findings as copy-pasteable GitHub issue markdown blocks |
| `/request-cves` | Generates CVE submission packages — MITRE form, GHSA draft, disclosure report, vendor email |
</details>

---

## Requirements

These skills are slash commands — they need an MCP server providing the `scan`, `kali`, `http`, `report`, and `session` tools. The recommended way to install everything is via [agent-smith](https://github.com/0x0pointer/agent-smith), which bundles:

- The MCP server (`python -m mcp_server`)
- Lightweight scanner Docker images (nmap, naabu, httpx, nuclei, ffuf, semgrep, trufflehog)
- The custom Kali container (`pentest-agent/kali-mcp`) with 100+ pre-installed tools
- The Metasploit container (`pentest-agent/metasploit`)
- The live findings dashboard at `localhost:7777`
- Installers for Claude Code and OpenCode

```bash
git clone --recursive https://github.com/0x0pointer/agent-smith
cd agent-smith
./installers/install.sh         # Claude Code
# or
./installers/install_opencode.sh  # OpenCode (BYO LLM)
```

Skills can also be wired into any custom MCP client that exposes the same five tools.

---

## Adding a new skill

Skills are plain markdown files with YAML frontmatter. The pattern:

```markdown
---
name: my-skill
description: |
  One-paragraph methodology summary. List the vulnerability classes, the
  surface area, and which other skills this one chains from / into.
argument-hint: <target> [option=value]
user-invocable: true
---

# Skill Title

You are a [role]. Your goal: [outcome].

**Request:** $ARGUMENTS

## Tools Available
## Workflow
### Phase 0 — Scope & Setup
### Phase 1 — Discovery
...
## Chaining Other Skills
```

Use `/web-exploit` or `/api-security` as a reference template — they show the full structure: phases, coverage matrix integration, reference-library lazy loading, and chaining tables.

After adding a skill, update the submodule pointer in `agent-smith` (`git add skills && git commit`) and re-run the installer to deploy it.

---

## Acknowledgements

The **mobile** skills (`mobile/android-security`, `mobile/ios-security`, `mobile/mobile-pentest-plan`,
`mobile/masvs-checklist`) were distilled and adapted from
[**dweinstein/mobile-security-skills**](https://github.com/dweinstein/mobile-security-skills) — its
per-MASVS-category checks, MASTG test-ID crosswalks, NowSecure risk-tiering, and workflow orchestration
were rewritten into Smith's tool-executing, chaining skill model. That collection is itself built on:

- [OWASP MASVS v2](https://mas.owasp.org/MASVS/) — Mobile Application Security Verification Standard
- [OWASP MASTG](https://mas.owasp.org/MASTG/) — Mobile Application Security Testing Guide
- [NowSecure Secure Mobile Development](https://github.com/nowsecure/secure-mobile-development)

---

## License

GNU Affero General Public License v3.0 — see [LICENSE](LICENSE).

> Built for offensive-security professionals. Use it to make the internet safer.
