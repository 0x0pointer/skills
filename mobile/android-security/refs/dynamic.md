# Android dynamic analysis — Frida/objection (needs the android-dynamic setup gate)

Gate first: `session(action="setup_gate", options={"action":"check","id":"android-dynamic"})` must
pass (`frida-ps -U` returns processes) before running anything here. No device → `wishlist_add` and
stay on static; never stall.

## adb transport (Kali container → device)
The Kali container has its own adb server. Reach an emulator/device the operator exposed:
- `kali(command="adb connect host.docker.internal:5555")` (host emulator; kali_runner rewrites 127.0.0.1→host.docker.internal), then `adb devices`.
- Or a physical device on the LAN: `adb connect <device-ip>:5555`.

## objection (Frida wrapper — the 80/20 dynamic tool)
```
kali(command="objection -g <package> explore")
# inside the session (or via -s 'cmd'):
android sslpinning disable                 # MASVS-NETWORK — bypass cert pinning
android keystore list                      # MASVS-STORAGE/CRYPTO — dump KeyStore
android hooking watch class <class>        # observe auth/crypto calls
memory dump all /tmp/mem.bin               # scrape secrets from heap
```
- `objection ... -s "android sslpinning disable"` runs a one-shot hook — good for scripted use via `kali()`.

## Frida direct (targeted hooks)
```
frida -U -f <package> -l hook.js --no-pause
```
Hook `javax.crypto.Cipher`, `SharedPreferences$Editor`, custom auth methods to confirm CRYPTO/AUTH findings.

## Traffic capture
Disable pinning (above), then route through the intercepting proxy (Burp/mitmproxy). Backend
endpoints captured here → chain `/api-security`. Set the device proxy or use `adb reverse`.

## IPC / deeplink abuse (MASVS-PLATFORM) — often no root needed
```
adb shell am start -a android.intent.action.VIEW -d "<scheme>://<host>/<path>"   # deeplink
adb shell am start -n <package>/<exported.Activity> --es key value                # exported activity
adb shell am broadcast -n <package>/<exported.Receiver> ...                        # exported receiver
content query --uri content://<exported.provider>/...                             # exported provider → possible SQLi
```

## Hybrid / WebView apps (Cordova/Ionic/Capacitor/RN-WebView)
The security surface is the WebView DOM. Drive it via Playwright-Android over adb (Chrome/WebView
DevTools protocol) from `kali()` — the same adb transport + this setup gate. Native UI automation
(mobile-mcp, if wired) drives native flows; Playwright drives the WebView.

## frida client↔server version coupling
The device's `frida-server` MUST match the Kali container's `frida-tools` (pinned 12.5.x → frida 16.x).
A mismatch yields "unable to connect"/protocol errors — push the matching `frida-server` release.
