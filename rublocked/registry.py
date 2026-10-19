"""Build the monitored domain registry from the Orgview export of the government domains base.

The source (data/registry/Domains-Orgview.csv) lists about 7,700 hosts of federal bodies,
their regional offices, courts and election commissions with a curated type, status and
archive priority. Only significant sites enter the registry: main sites of federal and
regional bodies, state information systems and institutions, subject-level courts and
election commissions. Aliases, technical hosts, language and mobile versions, sites
marked inactive or not worth archiving, district courts and sub-regional offices are left
out.

The registry is a CSV committed to the repository (data/registry/domains.csv). It is
rebuilt only when the source list changes, so monthly runs measure a stable cohort.
"""
import collections
import csv
import logging
import re

from .common import DATA_DIR, normalize_host, host_display

log = logging.getLogger(__name__)

SOURCE_FILE = DATA_DIR / "registry" / "Domains-Orgview.csv"
REGISTRY_FILE = DATA_DIR / "registry" / "domains.csv"
FIELDS = ["host", "display", "category", "name", "org", "region", "type", "priority"]

CATEGORIES = {
    "federal": "Федеральные органы власти",
    "gis": "Государственные информационные системы и порталы",
    "institution": "Госучреждения, фонды и программы",
    "regional": "Территориальные органы и региональные органы власти",
    "courts": "Суды",
    "elections": "Избирательные комиссии",
}

# Domain types of the source kept in the registry
TYPE_CATEGORY = {
    "Сайт органа власти": "federal",
    "Сайт комиссии/совета/комитета": "federal",
    "Сайт подразделения при органе власти": "federal",
    "Сайт общ/эксп/консультативного органа": "federal",
    "Сайт государственной информационной системы": "gis",
    "Портал открытых данных": "gis",
    "Сайт госучреждения": "institution",
    "Сайт государственной НКО": "institution",
    "Сайт государственной программы/проекта": "institution",
    "Просветительский сайт": "institution",
    "Сайт госкорпорации": "institution",
    "Сайт особой государственной организации": "institution",
    "Сайт СМИ": "institution",
    "Сайт территориального управления ФОИВ": "regional",
    "Сайт правительства субъекта федерации": "regional",
    "Официальный сайт суда": "courts",
    "Сайт избирательной комиссии": "elections",
}
# "Иное" is mostly technical hosts; only the ones curated as high archive priority stay
OTHER_TYPE = "Иное"
HIGH_PRIORITY = {"Наивысший", "Высокий"}
SKIP_STATUS = {"Неактивен", "Запаролено", "Пустая страница", "Перенаправляет", "Другой сайт"}
SKIP_PRIORITY = {"Не архивируется", "Незначительный"}
# Subdomain labels of services, mirrors, language and mobile versions, test servers
TECH_LABELS = {
    "autodiscover", "mail", "webmail", "owa", "smtp", "pop", "imap", "mx", "ftp", "vpn", "pda", "m", "mobile",
    "wap", "en", "eng", "english", "cn", "zh", "de", "fr", "es", "old", "new", "last", "beta", "adm", "admin",
    "limited", "api", "static", "cdn", "special", "forum", "lk", "calc", "guard",
}
# and personal account logins (lk, lkfl2, lknpd)
TECH_PATTERN = re.compile(r"^(test|dev|demo|stage|staging|lk)|old$")
# A label that is a region code marks an office below another regional office
REGION_CODE = re.compile(r"^(r|to|tu|git|ufk)?(\d{2,3})(reg)?$")
# Registrable domains under which bodies get a third-level domain
SHARED_SLD = {"gov.ru", "msk.ru", "spb.ru"}
# Courts of the subject level and above; district courts and magistrates are left out
HIGH_COURT = re.compile(r"областн|краев|верховн|окружн|апелляц|кассац|арбитражн|автономн|интеллектуальн|"
                        r"конституционн|уставн")
LOW_COURT = re.compile(r"районн|гарнизонн|миров|участ|городской суд")
CITY_COURT = re.compile(r"^(московский|санкт-петербургский|севастопольский) городской суд")
JUDICIAL_OFFICE = "управление судебного департамента"

REGIONS = {
    "01": "Республика Адыгея", "02": "Республика Башкортостан", "03": "Республика Бурятия",
    "04": "Республика Алтай", "05": "Республика Дагестан", "06": "Республика Ингушетия",
    "07": "Кабардино-Балкарская Республика", "08": "Республика Калмыкия",
    "09": "Карачаево-Черкесская Республика", "10": "Республика Карелия", "11": "Республика Коми",
    "12": "Республика Марий Эл", "13": "Республика Мордовия", "14": "Республика Саха (Якутия)",
    "15": "Республика Северная Осетия — Алания", "16": "Республика Татарстан", "17": "Республика Тыва",
    "18": "Удмуртская Республика", "19": "Республика Хакасия", "20": "Чеченская Республика",
    "21": "Чувашская Республика", "22": "Алтайский край", "23": "Краснодарский край",
    "24": "Красноярский край", "25": "Приморский край", "26": "Ставропольский край",
    "27": "Хабаровский край", "28": "Амурская область", "29": "Архангельская область",
    "30": "Астраханская область", "31": "Белгородская область", "32": "Брянская область",
    "33": "Владимирская область", "34": "Волгоградская область", "35": "Вологодская область",
    "36": "Воронежская область", "37": "Ивановская область", "38": "Иркутская область",
    "39": "Калининградская область", "40": "Калужская область", "41": "Камчатский край",
    "42": "Кемеровская область", "43": "Кировская область", "44": "Костромская область",
    "45": "Курганская область", "46": "Курская область", "47": "Ленинградская область",
    "48": "Липецкая область", "49": "Магаданская область", "50": "Московская область",
    "51": "Мурманская область", "52": "Нижегородская область", "53": "Новгородская область",
    "54": "Новосибирская область", "55": "Омская область", "56": "Оренбургская область",
    "57": "Орловская область", "58": "Пензенская область", "59": "Пермский край",
    "60": "Псковская область", "61": "Ростовская область", "62": "Рязанская область",
    "63": "Самарская область", "64": "Саратовская область", "65": "Сахалинская область",
    "66": "Свердловская область", "67": "Смоленская область", "68": "Тамбовская область",
    "69": "Тверская область", "70": "Томская область", "71": "Тульская область",
    "72": "Тюменская область", "73": "Ульяновская область", "74": "Челябинская область",
    "75": "Забайкальский край", "76": "Ярославская область", "77": "Москва",
    "78": "Санкт-Петербург", "79": "Еврейская автономная область",
    "83": "Ненецкий автономный округ", "86": "Ханты-Мансийский автономный округ — Югра",
    "87": "Чукотский автономный округ", "89": "Ямало-Ненецкий автономный округ",
    "91": "Республика Крым", "92": "Севастополь",
}
FEDERATION = "Российская Федерация"

REGION_ALIASES = {
    "ханты-мансийский автономный округ": "Ханты-Мансийский автономный округ — Югра",
}


def _region_key(name):
    return " ".join(name.lower().replace("—", "-").replace(" - ", "-").replace("ё", "е").split())


_CANONICAL = {_region_key(name): name for name in REGIONS.values()}


def normalize_region(name):
    """Map spelling variants to one canonical region name.

    Offices covering several regions list them all; the first one is where they sit.
    """
    name = (name or "").split(",")[0].strip()
    if not name:
        return name
    key = _region_key(name)
    return REGION_ALIASES.get(key) or _CANONICAL.get(key, name)


def _base(host):
    """The domain of the body itself: example.ru, or example.gov.ru under a shared zone."""
    labels = host.split(".")
    n = 3 if ".".join(labels[-2:]) in SHARED_SLD else 2
    return ".".join(labels[-n:])


def _region_from_host(host, slugs):
    """Region of a regional office from a code (to02.minjust.ru) or a known slug (bryansk.fas.gov.ru)."""
    for label in host.split("."):
        m = REGION_CODE.match(label)
        if m and m.group(2) in REGIONS:
            return REGIONS[m.group(2)]
    return slugs.get(host.split(".")[0], "")


def _region_slugs(rows):
    """First labels that the source ties to a single region, such as bryansk or tatarstan."""
    seen = collections.defaultdict(collections.Counter)
    for r in rows:
        region = normalize_region(r["Region"])
        if region in _CANONICAL.values() and "," not in r["Region"]:
            seen[normalize_host(r["Domain"]).split(".")[0]][region] += 1
    return {label: c.most_common(1)[0][0] for label, c in seen.items()
            if len(c) == 1 and not REGION_CODE.match(label) and sum(c.values()) >= 2}


def _category(r, host):
    """Category of a source row, or None with the reason it is left out."""
    kind, gov = r["Domain type"], r["GovType"]
    if kind == OTHER_TYPE:
        if r["Archive priority"] not in HIGH_PRIORITY:
            return None, "other"
        category = "federal"
    else:
        category = TYPE_CATEGORY.get(kind)
        if not category:
            return None, "type"
    # Some court sites are typed as regional offices of the Judicial Department
    if category == "regional" and host.endswith((".arbitr.ru", ".sudrf.ru")):
        category = "courts"
    if category == "courts" and host != _base(host):
        if host.endswith(".arbitr.ru"):
            # Every arbitration court is of the subject level or above
            if host.count(".") > 2:
                return None, "court"
        else:
            name = " ".join(r["Name"].lower().split())
            if name.startswith(JUDICIAL_OFFICE):
                return "regional", None
            if not (CITY_COURT.search(name) or (HIGH_COURT.search(name) and not LOW_COURT.search(name))):
                return None, "court"
    if category == "elections" and host.count(".") > 2:
        return None, "elections"
    if category == "federal" and gov == "Судебная власть":
        category = "courts"
    elif category == "federal" and gov == "Избирательные комиссии":
        category = "elections"
    elif gov == "Региональная власть":
        category = "regional"
    return category, None


def select(rows):
    """Pick significant hosts from source rows; returns ({host: (category, row)}, Counter of reasons)."""
    variants = collections.defaultdict(list)
    for r in rows:
        host = normalize_host(r["Domain"])
        if host and "." in host:
            variants[host].append(r)

    chosen, dropped = {}, collections.Counter()
    for host, rs in variants.items():
        sub = host[: -len(_base(host))].strip(".").split(".") if host != _base(host) else []
        if any(label in TECH_LABELS or TECH_PATTERN.search(label) for label in sub):
            dropped["technical"] += 1
            continue
        # An office below a regional office, such as a district police department
        if any(REGION_CODE.match(label) for label in sub[1:]):
            dropped["subregional"] += 1
            continue
        active = any(r["Status"] == "Активен" for r in rs)
        reason = None
        for r in rs:
            primary = normalize_host(r["Primary domain"]) if r["Primary domain"].strip() else ""
            if primary and primary != host:
                reason = reason or "alias"
            elif r["Status"] in SKIP_STATUS and not active:
                reason = reason or "status"
            elif r["Archive priority"] in SKIP_PRIORITY:
                reason = reason or "priority"
            else:
                category, why = _category(r, host)
                if category:
                    chosen[host] = (category, r)
                    break
                reason = reason or why
        else:
            dropped[reason] += 1

    # Branches of a site already in the registry, such as a university's regional branch
    for host in sorted(chosen, key=lambda h: h.count(".")):
        base = _base(host)
        parent = host.split(".", 1)[1]
        while len(parent) > len(base):
            if parent in chosen:
                del chosen[host]
                dropped["branch"] += 1
                break
            parent = parent.split(".", 1)[1]
    # Two spellings of one site: oblsud--svd.sudrf.ru and oblsud.svd.sudrf.ru, altai_rep and altai-rep
    for host in list(chosen):
        twin = None
        if host.endswith(".sudrf.ru") and "--" not in host:
            twin = host.replace(".", "--", host.count(".") - 2)
        elif "_" in host:
            twin = host.replace("_", "-")
        if twin and twin != host and twin in chosen:
            del chosen[host]
            dropped["duplicate"] += 1
    return chosen, dropped


def build():
    with open(SOURCE_FILE, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    chosen, dropped = select(rows)
    log.info("source: %d rows, %d selected; left out: %s", len(rows), len(chosen), dict(dropped.most_common()))
    slugs = _region_slugs(rows)
    result = []
    for host, (category, r) in chosen.items():
        region = normalize_region(r["Region"])
        if category in ("regional", "courts", "elections") and region in ("", FEDERATION):
            region = _region_from_host(host, slugs) or region
        if not region and category in ("federal", "gis", "institution"):
            region = FEDERATION
        result.append({"host": host, "display": host_display(host), "category": category,
                       "name": " ".join(r["Name"].split()), "org": " ".join(r["Organization"].split()),
                       "region": region, "type": r["Domain type"], "priority": r["Archive priority"]})
    result.sort(key=lambda r: (r["category"], r["host"]))
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(REGISTRY_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(result)
    return result


def load():
    with open(REGISTRY_FILE, encoding="utf-8") as f:
        return list(csv.DictReader(f))
