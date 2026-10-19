"""Classify an HTTP response: real content, WAF challenge, block page or error.

The same classifier runs on live probe responses and on archived Wayback snapshots, so
"archived" can mean "archived with real content" instead of "a capture exists".
"""
import re

# Protection and CDN vendors common on Russian government sites. Each rule lists
# substrings searched in the Server header, cookie names, other header names, the
# body, the CNAME chain and the AS name of the hosting network.
VENDORS = {
    "ddos-guard": {"server": ["ddos-guard"], "cookie": ["__ddg"], "body": ["ddos-guard"],
                   "cname": ["ddos-guard"], "asn": ["ddos-guard"]},
    "qrator": {"server": ["qrator"], "header": ["x-qrator"], "body": ["qrator"],
               "cname": ["qrator"], "asn": ["qrator", "curator"]},
    "servicepipe": {"cookie": ["spid", "spsc", "spsn"], "body": ["servicepipe"],
                    "cname": ["servicepipe"], "asn": ["servicepipe"]},
    "stormwall": {"server": ["stormwall"], "cookie": ["swp_token"], "body": ["stormwall"],
                  "cname": ["stormwall"], "asn": ["stormwall"]},
    "variti": {"server": ["variti"], "body": ["variti"], "cname": ["variti"], "asn": ["variti"]},
    "ngenix": {"server": ["ngenix"], "header": ["x-ngenix"], "cname": ["ngenix"], "asn": ["ngenix"]},
    "cloudflare": {"server": ["cloudflare"], "header": ["cf-ray"], "cname": ["cloudflare"],
                   "asn": ["cloudflare"]},
    "gcore": {"server": ["gcore"], "cname": ["gcdn.co", "gcorelabs"], "asn": ["g-core", "gcore"]},
    "bizone": {"body": ["bi.zone"], "cname": ["bizone"], "asn": ["bi.zone", "bizone"]},
    "cdnvideo": {"server": ["cdnvideo"], "cname": ["cdnvideo"], "asn": ["cdnvideo"]},
}

CHALLENGE_MARKERS = [
    "checking your browser", "проверка браузера", "проверяем ваш браузер", "проверка вашего браузера",
    "please enable javascript", "please enable cookies", "включите javascript",
    "enable javascript and cookies", "js-challenge", "challenge-platform", "ddos protection",
    "защита от ddos", "проверка на робота", "you are not a robot", "я не робот",
    "smartcaptcha", "captcha-container", "g-recaptcha", "h-captcha", "<title>just a moment",
    "<title>ddos-guard", "servicepipe.ru", "__qrator", "data-variti",
    "data processing... please, wait",
]

BLOCK_MARKERS = [
    "access denied", "access forbidden", "403 forbidden", "доступ запрещен", "доступ запрещён",
    "доступ ограничен", "доступ к сайту ограничен", "access is restricted", "access restricted",
    "not available in your region", "not available in your country", "from your country",
    "from your region", "из вашей страны", "из вашего региона", "для вашего региона",
    "недоступен в вашем регионе", "ваш ip-адрес заблокирован", "your ip address has been blocked",
    "request blocked", "запрос заблокирован", "the requested url was rejected",
    "web application firewall", "request rejected",
]

# A script that writes a cookie or navigates away, not one that only reads the URL
JS_GATE_RE = re.compile(r"(?:window\.|document\.)?location(?:\.href|\.pathname)?\s*=[^=]"
                        r"|location\.(?:replace|reload|assign)\s*\(|document\.cookie\s*=[^=]|/ddos0")
APP_ROOT_RE = re.compile(r'id=["\'](?:app|root|__next|__nuxt)["\']|<app-root|ng-app|data-reactroot', re.I)

# Registrar shops and parking services that expired domains redirect to
PARKING_HOSTS = ["reg.ru", "nic.ru", "r01.ru", "webnames.ru", "2domains.ru", "sedo.com", "dan.com",
                 "afternic.com", "parkingcrew.net", "bodis.com", "domains.ru", "timeweb.ru", "beget.com"]
PARKING_MARKERS = ["домен продается", "домен продаётся", "домен припаркован", "domain is for sale",
                   "this domain is for sale", "buy this domain", "домен зарегистрирован в", "parked domain",
                   "сайт не опубликован", "домен не прилинкован"]

# Gambling, loan and adult spam typical of expired government domains taken over by
# third parties. Strong markers count anywhere; weak ones only in the title.
SPAM_STRONG = ["казино", "casino", "1xbet", "букмекер", "pin up", "pin-up", "pinup", "вулкан", "vavada",
               "joycasino", "riobet", "mostbet", "melbet", "игровые автоматы", "слоты", "фриспин",
               "porn", "порно", "escort", "эскорт"]
SPAM_WEAK = ["займ", "кредит онлайн", "ставки на спорт", "зеркало"]


def detect_spam(title, text=""):
    title = (title or "").lower()
    for marker in SPAM_STRONG + SPAM_WEAK:
        if marker in title:
            return marker
    low = (text or "")[:100000].lower()
    hits = [m for m in SPAM_STRONG if m in low]
    return hits[0] if len(hits) >= 2 else None


_SCRIPT_RE = re.compile(r"<(script|style|noscript)[^>]*>.*?</\1>", re.S | re.I)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)
_LINK_RE = re.compile(r"<a\s[^>]*href", re.I)
_SCRIPT_TAG_RE = re.compile(r"<script", re.I)


def decode_body(body, content_type=""):
    charset = None
    m = re.search(r"charset=([\w-]+)", content_type or "", re.I)
    if m:
        charset = m.group(1)
    else:
        m = re.search(rb"<meta[^>]+charset=[\"']?([\w-]+)", body[:4096], re.I)
        if m:
            charset = m.group(1).decode("ascii", "ignore")
    for enc in (charset, "utf-8", "cp1251"):
        if not enc:
            continue
        try:
            return body.decode(enc)
        except (LookupError, UnicodeDecodeError):
            continue
    return body.decode("utf-8", "replace")


def page_stats(text):
    title = _TITLE_RE.search(text)
    visible = _WS_RE.sub(" ", _TAG_RE.sub(" ", _SCRIPT_RE.sub(" ", text))).strip()
    return {
        "title": _WS_RE.sub(" ", title.group(1)).strip()[:200] if title else "",
        "text_len": len(visible),
        "links": len(_LINK_RE.findall(text)),
        "scripts": len(_SCRIPT_TAG_RE.findall(text)),
    }


def detect_vendors(headers=None, cookies=(), body_lower="", cnames=(), asn_name=""):
    """Return a sorted list of protection/CDN vendors seen in the response or network."""
    headers = {k.lower(): v.lower() for k, v in (headers or {}).items()}
    server = headers.get("server", "")
    cookies = [c.lower() for c in cookies]
    cnames = " ".join(cnames).lower()
    asn_name = (asn_name or "").lower()
    found = set()
    for vendor, rules in VENDORS.items():
        if any(s in server for s in rules.get("server", [])):
            found.add(vendor)
        elif any(c.startswith(p) for p in rules.get("cookie", []) for c in cookies):
            found.add(vendor)
        elif any(h in headers for h in rules.get("header", [])):
            found.add(vendor)
        elif any(s in body_lower for s in rules.get("body", [])):
            found.add(vendor)
        elif cnames and any(s in cnames for s in rules.get("cname", [])):
            found.add(vendor)
        elif asn_name and any(s in asn_name for s in rules.get("asn", [])):
            found.add(vendor)
    return sorted(found)


def classify(status, text, stats=None):
    """Return (kind, reason) for a final HTTP response.

    kind is one of: content, shell, challenge, blocked, empty, client_error, server_error.
    A 200 response counts as content unless there is explicit evidence otherwise, so
    single-page applications with little server-rendered text are not penalised.
    """
    stats = stats or page_stats(text)
    low = text[:200000].lower()
    small = stats["text_len"] < 1500 and stats["links"] < 15
    challenge = next((m for m in CHALLENGE_MARKERS if m in low), None)
    block = next((m for m in BLOCK_MARKERS if m in low), None)

    if status in (401, 403, 429, 451) or (status and status >= 500 and status != 503):
        if challenge:
            return "challenge", challenge
        if status >= 500:
            return "server_error", f"http {status}"
        return "blocked", block or f"http {status}"
    if status == 503:
        # DDoS-Guard and others answer 503 with a JS challenge
        return ("challenge", challenge) if challenge else ("server_error", "http 503")
    if status and status >= 400:
        return "client_error", f"http {status}"
    if challenge and small:
        return "challenge", challenge
    if block and small:
        return "blocked", block
    if stats["text_len"] < 30 and stats["links"] == 0 and stats["scripts"] == 0:
        return "empty", "no text"
    if stats["text_len"] < 200 and stats["links"] < 5 and stats["scripts"] > 0:
        # A small script that sets a cookie or reloads the page is an anti-bot check:
        # crawlers that do not run JavaScript never get past it
        if (len(text) < 4096 or not stats["title"]) and JS_GATE_RE.search(low) and not APP_ROOT_RE.search(text):
            return "challenge", "js cookie/redirect gate"
        # A JavaScript application shell: the page is real, but the HTML carries no
        # content, so an archived copy usually replays as a blank page
        return "shell", "js app shell"
    return "content", ""


def detect_parking(final_host, title):
    """Return a marker when the domain is parked or offered for sale."""
    final_host = (final_host or "").lower()
    if any(final_host == h or final_host.endswith("." + h) for h in PARKING_HOSTS):
        return final_host
    title = (title or "").lower()
    return next((m for m in PARKING_MARKERS if m in title), None)
