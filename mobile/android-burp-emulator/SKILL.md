---
name: android-burp-emulator
description: Start a rooted Android emulator with the Burp Suite CA injected as a trusted SYSTEM certificate (Android 14+ APEX/Conscrypt bind-mount technique) and the device proxy pointed at Burp, so all app HTTPS traffic can be intercepted / man-in-the-middled. Use this whenever the user wants to proxy, intercept, MITM or inspect Android app or emulator traffic through Burp (or another intercepting proxy like mitmproxy/ZAP/Caido), install a Burp/proxy CA cert on an emulator or AVD, fix "cert not trusted" / SSLHandshakeException when proxying an Android app, re-inject the cert after an emulator reboot, or set up the dynamic-analysis device for a mobile pentest — even if they don't say "system certificate" or "emulator" explicitly.
argument-hint: "[--api 36] [--proxy 127.0.0.1:8080] [--cert burp.der] [--inject-only] [--headless]"
user-invocable: true
---

# Android emulator + Burp system CA

Goal: one command that leaves the user with a booted emulator where **every app** trusts Burp's CA and traffic flows through Burp.

## Why it's done this way (so you can troubleshoot)

- **User CAs are useless** — since Android 7 apps ignore user-installed CAs unless they opt in. The cert must go in the **system** store, which needs root.
- **Root needs a `google_apis` image.** `google_apis_playstore` images are production builds; `adb root` is refused. The script refuses Play Store AVDs for that reason.
- **Android 14+ moved CAs into APEX** (`/apex/com.android.conscrypt/cacerts`): read-only, and mounted with PRIVATE propagation, so a remount in the adb shell is invisible to apps. The fix (from HTTP Toolkit's [Android 14 post](https://httptoolkit.com/blog/android-14-install-system-ca-certificate/)): put the CAs + Burp's in a tmpfs over `/system/etc/security/cacerts`, then `nsenter` into the **Zygote's** mount namespace (all future apps) and **each running app's** namespace (existing apps) and bind-mount it over the APEX path. No reboot needed. It's **temporary**: a reboot drops it, just re-inject.
- **Android 17 (API 37) needs Certificate Transparency.** Apps targeting API 37 on Android 17 reject certs that have no SCTs, and Burp's leaf certs have none. So injecting the CA isn't enough there. **Default to API 36**, and only use 37 if the user explicitly needs it (then explain the CT caveat; only HTTP Toolkit currently fakes CT logs).
- **Proxy address:** inside the emulator `10.0.2.2` is the host's loopback, so Burp's default `127.0.0.1:8080` listener works with no extra Burp config.

## Workflow

The bundled script does everything idempotently: it installs cmdline-tools/system image if missing (it uses Android Studio's bundled Java when there's no system JDK), creates the AVD, boots it, roots adbd, fetches Burp's cert from `http://<proxy>/cert`, converts it to `<subject_hash_old>.0`, injects it, verifies it from **inside an app's namespace**, and sets the global HTTP proxy.

1. **Check Burp is listening:** `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/cert` should return `200`. If not, ask the user to start Burp, or get the listener address / an exported cert (`--cert file.der|pem`).
2. **Run it** (first run downloads ~1.5 GB, so tell the user and use a long timeout or run it in the background):
   ```bash
   bash <this-skill-dir>/scripts/burp-emulator.sh            # API 36, AVD burp_api36
   ```
   `<this-skill-dir>` is wherever this SKILL.md was installed (e.g. `~/.claude/skills/android-burp-emulator`, `~/.config/opencode/skills/android-burp-emulator`, or `mobile/android-burp-emulator` in the skills repo).
   Options: `--api N`, `--avd NAME`, `--proxy host:port`, `--cert path`, `--headless`, `--wipe`, `--no-proxy`, `--serial emulator-XXXX`.
3. **Read the output.** Success means `OK: <hash>.0 visible in app namespace` followed by `Ready: emulator-XXXX`. Any `[x]` line is a hard stop; see Troubleshooting below.
4. **Verify traffic actually lands in Burp.** Have the user open an app (or drive one: `adb -s <serial> shell am start -a android.intent.action.VIEW -d https://example.com`). If the Burp MCP tools are available, use `get_proxy_http_history` to confirm requests show up with decrypted HTTPS. "Cert injected" alone doesn't prove the setup works; only intercepted traffic does.
5. **Tell the user** the serial, the CA hash, that injection resets on reboot, and the follow-up commands below.

### Follow-ups

| Situation | Command |
|---|---|
| Emulator rebooted / cert gone | `burp-emulator.sh --inject-only --serial emulator-XXXX` |
| Already have a rooted emulator running | `burp-emulator.sh --inject-only` |
| Stop proxying | `burp-emulator.sh --unset-proxy --serial emulator-XXXX` |
| Burp on a different port / remote host | `--proxy 192.168.1.10:8081` |
| Proxy not Burp (mitmproxy, ZAP, Caido) | `--cert ~/.mitmproxy/mitmproxy-ca-cert.pem --proxy 127.0.0.1:8080` |

## Troubleshooting

- **`adb root refused`**: the image is a Play Store or user build. Make a `google_apis` AVD (the script does this by default; don't pass `--avd` pointing at a Play Store AVD).
- **Traffic shows in Burp but the app fails TLS**: that's likely **certificate pinning**, not the CA. This needs Frida/objection (`objection -g <pkg> explore --startup-command "android sslpinning disable"`), which belongs to `/android-security`'s dynamic phase.
- **App ignores the proxy entirely** (Flutter, some games, raw sockets): the global `http_proxy` setting is only honoured by proxy-aware stacks. Options: start the emulator with `-http-proxy` (edit the launch, and drop the global setting so it doesn't double-proxy), or Burp invisible proxying + iptables redirect on the device.
- **Android 17 / API 37 `Certificate transparency failed` / `NOT_ENOUGH_SCTS`**: expected (see above). Use API ≤ 36.
- **Chrome warns but other apps work**: Chrome has its own root store and CT policy. Test with a non-Chrome app, or launch Chrome with `--ignore-certificate-errors-spki-list` via `/data/local/tmp/chrome-command-line`.
- **Boot timeout**: check `$TMPDIR/burp-emulator/emulator.log`. Usually there's no hardware acceleration or the AVD is already locked by another instance.

## Files

- `scripts/burp-emulator.sh`: host-side orchestrator (SDK bootstrap → AVD → boot → root → inject → proxy).
- `scripts/inject-ca.sh`: device-side injector (tmpfs + Zygote/app-namespace bind mounts; falls back to the plain system dir on Android < 14). Can be pushed and run by hand: `adb push ... && adb shell sh /data/local/tmp/inject-ca.sh /data/local/tmp/<hash>.0`.
