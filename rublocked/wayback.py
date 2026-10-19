"""Wayback Machine coverage of the monitored sites.

Two collectors:

* sparklines: one request per host returns the number of homepage captures per month
  for the whole history and the best HTTP status class of each month ('2' = a 200
  capture exists, '3' = redirects only, '4'/'5' = errors only or no captures).
* snapshots: for every year with a 200 capture, the last such capture is downloaded
  and classified with fingerprint.classify, because a 200 capture can still be a WAF
  challenge or an empty page.
"""
import concurrent.futures
import hashlib
import json
import logging
import threading
import time
from datetime import date

import httpx

from . import fingerprint
from .common import DATA_DIR, MONITOR_UA, START_MONTH, current_month, read_jsonl, utcnow, write_jsonl

log = logging.getLogger(__name__)

WAYBACK_DIR = DATA_DIR / "wayback"
SPARKLINE_DIR = WAYBACK_DIR / "sparkline"
SNAPSHOTS_FILE = WAYBACK_DIR / "snapshots.jsonl.gz"
SPARKLINE_URL = "https://web.archive.org/__wb/sparkline"
CDX_URL = "https://web.archive.org/cdx/search/cdx"
FIRST_YEAR = int(START_MONTH[:4])
MAX_SNAPSHOT = 512 * 1024


class Client:
    """HTTP client for archive.org with adaptive, polite pacing.

    archive.org answers bursts with 429 and then refuses connections from the client
    IP for a while, so the interval between requests grows on every throttling
    signal and shrinks slowly after a run of successful requests.
    """

    def __init__(self, min_interval=1.2, max_interval=12.0):
        self.http = httpx.Client(trust_env=False, timeout=httpx.Timeout(90, connect=20),
                                 headers={"User-Agent": MONITOR_UA}, follow_redirects=True)
        self.floor = min_interval
        self.ceiling = max_interval
        self.interval = min_interval
        self.lock = threading.Lock()
        self.last = 0.0
        self.streak = 0

    def _throttled(self, reason, factor=1.5, pause=60):
        with self.lock:
            self.interval = min(self.ceiling, self.interval * factor)
            self.streak = 0
        log.warning("archive.org throttling (%s): interval now %.1fs, pausing %ds", reason, self.interval, pause)
        time.sleep(pause)

    def _ok(self):
        with self.lock:
            self.streak += 1
            if self.streak >= 25:
                self.interval = max(self.floor, self.interval * 0.85)
                self.streak = 0

    def get(self, url, params=None, stream_limit=None, tries=6):
        for attempt in range(tries):
            with self.lock:
                wait = self.last + self.interval - time.monotonic()
                if wait > 0:
                    time.sleep(wait)
                self.last = time.monotonic()
            try:
                if stream_limit:
                    with self.http.stream("GET", url, params=params) as r:
                        body = bytearray()
                        for chunk in r.iter_bytes():
                            body.extend(chunk)
                            if len(body) >= stream_limit:
                                break
                        r._content = bytes(body)  # keep a truncated body on the response
                        resp = r
                else:
                    resp = self.http.get(url, params=params)
            except (httpx.ConnectError, httpx.ConnectTimeout) as e:
                # Refused connections follow throttling; timeouts are often the network
                self._throttled(type(e).__name__, factor=1.2, pause=30)
                continue
            except httpx.HTTPError as e:
                log.warning("%s %s: %s (attempt %d)", url, params, e, attempt + 1)
                time.sleep(10)
                continue
            if resp.status_code == 429:
                self._throttled("429")
                continue
            if resp.status_code in (502, 503, 504):
                log.warning("%s answered %d (attempt %d)", url, resp.status_code, attempt + 1)
                time.sleep(20)
                continue
            self._ok()
            return resp
        return None


def sparkline_path(host):
    return SPARKLINE_DIR / f"{host}.json"


def load_sparkline(host):
    path = sparkline_path(host)
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def update_sparklines(hosts, force=False, concurrency=3):
    SPARKLINE_DIR.mkdir(parents=True, exist_ok=True)
    month = current_month()
    client = Client()
    todo = []
    for host in hosts:
        cached = load_sparkline(host)
        if force or not cached or not cached.get("fetched", "").startswith(month):
            todo.append(host)
    log.info("sparklines: %d of %d hosts to fetch", len(todo), len(hosts))
    done = 0
    lock = threading.Lock()

    def work(host):
        nonlocal done
        resp = client.get(SPARKLINE_URL, params={"output": "json", "url": host, "collection": "web"})
        if resp is None or resp.status_code != 200:
            log.warning("sparkline failed for %s: %s", host, resp and resp.status_code)
            return
        try:
            data = resp.json()
        except ValueError:
            log.warning("sparkline for %s is not JSON", host)
            return
        record = {"host": host, "fetched": utcnow().isoformat(timespec="seconds"),
                  "first_ts": data.get("first_ts"), "last_ts": data.get("last_ts"),
                  "years": data.get("years") or {}, "status": data.get("status") or {}}
        with open(sparkline_path(host), "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, separators=(",", ":"))
        with lock:
            done += 1
            if done % 100 == 0:
                log.info("sparklines: %d/%d", done, len(todo))

    # Requests overlap, but their start times are paced by the shared client
    with concurrent.futures.ThreadPoolExecutor(concurrency) as pool:
        list(pool.map(work, todo))


def monthly_series(spark, months):
    """Return (counts, classes) aligned with months; class is '2', '3', '4', '5' or '0' (none)."""
    counts, classes = [], []
    years = (spark or {}).get("years", {})
    status = (spark or {}).get("status", {})
    for m in months:
        y, mm = m.split("-")
        values = years.get(y) or [0] * 12
        count = values[int(mm) - 1] if len(values) >= int(mm) else 0
        st = status.get(y, "")
        cls = st[int(mm) - 1] if len(st) >= int(mm) else "0"
        counts.append(count)
        classes.append(cls if count else "0")
    return counts, classes


def _snapshot_years(spark):
    """Map year -> last month (1-12) with a 200 homepage capture."""
    out = {}
    for year, st in sorted((spark or {}).get("status", {}).items()):
        counts = (spark.get("years") or {}).get(year) or []
        months = [i + 1 for i, (c, n) in enumerate(zip(st, counts)) if c == "2" and n]
        if int(year) >= FIRST_YEAR and months:
            out[int(year)] = months[-1]
    return out


def _replay(client, ts, original):
    snap = client.get(f"https://web.archive.org/web/{ts}id_/{original}", stream_limit=MAX_SNAPSHOT)
    if snap is None:
        return None, None
    x_ts = snap.headers.get("x-ts", "")
    return snap, int(x_ts) if x_ts.isdigit() else snap.status_code


def last_captures(client, host):
    """Return {year: (timestamp, original)} of the last month's first HTTP 200 capture.

    One CDX request per host: captures are collapsed to the first 200 HTML capture of
    each month, so the result has at most one row per month since FIRST_YEAR.
    """
    resp = client.get(CDX_URL, params={"url": host + "/", "from": str(FIRST_YEAR),
                                        "filter": ["statuscode:200", "mimetype:text/html"],
                                        "collapse": "timestamp:6", "fl": "timestamp,original",
                                        "output": "json"})
    if resp is None or resp.status_code != 200:
        return None
    try:
        rows = resp.json()
    except ValueError:
        return None
    out = {}
    for ts, original in rows[1:]:
        out[int(ts[:4])] = (ts, original)  # rows are in time order, the last one wins
    return out


def classify_snapshot(client, host, year, ts, original):
    """Download the capture at its exact timestamp (no redirect) and classify it."""
    rec = {"host": host, "year": year, "checked": utcnow().isoformat(timespec="seconds"),
           "timestamp": ts, "original": original}
    snap, status = _replay(client, ts, original)
    if snap is None:
        rec["error"] = "fetch failed"
        return rec
    body = snap.content
    text = fingerprint.decode_body(body, snap.headers.get("content-type", ""))
    stats = fingerprint.page_stats(text)
    rec["status"] = status
    rec.update(stats)
    rec["size"] = len(body)
    rec["sha1"] = hashlib.sha1(body).hexdigest()
    rec["source"] = snap.headers.get("x-archive-src", "")[:120]
    rec["kind"], rec["reason"] = fingerprint.classify(status, text, stats)
    rec["spam"] = fingerprint.detect_spam(stats["title"], text)
    return rec


def load_snapshots():
    return {(r["host"], r["year"]): r for r in read_jsonl(SNAPSHOTS_FILE)}


def update_snapshots(hosts, concurrency=1):
    """Classify the last 200 capture of every year; past years are checked once.

    The current year and the 2021 baseline go first, so a partial run already answers
    "then versus now"; the other years follow in a second pass.
    """
    existing = load_snapshots()
    this_year = date.today().year
    month = current_month()
    todo = {}
    for host in hosts:
        for year in _snapshot_years(load_sparkline(host)):
            done = existing.get((host, year))
            if done and not done.get("error") and (year < this_year - 1 or done["checked"].startswith(month)):
                continue
            todo.setdefault(host, set()).add(year)
    first = {this_year, 2021}
    passes = [first, {y for ys in todo.values() for y in ys} - first]
    log.info("snapshots: %d host-years on %d hosts to classify", sum(map(len, todo.values())), len(todo))
    client = Client()
    lock = threading.Lock()
    captures = {}
    done_count = 0

    def save():
        write_jsonl(SNAPSHOTS_FILE, sorted(existing.values(), key=lambda r: (r["host"], r["year"])))

    def work(item):
        nonlocal done_count
        host, years = item
        if host not in captures:
            captures[host] = last_captures(client, host)
        caps = captures[host]
        for year in sorted(years):
            if caps is None:
                rec = {"host": host, "year": year, "checked": utcnow().isoformat(timespec="seconds"),
                       "error": "cdx failed"}
            elif year not in caps:
                rec = {"host": host, "year": year, "checked": utcnow().isoformat(timespec="seconds"),
                       "kind": "none"}
            else:
                rec = classify_snapshot(client, host, year, *caps[year])
            with lock:
                existing[(host, year)] = rec
                done_count += 1
                if done_count % 200 == 0:
                    log.info("snapshots: %d host-years done", done_count)
                    save()

    for years in passes:
        items = [(h, ys & years) for h, ys in sorted(todo.items()) if ys & years]
        log.info("snapshots pass %s: %d hosts", sorted(years), len(items))
        with concurrent.futures.ThreadPoolExecutor(concurrency) as pool:
            list(pool.map(work, items))
        save()
