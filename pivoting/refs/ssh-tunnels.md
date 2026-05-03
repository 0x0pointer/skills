### Ref: SSH tunneling

**Root pattern:** OpenSSH carries a tunneling sublanguage that does the same job as chisel/ligolo-ng for any environment where sshd is reachable and you have valid credentials. Three flag families cover ~95% of pivot use cases — `-L` for "I want to reach a service through the pivot", `-R` for "I want the pivot to reach a service on me", `-D` for "I want a SOCKS proxy" — plus `ProxyJump` for chaining bastions and `sshuttle`/`-w` for VPN-like layer-3 reach. Use SSH tunnels when sshd + creds are both available; the tunnels survive `ControlMaster` reuse, persist trivially via `~/.ssh/config`, and leave nothing on disk on the pivot beyond the standard auth.log entry.

**When to use:**
- The pivot has reachable sshd (inbound from attacker, OR outbound from pivot back to attacker)
- You have valid creds (password, key, or Kerberos ticket)
- You want a tunnel that doesn't require dropping a binary on the pivot

**When NOT to use:**
- sshd unreachable / no creds → use chisel
- Need ICMP, UDP, or layer-3 (without `-w` + `PermitTunnel`, which is rarely enabled) → use ligolo-ng or sshuttle
- You need to evade auth.log and process listings — every ssh session is logged

---

#### Local forward (`-L LPORT:RHOST:RPORT`)

**Direction:** attacker → pivot → internal service. Listens on the **attacker** side; forwards each new connection through the ssh tunnel and out to `RHOST:RPORT` from the pivot.

```
# Single internal service:
Bash("ssh -L 1433:db01.internal:1433 user@PIVOT -N -f -o ServerAliveInterval=30")
Bash("impacket-mssqlclient sa:'PASSWORD'@127.0.0.1")

# Multi-port in one ssh session (each -L adds a listener):
Bash("ssh -L 1433:db:1433 -L 3306:mysql:3306 -L 5432:postgres:5432 user@PIVOT -N -f")

# Bind on non-loopback so other hosts on the attacker's segment can use the forward:
Bash("ssh -L 0.0.0.0:1433:db:1433 user@PIVOT -N -f")
# Requires `GatewayPorts clientspecified` (or `yes`) in the attacker's local sshd_config — irrelevant
# unless the attacker's sshd is mediating; for local ssh client there's no extra config needed.
```

Background flag breakdown:
- `-N` — don't run a remote command (we want the tunnel only)
- `-f` — fork to background after auth
- `-o ServerAliveInterval=30` — send a keepalive every 30s; without this, NAT/firewall idle-timeouts kill long-lived tunnels

---

#### Remote forward (`-R RPORT:LHOST:LPORT`)

**Direction:** pivot → attacker. Listens on the **pivot** side (or anywhere `GatewayPorts` allows); forwards each connection back through the tunnel to `LHOST:LPORT` reachable from the attacker.

```
# Expose the attacker's local web server (port 80) to the pivot's loopback on port 8080:
Bash("ssh -R 8080:127.0.0.1:80 user@PIVOT -N -f -o ServerAliveInterval=30")
# On the pivot:  curl http://127.0.0.1:8080/  → reaches attacker:80
```

**`GatewayPorts` gotcha** — by default, `-R` binds the listener on the pivot's loopback only. Internal hosts (other than the pivot itself) cannot reach it. To bind on the pivot's external interface so other internal hosts can call it, the **pivot's** `/etc/ssh/sshd_config` must have:
```
GatewayPorts yes
# or for client-controlled bind:
GatewayPorts clientspecified
```
Then:
```
Bash("ssh -R 0.0.0.0:8080:127.0.0.1:80 user@PIVOT -N -f")
# Now any internal host can reach the attacker's web server at PIVOT_INTERNAL:8080
```
You usually can't change sshd_config on a pivot you don't own — if `GatewayPorts` is off, switch to chisel reverse mode (which doesn't have this restriction).

---

#### Dynamic forward / SOCKS5 (`-D LPORT`)

**Direction:** attacker → pivot → anything reachable from the pivot. Listens on the **attacker** side as a SOCKS proxy; per-connection target is decided by the SOCKS client (proxychains, browser, curl `--socks5`).

```
Bash("ssh -D 1080 user@PIVOT -N -f -o ServerAliveInterval=30")

# Then via proxychains4:
Bash("proxychains4 nmap -sT -Pn --top-ports 100 INTERNAL_NET/24")

# Or directly via curl:
Bash("curl -sS --socks5 127.0.0.1:1080 http://internal-app/")
```

OpenSSH's `-D` provides SOCKS4 *and* SOCKS5 — proxychains negotiates SOCKS5 by default. If the proxychains config is set to `socks4`, change it to `socks5` for IPv6 / hostname-resolution support (`proxy_dns` in proxychains4.conf relies on SOCKS5 hostname resolution).

When to prefer `-D` over chisel: sshd reachable + creds available, and you want zero binaries on the pivot.

---

#### Reverse dynamic SOCKS (`-R 1080`)

**Direction:** pivot → attacker → anything. Less common — used when the **pivot** wants SOCKS egress *out through the attacker* (e.g., the pivot has very limited tools but reaches an interesting external resource). Requires a SOCKS server running on the attacker side.

```
# Attacker — run a SOCKS server (microsocks is small and stateless):
Bash("apt install -y microsocks")
Bash("tmux new-session -d -s socks 'microsocks -i 127.0.0.1 -p 1080'")

# Pivot — forward attacker's SOCKS into the pivot's loopback:
ssh -R 1080:127.0.0.1:1080 user@ATTACKER -N -f -o ServerAliveInterval=30
# (this command runs FROM the pivot)

# Pivot now has a SOCKS5 listener at 127.0.0.1:1080 that egresses via the attacker
```

Use this when an internal-only pivot needs to reach an external service for staging (e.g., download a tool from GitHub through the attacker's egress).

---

#### Jump host / multi-hop (`-J` / `ProxyJump`)

Chain through one or more bastions without nested ssh calls. Modern, supersedes the legacy `ProxyCommand nc %h %p` pattern.

```
# Inline:
Bash("ssh -J user@bastion1,user@bastion2 user@final-target")

# Or persist in ~/.ssh/config:
cat >> ~/.ssh/config <<'EOF'
Host bastion1
    HostName 10.0.0.10
    User pivot

Host internal
    HostName 192.168.50.20
    User admin
    ProxyJump bastion1
EOF
# Then:  ssh internal
```

`ProxyJump` opens an ssh connection to each hop in turn and chains the `stdin`/`stdout` of each into the next; auth happens against each hop in order. You can combine `-J` with `-L`/`-R`/`-D` — e.g., `ssh -J bastion1 -L 1433:db:1433 user@internal -N -f` opens a local forward on the attacker that goes attacker → bastion1 → internal → db.

`ProxyCommand` (the legacy form) is still useful when the bastion has no sshd and you can only reach the final host via an HTTP CONNECT proxy or netcat relay:
```
Host internal
    ProxyCommand corkscrew proxy.corp.com 8080 %h %p
```

---

#### `ssh_config` persistence + `ControlMaster`

`ControlMaster` reuses one TCP+auth handshake for many subsequent ssh invocations — every new `ssh user@pivot` (and every `-L`/`-R`/`-D` you add later) shares the same multiplexed connection. Critical for engagements: you authenticate once and add tunnels on demand without re-typing creds or burning the auth.log.

```
cat >> ~/.ssh/config <<'EOF'
Host pivot
    HostName PIVOT_IP
    User user
    IdentityFile ~/.ssh/engagement_key
    ControlMaster auto
    ControlPath ~/.ssh/cm-%r@%h:%p
    ControlPersist 10m
    ServerAliveInterval 30
EOF

# First call creates the master:
ssh pivot true

# Subsequent calls reuse it — no new auth, no new auth.log entry on the pivot:
ssh -O forward -L 1433:db:1433 pivot       # add a forward dynamically
ssh -O forward -L 3306:mysql:3306 pivot    # add another
ssh -O cancel  -L 1433:db:1433 pivot       # remove a forward
ssh -O check   pivot                       # is the master still alive?
ssh -O exit    pivot                       # close the master
```

`ssh -O forward` adds tunnels to a running master without spawning a new ssh process. Pair with `ControlPersist 10m` so the master stays up for 10 minutes of inactivity.

---

#### TUN/TAP layer-3 (`-w local:remote`)

The closest SSH gets to ligolo-ng — a real layer-3 TUN tunnel between attacker and pivot. **Almost never available** in production: `PermitTunnel yes` must be set in the pivot's sshd_config and you usually need root on the pivot to bring up the interface. Useful in lab/CTF environments where you control sshd.

```
# Pivot (one-time): /etc/ssh/sshd_config
#   PermitTunnel yes
#   systemctl restart sshd

# Attacker:
Bash("ssh -w 0:0 user@PIVOT -o Tunnel=point-to-point")
# Inside the ssh session, on the pivot:
ip link set tun0 up
ip addr add 10.99.99.2/30 dev tun0
ip route add INTERNAL_NET/CIDR dev tun0

# On the attacker, in another shell:
ip link set tun0 up
ip addr add 10.99.99.1/30 dev tun0
```

If you need L3 and don't control sshd, use ligolo-ng instead — it does the same thing with one binary and no sshd_config change.

---

#### sshuttle — "poor man's VPN"

`sshuttle` wraps SSH and patches in iptables (Linux) or pf (macOS) rules on the **attacker** side to redirect packets destined for chosen CIDRs through an SSH connection to the pivot. No proxychains, no per-tool config — every tool just works against the internal network. It does NOT need root on the pivot, and it does NOT need any binary dropped on the pivot — only python on the pivot side (which is almost always there).

```
# Single CIDR:
Bash("sshuttle -r user@PIVOT 10.10.0.0/16")

# Multiple CIDRs:
Bash("sshuttle -r user@PIVOT 10.10.0.0/16 192.168.50.0/24")

# Route DNS through the pivot too (resolves internal hostnames):
Bash("sshuttle -r user@PIVOT 10.10.0.0/16 --dns")

# Auto-detect CIDRs from the pivot's routing table:
Bash("sshuttle -r user@PIVOT --auto-nets --dns")
```

`sshuttle` runs in the foreground by default — start it in a tmux session if you need other commands while it's up:
```
Bash("tmux new-session -d -s sshuttle 'sshuttle -r user@PIVOT 10.10.0.0/16 --dns'")
```

**vs `ssh -D` + proxychains:** sshuttle is faster (no per-connection SOCKS handshake), supports DNS routing natively, and any tool works without per-tool wrapping. **vs ligolo-ng:** sshuttle requires sshd + creds; ligolo-ng works with any callback channel. Trade-off: sshuttle modifies iptables on the attacker (visible to host EDR running on the *attacker*'s box, which usually doesn't matter).

---

#### Agent forwarding (`-A`)

`-A` forwards the attacker's `ssh-agent` socket to the pivot, so any further ssh calls from the pivot use the attacker's keys. **Useful for multi-hop without nested keys**, **dangerous on shared/untrusted pivots** — a root attacker on the pivot can impersonate the attacker for as long as the agent socket is alive.

Hygiene:
- Only forward the agent when chaining to a host you control next
- Prefer `ProxyJump` (which doesn't expose the agent socket on intermediate hops) over `-A`
- Use `IdentitiesOnly yes` + a per-engagement key in `ssh_config`, never reuse personal keys
- Tear down the agent when done: `ssh-add -D` (delete all keys) or kill `ssh-agent`

---

#### Quick lookup — pick the right form

| Goal | Form |
|------|------|
| Reach one internal TCP port | `ssh -L LPORT:RHOST:RPORT user@PIVOT -N -f` |
| Expose attacker service to pivot | `ssh -R RPORT:127.0.0.1:LPORT user@PIVOT -N -f` (+ `GatewayPorts yes` for non-loopback) |
| Wrap many tools through pivot (TCP only) | `ssh -D 1080 user@PIVOT -N -f` + proxychains4 |
| Wrap many tools through pivot (incl. DNS, no proxychains) | `sshuttle -r user@PIVOT CIDR --dns` |
| Chain through bastions | `ssh -J u@b1,u@b2 user@target` or `ProxyJump` in `~/.ssh/config` |
| Full L3 reach (lab only) | `ssh -w 0:0` + `PermitTunnel yes` (or use ligolo-ng) |
| Reuse one auth across many tunnels | `ControlMaster auto` + `ControlPersist 10m` + `ssh -O forward` |
