#!/bin/sh
set -eu

target="$1"
nut_gid="$(awk -F: '$1 == "nut" { print $3; exit }' "$target/etc/group")"

if [ -z "$nut_gid" ]; then
    echo "NUT group not found in target /etc/group" >&2
    exit 1
fi

chown 0:"$nut_gid" \
    "$target/etc/nut/upsd.conf" \
    "$target/etc/nut/upsd.users"
chmod 0640 \
    "$target/etc/nut/upsd.conf" \
    "$target/etc/nut/upsd.users"
chown 0:0 "$target/usr/local/sbin/nut-start.sh"
chmod 0755 "$target/usr/local/sbin/nut-start.sh"
