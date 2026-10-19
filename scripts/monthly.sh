#!/bin/sh
# Monthly run: probe, WHOIS, Wayback, snapshots, Common Crawl, site build.
set -eu
cd "$(dirname "$0")/.."
mkdir -p logs
log="logs/monthly-$(date +%Y-%m).log"
.venv/bin/python -m rublocked monthly >> "$log" 2>&1
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) monthly run finished" >> "$log"
