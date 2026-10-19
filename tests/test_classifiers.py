"""Unit tests for the offline parts: python -m unittest discover tests"""
import tempfile
import unittest
from pathlib import Path

from rublocked import build, commoncrawl, fingerprint, registry, wayback
from rublocked.common import month_range, normalize_host
from rublocked.probe import check_vantage, derive_status, parse_robots
from rublocked.whois import registrable


class ClassifyTest(unittest.TestCase):
    def test_content(self):
        page = "<html><title>Минфин</title><body>" + "<a href='/x'>новость</a> текст " * 50 + "</body></html>"
        self.assertEqual(fingerprint.classify(200, page)[0], "content")

    def test_js_shell(self):
        page = '<html><title>Минэнерго</title><script src="/main.js"></script><app-root></app-root></html>' + " " * 5000
        self.assertEqual(fingerprint.classify(200, page)[0], "shell")

    def test_js_gate(self):
        page = "<script>c='/DDoS02/77c9627b';window.location.pathname=c;</script>"
        self.assertEqual(fingerprint.classify(200, page), ("challenge", "js cookie/redirect gate"))

    def test_spa_reading_location_is_shell(self):
        page = ('<html><title></title><script>const e=new URLSearchParams(window.location.search).get("t")</script>'
                '<script src="/app.js"></script><body><div id="app"></div></body></html>')
        self.assertEqual(fingerprint.classify(200, page)[0], "shell")

    def test_cookie_reload_gate(self):
        page = ('<html><title></title><script>document.cookie = "BX_USER_UID=bx5d"; '
                'setTimeout(function(){ window.location.href = "http://x.ru/"; }, 1000);</script></html>')
        self.assertEqual(fingerprint.classify(200, page)[0], "challenge")

    def test_waf_challenge_503(self):
        page = "<html><title>DDoS-Guard</title>Checking your browser before accessing</html>"
        self.assertEqual(fingerprint.classify(503, page)[0], "challenge")

    def test_block_page(self):
        page = "<html><title>Доступ запрещен</title><body>Доступ запрещен</body></html>"
        self.assertEqual(fingerprint.classify(403, page), ("blocked", "доступ запрещен"))

    def test_empty(self):
        self.assertEqual(fingerprint.classify(200, "")[0], "empty")

    def test_server_error(self):
        self.assertEqual(fingerprint.classify(502, "<html>Bad gateway</html>")[0], "server_error")

    def test_vendors(self):
        self.assertEqual(fingerprint.detect_vendors({"Server": "ddos-guard"}), ["ddos-guard"])
        self.assertEqual(fingerprint.detect_vendors(cookies=["spid", "x"]), ["servicepipe"])
        self.assertEqual(fingerprint.detect_vendors(asn_name="CCT-AS NGENIX"), ["ngenix"])
        self.assertEqual(fingerprint.detect_vendors({"Server": "nginx"}), [])

    def test_spam(self):
        self.assertEqual(fingerprint.detect_spam("Пин Ап казино - Вход"), "казино")
        self.assertIsNone(fingerprint.detect_spam("Корпорация МСП", "займы для малого бизнеса"))
        self.assertIsNone(fingerprint.detect_spam("Служба по тарифам"))

    def test_parking(self):
        self.assertEqual(fingerprint.detect_parking("www.reg.ru", ""), "www.reg.ru")
        self.assertEqual(fingerprint.detect_parking("x.ru", "Домен припаркован в Timeweb"), "домен припаркован")
        self.assertIsNone(fingerprint.detect_parking("minfin.gov.ru", "Минфин России"))


class RobotsTest(unittest.TestCase):
    def test_blocks_all(self):
        self.assertEqual(parse_robots("User-agent: *\nDisallow: /\n"), {"blocks_all": True, "blocks_ia": False})

    def test_blocks_ia_only(self):
        text = "User-agent: ia_archiver\nDisallow: /\n\nUser-agent: *\nDisallow: /admin\n"
        self.assertEqual(parse_robots(text), {"blocks_all": False, "blocks_ia": True})

    def test_shared_group(self):
        text = "User-agent: Yandex\nUser-agent: *\nDisallow: /\n"
        self.assertTrue(parse_robots(text)["blocks_all"])

    def test_allows(self):
        self.assertEqual(parse_robots("User-agent: *\nDisallow:\n"), {"blocks_all": False, "blocks_ia": False})


class StatusTest(unittest.TestCase):
    def test_dns(self):
        self.assertEqual(derive_status({"dns": {"status": "nxdomain"}}), "dns")

    def test_timeout(self):
        rec = {"dns": {"status": "ok"}, "tcp": {"443": {"state": "timeout"}, "80": {"state": "timeout"}}}
        self.assertEqual(derive_status(rec), "timeout")

    def test_http_only(self):
        rec = {"dns": {"status": "ok"}, "tcp": {"443": {"state": "timeout"}, "80": {"state": "open"}},
               "http": {"kind": "content"}}
        self.assertEqual(derive_status(rec), "ok")


class HelpersTest(unittest.TestCase):
    def test_normalize_host(self):
        self.assertEqual(normalize_host("https://WWW.Minfin.gov.ru/ru/"), "minfin.gov.ru")
        self.assertEqual(normalize_host("дом.рф"), "xn--d1aqf.xn--p1ai")

    def test_registrable(self):
        self.assertEqual(registrable("www.dep-economy44.ru"), "dep-economy44.ru")
        self.assertEqual(registrable("admin.msk.ru"), "admin.msk.ru")
        self.assertEqual(registrable("xn--d1aqf.xn--p1ai"), "xn--d1aqf.xn--p1ai")
        self.assertIsNone(registrable("roe.com"))

    def test_month_range(self):
        self.assertEqual(month_range("2021-11", "2022-02"), ["2021-11", "2021-12", "2022-01", "2022-02"])

    def test_monthly_series(self):
        spark = {"years": {"2022": [5, 0, 3] + [0] * 9}, "status": {"2022": "243444444444"}}
        counts, classes = wayback.monthly_series(spark, ["2022-01", "2022-02", "2022-03", "2023-01"])
        self.assertEqual(counts, [5, 0, 3, 0])
        self.assertEqual(classes, ["2", "0", "3", "0"])


def _row(domain, kind, name="", status="", priority="", primary="", region="", gov="Федеральная исполнительная власть"):
    return {"Domain": domain, "Domain type": kind, "Name": name, "Status": status, "Archive priority": priority,
            "Primary domain": primary, "Region": region, "GovType": gov, "Organization": ""}


class RegistryTest(unittest.TestCase):
    def test_select(self):
        territorial = "Сайт территориального управления ФОИВ"
        court = "Официальный сайт суда"
        rows = [
            _row("minfin.gov.ru", "Сайт органа власти", status="Активен"),
            _row("www.minfin.gov.ru", "Сайт органа власти"),
            _row("minfin.ru", "Сайт органа власти", primary="minfin.gov.ru"),
            _row("mail.minfin.gov.ru", "Сайт органа власти"),
            _row("en.minfin.gov.ru", "Сайт органа власти"),
            _row("old-site.gov.ru", "Сайт органа власти", status="Неактивен"),
            _row("50.mvd.ru", territorial),
            _row("balashikha.50.mvd.ru", territorial),
            _row("kirov.roskazna.ru", territorial),
            _row("mosu.mvd.ru", "Сайт госучреждения"),
            _row("rf.mosu.mvd.ru", "Сайт госучреждения"),
            _row("oblsud.svd.sudrf.ru", court, "Свердловский областной суд"),
            _row("oblsud--svd.sudrf.ru", court, "Свердловский областной суд"),
            _row("vs.tat.sudrf.ru", court, "Верховный суд Республики Татарстан"),
            _row("mosgorsud.msk.sudrf.ru", court, "Московский городской суд"),
            _row("lugasud.lo.sudrf.ru", court, "Лужский городской суд Ленинградской области"),
            _row("oktb.hmao.sudrf.ru", court, "Октябрьский районный суд Ханты-Мансийского автономного округа"),
            _row("1.kln.msudrf.ru", court, "Судебный участок № 1"),
            _row("belgorod.arbitr.ru", court),
            _row("kad.arbitr.ru", court),
            _row("tatarstan.izbirkom.ru", "Сайт избирательной комиссии"),
            _row("tatarstan.vybory.izbirkom.ru", "Сайт избирательной комиссии"),
            _row("misc.gov.ru", "Иное"),
            _row("gov.ru", "Иное", priority="Наивысший"),
            _row("api.nalog.ru", "Сервис API"),
        ]
        chosen, _ = registry.select(rows)
        self.assertEqual({h: c for h, (c, _) in chosen.items()}, {
            "minfin.gov.ru": "federal", "gov.ru": "federal",
            "50.mvd.ru": "regional", "kirov.roskazna.ru": "regional", "mosu.mvd.ru": "institution",
            "oblsud--svd.sudrf.ru": "courts", "vs.tat.sudrf.ru": "courts", "mosgorsud.msk.sudrf.ru": "courts",
            "belgorod.arbitr.ru": "courts", "kad.arbitr.ru": "courts",
            "tatarstan.izbirkom.ru": "elections",
        })

    def test_region(self):
        self.assertEqual(registry.normalize_region("Ленинградская область,Санкт-Петербург"), "Ленинградская область")
        self.assertEqual(registry.normalize_region("Удмуртская республика"), "Удмуртская Республика")



class VantageTest(unittest.TestCase):
    def test_check_vantage(self):
        check_vantage("ru", {"country": "RU"})
        check_vantage("abroad", {"country": "DE"})
        check_vantage("abroad", {"error": "ipinfo unreachable"})
        with self.assertRaises(RuntimeError):
            check_vantage("ru", {"country": "DE"})
        with self.assertRaises(RuntimeError):
            check_vantage("ru", {"error": "ipinfo unreachable"})
        with self.assertRaises(RuntimeError):
            check_vantage("abroad", {"country": "RU"})

    def test_geo_class(self):
        def geo(abroad, ru):
            d = {"s": abroad, "g": build.STATUS_GROUP[abroad]}
            build._add_ru(d, {"status": ru, "http": {}})
            return d.get("geo")
        self.assertEqual(geo("ok", "ok"), "open")
        self.assertEqual(geo("timeout", "ok"), "geoblock")
        self.assertEqual(geo("challenge", "ok"), "geoblock")
        self.assertEqual(geo("timeout", "timeout"), "closed")
        self.assertEqual(geo("ok", "refused"), "ru_fail")
        self.assertIsNone(geo("dns", "ok"))
        d = {"s": "ok", "g": "ok"}
        build._add_ru(d, None)
        self.assertNotIn("rs", d)



class BackfillTest(unittest.TestCase):
    def test_resume_only_for_same_hosts(self):
        saved = commoncrawl.BACKFILL_FILE
        with tempfile.TemporaryDirectory() as tmp:
            commoncrawl.BACKFILL_FILE = Path(tmp) / "backfill.json"
            try:
                self.assertEqual(commoncrawl.backfill_done(["a.ru", "b.ru"]), set())
                commoncrawl.save_backfill(["b.ru", "a.ru"], {"CC-MAIN-2022-05"})
                self.assertEqual(commoncrawl.backfill_done(["a.ru", "b.ru"]), {"CC-MAIN-2022-05"})
                # The registry changed: the saved progress is for other hosts
                self.assertEqual(commoncrawl.backfill_done(["a.ru", "c.ru"]), set())
            finally:
                commoncrawl.BACKFILL_FILE = saved


if __name__ == "__main__":
    unittest.main()
