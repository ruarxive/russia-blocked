"""WHOIS of the registrable domains in the .ru, .su and .рф zones (whois.tcinet.ru).

Expired government domains are often re-registered by third parties and reused for
casino or loan spam, sometimes with a copy of the old government site. Archives keep
capturing them as if they were still government sites. A creation date after the
registry was compiled is the clearest sign that the domain changed hands.
"""
import logging
import socket
import time
from datetime import datetime

from .common import DATA_DIR, read_jsonl, utcnow, write_jsonl

log = logging.getLogger(__name__)

WHOIS_SERVER = "whois.tcinet.ru"
WHOIS_FILE = DATA_DIR / "whois" / "whois.jsonl.gz"
ZONES = ("ru", "su", "xn--p1ai")
# Second-level zones of .ru where domains are registered at the third level
GEO_SLD = {"msk", "spb", "com", "net", "org", "pp", "nov", "kchr", "khakassia", "mari-el", "tatarstan",
           "udmurtia", "yakutia", "bashkiria", "chuvashia", "kalmykia", "dagestan", "adygeya", "kuban"}
# Registrable domains that hold many registry hosts and are controlled by the state
SKIP = {"gov.ru"}
MAX_AGE_DAYS = 90
FIELDS = ("created", "paid-till", "registrar", "org", "person", "state", "free-date")


def registrable(host):
    labels = host.split(".")
    if labels[-1] not in ZONES or len(labels) < 2:
        return None
    if len(labels) >= 3 and labels[-2] in GEO_SLD:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def query(domain, timeout=20):
    with socket.create_connection((WHOIS_SERVER, 43), timeout=timeout) as sock:
        sock.sendall((domain + "\r\n").encode("idna" if not domain.isascii() else "ascii"))
        buf = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            buf += chunk
    text = buf.decode("utf-8", "replace")
    rec = {"domain": domain, "checked": utcnow().isoformat(timespec="seconds")}
    if "No entries found" in text:
        rec["registered"] = False
        return rec
    if "limit" in text.lower() and "exceed" in text.lower():
        raise RuntimeError("whois rate limit")
    rec["registered"] = True
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = (p.strip() for p in line.split(":", 1))
        if key in FIELDS and key not in rec:
            rec[key] = value
    return rec


def load():
    return {r["domain"]: r for r in read_jsonl(WHOIS_FILE)}


def update(hosts, interval=1.0):
    existing = load()
    domains = sorted({d for d in (registrable(h) for h in hosts) if d and d not in SKIP})
    now = utcnow()
    todo = []
    for d in domains:
        rec = existing.get(d)
        if rec and not rec.get("error"):
            age = (now - datetime.fromisoformat(rec["checked"])).days
            if age < MAX_AGE_DAYS:
                continue
        todo.append(d)
    log.info("whois: %d of %d registrable domains to query", len(todo), len(domains))
    for i, d in enumerate(todo, 1):
        for attempt in range(4):
            try:
                existing[d] = query(d)
                break
            except (OSError, RuntimeError) as e:
                log.warning("whois %s: %s (attempt %d)", d, e, attempt + 1)
                time.sleep(30 * (attempt + 1))
        else:
            existing[d] = {"domain": d, "checked": now.isoformat(timespec="seconds"), "error": "failed"}
        time.sleep(interval)
        if i % 100 == 0:
            log.info("whois: %d/%d", i, len(todo))
            write_jsonl(WHOIS_FILE, [existing[k] for k in sorted(existing)])
    write_jsonl(WHOIS_FILE, [existing[k] for k in sorted(existing)])
