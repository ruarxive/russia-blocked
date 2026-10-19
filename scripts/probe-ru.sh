#!/bin/sh
# Probe the registry from a Russian vantage point: an AmneziaWG tunnel inside a Docker
# container, so the tunnel never changes the routing of this machine.
# Extra arguments go to `rublocked probe`, e.g. --limit 50 or --hosts a.ru b.ru.
# Exit code 3: no VPN config, the step is skipped.
set -eu
cd "$(dirname "$0")/.."
# launchd starts jobs with a minimal PATH that does not include the Docker CLI
PATH="$PATH:/usr/local/bin:/opt/homebrew/bin"
conf=${RU_VPN_CONF:-secrets/rusgate.conf}
if [ ! -r "$conf" ]; then
  echo "probe-ru: no VPN config at $conf, skipped" >&2
  exit 3
fi
image=rublocked-probe-ru
docker build -q -t "$image" -f docker/probe-ru/Dockerfile . >/dev/null
# The container resolver must be reachable through the tunnel: Docker's own one is not
exec docker run --rm --cap-add NET_ADMIN --device /dev/net/tun --dns 77.88.8.8 --dns 77.88.8.1 \
  --sysctl net.ipv4.conf.all.src_valid_mark=1 --sysctl net.ipv6.conf.all.disable_ipv6=0 \
  -v "$PWD:/app" -v "$PWD/$conf:/secrets/vpn.conf:ro" \
  "$image" probe --vantage ru "$@"
