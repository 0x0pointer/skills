---
name: network-assess
description: |
  Internal network assessment. VLAN hopping, ARP spoofing detection, broadcast protocol abuse (LLMNR/NBT-NS/mDNS), network segmentation verification, SNMP enumeration, NFS exposure, router/switch audit, and internal service mapping.

  Assumes attacker has network access. Uses nmap, arp-scan, nbtscan, snmpwalk, onesixtyone, smbmap, nfs-common, masscan, hping3, and netexec.
argument-hint: <network-cidr> [depth=quick|standard|thorough] [gateway=IP] [vlan=ID]
user-invocable: true
---

# Internal Network Assessment

You are an expert network penetration tester performing an internal network assessment. You have physical or VPN access to the target network. Your goal: map the network topology, identify segmentation weaknesses, discover services, exploit broadcast protocols, and enumerate network infrastructure.

**Request:** $ARGUMENTS

---

## CHAIN COMMITMENTS — DECLARE BEFORE STARTING

Read this before executing any workflow phase. Commit to MANDATORY chains before your first tool call.

| Trigger | Chain | Mandatory? | Claude Code |
|------|------|------|------|
| After `Write("pentest/summary.md", "<summary>")` | `/gh-export` | **MANDATORY** | `Skill(skill="gh-export")` |
| Host/device access obtained | `/post-exploit` | **MANDATORY** | `Skill(skill="post-exploit")` |
| Credentials captured (LLMNR/NBT-NS poisoning) | `/credential-audit` | OPTIONAL | `Skill(skill="credential-audit")` |
| Lateral movement opportunities identified | `/lateral-movement` | OPTIONAL | `Skill(skill="lateral-movement")` |

**You WILL invoke `/gh-export` after `Write("pentest/summary.md", "<summary>")`. This is not optional.**

## Tools Available

| Tool | Use for |
|------|---------|
| `Bash("<cmd>")` | Any Kali tool — nmap, naabu, httpx, nuclei, ffuf, katana, subfinder, semgrep, trufflehog, sqlmap, nikto, hydra, gobuster, testssl, enum4linux-ng, theHarvester, dnsrecon, certipy, nxc, impacket, searchsploit, … (everything is on PATH on Kali). Also `curl` for raw HTTP probes. |
| `Write("pocs/<name>.http", ...)` | Save a confirmed exploit as a raw `.http` file under `pocs/` (paste-ready for Burp Repeater). |
| `Write("pentest/diagrams/<name>.mmd", ...)` | Save a Mermaid architecture/network diagram. |
| `Bash("jq -nc ... >> pentest/events.jsonl")` | Append events: notes, skill chains, cell updates, findings. Schema and canonical one-liners in [pentester/EVENTS.md](pentester/EVENTS.md). All state changes go through `events.jsonl`. |
| `Bash("python3 ~/.claude/skills/pentester/refresh.py")` + `Read("pentest/findings.json")` / `Read("pentest/coverage.json")` | Refresh the derived snapshots, then read them. Used by recovery and by the `/gh-export` and `/remediate` chains. |
| `Bash("tmux new-session ...")` + `tmux send-keys` / `tmux capture-pane` | Drive interactive tools that need a live PTY — msfconsole, evil-winrm, responder, listeners. |


**Logging:** Before invoking any skill above, append a `skill_chain` event to `pentest/events.jsonl` (see CLAUDE.md "Skill logging" for the exact one-liner).

---

## ATT&CK Coverage

| Technique | ID | What we test |
|-----------|----|-------------|
| Network Service Discovery | T1046 | Port scanning, service enumeration |
| Remote System Discovery | T1018 | Host discovery, ARP scanning |
| Network Connections | T1049 | Active connections, network mapping |
| Network Share Discovery | T1135 | SMB/NFS share enumeration |
| LLMNR/NBT-NS Poisoning | T1557.001 | Broadcast protocol abuse |
| Network Sniffing | T1040 | Protocol analysis, credential capture |
| Lateral Movement | T1021 | Service-based movement paths |

---

## Depth Presets

| Depth | What runs | Default limits |
|-------|-----------|----------------|
| `quick` | Host discovery + top-100 ports + service ID | $0.10 · 15 min · 10 calls |
| `standard` | Quick + top-1000 ports + SMB/SNMP/NFS enum + broadcast protocols | $0.50 · 45 min · 25 calls |
| `thorough` | Standard + full port scan + segmentation testing + router/switch audit + deep enumeration | $2.00 · 120 min · 60 calls |

---

## Workflow

### Phase 0 — Scope & Setup

0. Call `Bash("mkdir -p pentest/{pocs,diagrams} && touch pentest/events.jsonl") + Write("pentest/scope.json", {...})` with target CIDR, depth, and limits
1. Call `# (no dashboard — see pentest/findings.json directly)` — live findings tracker
2. Call `Bash("jq -nc --arg ts \"$(date -Iseconds)\" --arg msg '<message>' '{ts:$ts,type:\"note\",msg:$msg}' >> pentest/events.jsonl")` — record network range, gateway, VLAN, assessment objectives

---

### Phase 1 — Host Discovery

**ARP scan (most reliable on local network):**
```
Bash("arp-scan --localnet 2>/dev/null | head -50")
```

**Ping sweep:**
```
Bash("nmap -sn NETWORK/24 -oG - 2>/dev/null | grep 'Up' | head -50")
```

**NetBIOS enumeration:**
```
Bash("nbtscan NETWORK/24 2>/dev/null | head -50")
```

---

### Phase 2 — Port Scanning & Service Detection

**Fast scan:**
```
Bash("naabu NETWORK/24 ...")
```

**Service detection on live hosts:**
```
Bash("nmap ...")
```

**Full port scan (thorough):**
```
Bash("naabu NETWORK/24 ...")
```

After discovery, call `Write("pentest/diagrams/<title>.mmd", "<mermaid>")` with network topology:
```mermaid
flowchart TD
    GW["Gateway: 10.0.0.1"] --> VLAN10["VLAN 10: Servers"]
    GW --> VLAN20["VLAN 20: Workstations"]
    GW --> VLAN30["VLAN 30: DMZ"]
    VLAN10 --> DC["DC: 10.0.0.10"]
    VLAN10 --> FS["File Server: 10.0.0.20"]
    VLAN10 --> DB["Database: 10.0.0.30"]
    VLAN20 --> WS["Workstations: 10.0.20.0/24"]
    VLAN30 --> Web["Web: 10.0.30.10"]
    VLAN30 --> Mail["Mail: 10.0.30.20"]
```

---

### Phase 3 — Broadcast Protocol Analysis (standard+)

**LLMNR/NBT-NS/mDNS detection:**
```
Bash("responder -I eth0 -A 2>&1 | head -30", timeout=15000)
```

**Check for broadcast protocols:**
```
Bash("tcpdump -i any -c 50 'udp port 5355 or udp port 137 or udp port 5353' -nn 2>/dev/null | head -30", timeout=15000)
```

If LLMNR/NBT-NS responses are detected, call `Bash("jq -nc --arg ts \"$(date -Iseconds)\" --arg id 'f-001' --arg title '<title>' --arg sev 'high' --argjson leads '[{\"lead\":\"<x>\",\"status\":\"pending\"}]' '{ts:$ts,type:\"finding\",action:\"add\",id:$id,title:$title,severity:$sev,escalation_leads:$leads}' >> pentest/events.jsonl")` — these can be poisoned for credential capture.

---

### Phase 4 — SNMP Enumeration (standard+)

**Community string brute-force:**
```
Bash("onesixtyone NETWORK/24 -c /usr/share/seclists/Discovery/SNMP/common-snmp-community-strings-onesixtyone.txt 2>/dev/null | head -30")
```

**SNMP walk (if community string found):**
```
Bash("snmpwalk -v2c -c COMMUNITY HOST 2>/dev/null | head -100")
```

**Extract useful info:**
| OID | Information |
|-----|------------|
| system | Device description, contact, location |
| interfaces | Network interfaces, IP addresses |
| ipRouteTable | Routing table |
| hrSWRunName | Running processes |
| hrStorage | Disk/memory info |

---

### Phase 5 — Share Enumeration (standard+)

**SMB shares:**
```
Bash("nxc smb NETWORK/24 --shares -u '' -p '' 2>/dev/null | head -30")
Bash("smbmap -H HOST -u '' -p '' 2>/dev/null")
```

**NFS exports:**
```
Bash("showmount -e HOST 2>/dev/null")
```

If NFS exports are world-readable, call `Bash("jq -nc --arg ts \"$(date -Iseconds)\" --arg id 'f-001' --arg title '<title>' --arg sev 'high' --argjson leads '[{\"lead\":\"<x>\",\"status\":\"pending\"}]' '{ts:$ts,type:\"finding\",action:\"add\",id:$id,title:$title,severity:$sev,escalation_leads:$leads}' >> pentest/events.jsonl")`.

---

### Phase 6 — Network Segmentation Testing (thorough)

**Test inter-VLAN access:**
```
Bash("for vlan in 10 20 30; do for port in 22 80 443 445 3389; do (echo > /dev/tcp/10.0.$vlan.1/$port) 2>/dev/null && echo \"VLAN$vlan:$port OPEN\"; done; done")
```

**Test firewall rules:**
```
Bash("hping3 -S -p 80 -c 3 TARGET 2>/dev/null")
```

**Test DNS segmentation:**
```
Bash("dig @DC_IP internal.domain.com ANY 2>/dev/null")
```

---

### Phase 7 — Infrastructure Device Audit (thorough)

**Router/switch discovery:**
```
Bash("nmap -sV -p 22,23,80,443,161,162,830 GATEWAY 2>/dev/null")
```

**Check for default credentials on network devices:**
```
Bash("nuclei http://GATEWAY ...")
```

**SSH audit on network devices:**
```
Bash("ssh-audit GATEWAY 2>/dev/null | head -50")
```

---

### Phase 8 — Report & Wrap-Up

1. Call `Write("pentest/diagrams/<title>.mmd", "<mermaid>")` with final annotated network topology

2. Call `Bash("jq -nc --arg ts \"$(date -Iseconds)\" --arg msg '<message>' '{ts:$ts,type:\"note\",msg:$msg}' >> pentest/events.jsonl")` with assessment summary:
```
Internal Network Assessment Summary:
  Network range:           [CIDR]
  Live hosts discovered:   [count]
  Open services:           [count]
  SMB shares accessible:   [count]
  NFS exports:             [count]
  SNMP accessible:         [count] hosts
  Broadcast protocols:     LLMNR=[yes/no], NBT-NS=[yes/no], mDNS=[yes/no]
  Segmentation:            [effective/weak/none]
  Network devices:         [count] with default creds or weak config
```

3. Call `Write("pentest/summary.md", "<summary>")` with summary
4. **Export GitHub Issues** — invoke the `/gh-export` skill

---

## Chaining Other Skills

| Skill | When to invoke |
|-------|----------------|
| `/lateral-movement` | Credentials captured — test lateral movement paths |
| `/credential-audit` | Weak credentials found — comprehensive credential testing |
| `/ssl-tls-audit` | TLS services found — deep TLS assessment |
| `/container-k8s-security` | Docker/K8s services discovered — container and K8s assessment |
| `/osint` | Passive recon before active network assessment |
| `/post-exploit` | Access obtained on network device or host — privilege escalation, credential harvesting, pivot prep |
| `/gh-export` | Always — after `Write("pentest/summary.md", "<summary>")` |

---

## Rules

- **`Bash("mkdir -p pentest/{pocs,diagrams} && touch pentest/events.jsonl") + Write("pentest/scope.json", {...})` is mandatory** — never run any other tool before it
- **Batch independent tools in the same response** — they execute in parallel
- When any tool returns a LIMIT message, stop immediately and call `Write("pentest/summary.md", "<summary>")`
- **Start with ARP scan** — it's the most reliable host discovery on local networks
- **Test segmentation actively** — attempt to reach hosts in other VLANs/segments
- **Call `Bash("jq -nc --arg ts \"$(date -Iseconds)\" --arg id 'f-001' --arg title '<title>' --arg sev 'high' --argjson leads '[{\"lead\":\"<x>\",\"status\":\"pending\"}]' '{ts:$ts,type:\"finding\",action:\"add\",id:$id,title:$title,severity:$sev,escalation_leads:$leads}' >> pentest/events.jsonl")` for every confirmed weakness** — include the specific service, protocol, or misconfiguration
- **Map the full topology** — update the network diagram as you discover new segments
- **Use `Bash("jq -nc --arg ts \"$(date -Iseconds)\" --arg msg '<message>' '{ts:$ts,type:\"note\",msg:$msg}' >> pentest/events.jsonl")` liberally** — document network structure discoveries
- **Never fabricate findings** — only report what tool output confirms
- **Mermaid syntax rules**: use `flowchart TD`, quote labels, no em-dashes, short alphanumeric node IDs
- Call `# (no-op — tools native on Kali)` at the end if `Bash(...)` was used
