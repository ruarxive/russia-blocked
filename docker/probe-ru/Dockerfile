# Runs `python -m rublocked` behind an AmneziaWG tunnel to a Russian network.
# AmneziaWG is WireGuard with traffic obfuscation (Jc, S1-S4, H1-H4 in the config), so it
# needs its own userspace implementation and tools instead of wireguard-tools.
# The repository is mounted at /app at run time (scripts/probe-ru.sh), the VPN config at
# /secrets/vpn.conf; neither is baked into the image.
FROM golang:1.25-bookworm AS awg
ARG AWG_GO_VERSION=v3.1.20260828
ARG AWG_TOOLS_VERSION=v3.1.20260812
RUN git clone --depth 1 --branch "$AWG_GO_VERSION" https://github.com/amnezia-vpn/amneziawg-go /src/amneziawg-go \
    && cd /src/amneziawg-go && CGO_ENABLED=0 go build -trimpath -o /out/amneziawg-go . \
    && git clone --depth 1 --branch "$AWG_TOOLS_VERSION" https://github.com/amnezia-vpn/amneziawg-tools /src/amneziawg-tools \
    && make -C /src/amneziawg-tools/src \
    && cp /src/amneziawg-tools/src/wg /out/awg \
    && cp /src/amneziawg-tools/src/wg-quick/linux.bash /out/awg-quick \
    # /proc/sys is read-only in a container: src_valid_mark comes from `docker run --sysctl`,
    # so set it only when it is not set yet, as upstream wg-quick does
    && sed -i 's|\[\[ $proto == -4 \]\] && cmd sysctl -q net.ipv4.conf.all.src_valid_mark=1|[[ $proto == -4 \&\& $(sysctl -n net.ipv4.conf.all.src_valid_mark) != 1 ]] \&\& cmd sysctl -q net.ipv4.conf.all.src_valid_mark=1|' /out/awg-quick \
    && grep -q 'src_valid_mark) != 1' /out/awg-quick

FROM python:3.13-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends iproute2 nftables procps \
    && rm -rf /var/lib/apt/lists/*
COPY --from=awg /out/amneziawg-go /out/awg /out/awg-quick /usr/local/bin/

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY docker/probe-ru/entrypoint.sh /usr/local/bin/entrypoint.sh
WORKDIR /app
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
