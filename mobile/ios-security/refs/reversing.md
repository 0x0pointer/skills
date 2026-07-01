# iOS reversing quick reference (Kali container)

## Extract
`unzip <app>.ipa` → `Payload/<App>.app/`. The Mach-O executable is `<App>.app/<App>` (no extension).

## Inspect the Mach-O
- `class-dump <binary>` → Obj-C interfaces (class/method names) — the map for Frida hooks. (Swift-only
  binaries expose little via class-dump; lean on `strings`, symbols, and MobSF.)
- `otool -L <binary>` → linked dylibs/frameworks (third-party pods → known-CVE check).
- `otool -l <binary> | grep -A4 LC_ENCRYPTION_INFO` → `cryptid` (1 = FairPlay-encrypted).
- `otool -hv <binary>` → PIE/ARC/stack-canary flags.
- `nm -u <binary>` / `strings -a <binary>` → imported symbols, endpoints, secrets, debug strings.

## Swift specifics
Swift symbols are mangled — `swift-demangle` to read them. Much logic is inlined; MobSF + strings +
runtime hooks (Frida) usually beat static disassembly for Swift apps.

## Decrypt an App Store binary (needs jailbroken device)
`frida-ios-dump` (or `bagbak`/`flexdecrypt`) on the device produces a decrypted IPA (`cryptid 0`).
Only then does `class-dump`/MobSF see the real code. Without decryption, static coverage is partial —
say so in findings.

## Frameworks / plugins / extensions
Analyze `<App>.app/Frameworks/*.framework`, `PlugIns/*.appex` (share/notification/widget extensions),
and `WatchKit` payloads — each is its own binary + Info.plist with its own attack surface.

## Deep disassembly
For hard targets, load the Mach-O in Ghidra/radare2 (`r2 -A`) for JNI/ObjC-runtime call analysis and
hardcoded-secret hunting.
