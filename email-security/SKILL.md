---
name: email-security
description: |
  Email infrastructure security audit. Tests SPF, DKIM, DMARC configuration, open relay, email spoofing resilience, S/MIME, MTA-STS, TLS-RPT, and SMTP security.

  Uses swaks, dnsrecon, nmap SMTP scripts, smtp-user-enum, and dig. Pure skill markdown — no new infrastructure needed.
argument-hint: <domain> [depth=quick|standard|thorough]
user-invocable: true
---

# Email Infrastructure Security Audit

You are an expert email security auditor. Your goal: comprehensively assess the email infrastructure of a target domain — authentication mechanisms (SPF/DKIM/DMARC), transport security (STARTTLS/MTA-STS), relay configuration, spoofing resilience, and user enumeration — and report all weaknesses with remediation guidance.

**Request:** $ARGUMENTS

---

## CHAIN COMMITMENTS — DECLARE BEFORE STARTING

Read this before executing any workflow phase. Commit to MANDATORY chains before your first tool call.

| Trigger | Chain | Mandatory? | Claude Code |
|------|------|------|------|
| After `Write("pentest/summary.md", "<summary>")` | `/gh-export` | **MANDATORY** | `Skill(skill="gh-export")` |
| SMTP/STARTTLS weakness found | `/ssl-tls-audit` | OPTIONAL | `Skill(skill="ssl-tls-audit")` |
| Email credentials found | `/credential-audit` | OPTIONAL | `Skill(skill="credential-audit")` |
| Architecture review requested | `/threat-modeling` | OPTIONAL | `Skill(skill="threat-modeling")` |

**You WILL invoke `/gh-export` after `Write("pentest/summary.md", "<summary>")`. This is not optional.**


**Logging:** Before invoking any skill above, append a `skill_chain` event to `pentest/events.jsonl` (see CLAUDE.md "Skill logging" for the exact one-liner).

---

## Tools Available

| Tool | Use for |
|------|---------|
| `Bash("<cmd>")` | Any Kali tool — nmap, naabu, httpx, nuclei, ffuf, katana, subfinder, semgrep, trufflehog, sqlmap, nikto, hydra, gobuster, testssl, enum4linux-ng, theHarvester, dnsrecon, certipy, nxc, impacket, searchsploit, … (everything is on PATH on Kali). Also `curl` for raw HTTP probes. |
| `Write("pocs/<name>.http", ...)` | Save a confirmed exploit as a raw `.http` file under `pocs/` (paste-ready for Burp Repeater). |
| `Write("pentest/diagrams/<name>.mmd", ...)` | Save a Mermaid architecture/network diagram. |
| `Bash("jq -nc ... >> pentest/events.jsonl")` | Append events: notes, skill chains, cell updates, findings. Schema and canonical one-liners in [pentester/EVENTS.md](pentester/EVENTS.md). All state changes go through `events.jsonl`. |
| `Bash("python3 ~/.claude/skills/pentester/refresh.py")` + `Read("pentest/findings.json")` / `Read("pentest/coverage.json")` | Refresh the derived snapshots, then read them. Used by recovery and by the `/gh-export` and `/remediate` chains. |
| `Bash("tmux new-session ...")` + `tmux send-keys` / `tmux capture-pane` | Drive interactive tools that need a live PTY — msfconsole, evil-winrm, responder, listeners. |

---

## Testing Matrix

| Category | Tests | Tools | Severity if failed |
|----------|-------|-------|--------------------|
| **SPF** | Record exists, syntax valid, not too permissive (+all), include chain | dig | High if missing/misconfigured |
| **DKIM** | Selector discovery, key size, algorithm | dig | High if missing |
| **DMARC** | Record exists, policy (none/quarantine/reject), rua/ruf reporting | dig | High if p=none or missing |
| **STARTTLS** | SMTP STARTTLS supported, certificate valid | openssl, nmap | Medium |
| **MTA-STS** | Policy published, mode (enforce/testing/none) | Bash("curl ...") | Low-Medium |
| **TLS-RPT** | TLSRPT DNS record for failure reporting | dig | Low |
| **Open relay** | Test if server relays mail for external domains | swaks | Critical |
| **Spoofing** | Send spoofed email, check if accepted/rejected | swaks | High |
| **User enumeration** | VRFY, EXPN, RCPT TO response differences | smtp-user-enum | Medium |
| **SMTP banner** | Information disclosure in banner | nmap | Low |

---

## Depth Presets

| Depth | What runs | Default limits |
|-------|-----------|----------------|
| `quick` | SPF + DKIM + DMARC + MX lookup | $0.05 · 5 min · 5 calls |
| `standard` | Quick + STARTTLS + MTA-STS + open relay test + spoofing test | $0.15 · 15 min · 12 calls |
| `thorough` | Standard + user enumeration + full SMTP audit + TLS cert analysis | $0.30 · 30 min · 20 calls |

---

## Workflow

### Phase 0 — Scope & Setup

0. Call `Bash("mkdir -p pentest/{pocs,diagrams} && touch pentest/events.jsonl") + Write("pentest/scope.json", {...})` with target domain, depth, and limits
1. Call `# (no dashboard — see pentest/findings.json directly)` — live findings tracker
2. Call `Bash("jq -nc --arg ts \"$(date -Iseconds)\" --arg msg '<message>' '{ts:$ts,type:\"note\",msg:$msg}' >> pentest/events.jsonl")` — record target domain, known mail provider

---

### Phase 1 — DNS Record Analysis

Run in parallel:

```
Bash("dig DOMAIN MX +short")
Bash("dig DOMAIN TXT +short | grep -i spf")
Bash("dig _dmarc.DOMAIN TXT +short")
Bash("dig _mta-sts.DOMAIN TXT +short")
Bash("dig _smtp._tls.DOMAIN TXT +short")
```

**SPF analysis:**
| Finding | Severity |
|---------|----------|
| No SPF record | **High** |
| `+all` mechanism | **Critical** — anyone can send as this domain |
| `~all` (softfail) | **Medium** — should be `-all` |
| Too many DNS lookups (>10) | **Medium** — SPF permerror |
| `include:` chain too deep | **Low** |

**DMARC analysis:**
| Finding | Severity |
|---------|----------|
| No DMARC record | **High** |
| `p=none` | **High** — no enforcement |
| `p=quarantine` | **Medium** — should be `reject` for mature domains |
| No `rua=` reporting | **Medium** — no visibility into failures |
| `pct=` < 100 | **Low** — partial enforcement |

**DKIM — discover selectors:**

Start with common selectors, then expand if needed. Selector naming is organization-specific — these are examples, not an exhaustive list:
```
Bash("for sel in default google selector1 selector2 k1 k2 k3 mail dkim s1 s2 s1024 s2048 smtp protonmail mandrill mxvault; do R=$(dig ${sel}._domainkey.DOMAIN TXT +short 2>/dev/null); [ -n \"$R\" ] && echo \"$sel: $R\"; done")
```

If no selectors found, try brute-forcing with a wordlist or checking email headers from the domain for the `s=` tag:
```
Bash("swaks --to test@DOMAIN --server MX_HOST 2>&1 | grep -i 'dkim-signature' | grep -oP 's=\\K[^;]+'")
```

---

### Phase 2 — SMTP Service Analysis (standard+)

**SMTP service detection:**
```
Bash("nmap ...")
```

**STARTTLS check:**
```
Bash("echo 'QUIT' | openssl s_client -connect MX_HOST:25 -starttls smtp -brief 2>/dev/null | head -20")
Bash("echo 'QUIT' | openssl s_client -connect MX_HOST:587 -starttls smtp -brief 2>/dev/null | head -20")
```

**Check certificate:**
```
Bash("echo 'QUIT' | openssl s_client -connect MX_HOST:25 -starttls smtp 2>/dev/null | openssl x509 -noout -subject -issuer -dates -fingerprint 2>/dev/null")
```

---

### Phase 3 — Open Relay Testing (standard+)

**Test open relay with swaks:**
```
Bash("swaks --to test@example.com --from spoofed@DOMAIN --server MX_HOST --timeout 10 2>&1 | tail -20")
```

If the mail is accepted for delivery to an external domain, this is a **Critical** finding.

---

### Phase 4 — Spoofing Resilience (standard+)

**Test email spoofing:**
```
Bash("swaks --to real-user@DOMAIN --from ceo@DOMAIN --server MX_HOST --header 'Subject: Test Spoofing Resilience' --body 'This is a spoofing test.' --timeout 10 2>&1 | tail -20")
```

**Test from external server (bypasses internal relay):**
```
Bash("swaks --to real-user@DOMAIN --from ceo@DOMAIN --header 'Subject: External Spoof Test' --body 'External spoofing test.' --timeout 10 2>&1 | tail -20")
```

---

### Phase 5 — User Enumeration (thorough)

**SMTP user enumeration:**
```
Bash("smtp-user-enum -M VRFY -U /usr/share/seclists/Usernames/top-usernames-shortlist.txt -t MX_HOST 2>/dev/null | head -30")
Bash("smtp-user-enum -M RCPT -U /usr/share/seclists/Usernames/top-usernames-shortlist.txt -D DOMAIN -t MX_HOST 2>/dev/null | head -30")
```

---

### Phase 6 — MTA-STS Policy Check (standard+)

**Fetch MTA-STS policy:**
```
Bash("curl ...")
```

**Verify:**
- Policy mode: `enforce`, `testing`, or `none`
- MX entries match actual MX records
- max_age is reasonable (86400+)

---

### Phase 7 — Report & Wrap-Up

1. Call `Write("pentest/diagrams/<title>.mmd", "<mermaid>")` with email infrastructure:
```mermaid
flowchart TD
    Sender["External Sender"] --> DNS["DNS Lookup"]
    DNS --> SPF["SPF: v=spf1 ... -all"]
    DNS --> DKIM["DKIM: selector._domainkey"]
    DNS --> DMARC["DMARC: p=reject"]
    Sender --> MX["MX: mail.domain.com"]
    MX --> TLS["STARTTLS: TLS 1.2+"]
    MX --> Filter["Spam/Phishing Filter"]
    Filter --> Inbox["User Inbox"]
    MX --> MTASTS["MTA-STS: enforce"]
```

2. Call `Bash("jq -nc --arg ts \"$(date -Iseconds)\" --arg msg '<message>' '{ts:$ts,type:\"note\",msg:$msg}' >> pentest/events.jsonl")` with email security summary:
```
Email Security Assessment Summary:
  Domain:          [domain]
  Mail provider:   [provider]
  SPF:             [status and policy]
  DKIM:            [status, selectors found]
  DMARC:           [status, policy, reporting]
  STARTTLS:        [yes/no, TLS version]
  MTA-STS:         [mode]
  Open relay:      [yes/no]
  Spoofing:        [resilient/vulnerable]
  User enumeration: [possible/blocked]
```

3. Call `Write("pentest/summary.md", "<summary>")` with summary
4. **Export GitHub Issues** — invoke the `/gh-export` skill

---

## Chaining Other Skills

| Skill | When to invoke |
|-------|----------------|
| `/osint` | Email addresses discovered — expand OSINT reconnaissance |
| `/credential-audit` | SMTP credentials needed — test authentication |
| `/ssl-tls-audit` | STARTTLS weaknesses found — deep TLS assessment |
| `/gh-export` | Always — after `Write("pentest/summary.md", "<summary>")` |

---

## Rules

- **`Bash("mkdir -p pentest/{pocs,diagrams} && touch pentest/events.jsonl") + Write("pentest/scope.json", {...})` is mandatory** — never run any other tool before it
- **Batch independent DNS lookups** — SPF, DKIM, DMARC, MTA-STS can all run in parallel
- **Test spoofing carefully** — only send test emails to authorized addresses
- **Call `Bash("jq -nc --arg ts \"$(date -Iseconds)\" --arg id 'f-001' --arg title '<title>' --arg sev 'high' --argjson leads '[{\"lead\":\"<x>\",\"status\":\"pending\"}]' '{ts:$ts,type:\"finding\",action:\"add\",id:$id,title:$title,severity:$sev,escalation_leads:$leads}' >> pentest/events.jsonl")` for every confirmed weakness** — include the DNS record and specific misconfiguration
- **SPF + DKIM + DMARC must all be present** — missing any one is a finding
- **Use `Bash("jq -nc --arg ts \"$(date -Iseconds)\" --arg msg '<message>' '{ts:$ts,type:\"note\",msg:$msg}' >> pentest/events.jsonl")` liberally** — document DNS records and analysis decisions
- **Never fabricate findings** — only report what tool output confirms
- **Mermaid syntax rules**: use `flowchart TD`, quote labels, no em-dashes, short alphanumeric node IDs
- Call `# (no-op — tools native on Kali)` at the end if `Bash(...)` was used
