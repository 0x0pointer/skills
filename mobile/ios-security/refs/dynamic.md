# iOS dynamic analysis — Frida/objection (needs the ios-dynamic setup gate + a JAILBROKEN device)

Gate first: `session(action="setup_gate", options={"action":"check","id":"ios-dynamic"})` must pass
(`frida-ps -U` returns processes from the device). No device → `wishlist_add` and stay on static.
iOS dynamic cannot run in a container — Frida talks to the device over USB (usbmuxd) / SSH.

## objection (the 80/20 dynamic tool)
```
kali(command="objection -g <bundle-id> explore")
# or one-shot:  objection -g <bundle-id> explore -s "ios sslpinning disable"
ios sslpinning disable                 # MASVS-NETWORK — bypass cert pinning
ios keychain dump                      # MASVS-STORAGE — dump the Keychain
ios nsuserdefaults get                 # MASVS-STORAGE — read NSUserDefaults
ios cookies get                        # session cookies
env                                    # app container paths → pull files
ios hooking watch class <Class>        # observe auth/crypto/storage calls
```

## Frida direct
```
frida -U -f <bundle-id> -l hook.js --no-pause
```
Hook `CCCrypt`, `SecItemAdd`/`SecItemCopyMatching`, `LAContext.evaluatePolicy(...)` to confirm
CRYPTO/STORAGE/AUTH findings and to bypass jailbreak/anti-debug checks (MASVS-RESILIENCE).

## Traffic capture (MASVS-NETWORK)
Disable pinning (above), set the device HTTP proxy to the intercepting proxy (Burp/mitmproxy), install
the proxy CA on the device. Captured backend endpoints → chain `/api-security`; recovered tokens land
in `known_assets.auth_tokens`.

## URL-scheme & Universal-Link abuse (MASVS-PLATFORM)
```
objection> ios ui dump                      # inspect the current screen
# trigger a custom scheme:
frida ... -e 'ObjC ... openURL:'  OR on-device: uiopen "myscheme://path?param=payload"
```
Unvalidated scheme/link handlers → navigation to attacker content, state change, or WKWebView JS-bridge abuse.

## App Store IPA decryption (enables full STATIC too)
On the jailbroken device: `frida-ios-dump` produces a decrypted IPA (`cryptid 0`) — feed it back to
`scan(tool="mobsf")` for complete static coverage. This is why full App-Store static is device-gated.

## frida client↔server coupling
The device's Frida must match the host `frida-tools` version, or you get "unable to connect"/protocol
errors. Install the matching Frida build from the Frida repo (Sileo/Cydia).
