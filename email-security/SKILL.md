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

## Tools Available

| Tool | Use for |
|------|---------|
| `start_scan` | Define target, scope, depth, and hard limits — **always call this first** |
| `complete_scan` | Mark the scan done and write final notes |
| `kali_exec` | Kali tools: swaks, dig, nmap, smtp-user-enum, openssl s_client |
| `run_nmap` | SMTP service detection and NSE scripts |
| `http_request` | Check MTA-STS policy, web-based mail config |
| `report_finding` | Log confirmed vulnerabilities to findings.json |
| `report_diagram` | Save email infrastructure diagrams |
| `start_dashboard` | Serve dashboard.html at localhost:5000 |
| `log_note` | Write reasoning notes to session log |

---

## Testing Matrix

| Category | Tests | Tools | Severity if failed |
|----------|-------|-------|--------------------|
| **SPF** | Record exists, syntax valid, not too permissive (+all), include chain | dig | High if missing/misconfigured |
| **DKIM** | Selector discovery, key size, algorithm | dig | High if missing |
| **DMARC** | Record exists, policy (none/quarantine/reject), rua/ruf reporting | dig | High if p=none or missing |
| **STARTTLS** | SMTP STARTTLS supported, certificate valid | openssl, nmap | Medium |
| **MTA-STS** | Policy published, mode (enforce/testing/none) | http_request | Low-Medium |
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

0. Call `start_scan` with target domain, depth, and limits
1. Call `start_dashboard` — live findings tracker
2. Call `log_note` — record target domain, known mail provider

---

### Phase 1 — DNS Record Analysis

Run in parallel:

```
kali(command="dig DOMAIN MX +short")
kali(command="dig DOMAIN TXT +short | grep -i spf")
kali(command="dig _dmarc.DOMAIN TXT +short")
kali(command="dig _mta-sts.DOMAIN TXT +short")
kali(command="dig _smtp._tls.DOMAIN TXT +short")
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
```
kali(command="for sel in default google selector1 selector2 k1 k2 mail dkim s1 s2; do echo -n \"$sel: \"; dig ${sel}._domainkey.DOMAIN TXT +short 2>/dev/null; done")
```

---

### Phase 2 — SMTP Service Analysis (standard+)

**SMTP service detection:**
```
scan(tool="nmap", target=MX_HOST, options={"ports": "25,465,587", "flags": "--script smtp-commands,smtp-enum-users,smtp-open-relay,smtp-ntlm-info -sV"})
```

**STARTTLS check:**
```
kali(command="echo 'QUIT' | openssl s_client -connect MX_HOST:25 -starttls smtp -brief 2>/dev/null | head -20")
kali(command="echo 'QUIT' | openssl s_client -connect MX_HOST:587 -starttls smtp -brief 2>/dev/null | head -20")
```

**Check certificate:**
```
kali(command="echo 'QUIT' | openssl s_client -connect MX_HOST:25 -starttls smtp 2>/dev/null | openssl x509 -noout -subject -issuer -dates -fingerprint 2>/dev/null")
```

---

### Phase 3 — Open Relay Testing (standard+)

**Test open relay with swaks:**
```
kali(command="swaks --to test@example.com --from spoofed@DOMAIN --server MX_HOST --timeout 10 2>&1 | tail -20")
```

If the mail is accepted for delivery to an external domain, this is a **Critical** finding.

---

### Phase 4 — Spoofing Resilience (standard+)

**Test email spoofing:**
```
kali(command="swaks --to real-user@DOMAIN --from ceo@DOMAIN --server MX_HOST --header 'Subject: Test Spoofing Resilience' --body 'This is a spoofing test.' --timeout 10 2>&1 | tail -20")
```

**Test from external server (bypasses internal relay):**
```
kali(command="swaks --to real-user@DOMAIN --from ceo@DOMAIN --header 'Subject: External Spoof Test' --body 'External spoofing test.' --timeout 10 2>&1 | tail -20")
```

---

### Phase 5 — User Enumeration (thorough)

**SMTP user enumeration:**
```
kali(command="smtp-user-enum -M VRFY -U /usr/share/seclists/Usernames/top-usernames-shortlist.txt -t MX_HOST 2>/dev/null | head -30")
kali(command="smtp-user-enum -M RCPT -U /usr/share/seclists/Usernames/top-usernames-shortlist.txt -D DOMAIN -t MX_HOST 2>/dev/null | head -30")
```

---

### Phase 6 — MTA-STS Policy Check (standard+)

**Fetch MTA-STS policy:**
```
http_request(url="https://mta-sts.DOMAIN/.well-known/mta-sts.txt", method="GET")
```

**Verify:**
- Policy mode: `enforce`, `testing`, or `none`
- MX entries match actual MX records
- max_age is reasonable (86400+)

---

### Phase 7 — Report & Wrap-Up

1. Call `report_diagram` with email infrastructure:
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

2. Call `log_note` with email security summary:
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

3. Call `complete_scan` with summary
4. **Export GitHub Issues** — invoke the `/gh-export` skill

---

## Chaining Other Skills

| Skill | When to invoke |
|-------|----------------|
| `/osint` | Email addresses discovered — expand OSINT reconnaissance |
| `/credential-audit` | SMTP credentials needed — test authentication |
| `/ssl-tls-audit` | STARTTLS weaknesses found — deep TLS assessment |
| `/gh-export` | Always — after `complete_scan` |

---

## Rules

- **`start_scan` is mandatory** — never run any other tool before it
- **Batch independent DNS lookups** — SPF, DKIM, DMARC, MTA-STS can all run in parallel
- **Test spoofing carefully** — only send test emails to authorized addresses
- **Call `report_finding` for every confirmed weakness** — include the DNS record and specific misconfiguration
- **SPF + DKIM + DMARC must all be present** — missing any one is a finding
- **Use `log_note` liberally** — document DNS records and analysis decisions
- **Never fabricate findings** — only report what tool output confirms
- **Mermaid syntax rules**: use `flowchart TD`, quote labels, no em-dashes, short alphanumeric node IDs
- Call `stop_kali` at the end if `kali_exec` was used
