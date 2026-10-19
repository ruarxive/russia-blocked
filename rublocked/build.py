"""Aggregate the collected data into JSON files for the static site (site/data/)."""
import collections
import csv
import gzip
import json
import logging
import shutil
from datetime import date

from . import commoncrawl, fingerprint, probe, registry, wayback, whois
from .common import DATA_DIR, SITE_DIR, START_MONTH, current_month, month_range, utcnow

log = logging.getLogger(__name__)

OUT_DIR = SITE_DIR / "data"
DOWNLOAD_DIR = OUT_DIR / "download"

# Live probe statuses grouped for charts
STATUS_GROUP = {
    "ok": "ok",
    "challenge": "waf", "blocked": "waf", "empty": "waf",
    "timeout": "noconn", "refused": "noconn", "http_timeout": "noconn", "http_error": "noconn",
    "server_error": "error", "client_error": "error",
    "dns": "gone", "lost": "gone",
}
GROUPS = ["ok", "waf", "noconn", "error", "gone"]
# A live site seen from abroad and from Russia: open from both, closed only for foreign
# visitors (geoblocking, WAF rules for foreign addresses), closed from both, or closed only
# from the Russian network
GEO = ["open", "geoblock", "closed", "ru_fail"]
# The registry was compiled in 2020 and last updated in October 2022. A registrable
# domain created after the last update was dropped and registered again by someone
# else; one created between 2021 and that update may be a legitimate new government
# domain, so it also needs a private owner or hosting outside Russia.
REREGISTERED_AFTER = "2021-01-01"
REGISTRY_UPDATED = "2022-11-01"
# One-letter codes of classified Wayback snapshots, per year
SNAP_CODE = {"content": "c", "shell": "s", "challenge": "j", "blocked": "b", "empty": "e",
             "client_error": "x", "server_error": "x", "none": "n"}
BASELINE_YEAR = "2021"
BASELINE_CRAWLS = {"CC-MAIN-2021-49", "CC-MAIN-2022-05"}


def _lost_reason(rec, who):
    """Why a domain is no longer the government site, or None."""
    http = (rec or {}).get("http") or {}
    if rec and (rec.get("offsite") or http.get("status") == 200):
        parked = fingerprint.detect_parking(rec.get("final_host"), http.get("title"))
        if parked:
            return f"parked:{parked}"
    spam = http.get("spam") or fingerprint.detect_spam(http.get("title"))
    if spam and http.get("status") == 200:
        return f"spam:{spam}"
    if not (who and who.get("registered")):
        return None
    created = who.get("created") or ""
    abroad = ((rec or {}).get("asn") or {}).get("country") not in (None, "RU")
    if created >= REGISTRY_UPDATED or (created >= REREGISTERED_AFTER and (who.get("person") or abroad)):
        return f"rereg:{created[:10]}"
    return None


def _probe_fields(rec):
    if not rec:
        return {"s": None, "g": None}
    http = rec.get("http") or {}
    tls = rec.get("tls") or {}
    asn = rec.get("asn") or {}
    tcp = rec.get("tcp") or {}
    robots = rec.get("robots") or {}
    out = {
        "s": rec["status"], "g": STATUS_GROUP.get(rec["status"]),
        "ip": (rec["dns"].get("ips") or [None])[0],
        "asn": f"AS{asn['asn']} {asn['name']}" if asn else None,
        "ac": asn.get("country"),
        "v": rec.get("vendors") or [],
        "p443": (tcp.get("443") or {}).get("state"),
        "p80": (tcp.get("80") or {}).get("state"),
        "ruca": bool(tls.get("ru_ca")),
        "tlsok": tls.get("verified"),
        "iss": tls.get("issuer"),
        "hs": http.get("status"),
        "hk": http.get("kind"),
        "hr": http.get("reason") or http.get("error"),
        "t": http.get("title"),
        "rb": "ia" if robots.get("blocks_ia") else ("all" if robots.get("blocks_all") else ""),
    }
    if rec.get("offsite"):
        out["fh"] = rec.get("final_host")
    return out


def active_cohort_hosts(hosts):
    """Hosts of the 2021 cohort that are still government sites.

    Only these enter the archive shares, so only their snapshots need classifying.
    """
    probe_month = probe.latest_month()
    probes = probe.load(probe_month) if probe_month else {}
    whois_db = whois.load()
    out = []
    for host in hosts:
        spark = wayback.load_sparkline(host) or {}
        st = spark.get("status", {}).get(BASELINE_YEAR, "")
        counts = spark.get("years", {}).get(BASELINE_YEAR) or []
        if not any(c == "2" and n for c, n in zip(st, counts)):
            continue
        rec = probes.get(host)
        if rec and (rec["status"] == "dns" or _lost_reason(rec, whois_db.get(whois.registrable(host) or ""))):
            continue
        out.append(host)
    return out


def build():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    hosts = registry.load()
    now_month = current_month()
    months = month_range(START_MONTH, now_month)
    complete = months[:-1]  # the current month is still being archived
    this_year = date.today().year
    years = list(range(int(START_MONTH[:4]), this_year + 1))

    probe_month = probe.latest_month()
    probes = probe.load(probe_month) if probe_month else {}
    meta = probe.load_meta(probe_month) if probe_month else {}
    ru_month = probe.latest_month("ru")
    probes_ru = probe.load(ru_month, "ru") if ru_month else {}
    meta_ru = probe.load_meta(ru_month, "ru") if ru_month else {}
    snapshots = wayback.load_snapshots()
    whois_db = whois.load()
    crawls, cc_rows, cc_queried = commoncrawl.load()
    crawl_ids = [c["crawl"] for c in crawls]
    cc = collections.defaultdict(dict)
    for r in cc_rows:
        agg = cc[r["host"]].setdefault(r["crawl"], collections.Counter())
        for k in commoncrawl.COLUMNS:
            agg[k] += int(r[k])
    cc_done = sorted({r["crawl"] for r in cc_rows})

    domains = []
    for h in hosts:
        host = h["host"]
        spark = wayback.load_sparkline(host)
        counts, classes = wayback.monthly_series(spark, months)
        wb = "".join(classes) if spark else ""
        last_ok = next((m for m, c in zip(reversed(months), reversed(classes)) if c == "2"), None) if spark else None
        base_idx = [i for i, m in enumerate(months) if m.startswith(BASELINE_YEAR)]
        cohort = bool(spark) and any(classes[i] == "2" for i in base_idx)

        sn, sts = [], []
        for year in years:
            rec = snapshots.get((host, year))
            if not spark:
                sn.append("?")
            elif not any(c == "2" for m, c in zip(months, classes) if m.startswith(str(year))):
                sn.append("n")
            elif rec is None or rec.get("error"):
                sn.append("?")
            else:
                sn.append(SNAP_CODE.get(rec.get("kind"), "?"))
            sts.append(rec.get("timestamp", "") if rec and not rec.get("error") else "")

        ccs = ""
        # Hosts added after the earlier crawls were queried have no Common Crawl data yet
        if cc_done and host in cc_queried:
            for crawl in crawl_ids:
                if crawl not in cc_done:
                    ccs += "?"
                    continue
                a = cc[host].get(crawl)
                if not a:
                    ccs += "0"
                elif a["fetch_200"] > 0:
                    ccs += "2"
                elif a["fetch_3xx"] > 0 and a["fetch_4xx"] + a["fetch_5xx"] + a["fetch_other"] == 0:
                    ccs += "3"
                elif a["fetch_4xx"] + a["fetch_5xx"] + a["fetch_other"] + a["fetch_gone"] > 0:
                    ccs += "e"
                else:
                    ccs += "u"  # known to the crawler but not fetched
        d = {"h": host, "d": h["display"], "c": h["category"], "n": h["name"] or h["org"], "o": h["org"],
             "r": h["region"], "wb": wb, "wn": sum(counts), "wl": last_ok, "co": cohort,
             "sn": "".join(sn), "sts": sts, "ccs": ccs,
             "ccb": bool(ccs) and any(cc[host].get(c, {}).get("fetch_200", 0) > 0 for c in BASELINE_CRAWLS)}
        d.update(_probe_fields(probes.get(host)))
        who = whois_db.get(whois.registrable(host) or "")
        if who and not who.get("error"):
            d["wc"] = (who.get("created") or "")[:10] or None
            d["wr"] = who.get("registrar")
            d["wo"] = "person" if who.get("person") else ("org" if "org" in who else None)
            d["free"] = who.get("registered") is False
        lost = _lost_reason(probes.get(host), who)
        if lost and d["s"]:
            d["lr"] = lost
            d["s"], d["g"] = "lost", "gone"
        # Only sites that still exist as government sites count in the archive shares
        d["act"] = d["s"] is None or d["g"] != "gone"
        _add_ru(d, probes_ru.get(host))
        domains.append(d)

    summary = _summarize(domains, months, complete, years, crawls, cc_done, probe_month, meta)
    summary["probe_ru"] = {"month": ru_month, "vantage": meta_ru.get("vantage"),
                           "started_at": meta_ru.get("started_at"), "finished_at": meta_ru.get("finished_at")}
    summary.update(_summarize_ru(domains))
    with open(OUT_DIR / "domains.json", "w", encoding="utf-8") as f:
        json.dump(domains, f, ensure_ascii=False, separators=(",", ":"))
    with open(OUT_DIR / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, separators=(",", ":"))
    _downloads(domains, months, years, probe_month)
    log.info("site data written: %d domains, probe month %s", len(domains), probe_month)


def _add_ru(d, rec):
    """Fields of the Russian probe and the comparison class of the two views."""
    if not rec:
        return
    http = rec.get("http") or {}
    d["rs"], d["rg"] = rec["status"], STATUS_GROUP.get(rec["status"])
    d["rhs"], d["rhk"] = http.get("status"), http.get("kind")
    d["rhr"] = http.get("reason") or http.get("error")
    # Taken over or deleted domains are no longer government sites, whatever either side sees
    if d["s"] and d["g"] != "gone":
        ok_abroad, ok_ru = d["g"] == "ok", d["rg"] == "ok"
        d["geo"] = ("open" if ok_ru else "ru_fail") if ok_abroad else ("geoblock" if ok_ru else "closed")


def _summarize_ru(domains):
    scopes = ["all"] + list(registry.CATEGORIES)
    live_ru, geo = {}, {}
    for scope in scopes:
        group = [d for d in domains if (scope == "all" or d["c"] == scope) and d.get("rs")]
        live_ru[scope] = {"n": len(group), "groups": {g: sum(1 for d in group if d["rg"] == g) for g in GROUPS}}
        compared = [d for d in group if d.get("geo")]
        geo[scope] = {"n": len(compared), **{k: sum(1 for d in compared if d["geo"] == k) for k in GEO}}
    # Status group seen from abroad by status group seen from Russia, for live sites
    matrix = {a: {r: 0 for r in GROUPS} for a in GROUPS if a != "gone"}
    for d in domains:
        if d.get("geo"):
            matrix[d["g"]][d["rg"]] += 1
    return {"live_ru": live_ru, "geo": geo, "geo_matrix": matrix}


def _summarize(domains, months, complete, years, crawls, cc_done, probe_month, meta):
    cats = list(registry.CATEGORIES)
    scopes = ["all"] + cats

    def in_scope(d, scope):
        return scope == "all" or d["c"] == scope

    # Wayback monthly coverage: share of hosts with a 200 homepage capture
    timeline = {}
    for scope in scopes:
        group = [d for d in domains if in_scope(d, scope) and d["wb"]]
        cohort = [d for d in group if d["co"] and d["act"]]
        series = {"n": len(group), "cohort_n": len(cohort),
                  "archived": [], "redirect": [], "error": [], "cohort_archived": []}
        for i in range(len(months)):
            col = collections.Counter(d["wb"][i] for d in group)
            series["archived"].append(col["2"])
            series["redirect"].append(col["3"])
            series["error"].append(col["4"] + col["5"])
            series["cohort_archived"].append(sum(1 for d in cohort if d["wb"][i] == "2"))
        timeline[scope] = series

    # Classified snapshot quality per year, for the baseline cohort
    quality = {}
    for scope in scopes:
        cohort = [d for d in domains if in_scope(d, scope) and d["co"] and d["act"]]
        quality[scope] = {str(y): dict(collections.Counter(d["sn"][i] for d in cohort))
                          for i, y in enumerate(years)}

    # Months since the last 200 capture, for the cohort, as of the last complete month
    last_complete = complete[-1]
    ly, lm = map(int, last_complete.split("-"))
    gap_buckets = ["0", "1-3", "4-6", "7-12", "13-24", "25+"]
    gaps = {}
    for scope in scopes:
        counter = collections.Counter()
        for d in domains:
            if not (in_scope(d, scope) and d["co"] and d["act"]):
                continue
            if not d["wl"]:
                counter["25+"] += 1
                continue
            y, m = map(int, d["wl"].split("-"))
            gap = max(0, (ly - y) * 12 + (lm - m))
            bucket = "0" if gap == 0 else "1-3" if gap <= 3 else "4-6" if gap <= 6 else \
                "7-12" if gap <= 12 else "13-24" if gap <= 24 else "25+"
            counter[bucket] += 1
        gaps[scope] = [counter[b] for b in gap_buckets]

    # Live probe
    live = {}
    for scope in scopes:
        probed = [d for d in domains if in_scope(d, scope) and d["s"]]
        live[scope] = {"n": len(probed),
                       "groups": {g: sum(1 for d in probed if d["g"] == g) for g in GROUPS},
                       "statuses": dict(collections.Counter(d["s"] for d in probed))}
    alive = [d for d in domains if d["s"] and d["g"] != "gone"]
    vendors = collections.Counter(v for d in alive for v in d["v"])
    countries = collections.Counter(d["ac"] or "?" for d in alive)
    asns = collections.Counter(d["asn"] for d in alive if d["asn"])
    flags = {
        "alive": len(alive),
        "ru_ca": sum(1 for d in alive if d["ruca"]),
        "tls_untrusted": sum(1 for d in alive if d["tlsok"] is False),
        "https_closed_http_open": sum(1 for d in alive if d["p443"] != "open" and d["p80"] == "open"),
        "robots_all": sum(1 for d in alive if d["rb"] == "all"),
        "robots_ia": sum(1 for d in alive if d["rb"] == "ia"),
        "with_vendor": sum(1 for d in alive if d["v"]),
        "hosted_ru": countries.get("RU", 0),
        "lost": sum(1 for d in domains if d["s"] == "lost"),
        "free": sum(1 for d in domains if d.get("free")),
    }

    # Common Crawl per crawl: hosts fetched with 200, among the pre-2022 baseline
    cc_series = {}
    for scope in scopes:
        group = [d for d in domains if in_scope(d, scope) and d["ccs"]]
        base = [d for d in group if d["ccb"]]
        series = {"n": len(group), "baseline_n": len(base), "ok": [], "error": [], "baseline_ok": []}
        for i in range(len(crawls)):
            col = collections.Counter(d["ccs"][i] for d in group)
            series["ok"].append(col["2"] if "?" not in col else None)
            series["error"].append(col["e"] if "?" not in col else None)
            series["baseline_ok"].append(sum(1 for d in base if d["ccs"][i] == "2") if "?" not in col else None)
        cc_series[scope] = series

    # Sites of regional offices, courts and election commissions by region
    regions = collections.defaultdict(lambda: collections.Counter())
    subjects = set(registry.REGIONS.values())
    for d in domains:
        if d["r"] in subjects and d["s"]:
            regions[d["r"]]["n"] += 1
            regions[d["r"]][d["g"]] += 1
            regions[d["r"]]["cohort"] += d["co"]
            regions[d["r"]]["recent"] += d["co"] and bool(d["wl"]) and d["wl"] >= complete[-12]

    cohort = [d for d in domains if d["co"] and d["act"]]
    recent = [d for d in cohort if d["wl"] and d["wl"] >= complete[-12]]
    this_year_idx = len(years) - 1
    content_now = [d for d in cohort if d["sn"][this_year_idx] == "c"]
    return {
        "generated_at": utcnow().isoformat(timespec="seconds"),
        "months": months, "complete_months": len(complete), "years": years,
        "categories": registry.CATEGORIES,
        "probe": {"month": probe_month, "vantage": meta.get("vantage"), "started_at": meta.get("started_at"),
                  "finished_at": meta.get("finished_at")},
        "kpi": {
            "hosts": len(domains),
            "probed": sum(1 for d in domains if d["s"]),
            "alive": len(alive),
            "unreachable": sum(1 for d in alive if d["g"] != "ok"),
            "lost": sum(1 for d in domains if d["s"] == "lost"),
            "cohort": len(cohort),
            "cohort_archived_last12": len(recent),
            "cohort_archived_last_month": sum(1 for d in cohort if d["wb"] and d["wb"][len(complete) - 1] == "2"),
            "cohort_content_this_year": len(content_now),
            "cohort_snap_checked_this_year": sum(1 for d in cohort if d["sn"][this_year_idx] != "?"),
        },
        "timeline": timeline, "quality": quality, "gap_buckets": gap_buckets, "gaps": gaps,
        "live": live, "flags": flags,
        "vendors": vendors.most_common(), "countries": countries.most_common(15), "asns": asns.most_common(15),
        "crawls": crawls, "crawls_done": cc_done, "commoncrawl": cc_series,
        "regions": {r: dict(c) for r, c in sorted(regions.items())},
    }


def _downloads(domains, months, years, probe_month):
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    fields = ["host", "display", "category", "name", "org", "region", "live_status", "status_group",
              "ip", "asn", "asn_country", "vendors", "port_443", "port_80", "russian_trusted_ca",
              "tls_verified", "http_status", "page_kind", "title", "robots_block",
              "ru_live_status", "ru_status_group", "ru_http_status", "ru_page_kind", "abroad_vs_russia",
              "lost_reason", "whois_created", "whois_registrar", "free_to_register",
              "wayback_captures_total", "wayback_last_200_month", "baseline_2021",
              "wayback_monthly_" + months[0] + "_" + months[-1],
              "snapshot_quality_" + str(years[0]) + "_" + str(years[-1]), "commoncrawl_per_crawl"]
    with gzip.open(DOWNLOAD_DIR / "domains.csv.gz", "wt", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(fields)
        for d in domains:
            w.writerow([d["h"], d["d"], d["c"], d["n"], d["o"], d["r"], d["s"], d["g"], d.get("ip"), d.get("asn"),
                        d.get("ac"), ";".join(d.get("v") or []), d.get("p443"), d.get("p80"), d.get("ruca"),
                        d.get("tlsok"), d.get("hs"), d.get("hk"), d.get("t"), d.get("rb"),
                        d.get("rs"), d.get("rg"), d.get("rhs"), d.get("rhk"), d.get("geo"), d.get("lr"), d.get("wc"),
                        d.get("wr"), d.get("free"), d["wn"], d["wl"],
                        d["co"], d["wb"], d["sn"], d["ccs"]])
    for src, name in [(registry.REGISTRY_FILE, "registry.csv"), (whois.WHOIS_FILE, "whois.jsonl.gz"),
                      (wayback.SNAPSHOTS_FILE, "wayback_snapshots.jsonl.gz"),
                      (commoncrawl.HOSTS_FILE, "commoncrawl_hosts.csv.gz")]:
        if src.exists():
            shutil.copyfile(src, DOWNLOAD_DIR / name)
    for point, prefix in (("abroad", "probe_"), ("ru", "probe_ru_")):
        for path in probe.VANTAGES[point]["dir"].glob("*.jsonl.gz"):
            shutil.copyfile(path, DOWNLOAD_DIR / f"{prefix}{path.name}")
