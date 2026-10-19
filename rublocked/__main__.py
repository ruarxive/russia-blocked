"""Command line: python -m rublocked <command>."""
import argparse
import logging

from . import registry
from .common import current_month


def main():
    parser = argparse.ArgumentParser(prog="rublocked", description=__doc__)
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("registry", help="rebuild data/registry/domains.csv from the Orgview export")

    p = sub.add_parser("probe", help="probe all registry hosts from this vantage point")
    p.add_argument("--month", default=None)
    p.add_argument("--vantage", choices=["abroad", "ru"], default="abroad",
                   help="side of the border the network is on; ru runs inside the VPN container (scripts/probe-ru.sh)")
    p.add_argument("--concurrency", type=int, default=None, help="parallel hosts (default 40 abroad, 10 from Russia)")
    p.add_argument("--limit", type=int, default=0, help="probe only the first N hosts (testing)")
    p.add_argument("--hosts", nargs="*", help="probe only these hosts")

    w = sub.add_parser("wayback", help="refresh Wayback Machine monthly capture history")
    w.add_argument("--limit", type=int, default=0)
    w.add_argument("--force", action="store_true", help="refetch even if fetched this month")

    s = sub.add_parser("snapshots", help="classify the content of sampled Wayback snapshots")
    s.add_argument("--limit", type=int, default=0)
    s.add_argument("--concurrency", type=int, default=1)

    c = sub.add_parser("commoncrawl", help="collect per-crawl host statistics from the Common Crawl host index")
    c.add_argument("--crawls", nargs="*", help="only these crawls (default: all missing ones)")

    sub.add_parser("whois", help="refresh WHOIS of .ru/.su/.рф registrable domains (lost domain detection)")

    sub.add_parser("build", help="aggregate data into site/data/*.json")

    m = sub.add_parser("monthly", help="the monthly run: probe, wayback, snapshots, commoncrawl, build")
    m.add_argument("--skip", nargs="*", default=[],
                   choices=["probe", "probe-ru", "whois", "wayback", "snapshots", "commoncrawl"])

    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    if args.command == "registry":
        rows = registry.build()
        print(f"{len(rows)} hosts written to {registry.REGISTRY_FILE}")
        return

    hosts = [r["host"] for r in registry.load()]
    if getattr(args, "limit", 0):
        hosts = hosts[: args.limit]

    if args.command == "probe":
        from . import probe
        if args.hosts:
            from .common import normalize_host
            hosts = [normalize_host(h) for arg in args.hosts for h in arg.split()]
        concurrency = args.concurrency or (10 if args.vantage == "ru" else 40)
        probe.run(hosts, month=args.month, concurrency=concurrency, merge=bool(args.hosts), point=args.vantage)
    elif args.command == "wayback":
        from . import wayback
        wayback.update_sparklines(hosts, force=args.force)
    elif args.command == "snapshots":
        from . import build, wayback
        wayback.update_snapshots(build.active_cohort_hosts(hosts), concurrency=args.concurrency)
    elif args.command == "commoncrawl":
        from . import commoncrawl
        commoncrawl.update(hosts, crawls=args.crawls)
    elif args.command == "whois":
        from . import whois
        whois.update(hosts)
    elif args.command == "build":
        from . import build
        build.build()
    elif args.command == "monthly":
        from . import build, commoncrawl, probe, wayback, whois
        if "probe" not in args.skip:
            probe.run(hosts, month=current_month())
        if "probe-ru" not in args.skip:
            # Right after the foreign probe, so both views describe the same days
            probe.run_ru()
        if "whois" not in args.skip:
            whois.update(hosts)
        if "wayback" not in args.skip:
            wayback.update_sparklines(hosts)
        if "snapshots" not in args.skip:
            wayback.update_snapshots(build.active_cohort_hosts(hosts))
        if "commoncrawl" not in args.skip:
            commoncrawl.update(hosts)
        build.build()


if __name__ == "__main__":
    main()
