<p align="center">
  <img src="https://nullpointer.studio/design/FullLogo_Transparent.png" alt="nullpointer.studio" width="320">
</p>

# skills

**A library of offensive-security skills that teach your LLM how to think like a pentester.**
Drop them into Claude Code on a Kali host and run end-to-end engagements with a single slash command.

> ⚠️ **Authorized testing only.** Use these skills against systems you own or have explicit written permission to test. Unauthorized access is illegal.

> 🍴 **This is a fork.** The upstream project is [`0x0pointer/skills`](https://github.com/0x0pointer/skills), designed to run through an MCP server ([`0x0pointer/agent-smith`](https://github.com/0x0pointer/agent-smith)) that brokers five consolidated tools (`session`, `scan`, `kali`, `http`, `report`) and ships a Docker bundle (Kali container, scanner images, Metasploit container, live findings dashboard). If you want that turnkey, MCP-driven, multi-client (Claude Code / OpenCode / any MCP client) experience, use the upstream repo.
>
> **What this fork changes:** every skill has been rewritten to run **natively in Claude Code on Kali** — no MCP server, no Docker, no dashboard. The five MCP tools have been replaced with Claude Code's built-in `Bash`, `Read`, `Write`, and `Edit`:
>
> | Upstream (MCP) | This fork (native) |
> |---|---|
> | `kali(command="...")` | `Bash("...")` |
> | `scan(tool="nmap", ...)` | `Bash("nmap ...")` (same for naabu, httpx, nuclei, ffuf, katana, subfinder, semgrep, trufflehog) |
> | `http(action="request", ...)` | `Bash("curl ...")` |
> | `http(action="save_poc", ...)` | `Write("pocs/<name>.http", ...)` |
> | `report(action="finding"/"diagram"/"note"/"coverage"/"dashboard", ...)` | `Read`/`Write` against `pentest/findings.json`, `pentest/coverage.json`, `pentest/diagrams/*.mmd`, `pentest/notes.log` (no dashboard) |
> | `session(action="start"/"complete"/"recovery"/"set_skill"/"set_codebase", ...)` | `mkdir -p pentest/{pocs,diagrams}` + `Write` on `pentest/scope.json`, `pentest/summary.md`, `pentest/skill_chain.log` |
> | `session(action="start_kali"/"stop_kali"/"pull_images")` | dropped — tools are native on Kali |
> | Interactive PTY tools (msfconsole, evil-winrm, responder, listeners) | `tmux new-session` + `send-keys` / `capture-pane` |
> | Dual-mode chain blocks (`# Claude Code: ...` + `# READ THIS FILE NOW (opencode): cat ~/.config/opencode/commands/...`) | single `Skill(skill="<name>", args="...")` call |
>
> See [`migrate_native.py`](migrate_native.py) for the rewrite logic — it's idempotent, so you can re-run it after pulling fresh upstream changes to re-apply the conversion. The trade-off: this fork does not work with OpenCode, other MCP clients, or hosts without the Kali toolchain on `PATH`. Burp routing (`poc=True`) is gone too — confirmed exploits are saved as `.http` files for paste-into-Repeater instead of being live-tunneled. If any of those constraints are deal-breakers, use upstream.

<p align="center">
  <img src="https://nullpointer.studio/design/FullLogo_Transparent.png" alt="skills hero" width="0" height="0">
  <!-- TODO: drop a hero gif of /pentester running end-to-end into the parent agent-smith repo's docs/gifs/ -->
</p>

---

## Why these skills

- 🧠 **Pattern teachings, not payload libraries.**


Each skill is a prompt that teaches a vulnerability *class* — the surface area, the verification logic, the chaining rules. The LLM invents the actual attacks. Two runs against the same target produce different attack paths.
- 🛠 **Native on Kali.**


Runs straight in Claude Code on a Kali host — no MCP server, no Docker. Skills drive `nmap`, `naabu`, `httpx`, `nuclei`, `ffuf`, `katana`, `subfinder`, `sqlmap`, `hydra`, `nikto`, … via the built-in `Bash` tool. Artifacts (findings, notes, coverage, PoCs, diagrams) land under `./pentest/`.
- 🔗 **Skills chain themselves.**


`/pentester` discovers an API surface and pivots into `/api-security`; `/api-security` finds an LLM endpoint and pivots into `/ai-redteam`; `/codebase` finds an injection point and pivots into `/web-exploit`. The agent decides what to run next based on what it just found — you don't write the orchestration.
- 📚 **Methodology-first.**


Every skill is grounded in a public framework: OWASP Web/API/LLM Top 10, ASVS 5.0, AITG, MCP Top 10, MITRE ATT&CK, PASTA, STRIDE. The skills enforce *coverage*, not just *testing*.
- 📦 **End-to-end deliverables.**


Findings, PoCs (Burp-ready `.http` files), threat models, code patches, GitHub issues, and CVE submission packages — all generated for you.
- 🔌 **No external dependencies.**


Just Claude Code + Kali. The skills speak `Bash`, `Read`, `Write`, `Edit` — Claude Code's built-in tools — so there is no MCP server to run, no Docker images to pull, no dashboard to keep alive. `tmux` covers tools that need a live PTY.

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

## Setup — Claude Code on Kali (native)

These skills run natively in Claude Code on a Kali Linux host. Every Kali tool (nmap, naabu, httpx, nuclei, ffuf, katana, subfinder, sqlmap, hydra, nikto, enum4linux-ng, theHarvester, certipy, nxc, impacket, …) is on `PATH`, so the skills drive them straight through Claude Code's built-in `Bash` tool. No MCP server, no Docker, no dashboard — just the native tools you already have.

```bash
# 1. Clone (or copy) the skills directory into Claude Code's skills folder.
git clone https://github.com/0x0pointer/skills ~/.claude/skills
# or, if this repo is your skills/ directly:
ln -s "$PWD/skills" ~/.claude/skills

# 2. Start Claude Code in the directory you want artifacts written to.
cd ~/engagements/acme/
claude
```

Each skill becomes a slash command (`/pentester`, `/web-exploit`, `/api-security`, …) and writes artifacts under `./pentest/`:

| Path | Contents |
|---|---|
| `pentest/scope.json` | Target, depth, scope, and any custom limits set at session start |
| `pentest/findings.json` | Every confirmed vulnerability with evidence (read → mutate → write) |
| `pentest/notes.log` | Reasoning trail — append-only via `echo … >> pentest/notes.log` |
| `pentest/coverage.json` | Endpoint × injection-class test matrix |
| `pentest/pocs/<name>.http` | Burp-paste-ready raw HTTP request for each confirmed exploit |
| `pentest/diagrams/<name>.mmd` | Mermaid diagrams (network topology, app architecture) |
| `pentest/skill_chain.log` | Audit trail of which sub-skills were invoked from where |
| `pentest/summary.md` | Final summary written at `session complete` |

For interactive tools that need a live PTY (msfconsole, evil-winrm, responder, listeners), the skills drive a `tmux` session via `Bash`:

```bash
tmux new-session -d -s msf 'msfconsole -q'
tmux send-keys -t msf 'use exploit/...' Enter
tmux capture-pane -t msf -p
```

> 🧠 **Authorization only.** These skills generate real attack traffic. Run them only against systems you own or have explicit written permission to test.

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
| `/metasploit` | Exploit validation against confirmed CVEs — drives `msfconsole` in a `tmux` session |
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

- A working Kali Linux install (host, VM, or WSL) with the standard offensive-security toolchain on `PATH`. A vanilla `kali-rolling` with `kali-linux-default` (or `kali-linux-large`) covers the great majority of skill workflows. Specific tools each skill expects are listed at the top of every `SKILL.md`.
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed on the same Kali host, with an Anthropic API key configured.
- `tmux` (for skills that drive interactive REPLs like `msfconsole`).
- Optional: `jq` (some skills use it for ad-hoc `pentest/findings.json` mutations).

The skills are plain markdown with YAML frontmatter — drop the directory at `~/.claude/skills/` and Claude Code picks them up automatically as slash commands.

### Migrating from the MCP-based version

If you have an older copy of these skills that uses the 5-tool MCP API (`session`, `scan`, `kali`, `http`, `report`), run [migrate_native.py](migrate_native.py) once to rewrite them:

```bash
cd skills
python3 migrate_native.py --dry-run   # preview
python3 migrate_native.py              # apply
```

The script is idempotent — re-running on already-migrated files is a no-op.

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

After adding a skill, drop the new file into `~/.claude/skills/` (or just commit it in this repo if you have it cloned there) — Claude Code picks it up on the next session.

---

## License

GNU Affero General Public License v3.0 — see [LICENSE](LICENSE).

> Built for offensive-security professionals. Use it to make the internet safer.
