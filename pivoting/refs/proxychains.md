### Ref: proxychains4

**Root pattern:** proxychains4 hooks each TCP connection a target program tries to make and reroutes it through one or more SOCKS/HTTP proxies. It's the standard way to get pre-existing tools (nmap, smbclient, impacket, curl, evil-winrm) to traverse a SOCKS tunnel without recompiling them. Use proxychains whenever the tunnel exposes a SOCKS5/SOCKS4/HTTP-CONNECT proxy (chisel reverse SOCKS, `ssh -D`, msf `socks_proxy`); skip it entirely when ligolo-ng/sshuttle is in play because the OS routing table handles those.

**When to use:**
- Tunnel exposes a SOCKS proxy on the attacker (chisel `R:1080:socks`, `ssh -D 1080`, msf `socks_proxy`)
- You want to wrap a TCP-only tool with no SOCKS support of its own
- You want to chain *multiple* SOCKS hops (multi-pivot)

**When NOT to use:**
- The tunnel is layer-3 (ligolo-ng TUN, sshuttle, SSH `-w`) — proxychains adds overhead with no benefit
- The tool needs UDP (DNS to internal resolvers, NFS, SNMP) — proxychains can't carry UDP
- The tool needs ICMP (`ping`, `nmap -sP`, traceroute) — proxychains can't carry ICMP either
- The tool already speaks SOCKS natively (`curl --socks5`, `nmap --proxy`) — use that, it's faster

---

**Step 1 — Locate and back up the config:**

The config file is `/etc/proxychains4.conf` on Kali (sometimes `/etc/proxychains.conf` on older distros — `which proxychains4 && proxychains4 --help` will tell you which build you have).

```
Bash("[ -f /etc/proxychains4.conf.bak ] || sudo cp /etc/proxychains4.conf /etc/proxychains4.conf.bak")
Bash("ls -la /etc/proxychains4.conf*")
```

The `.bak` lets Phase 13 cleanup restore the original — restore it before declaring the engagement complete.

**Step 2 — Append the proxy entry** (idempotent — only adds if not already present):
```
Bash("grep -q '^socks5 127.0.0.1 1080' /etc/proxychains4.conf || echo 'socks5 127.0.0.1 1080' | sudo tee -a /etc/proxychains4.conf")
Bash("tail -10 /etc/proxychains4.conf")
```

The proxy line format is: `<type> <host> <port> [user] [pass]` — e.g. `socks5 127.0.0.1 1080`, `http 10.0.0.5 8080 user pass`.

**Step 3 — Pick the chain type** at the top of the config (uncomment exactly one):
```
# strict_chain      # ALL listed proxies in order, fail if any are down — use for single-proxy and verified multi-hop
# dynamic_chain     # All listed proxies in order, skip dead ones — convenient but unpredictable in multi-hop
# random_chain      # Random subset of listed proxies — only useful for evading per-IP rate limits
```

For typical single-pivot work: `strict_chain`. For multi-hop: still `strict_chain`, fixed order.

---

**Step 4 — Run a tool through proxychains:**

```
# Quiet mode strips the [proxychains] DNS-resolution noise from output
Bash("proxychains4 -q nmap -sT -Pn --top-ports 100 INTERNAL_HOST")
Bash("proxychains4 -q smbclient -L //INTERNAL_HOST -U user%pass")
Bash("proxychains4 -q impacket-secretsdump DOMAIN/USER:'PASS'@INTERNAL_DC")
Bash("proxychains4 -q curl -sS http://internal-app/")
```

**Why `nmap -sT -Pn` (TCP connect + no ping)** — the default `-sS` SYN scan uses raw sockets that proxychains can't hook; `-Pn` skips the ICMP ping prefix that also can't traverse SOCKS. **Always pass `-sT -Pn` to nmap through proxychains** or you'll get cryptic "no route to host" errors.

---

**Multi-hop chain** (attacker → pivot1 → pivot2 → final-target):

After standing up the second SOCKS (see SKILL.md Phase 10), edit `/etc/proxychains4.conf` to list both proxies in order:
```
strict_chain
proxy_dns
[ProxyList]
socks5 127.0.0.1 1080            # first hop — attacker → pivot1
socks5 127.0.0.1 1081            # second hop — attacker port that pivot1 forwards to pivot2's SOCKS
```

`strict_chain` walks proxies top-to-bottom for every connection; the first proxy receives the connection from the local tool, asks the second proxy to reach the final target, and so on. Test the chain with `proxychains4 -q curl --max-time 10 http://FINAL_TARGET/` — if it hangs, one of the hops is broken.

---

**`proxy_dns` — what it does and pitfalls**

`proxy_dns` (enabled by default) resolves hostnames *through* the proxy instead of locally. With it enabled, `proxychains4 nmap internal-app` resolves `internal-app` against the pivot's DNS, which is usually what you want — internal hostnames don't resolve on the attacker.

It only works against SOCKS5 proxies that support hostname resolution. SOCKS4 and HTTP proxies fall back to local DNS. Verify resolution with:
```
Bash("proxychains4 -q dig @INTERNAL_DNS_IP internal.host.local")
# Or simpler — does the tool reach the host?
Bash("proxychains4 -q curl --max-time 5 http://internal.host.local/")
```

If `proxy_dns` is causing weird hangs, comment it out and pre-resolve with `nslookup` against the pivot, then use IPs directly.

---

**`quiet_mode`** — append at the top of the file to silence per-connection logs:
```
quiet_mode
```
Equivalent to passing `-q` on every invocation. Disable when debugging — proxychains' verbose output tells you which proxy in the chain failed.

---

**`tcp_read_time_out` / `tcp_connect_time_out`** — bump these for high-latency tunnels:
```
tcp_read_time_out 30000     # 30s (default is 15s)
tcp_connect_time_out 8000   # 8s  (default is 8s)
```

Useful when tunneling over a slow chisel HTTPS link or across multiple geographic hops.

---

**Common pitfalls:**

| Symptom | Cause | Fix |
|---------|-------|-----|
| `connection refused` from every connection | SOCKS listener not actually up | `ss -tlnp \| grep 1080` on the attacker — restart chisel/ssh -D |
| nmap reports all ports `filtered` | Used `-sS` (SYN scan) | Switch to `-sT -Pn` (TCP connect, no ping) |
| Hostnames don't resolve | `proxy_dns` disabled OR proxy is SOCKS4 | Use SOCKS5; or pre-resolve with `nslookup INTERNAL_DNS` |
| Long hang on every connection | Default timeout too short for the tunnel RTT | Bump `tcp_connect_time_out` and `tcp_read_time_out` |
| Tool needs UDP — fails silently | proxychains can't carry UDP | Switch the whole pivot to ligolo-ng |
| Tool needs ICMP — `ping` shows 100% loss | proxychains can't carry ICMP | ditto |
| Tool segfaults under proxychains | Tool uses raw sockets / linked statically | ditto, or run the tool natively from the pivot itself |

---

**Quick lookup — when to switch tools**

| You need… | Use this instead of proxychains |
|-----------|--------------------------------|
| UDP scan, NFS mount, internal DNS lookup | ligolo-ng |
| Native nmap SYN scan, OS detection, ICMP | ligolo-ng or sshuttle |
| Tool already supports SOCKS (`curl --socks5`, `git -c http.proxy=socks5://…`) | The tool's native flag |
| Browser only — no other tools | FoxyProxy / browser SOCKS settings (no global config touch needed) |

---

**Cleanup checklist:**
```
# Restore the original config:
Bash("[ -f /etc/proxychains4.conf.bak ] && sudo mv /etc/proxychains4.conf.bak /etc/proxychains4.conf && tail -5 /etc/proxychains4.conf")
```

Append a `note` event confirming the restore.
