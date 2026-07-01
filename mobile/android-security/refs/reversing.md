# Android reversing quick reference (Kali container)

## Decompile / disassemble
- `jadx -d /tmp/out <app>.apk` — DEX → readable Java (best first read). `jadx-gui` not needed headless.
- `apktool d <app>.apk -o /tmp/apk` — smali + decoded resources + AndroidManifest.xml (the authoritative manifest).
- `d2j-dex2jar <app>.apk -o /tmp/app.jar` — DEX → JAR for other Java tooling.

## Repackaging (to test tamper/anti-repackaging — MASVS-RESILIENCE)
```
apktool b /tmp/apk -o /tmp/patched.apk
# align + sign (debug key) so it installs:
zipalign -p 4 /tmp/patched.apk /tmp/aligned.apk
apksigner sign --ks ~/.android/debug.keystore --ks-pass pass:android /tmp/aligned.apk
```
If it installs and runs, integrity/signature checks are absent or bypassable.

## React Native / Hermes
- Classic RN: `assets/index.android.bundle` is JS — read it directly (often full of logic + endpoints).
- Hermes bytecode (`.hbc` / a binary bundle): use `hbctool` / `hermes-dec` to disassemble (not in the base image — install ad hoc). Flag RN apps in findings so the reviewer knows the bytecode caveat.

## Flutter
Logic compiles to native `libapp.so` (Dart AOT) — reverse with `reflutter`/`blutter` if needed; most
value is still in the manifest, network config, and any embedded secrets.

## Native libs
`libs/<abi>/*.so` — `strings`, `nm`, and (if warranted) Ghidra/radare2 for JNI-exposed logic and
hardcoded secrets.

## Multi-APK / split APKs
`adb shell pm path <pkg>` lists `base.apk` + `split_*.apk`; pull and analyze all — code/resources are
split across them.
