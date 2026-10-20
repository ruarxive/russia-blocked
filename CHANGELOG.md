# Changelog

All notable changes to the code, the site and the published data. The project has no
versioned releases: entries are grouped by date.

## 2026-10-20

### Data

- Common Crawl backfill of the 1,727 hosts added with the new registry is complete for
  all 26 crawls; `data/commoncrawl/queried.txt` lists them.

### Documentation

- README: the probe from Russia in the table of measured sources, the full repository
  layout, command options, tests, the open data downloads, the Yandex.Metrika counter,
  updated limits.
- This changelog.

## 2026-10-19

### Added

- Access check from Russia: `probe --vantage ru` runs inside a Docker container with an
  AmneziaWG tunnel (`scripts/probe-ru.sh`, `docker/probe-ru/`), so the routing of the
  host and the other collectors stays abroad. `monthly` runs it right after the foreign
  probe and skips it when there is no VPN config in `secrets/`; `monthly --skip probe-ru`
  skips it on purpose. Results go to `data/probes/ru/`.
- Both probes refuse to run from the wrong side of the border. The Russian probe
  resolves names through Yandex DNS and keeps no exit IP in its metadata.
- The site compares the two views: the share of sites closed to foreign visitors only in
  the hero, a chart by category, a status matrix, a table column and filter, the site
  card and the methodology. Raw probe results from Russia are in the downloads.
- Yandex.Metrika counter on the site.
- Deploy to GitHub Pages from Actions (`.github/workflows/pages.yml`): every push to
  `main` builds `site/data/` from the committed `data/` and deploys `site/`.
- Common Crawl backfill resumes after an interruption:
  `data/commoncrawl/backfill.json` records the crawls already done for the current set of
  new hosts and is removed when the backfill is complete.

### Changed

- The site moved to <https://ruarxive.org/russia-blocked/>, a project page of the
  ruarxive organization: the CNAME and the subpath `robots.txt` are gone; canonical and
  Open Graph URLs, sitemap, feedback links and the crawler User-Agent point at the new
  address.
- DuckDB runs with a 1 GB memory limit and 2 threads, without an external file cache,
  and spills to `data/cache/duckdb/`. A crawl query had grown to about 4 GB.

### Data

- First monthly probe from Russia, 2026-10: 2,254 hosts, Moscow, AS50340 Selectel.
- Wayback Machine history and snapshot classification (all years) for the hosts added
  with the new registry.

### Initial release

- Monthly probe of 2,254 government hosts from abroad (first run 2026-10 from
  Frankfurt am Main, DigitalOcean): DNS, ASN, TCP, TLS chain, homepage classification,
  protection vendor, robots.txt.
- WHOIS of .ru/.su/.рф domains to detect government domains taken over by third parties.
- Wayback Machine monthly captures since 2019 and classification of the last HTTP 200
  homepage snapshot of each year.
- Common Crawl Host Index statistics per host and crawl, December 2021 to April 2025.
- Registry built from the federal part of the govdomains base (Orgview export).
- Static site in Russian and English with a feedback form that opens a prefilled GitHub
  issue or email.
- Materials and data under CC BY 4.0, code under MIT.
