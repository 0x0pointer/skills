#!/usr/bin/env bash
# Start a rootable Android emulator with the Burp Suite CA injected as a SYSTEM cert and the
# device proxy pointed at Burp. Idempotent: reuses SDK packages / AVD / running emulator.
#
#   burp-emulator.sh [--api 36] [--avd NAME] [--proxy 127.0.0.1:8080] [--cert burp.der]
#                    [--serial emulator-5554] [--inject-only] [--no-proxy] [--headless]
#                    [--wipe] [--unset-proxy]
set -euo pipefail

API=36
AVD=""
PROXY="127.0.0.1:8080"
CERT_IN=""
SERIAL=""
INJECT_ONLY=0
SET_PROXY=1
HEADLESS=0
WIPE=0
UNSET_PROXY=0
BOOT_TIMEOUT=420

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="${TMPDIR:-/tmp}/burp-emulator"
mkdir -p "$WORK"

log()  { printf '\033[1;34m[*]\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m[+]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; exit 1; }

while [ $# -gt 0 ]; do
    case "$1" in
        --api) API="$2"; shift 2 ;;
        --avd) AVD="$2"; shift 2 ;;
        --proxy) PROXY="$2"; shift 2 ;;
        --cert) CERT_IN="$2"; shift 2 ;;
        --serial) SERIAL="$2"; shift 2 ;;
        --inject-only) INJECT_ONLY=1; shift ;;
        --no-proxy) SET_PROXY=0; shift ;;
        --headless) HEADLESS=1; shift ;;
        --wipe) WIPE=1; shift ;;
        --unset-proxy) UNSET_PROXY=1; shift ;;
        -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
        *) die "unknown option: $1" ;;
    esac
done

# ---------------------------------------------------------------- SDK + Java
SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-$HOME/Library/Android/sdk}}"
[ -d "$SDK" ] || SDK="$HOME/Android/Sdk"
[ -d "$SDK" ] || die "Android SDK not found (set ANDROID_HOME)"
export ANDROID_HOME="$SDK" ANDROID_SDK_ROOT="$SDK"
ADB="$SDK/platform-tools/adb"
EMU="$SDK/emulator/emulator"
[ -x "$ADB" ] || die "adb missing at $ADB (install platform-tools via Android Studio SDK Manager)"

ensure_java() {
    java -version >/dev/null 2>&1 && return
    for j in "/Applications/Android Studio.app/Contents/jbr/Contents/Home" \
             "/Applications/Android Studio.app/Contents/jre/Contents/Home" \
             "/opt/android-studio/jbr"; do
        [ -x "$j/bin/java" ] && { export JAVA_HOME="$j" PATH="$j/bin:$PATH"; return; }
    done
    die "no Java runtime (needed by sdkmanager). Install a JDK or Android Studio."
}

ensure_cmdline_tools() {
    SDKMANAGER="$SDK/cmdline-tools/latest/bin/sdkmanager"
    AVDMANAGER="$SDK/cmdline-tools/latest/bin/avdmanager"
    [ -x "$SDKMANAGER" ] && return
    log "Installing Android cmdline-tools into $SDK/cmdline-tools/latest"
    local os; case "$(uname -s)" in Darwin) os=mac ;; Linux) os=linux ;; *) die "unsupported OS" ;; esac
    local zip
    zip=$(curl -fsSL https://dl.google.com/android/repository/repository2-3.xml \
          | grep -oE "commandlinetools-${os}-[0-9]+_latest\.zip" | sort -t- -k3 -n | tail -1)
    [ -n "$zip" ] || die "could not find cmdline-tools download"
    curl -fL# "https://dl.google.com/android/repository/$zip" -o "$WORK/$zip"
    rm -rf "$WORK/ct" && mkdir -p "$WORK/ct" "$SDK/cmdline-tools"
    unzip -q "$WORK/$zip" -d "$WORK/ct"
    rm -rf "$SDK/cmdline-tools/latest"
    mv "$WORK/ct/cmdline-tools" "$SDK/cmdline-tools/latest"
}

# ---------------------------------------------------------------- Burp cert
prepare_cert() {
    local der="$WORK/burp.der" pem="$WORK/burp.pem"
    if [ -n "$CERT_IN" ]; then
        [ -f "$CERT_IN" ] || die "cert file not found: $CERT_IN"
        if openssl x509 -inform PEM -in "$CERT_IN" -noout 2>/dev/null; then
            cp "$CERT_IN" "$pem"
        else
            openssl x509 -inform DER -in "$CERT_IN" -out "$pem" || die "cert is neither PEM nor DER"
        fi
    else
        log "Fetching Burp CA from http://$PROXY/cert"
        curl -fsS --noproxy '*' -m 10 "http://$PROXY/cert" -o "$der" \
            || die "Burp not reachable at $PROXY. Start Burp (Proxy > Options listener) or pass --cert"
        openssl x509 -inform DER -in "$der" -out "$pem" || die "downloaded file is not a certificate"
    fi
    HASH=$(openssl x509 -inform PEM -subject_hash_old -in "$pem" -noout)
    CERT_FILE="$WORK/$HASH.0"
    cp "$pem" "$CERT_FILE"
    ok "CA: $(openssl x509 -in "$pem" -noout -subject | sed 's/^subject=//')  ->  $HASH.0"
}

# ---------------------------------------------------------------- device helpers
adb_s() { "$ADB" -s "$SERIAL" "$@"; }

wait_boot() {
    local t=0
    log "Waiting for $SERIAL to boot (up to ${BOOT_TIMEOUT}s)"
    "$ADB" -s "$SERIAL" wait-for-device
    until [ "$(adb_s shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = 1 ]; do
        sleep 3; t=$((t + 3))
        [ $t -ge $BOOT_TIMEOUT ] && die "boot timeout; see $WORK/emulator.log"
    done
    ok "Booted"
}

device_proxy_addr() {
    # 10.0.2.2 is the emulator's alias for the host loopback.
    local host="${PROXY%:*}" port="${PROXY##*:}"
    case "$host" in 127.0.0.1|localhost|0.0.0.0) host=10.0.2.2 ;; esac
    echo "$host:$port"
}

pick_running_emulator() {
    "$ADB" devices | awk '/^emulator-[0-9]+\tdevice$/ {print $1}' | head -1
}

# ---------------------------------------------------------------- modes
if [ $UNSET_PROXY -eq 1 ]; then
    [ -n "$SERIAL" ] || SERIAL=$(pick_running_emulator)
    [ -n "$SERIAL" ] || die "no running emulator"
    adb_s shell settings put global http_proxy :0
    ok "Proxy cleared on $SERIAL"; exit 0
fi

prepare_cert

if [ $INJECT_ONLY -eq 1 ]; then
    [ -n "$SERIAL" ] || SERIAL=$(pick_running_emulator)
    [ -n "$SERIAL" ] || die "no running emulator for --inject-only"
else
    ARCH=$(uname -m); case "$ARCH" in arm64|aarch64) ABI=arm64-v8a ;; *) ABI=x86_64 ;; esac
    [ -n "$AVD" ] || AVD="burp_api${API}"
    PKG="system-images;android-${API};google_apis;${ABI}"

    if [ "${API%%.*}" -ge 37 ]; then
        warn "Android 17+ (API 37) enforces Certificate Transparency for apps targeting API 37."
        warn "Burp-signed certs carry no SCTs, so those apps will still reject Burp. Prefer --api 36."
    fi

    if ! "$EMU" -list-avds 2>/dev/null | grep -qx "$AVD"; then
        ensure_java; ensure_cmdline_tools
        if [ ! -d "$SDK/system-images/android-${API}/google_apis/${ABI}" ]; then
            log "Installing $PKG (one-time, ~1.5 GB)"
            yes | "$SDKMANAGER" --licenses >/dev/null 2>&1 || true
            "$SDKMANAGER" --install "$PKG" "emulator" "platform-tools" | grep -v '^\[=' || true
        fi
        log "Creating AVD $AVD"
        echo no | "$AVDMANAGER" create avd -n "$AVD" -k "$PKG" -d pixel_7 >/dev/null 2>&1 \
            || echo no | "$AVDMANAGER" create avd -n "$AVD" -k "$PKG" >/dev/null
        CFG="$HOME/.android/avd/$AVD.avd/config.ini"
        [ -f "$CFG" ] && { sed -i.bak '/^hw.keyboard=/d' "$CFG"; echo "hw.keyboard=yes" >> "$CFG"; }
        ok "AVD $AVD created"
    fi

    grep -q 'playstore' "$HOME/.android/avd/$AVD.avd/config.ini" 2>/dev/null \
        && die "$AVD uses a Play Store image: 'adb root' is blocked there. Use a google_apis AVD."

    # Reuse an emulator already running this AVD, else start one on a free port.
    for s in $("$ADB" devices | awk '/^emulator-/ {print $1}'); do
        name=$("$ADB" -s "$s" emu avd name 2>/dev/null | head -1 | tr -d '\r')
        [ "$name" = "$AVD" ] && SERIAL="$s"
    done
    if [ -z "$SERIAL" ]; then
        PORT=5554
        while "$ADB" devices | grep -q "emulator-$PORT"; do PORT=$((PORT + 2)); done
        SERIAL="emulator-$PORT"
        ARGS=(-avd "$AVD" -port "$PORT" -no-snapshot-load -no-boot-anim)
        [ $HEADLESS -eq 1 ] && ARGS+=(-no-window)
        [ $WIPE -eq 1 ] && ARGS+=(-wipe-data)
        log "Starting emulator $AVD on $SERIAL (log: $WORK/emulator.log)"
        nohup "$EMU" "${ARGS[@]}" >"$WORK/emulator.log" 2>&1 &
    else
        log "Reusing running emulator $SERIAL ($AVD)"
    fi
fi

wait_boot

log "Switching adbd to root"
adb_s root >/dev/null 2>&1 || true
sleep 2; "$ADB" -s "$SERIAL" wait-for-device
[ "$(adb_s shell id -u | tr -d '\r')" = 0 ] \
    || die "adb root refused — this image is not rootable (Play Store/production build)"

log "Injecting CA as system cert"
adb_s push "$CERT_FILE" "/data/local/tmp/$HASH.0" >/dev/null
adb_s push "$HERE/inject-ca.sh" /data/local/tmp/inject-ca.sh >/dev/null
adb_s shell sh /data/local/tmp/inject-ca.sh "/data/local/tmp/$HASH.0"

if [ $SET_PROXY -eq 1 ]; then
    DP=$(device_proxy_addr)
    adb_s shell settings put global http_proxy "$DP"
    ok "Device proxy -> $DP (Burp on host $PROXY)"
fi

echo
ok "Ready: $SERIAL  |  CA $HASH.0 trusted system-wide (until reboot)"
echo "    After a reboot re-run with: $0 --inject-only --serial $SERIAL"
echo "    Clear proxy:                $0 --unset-proxy --serial $SERIAL"
