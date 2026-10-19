#!/bin/sh
# Bring up the AmneziaWG tunnel from the mounted config, then run rublocked with the given arguments.
set -eu
conf=/secrets/vpn.conf
[ -r "$conf" ] || { echo "entrypoint: no VPN config at $conf" >&2; exit 3; }
dir=/etc/amnezia/amneziawg
mkdir -p "$dir"
# DNS= needs resolvconf, which the container lacks; the probe uses its own resolvers
grep -viE '^[[:space:]]*DNS[[:space:]]*=' "$conf" > "$dir/awg0.conf"
chmod 600 "$dir/awg0.conf"
# Without the kernel module awg-quick falls back to the userspace amneziawg-go
awg-quick up "$dir/awg0.conf" >&2
exec python -m rublocked "$@"
