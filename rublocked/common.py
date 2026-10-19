import gzip
import json
from datetime import date, datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
SITE_DIR = ROOT_DIR / "site"

# Identify the monitor honestly to archive services; probes of the measured sites use a
# browser user agent instead, because many WAFs block unknown agents outright.
MONITOR_UA = "ruarxive-blocked-monitor/0.1 (+https://ruarxive.org/russia-blocked/; archivability research)"
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

# The first month of the observation window
START_MONTH = "2019-01"


def normalize_host(value):
    value = value.strip().lower()
    if "://" in value:
        value = value.split("://", 1)[1]
    value = value.split("/", 1)[0].split(":", 1)[0].strip(".")
    if value.startswith("www."):
        value = value[4:]
    try:
        # Store IDN hosts in punycode, as DNS and archive indexes use it
        value = value.encode("idna").decode("ascii")
    except UnicodeError:
        pass
    return value


def host_display(host):
    try:
        return host.encode("ascii").decode("idna")
    except UnicodeError:
        return host


def utcnow():
    return datetime.now(timezone.utc)


def current_month():
    return utcnow().strftime("%Y-%m")


def month_range(start, end):
    """Inclusive list of YYYY-MM strings."""
    y, m = map(int, start.split("-"))
    ey, em = map(int, end.split("-"))
    out = []
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def write_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    opener = gzip.open if path.suffix == ".gz" else open
    # Write to a temporary file and rename, so a build running meanwhile never reads half a file
    tmp = path.with_name(path.name + ".tmp")
    with opener(tmp, "wt", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    tmp.replace(path)


def read_jsonl(path):
    path = Path(path)
    if not path.exists():
        return []
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def today():
    return date.today().isoformat()
