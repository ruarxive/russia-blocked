"""IP to ASN lookup with the public iptoasn.com dataset (downloaded once per month)."""
import bisect
import gzip
import ipaddress
import time

import httpx

from .common import DATA_DIR, MONITOR_UA

IP2ASN_URL = "https://iptoasn.com/data/ip2asn-v4.tsv.gz"
IP2ASN_FILE = DATA_DIR / "cache" / "ip2asn-v4.tsv.gz"
MAX_AGE = 30 * 86400


class AsnDB:
    def __init__(self):
        if not IP2ASN_FILE.exists() or time.time() - IP2ASN_FILE.stat().st_mtime > MAX_AGE:
            IP2ASN_FILE.parent.mkdir(parents=True, exist_ok=True)
            with httpx.stream("GET", IP2ASN_URL, headers={"User-Agent": MONITOR_UA},
                              timeout=120, follow_redirects=True) as r:
                r.raise_for_status()
                with open(IP2ASN_FILE, "wb") as f:
                    for chunk in r.iter_bytes():
                        f.write(chunk)
        self.starts, self.rows = [], []
        with gzip.open(IP2ASN_FILE, "rt", encoding="utf-8", errors="replace") as f:
            for line in f:
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 5 or parts[2] == "0":
                    continue
                self.starts.append(int(ipaddress.IPv4Address(parts[0])))
                self.rows.append((int(ipaddress.IPv4Address(parts[1])), int(parts[2]), parts[3], parts[4]))

    def lookup(self, ip):
        try:
            value = int(ipaddress.IPv4Address(ip))
        except ValueError:
            return None
        i = bisect.bisect_right(self.starts, value) - 1
        if i < 0 or value > self.rows[i][0]:
            return None
        _, asn, country, name = self.rows[i]
        return {"asn": asn, "country": country, "name": name}
