"""Per-crawl fetch statistics of the monitored hosts from the Common Crawl Host Index.

The host index (https://github.com/commoncrawl/cc-host-index) has one row per host and
crawl with counts of fetches by HTTP status class. Its Parquet files are sorted by SURT
host name, so DuckDB reads only the row groups that cover the requested hosts.
"""
import csv
import gzip
import hashlib
import io
import json
import logging
import os
from datetime import date

import duckdb
import httpx

from .common import DATA_DIR, MONITOR_UA

log = logging.getLogger(__name__)

PATHS_URL = "https://data.commoncrawl.org/projects/host-index-testing/v2.paths.gz"
BASE_URL = "https://data.commoncrawl.org/"
CC_DIR = DATA_DIR / "commoncrawl"
HOSTS_FILE = CC_DIR / "hosts.csv.gz"
CRAWLS_FILE = CC_DIR / "crawls.csv"
QUERIED_FILE = CC_DIR / "queried.txt"
# Crawls already backfilled for the current set of new hosts, so an interrupted backfill
# resumes instead of querying them again
BACKFILL_FILE = CC_DIR / "backfill.json"
# Without limits one crawl query grew to about 4 GB and pushed the machine into swap;
# DuckDB spills to TEMP_DIR instead
MEMORY_LIMIT = "1GB"
THREADS = 2
TEMP_DIR = DATA_DIR / "cache" / "duckdb"
PRIORITY = {"CC-MAIN-2021-49", "CC-MAIN-2022-05", "CC-MAIN-2022-21", "CC-MAIN-2022-40", "CC-MAIN-2023-14",
            "CC-MAIN-2023-50", "CC-MAIN-2024-26", "CC-MAIN-2025-05", "CC-MAIN-2025-18"}
COLUMNS = ["fetch_200", "fetch_3xx", "fetch_4xx", "fetch_5xx", "fetch_gone", "fetch_notModified",
           "fetch_other", "robots_200", "robots_4xx", "robots_5xx", "robots_other",
           "nutch_fetched", "nutch_unfetched", "nutch_gone"]


def to_surt(host):
    return ",".join(reversed(host.split(".")))


def crawl_date(crawl):
    """CC-MAIN-2022-05 -> Monday of ISO week 5 of 2022."""
    _, _, year, week = crawl.split("-")
    return date.fromisocalendar(int(year), int(week), 1).isoformat()


def list_crawls():
    r = httpx.get(PATHS_URL, headers={"User-Agent": MONITOR_UA}, timeout=60, trust_env=False)
    r.raise_for_status()
    files = {}
    for path in gzip.decompress(r.content).decode().split():
        crawl = path.split("crawl=")[1].split("/")[0]
        files.setdefault(crawl, []).append(BASE_URL + path)
    return files


def _read_existing():
    if not HOSTS_FILE.exists():
        return []
    with gzip.open(HOSTS_FILE, "rt", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _read_queried():
    if not QUERIED_FILE.exists():
        return set()
    return set(QUERIED_FILE.read_text(encoding="utf-8").split())


def _connect():
    # DuckDB httpfs honours HTTP(S)_PROXY; like the other collectors, connect directly
    for var in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        os.environ.pop(var, None)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(config={"memory_limit": MEMORY_LIMIT, "threads": THREADS,
                                 "preserve_insertion_order": False, "temp_directory": str(TEMP_DIR)})
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute("SET http_retries = 8; SET http_retry_wait_ms = 2000; SET http_timeout = 120000;")
    # Each crawl is read once, so caching its Parquet files only costs memory
    con.execute("SET enable_external_file_cache = false;")
    return con


def _hosts_key(hosts):
    return hashlib.sha1("\n".join(sorted(hosts)).encode()).hexdigest()


def backfill_done(new):
    """Crawls an interrupted run already backfilled for exactly these new hosts."""
    if not BACKFILL_FILE.exists():
        return set()
    state = json.loads(BACKFILL_FILE.read_text(encoding="utf-8"))
    return set(state.get("done", [])) if state.get("hosts") == _hosts_key(new) else set()


def save_backfill(new, done):
    state = {"hosts": _hosts_key(new), "n": len(new), "done": sorted(done)}
    BACKFILL_FILE.write_text(json.dumps(state, indent=1) + "\n", encoding="utf-8")


def _query(con, crawl, urls, hosts):
    """Host index rows of one crawl for the given hosts, or None if a query failed."""
    surt_to_host = {}
    for host in hosts:
        surt_to_host[to_surt(host)] = host
        surt_to_host[to_surt("www." + host)] = host
    groups = {}
    for surt in surt_to_host:
        groups.setdefault(surt.split(",", 1)[0], []).append(surt)
    cols = ", ".join(f"coalesce(try_cast({c} AS BIGINT), 0) AS {c}" for c in COLUMNS)
    rows = []
    for tld, surts in groups.items():
        lo, hi = min(surts), max(surts)
        # A literal IN list (not a subquery) keeps both filters inside the Parquet
        # scan, so only the row groups of this SURT range are downloaded
        values = ",".join("'" + v.replace("'", "''") + "'" for v in sorted(surts))
        sql = f"""
            SELECT surt_host_name, {cols}
            FROM read_parquet(?, union_by_name=true)
            WHERE surt_host_name BETWEEN ? AND ?
              AND surt_host_name IN ({values})
        """
        result = None
        for attempt in range(3):
            try:
                result = con.execute(sql, [urls, lo, hi]).fetchall()
                break
            except duckdb.Error as e:
                log.warning("commoncrawl %s %s failed (attempt %d): %s", crawl, tld, attempt + 1, str(e)[:200])
        if result is None:
            return None
        for surt, *values in result:
            rows.append({"crawl": crawl, "host": surt_to_host[surt], "surt": surt, **dict(zip(COLUMNS, values))})
    return rows


def update(hosts, crawls=None):
    """Query crawls missing from the data for all hosts, and all known crawls for new hosts.

    QUERIED_FILE lists the hosts whose rows cover every crawl in HOSTS_FILE; a host that
    is not there has no Common Crawl data yet, rather than zero fetches.
    """
    CC_DIR.mkdir(parents=True, exist_ok=True)
    files = list_crawls()
    # The crawl list is written first, so builds during a long backfill see it
    write_crawls(files)
    rows = _read_existing()
    done = {r["crawl"] for r in rows}
    queried = _read_queried()
    new = sorted(set(hosts) - queried)
    todo = crawls or [c for c in sorted(files) if c not in done]
    # Evenly spaced crawls first, so a partial backfill already shows the trend
    todo.sort(key=lambda c: (c not in PRIORITY, c))
    backfill = sorted((c for c in done if c in files), key=lambda c: (c not in PRIORITY, c)) if not crawls else []
    log.info("commoncrawl: %d crawls available, %d to query; %d new hosts to backfill in %d crawls",
             len(files), len(todo), len(new) if backfill else 0, len(backfill) if new else 0)
    con = _connect()

    complete = True
    if new and backfill:
        new_set = set(new)
        finished = backfill_done(new)
        if finished:
            log.info("commoncrawl: resuming backfill, %d crawls already done", len(finished & set(backfill)))
        for crawl in backfill:
            if crawl in finished:
                continue
            found = _query(con, crawl, files[crawl], new)
            if found is None:
                log.warning("commoncrawl %s backfill incomplete, will retry on the next run", crawl)
                complete = False
                break
            rows = [r for r in rows if not (r["crawl"] == crawl and r["host"] in new_set)] + found
            log.info("commoncrawl %s backfill: %d host rows for %d new hosts", crawl, len(found), len(new))
            _write(rows)
            finished.add(crawl)
            save_backfill(new, finished)
    for crawl in todo:
        found = _query(con, crawl, files[crawl], hosts)
        if found is None:
            # Leave the crawl out so the next run queries it again
            log.warning("commoncrawl %s incomplete, will retry on the next run", crawl)
            complete = False
            continue
        rows = [r for r in rows if r["crawl"] != crawl] + found
        log.info("commoncrawl %s: %d host rows", crawl, len(found))
        _write(rows)
    if complete and not crawls:
        QUERIED_FILE.write_text("\n".join(sorted(queried | set(hosts))) + "\n", encoding="utf-8")
        BACKFILL_FILE.unlink(missing_ok=True)


def write_crawls(crawls):
    with open(CRAWLS_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["crawl", "date"])
        for crawl in sorted(crawls):
            writer.writerow([crawl, crawl_date(crawl)])


def _write(rows):
    rows = sorted(rows, key=lambda r: (r["crawl"], r["host"], r["surt"]))
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["crawl", "host", "surt"] + COLUMNS)
    writer.writeheader()
    writer.writerows(rows)
    tmp = HOSTS_FILE.with_name(HOSTS_FILE.name + ".tmp")
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        f.write(buf.getvalue())
    tmp.replace(HOSTS_FILE)


def load():
    """(crawls, host rows, hosts covered by every crawl in the rows)."""
    crawls = []
    if CRAWLS_FILE.exists():
        with open(CRAWLS_FILE, encoding="utf-8") as f:
            crawls = list(csv.DictReader(f))
    return crawls, _read_existing(), _read_queried()
