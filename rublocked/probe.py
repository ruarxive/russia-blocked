"""Live probe of the monitored sites from the current vantage point.

For every host the probe records DNS, the hosting network, TCP reachability of ports
443 and 80, the TLS certificate (including whether it chains to the Russian Trusted
Root CA, which browsers and archive crawlers do not trust), the homepage HTTP response
classified by fingerprint.classify, and robots.txt rules that exclude archive crawlers.
"""
import asyncio
import hashlib
import json
import logging
import ssl
import time
from urllib.parse import urlsplit

import certifi
import dns.asyncresolver
import dns.exception
import dns.rdatatype
import dns.resolver
import httpx
from cryptography import x509

from . import fingerprint
from .asn import AsnDB
from .common import BROWSER_UA, DATA_DIR, current_month, utcnow, write_jsonl, read_jsonl, normalize_host

log = logging.getLogger(__name__)

PROBES_DIR = DATA_DIR / "probes"
DNS_SERVERS = ["8.8.8.8", "1.1.1.1"]
TCP_TIMEOUT = 10
HTTP_TIMEOUT = httpx.Timeout(25, connect=12)
HOST_TIMEOUT = 120
MAX_BODY = 1024 * 1024
KEEP_HEADERS = ["server", "content-type", "location", "x-powered-by", "via", "x-cache", "x-frame-options"]

# Statuses that may be transient and are re-probed once at lower concurrency
RETRY_STATUSES = {"timeout", "refused", "http_timeout", "http_error", "server_error"}


def vantage():
    """Describe where the probe runs from: public IP, country and network."""
    try:
        r = httpx.get("https://ipinfo.io/json", timeout=15, trust_env=False)
        d = r.json()
        return {"ip": d.get("ip"), "country": d.get("country"), "city": d.get("city"), "org": d.get("org")}
    except Exception as e:  # noqa: BLE001 - informational only
        return {"error": str(e)}


async def resolve(resolver, host):
    first = None
    for fqdn in (host, "www." + host):
        try:
            answer = await resolver.resolve(fqdn, "A")
        except dns.resolver.NXDOMAIN:
            status = "nxdomain"
        except dns.resolver.NoAnswer:
            status = "noanswer"
        except dns.resolver.NoNameservers:
            status = "servfail"
        except dns.exception.Timeout:
            status = "timeout"
        except dns.exception.DNSException as e:
            status = type(e).__name__.lower()
        else:
            cnames = [str(item).rstrip(".") for rrset in answer.response.answer
                      if rrset.rdtype == dns.rdatatype.CNAME for item in rrset]
            return {"status": "ok", "fqdn": fqdn, "ips": sorted(r.address for r in answer), "cnames": cnames}
        first = first or {"status": status, "fqdn": host, "ips": [], "cnames": []}
    return first


async def tcp_connect(ip, port):
    start = time.monotonic()
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(ip, port), TCP_TIMEOUT)
        writer.close()
        return {"state": "open", "ms": int((time.monotonic() - start) * 1000)}
    except asyncio.TimeoutError:
        return {"state": "timeout"}
    except ConnectionRefusedError:
        return {"state": "refused"}
    except OSError as e:
        return {"state": "unreachable", "error": str(e)[:120]}


async def tls_info(ip, fqdn):
    info = {}
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, 443, ssl=ctx, server_hostname=fqdn), TCP_TIMEOUT + 5)
    except (OSError, asyncio.TimeoutError, ssl.SSLError) as e:
        return {"error": (type(e).__name__ + " " + str(e))[:160]}
    sslobj = writer.get_extra_info("ssl_object")
    der = sslobj.getpeercert(binary_form=True)
    info["version"] = sslobj.version()
    writer.close()
    if der:
        cert = x509.load_der_x509_certificate(der)
        info["issuer"] = cert.issuer.rfc4514_string()[:200]
        info["subject"] = cert.subject.rfc4514_string()[:200]
        info["not_after"] = cert.not_valid_after_utc.date().isoformat()
        info["ru_ca"] = "russian trusted" in info["issuer"].lower()
    vctx = ssl.create_default_context(cafile=certifi.where())
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, 443, ssl=vctx, server_hostname=fqdn), TCP_TIMEOUT + 5)
        writer.close()
        info["verified"] = True
    except ssl.SSLCertVerificationError as e:
        info["verified"] = False
        info["verify_error"] = (e.verify_message or str(e))[:120]
    except (OSError, asyncio.TimeoutError, ssl.SSLError) as e:
        info["verified"] = False
        info["verify_error"] = (type(e).__name__ + " " + str(e))[:120]
    return info


async def fetch(client, url, limit=MAX_BODY):
    out = {"url": url}
    try:
        async with client.stream("GET", url) as resp:
            body = bytearray()
            async for chunk in resp.aiter_bytes():
                body.extend(chunk)
                if len(body) >= limit:
                    break
            out["status"] = resp.status_code
            out["final_url"] = str(resp.url)
            out["redirects"] = [[r.status_code, str(r.url)] for r in resp.history]
            out["headers"] = {k: resp.headers[k][:200] for k in KEEP_HEADERS if k in resp.headers}
            out["header_names"] = sorted({k.lower() for k in resp.headers.keys()})
            cookies = []
            for r in list(resp.history) + [resp]:
                cookies += [c.split("=", 1)[0].strip() for c in r.headers.get_list("set-cookie")]
            out["cookies"] = sorted(set(cookies))
            out["_body"] = bytes(body)
            out["_content_type"] = resp.headers.get("content-type", "")
    except httpx.TimeoutException as e:
        out["error"] = "timeout:" + type(e).__name__
    except httpx.TooManyRedirects:
        out["error"] = "redirect_loop"
    except httpx.HTTPError as e:
        out["error"] = (type(e).__name__ + ": " + str(e))[:200]
    except (ssl.SSLError, OSError, UnicodeError, ValueError) as e:
        out["error"] = (type(e).__name__ + ": " + str(e))[:200]
    return out


def parse_robots(text):
    """Return whether robots.txt disallows the whole site for all agents or for IA."""
    groups, agents, rules, last_was_agent = [], [], [], False
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, value = (s.strip() for s in line.split(":", 1))
        key = key.lower()
        if key == "user-agent":
            if not last_was_agent and agents:
                groups.append((agents, rules))
                agents, rules = [], []
            agents.append(value.lower())
            last_was_agent = True
        else:
            last_was_agent = False
            if key in ("disallow", "allow"):
                rules.append((key, value))
    if agents:
        groups.append((agents, rules))

    def blocks(names):
        for group_agents, group_rules in groups:
            if any(a in names for a in group_agents):
                return ("disallow", "/") in group_rules and ("allow", "/") not in group_rules
        return False

    return {"blocks_all": blocks({"*"}), "blocks_ia": blocks({"ia_archiver", "archive.org_bot"})}


def derive_status(rec):
    """Collapse probe evidence into one status per host."""
    if rec["dns"]["status"] != "ok":
        return "dns"
    tcp = rec.get("tcp", {})
    states = {v["state"] for v in tcp.values()}
    if states and "open" not in states:
        return "timeout" if "timeout" in states else "refused"
    http = rec.get("http", {})
    if http.get("error"):
        return "http_timeout" if http["error"].startswith("timeout") else "http_error"
    kind = http.get("kind")
    return {"content": "ok", "shell": "ok", "challenge": "challenge", "blocked": "blocked", "empty": "empty",
            "client_error": "client_error", "server_error": "server_error"}.get(kind, "http_error")


async def probe_host(host, resolver, client, asndb):
    rec = {"host": host, "probed_at": utcnow().isoformat(timespec="seconds")}
    rec["dns"] = await resolve(resolver, host)
    if rec["dns"]["status"] != "ok":
        rec["status"] = derive_status(rec)
        return rec
    fqdn, ip = rec["dns"]["fqdn"], rec["dns"]["ips"][0]
    rec["asn"] = asndb.lookup(ip)
    p443, p80 = await asyncio.gather(tcp_connect(ip, 443), tcp_connect(ip, 80))
    rec["tcp"] = {"443": p443, "80": p80}
    if p443["state"] == "open":
        rec["tls"] = await tls_info(ip, fqdn)

    http = None
    for scheme, port in (("https", p443), ("http", p80)):
        if port["state"] != "open":
            continue
        http = await fetch(client, f"{scheme}://{fqdn}/")
        if not http.get("error"):
            break
    if http is not None:
        body = http.pop("_body", b"")
        content_type = http.pop("_content_type", "")
        if not http.get("error"):
            text = fingerprint.decode_body(body, content_type)
            stats = fingerprint.page_stats(text)
            http.update(stats)
            http["size"] = len(body)
            http["sha1"] = hashlib.sha1(body).hexdigest()
            http["kind"], http["reason"] = fingerprint.classify(http["status"], text, stats)
            http["spam"] = fingerprint.detect_spam(stats["title"], text)
            final_host = normalize_host(urlsplit(http["final_url"]).hostname or "")
            rec["offsite"] = final_host != host and not final_host.endswith("." + host)
            rec["final_host"] = final_host
            rec["vendors"] = fingerprint.detect_vendors(
                http.get("headers"), http.get("cookies", []), text[:200000].lower(),
                rec["dns"]["cnames"], (rec.get("asn") or {}).get("name", ""))
            robots = await fetch(client, f"{urlsplit(http['final_url']).scheme}://{urlsplit(http['final_url']).netloc}/robots.txt", 65536)
            rbody = robots.pop("_body", b"")
            robots.pop("_content_type", None)
            rec["robots"] = {"status": robots.get("status"), "error": robots.get("error")}
            if robots.get("status") == 200 and b"<html" not in rbody[:500].lower():
                rec["robots"].update(parse_robots(rbody.decode("utf-8", "replace")))
        rec["http"] = http
    if "vendors" not in rec:
        rec["vendors"] = fingerprint.detect_vendors(
            cnames=rec["dns"]["cnames"], asn_name=(rec.get("asn") or {}).get("name", ""))
    rec["status"] = derive_status(rec)
    return rec


async def _run(hosts, concurrency):
    resolver = dns.asyncresolver.Resolver(configure=False)
    resolver.nameservers = DNS_SERVERS
    resolver.lifetime = 10
    asndb = AsnDB()
    limits = httpx.Limits(max_connections=concurrency * 2, max_keepalive_connections=0)
    headers = {"User-Agent": BROWSER_UA, "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
               "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8"}
    sem = asyncio.Semaphore(concurrency)
    results = {}
    async with httpx.AsyncClient(verify=False, trust_env=False, follow_redirects=True, max_redirects=10,
                                 timeout=HTTP_TIMEOUT, limits=limits, headers=headers) as client:
        async def one(host):
            async with sem:
                try:
                    rec = await asyncio.wait_for(probe_host(host, resolver, client, asndb), HOST_TIMEOUT)
                except asyncio.TimeoutError:
                    rec = {"host": host, "probed_at": utcnow().isoformat(timespec="seconds"),
                           "dns": {"status": "ok"}, "http": {"error": "timeout:host"}, "status": "http_timeout"}
                except Exception as e:  # noqa: BLE001 - one host must not stop the run
                    log.exception("probe failed for %s", host)
                    rec = {"host": host, "probed_at": utcnow().isoformat(timespec="seconds"),
                           "dns": {"status": "ok"}, "http": {"error": f"exception: {e}"[:200]}, "status": "http_error"}
                results[host] = rec
                if len(results) % 100 == 0:
                    log.info("probed %d/%d", len(results), len(hosts))
        await asyncio.gather(*(one(h) for h in hosts))
    return results


def run(hosts, month=None, concurrency=40, merge=False):
    """Probe hosts; with merge=True update only these hosts in an existing month file."""
    month = month or current_month()
    meta = {"month": month, "started_at": utcnow().isoformat(timespec="seconds"), "vantage": vantage(),
            "hosts": len(hosts)}
    log.info("probing %d hosts from %s", len(hosts), meta["vantage"])
    results = asyncio.run(_run(hosts, concurrency))
    retry = [h for h, r in results.items() if r["status"] in RETRY_STATUSES]
    if retry:
        log.info("re-probing %d hosts with transient failures", len(retry))
        second = asyncio.run(_run(retry, max(4, concurrency // 4)))
        for host, rec in second.items():
            rec["attempts"] = 2
            if rec["status"] not in RETRY_STATUSES:
                results[host] = rec
            else:
                results[host]["attempts"] = 2
    meta["finished_at"] = utcnow().isoformat(timespec="seconds")
    PROBES_DIR.mkdir(parents=True, exist_ok=True)
    if merge and (PROBES_DIR / f"{month}.jsonl.gz").exists():
        previous = load(month)
        previous.update(results)
        results = previous
        meta_path = PROBES_DIR / f"{month}.meta.json"
        if meta_path.exists():
            old = json.loads(meta_path.read_text(encoding="utf-8"))
            old["reprobed"] = old.get("reprobed", 0) + len(hosts)
            old["reprobed_at"] = meta["finished_at"]
            meta = old
    write_jsonl(PROBES_DIR / f"{month}.jsonl.gz", [results[h] for h in sorted(results)])
    with open(PROBES_DIR / f"{month}.meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    return results


def load(month):
    return {r["host"]: r for r in read_jsonl(PROBES_DIR / f"{month}.jsonl.gz")}
