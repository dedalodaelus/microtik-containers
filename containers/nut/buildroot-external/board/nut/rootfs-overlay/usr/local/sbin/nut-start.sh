#!/bin/sh
set -eu

mkdir -p /var/state/ups /run/nut

echo "Starting NUT USB driver..."
/usr/sbin/upsdrvctl start

echo "Starting NUT server on TCP/3493..."
exec /usr/sbin/upsd -F
