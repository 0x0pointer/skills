#!/system/bin/sh
# Device-side: inject a CA cert into the Android system trust store (temporary, until reboot).
# Runs as root on the emulator. Usage: sh inject-ca.sh /data/local/tmp/<subject_hash_old>.0
#
# Technique from https://httptoolkit.com/blog/android-14-install-system-ca-certificate/
#  - tmpfs over /system/etc/security/cacerts holding the original CAs + ours
#  - Android 14+: certs actually live in the immutable, PRIVATE-propagation APEX mount
#    /apex/com.android.conscrypt/cacerts, so we bind-mount our tmpfs over it inside the
#    Zygote's mount namespace (new apps) and every running app's namespace (existing apps).

set -u
CERT="${1:?usage: inject-ca.sh <path-to-hash.0>}"
NAME=$(basename "$CERT")
SYS=/system/etc/security/cacerts
APEX=/apex/com.android.conscrypt/cacerts

[ "$(id -u)" = 0 ] || { echo "ERROR: not root (need a google_apis image + 'adb root')"; exit 1; }
[ -f "$CERT" ] || { echo "ERROR: cert $CERT not found"; exit 1; }

# Source of the current trusted CAs: APEX on 14+, the system dir before that.
if [ -d "$APEX" ]; then SRC=$APEX; else SRC=$SYS; fi

TMP=/data/local/tmp/tmp-ca-copy
rm -rf "$TMP"; mkdir -p -m 700 "$TMP"
cp "$SRC"/* "$TMP"/

# Re-running: drop our previous tmpfs in this namespace so mounts don't pile up.
if grep -q " $SYS tmpfs " /proc/mounts; then umount "$SYS" 2>/dev/null; fi

mount -t tmpfs tmpfs "$SYS" || { echo "ERROR: tmpfs mount failed"; exit 1; }
mv "$TMP"/* "$SYS"/
cp "$CERT" "$SYS/$NAME"
rm -rf "$TMP"

chown root:root "$SYS" "$SYS"/*
chmod 755 "$SYS"
chmod 644 "$SYS"/*
chcon u:object_r:system_file:s0 "$SYS" "$SYS"/*

if [ "$SRC" = "$APEX" ]; then
    ZYGOTE_PID=$(pidof zygote || true)
    ZYGOTE64_PID=$(pidof zygote64 || true)

    # New apps inherit the Zygote's mounts.
    for Z_PID in $ZYGOTE_PID $ZYGOTE64_PID; do
        nsenter --mount=/proc/$Z_PID/ns/mnt -- /bin/mount --bind "$SYS" "$APEX"
    done

    # Already-running apps: every child of a Zygote.
    APP_PIDS=$(echo "$ZYGOTE_PID $ZYGOTE64_PID" | xargs -n1 ps -o 'PID' -P | grep -v PID)
    for PID in $APP_PIDS; do
        nsenter --mount=/proc/$PID/ns/mnt -- /bin/mount --bind "$SYS" "$APEX" &
    done
    wait

    # Verify from inside a real app's namespace, not just our shell's.
    # ps right-aligns PIDs; word-split to drop the padding.
    CHECK_PID=$(echo $APP_PIDS | awk '{print $1}')
    if [ -n "$CHECK_PID" ] && nsenter --mount=/proc/$CHECK_PID/ns/mnt -- ls "$APEX/$NAME" >/dev/null 2>&1; then
        echo "OK: $NAME visible in app namespace (pid $CHECK_PID) at $APEX"
    else
        echo "WARN: could not confirm $NAME inside an app namespace"
        exit 2
    fi
else
    ls "$SYS/$NAME" >/dev/null && echo "OK: $NAME installed in $SYS (pre-Android 14 path)"
fi

echo "System certificate injected ($(ls "$SYS" | wc -l) CAs trusted)"
