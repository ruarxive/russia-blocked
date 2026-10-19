window.I18N = {
  ru: {
    brand: "Госсайты вне архива",
    nav_archive: "Архивирование", nav_access: "Доступность", nav_domains: "Сайты", nav_method: "Методика и данные", nav_feedback: "Обратная связь",
    title: "Российские госсайты уходят из веб-архивов",
    lede: "С 2022 года многие сайты федеральных органов власти и их территориальных управлений, судов, избирательных комиссий и государственных информационных систем закрыты геоблокировками, DDoS-фильтрами и WAF. Зарубежные веб-архивы, прежде всего Internet Archive, не могут их сохранять, а обязательной государственной архивации общедоступных госресурсов нет. Мы каждый месяц проверяем {n} сайтов из-за рубежа и сопоставляем результат с тем, что о них есть в архивах с 2019 года.",
    hero_label: "госсайтов не открываются для зарубежного краулера: {n} из {total} работающих доменов",
    kpi_gap: "Перестали архивироваться",
    kpi_gap_note: "{n} из {total} сайтов, которые Wayback Machine сохранял в 2021 г., не имеют ни одного успешного снимка за последние 12 месяцев",
    kpi_content: "Сохранены с содержимым в {year}",
    kpi_content_note: "у остальных последний снимок года — WAF-заглушка, пустая страница, JS-оболочка или снимков нет (проверено {checked} из {total})",
    kpi_ruca: "Сертификат Russian Trusted CA",
    kpi_ruca_note: "сайтов с сертификатом, которому не доверяют браузеры и большинство краулеров",
    kpi_waf: "За DDoS-защитой или WAF",
    kpi_waf_note: "сайтов, где обнаружены DDoS-Guard, Qrator, Servicepipe, StormWall, Ngenix и др.",
    kpi_pending: "проверка снимков продолжается: {checked} из {total}",
    kpi_lost: "Госдомены перехвачены",
    kpi_lost_note: "истёкшие госдомены перерегистрированы третьими лицами: казино, займы, клоны госсайтов; ещё {free} свободны для регистрации",
    d_lost: "Домен утрачен", d_whois: "WHOIS",
    lost_spam: "на домене спам или казино («{m}»)", lost_rereg: "домен перерегистрирован {date}",
    whois_created: "создан {date}",
    owner: { person: "владелец — частное лицо", org: "владелец — организация" },
    asof: "Проверка доступности: {month}, точка наблюдения — {vantage}. Данные архивов обновлены {date}.",
    asof_noprobe: "Данные архивов обновлены {date}. Проверка доступности ещё не проводилась.",
    asof_ru: " Проверка из России: {month}, {vantage}.",
    hero_label_ru: "{pct} из них открываются из России ({n} из {total}): они закрыты именно для зарубежных посетителей",
    f_category: "Категория", f_region: "Регион", all: "Все", all_regions: "Все регионы",
    scope: "{n} сайтов в выборке",
    h_archive: "Архивирование в Wayback Machine",
    archive_lede: "Главная страница каждого сайта: сколько раз в месяц её сохранял Internet Archive и что именно сохранено. Доли считаются от сайтов, которые архивировались в 2021 году, то есть работали и были доступны архиву до 2022 года.",
    c_timeline: "Доля сайтов, сохранённых в Wayback Machine, по месяцам",
    c_timeline_sub: "Сайты, у которых в 2021 г. был хотя бы один снимок со статусом 200: доля тех, у кого такой снимок есть в данном месяце. Последние 2–3 месяца могут вырасти: архив индексирует снимки с задержкой.",
    s_cohort: "Сохранены в месяце",
    annot_war: "24.02.2022",
    c_quality: "Что сохранено: последний снимок главной страницы за год",
    c_quality_sub: "Последний за год снимок со статусом 200 скачан из архива и классифицирован по содержимому",
    c_gaps: "Сколько месяцев сайт не архивировался",
    c_gaps_sub: "Месяцев с последнего успешного снимка (статус 200) до {month}",
    gap_0: "0", gap_never: "нет с 2019",
    c_heat: "Каждый сайт — строка, каждый месяц — клетка",
    c_heat_sub: "Строки упорядочены по дате последнего успешного снимка. Наведите курсор, чтобы увидеть сайт; щёлкните, чтобы открыть карточку.",
    c_cc: "Common Crawl: сайты, успешно скачанные в каждом краулe",
    c_cc_sub: "Доля сайтов, у которых Common Crawl получил хотя бы одну страницу со статусом 200, среди скачанных в декабре 2021 – январе 2022",
    s_cc: "Скачаны в краулe",
    cc_pending: "Данные Common Crawl ещё собираются.",
    h_access: "Доступность из-за рубежа",
    h_access_ru: "Доступность из-за рубежа и из России",
    access_lede_ru: "Те же сайты проверены из российской сети ({vantage}, {month}), чтобы отличить блокировку зарубежных адресов от сайта, который не работает ни для кого.",
    c_geo: "Из-за рубежа и из России",
    c_geo_sub: "Работающие сайты, проверенные с обеих сторон границы",
    geo_matrix: "Статусы из-за рубежа (строки) и из России (столбцы)",
    geo: {
      open: "Открыт из-за рубежа и из России", geoblock: "Закрыт только для зарубежных посетителей",
      closed: "Не открывается и из России", ru_fail: "Не открывается только из России"
    },
    access_lede: "Проверка {month} из {vantage}: DNS, подключение к портам 443 и 80, TLS-сертификат, ответ главной страницы и robots.txt. Так сайт видят краулеры зарубежных веб-архивов.",
    access_lede_none: "Проверка доступности ещё не проводилась.",
    c_live: "Результат проверки по категориям",
    c_live_sub: "Доля доменов в каждой категории",
    c_reasons: "Причины недоступности",
    c_reasons_sub: "Детальный статус доменов, которые не открылись",
    c_barriers: "Другие барьеры для архивации",
    c_barriers_sub: "Среди работающих доменов; один сайт может попасть в несколько строк",
    c_vendors: "Защита от DDoS, WAF и CDN",
    c_vendors_sub: "Определено по заголовкам, cookie, CNAME и сети размещения",
    c_hosting: "Где размещены сайты",
    c_hosting_sub: "Автономные системы (сети) с наибольшим числом доменов; {ru} размещены в российских сетях",
    tableview: "Таблица",
    h_domains: "Все сайты",
    search_ph: "Домен или организация",
    th_site: "Сайт", th_category: "Категория", th_live: "Из-за рубежа", th_live_ru: "Из России", th_vendor: "Защита",
    th_last: "Последний снимок", th_years: "Снимки по годам",
    more: "Показать ещё",
    shown: "Показано {shown} из {n}",
    any_status: "Любой статус",
    arch_any: "Любая архивация", arch_recent: "Сохранялся за 12 мес.", arch_stale: "Не сохранялся 12+ мес.", arch_never: "Нет успешных снимков с 2019",
    never: "нет",
    month: "Месяц", share: "Доля", count: "Число", year: "Год", crawl: "Краул", total: "Всего", category: "Категория",
    sites: "сайтов",
    cat: {
      federal: "Федеральные органы власти", regional: "Территориальные органы", courts: "Суды",
      elections: "Избирательные комиссии", gis: "ГИС и госпорталы", institution: "Госучреждения и программы",
      all: "Все категории"
    },
    group: {
      ok: "Доступен", waf: "WAF, заглушка или пустой ответ", noconn: "Нет соединения (вероятно, геофильтр)",
      error: "Ошибка сервера", gone: "Сайта больше нет: домен удалён или перехвачен"
    },
    status: {
      ok: "Доступен", challenge: "JS-проверка WAF", blocked: "Страница блокировки", empty: "Пустой ответ",
      timeout: "Порты не отвечают", refused: "Соединение отклонено", http_timeout: "Нет HTTP-ответа",
      http_error: "Ошибка соединения/TLS", server_error: "Ошибка 5xx", client_error: "Ошибка 4xx",
      dns: "Домен не резолвится", lost: "Домен перехвачен"
    },
    snap: {
      c: "Содержимое", s: "JS-оболочка без текста", bad: "WAF, блокировка или ошибка", n: "Нет снимка 200 за год",
      u: "Не проверено", j: "JS-проверка WAF", b: "Страница блокировки", e: "Пустая страница", x: "Ошибка"
    },
    wb: { "2": "Есть снимок 200", "3": "Только редиректы", "4": "Только ошибки", "5": "Только ошибки", "0": "Нет снимков" },
    barrier: {
      ruca: "Сертификат Russian Trusted CA", tls: "Цепочка TLS не проверяется", https: "HTTPS закрыт, открыт только HTTP",
      robots_all: "robots.txt запрещает всё", robots_ia: "robots.txt запрещает краулер Internet Archive",
      shell: "Главная — JS-приложение без текста в HTML", offsite: "Перенаправляет на другой домен",
      free: "Домен истёк и свободен для регистрации"
    },
    d_live: "Проверка из-за рубежа", d_live_ru: "Проверка из России", d_geo: "Сравнение",
    d_archive: "Wayback Machine", d_years: "Последний снимок 200 по годам",
    d_cc: "Common Crawl по краулам", d_links: "Ссылки",
    d_status: "Статус", d_ip: "IP / сеть", d_ports: "Порты 443 / 80", d_tls: "TLS-сертификат", d_http: "HTTP-ответ",
    d_title: "Заголовок", d_vendors: "Защита / CDN", d_robots: "robots.txt", d_region: "Регион", d_org: "Организация",
    d_captures: "Снимков главной всего", d_lastok: "Последний снимок 200", d_cohort: "Сохранялся в 2021",
    d_open_site: "Открыть сайт", d_calendar: "Календарь Wayback", d_report: "Сообщить о неточности", d_close: "Закрыть",
    yes: "да", no: "нет", verified: "цепочка проверена", not_verified: "цепочка не проверена",
    cc_codes: { "2": "Скачан (200)", "3": "Только редиректы", e: "Только ошибки", u: "Известен, не скачан", "0": "Нет в краулe" },
    h_method: "Методика и данные",
    h_downloads: "Открытые данные",
    h_feedback: "Обратная связь",
    feedback_lede: "Нашли ошибку в данных о сайте, знаете госсайт, которого нет в реестре, или хотите что-то предложить? Напишите нам: сообщение можно отправить как публичный issue на GitHub или письмом.",
    fb_type: "Тема", fb_types: { error: "Неточность в данных", idea: "Предложение", other: "Другое" },
    fb_site: "Сайт, если сообщение о конкретном сайте", fb_site_ph: "например, minjust.gov.ru", fb_site_short: "Сайт",
    fb_message: "Сообщение", fb_contact: "Как с вами связаться (по желанию, только для письма)", fb_contact_ph: "email или Telegram", fb_contact_short: "Контакт",
    fb_github: "Создать issue на GitHub", fb_email: "Отправить письмо",
    fb_note_1: "Issue на GitHub публичный, для него нужен аккаунт GitHub. Письмо откроется в вашем почтовом клиенте; если этого не произошло, напишите на",
    fb_note_2: ".",
    fb_err_empty: "Напишите сообщение.",
    fb_context: "Данные: проверка {month} · {url} · язык страницы: {lang}",
    fb_pasted: "(Текст сообщения скопирован в буфер обмена: вставьте его сюда.)",
    fb_copied: "Сообщение слишком длинное для ссылки, поэтому оно скопировано в буфер обмена. Откройте форму и вставьте текст.",
    fb_too_long: "Сообщение слишком длинное для ссылки, а скопировать его не удалось. Сократите текст.",
    fb_open: "Открыть форму",
    method_html: `
<h3>Какие сайты</h3>
<p>Реестр — {n} значимых доменов: сайты федеральных органов власти и их территориальных органов в регионах, судов уровня субъекта и выше, ЦИК и избирательных комиссий субъектов, государственных информационных систем и порталов, госучреждений и программ. Основа — федеральная часть базы госдоменов <a href="https://github.com/infoculture/govdomains">govdomains</a>, около 7,7 тыс. хостов в состоянии 2020–2022 гг., то есть до начала массовых блокировок.</p>
<p>Из базы исключены зеркала и альтернативные имена одного сайта, технические хосты (почта, тестовые и служебные серверы, личные кабинеты, API), языковые, мобильные и специальные версии, сайты, которые уже тогда были неактивны, пусты, закрыты паролем или отмечены как не требующие архивации, районные и мировые суды, а также подразделения ниже уровня региона (районные отделы полиции, филиалы учреждений). Сайты органов власти субъектов РФ в эту базу почти не входят и в мониторинг не включены.</p>
<h3>Проверка доступности</h3>
<ul>
<li>Раз в месяц из дата-центра за пределами России; точка наблюдения указана на странице. Так сайты видят краулеры зарубежных архивов.</li>
<li>DNS запрашивается через публичные резолверы 8.8.8.8 и 1.1.1.1. Затем проверяется TCP-подключение к портам 443 и 80, TLS-сертификат и цепочка доверия (хранилище Mozilla), загружается главная страница с браузерным User-Agent и robots.txt.</li>
<li>Ответ классифицируется: содержимое, JS-оболочка, JS-проверка WAF, страница блокировки, пустой ответ или ошибка. JS-проверкой считается и маленькая страница без текста, которая только ставит cookie или перезагружает себя: краулеры, не исполняющие JavaScript, дальше неё не проходят. Защита определяется по заголовкам, cookie, CNAME и сети размещения.</li>
<li>Домены с временными ошибками проверяются повторно.</li>
</ul>
<h3>Проверка из России</h3>
<p>Те же сайты в те же дни проверяются второй раз из российской сети через VPN-туннель, теми же правилами классификации; имена разрешаются через DNS Яндекса. Сайт, который не открывается из-за рубежа, но открывается из России, закрыт именно для зарубежных посетителей: это геоблокировка или правило WAF для иностранных адресов. Сайт, который не открывается с обеих сторон, просто не работает или закрыт для всех. Сеть российской точки наблюдения указана на странице.</p>
<p><b>Ограничения.</b> Обе точки наблюдения — по одной сети. Адреса дата-центров и VPN часто блокируются строже домашних, поэтому часть сайтов может не открываться и из России, хотя у обычных российских пользователей работает. Если в месяце проверки из России не было, сравнение не показывается: тогда о геоблокировке можно судить только косвенно — DNS работает, IP в российской сети, а порты не отвечают.</p>
<h3>Утраченные домены</h3>
<p>Часть доменов из реестра больше не принадлежит государству: они истекли и перерегистрированы третьими лицами под казино, займы или копии старых госсайтов. Домен считается утраченным, если на нём спам, он припаркован или выставлен на продажу, либо по WHOIS (whois.tcinet.ru) создан после последнего обновления реестра (ноябрь 2022). Домены, созданные в 2021–2022 годах, считаются утраченными, только если их владелец — частное лицо или сайт размещён за пределами России. Утраченные и несуществующие домены не входят в доли доступности и архивации: архивы продолжают сохранять такие домены, но это уже не госсайты.</p>
<h3>Архивы</h3>
<ul>
<li><b>Wayback Machine.</b> Для главной страницы берётся число снимков по месяцам и лучший HTTP-статус месяца (с 2019 г.). Месяц считается сохранённым, если есть хотя бы один снимок со статусом 200.</li>
<li><b>Проверка содержимого.</b> Статус 200 не означает, что сохранено содержимое: часто это страница WAF, пустой ответ или JS-оболочка без текста. Поэтому для сайтов когорты 2021 года (см. ниже) за каждый год скачивается последний снимок со статусом 200 и классифицируется тем же классификатором, что и живой ответ.</li>
<li><b>Когорта 2021.</b> Основные доли считаются по сайтам, у которых был успешный снимок в 2021 году и которые существуют как госсайты сейчас. Это сайты, которые работали и архивировались до 2022 года; закрытые и утраченные домены не влияют на итог.</li>
<li><b>Common Crawl.</b> По <a href="https://github.com/commoncrawl/cc-host-index">Host Index</a> берётся число страниц хоста, скачанных со статусом 200 в каждом краулe. Индекс охватывает декабрь 2021 – апрель 2025.</li>
</ul>
<h3>Обновление</h3>
<p>Данные собираются ежемесячно: проверка доступности, история Wayback Machine, проверка снимков текущего года и новые краулы Common Crawl. Месячные срезы проверки сохраняются, чтобы со временем видеть динамику.</p>`,
    footer: `<p>Проект <a href="https://ruarxive.org">Ruarxive</a>. Данные: Internet Archive Wayback Machine, Common Crawl, govdomains, iptoasn.com.</p>
<p>Все материалы и данные сайта доступны по лицензии <a href="https://creativecommons.org/licenses/by/4.0/deed.ru" rel="license">CC BY 4.0</a>, код сайта — по лицензии <a href="https://github.com/ruarxive/russia-blocked/blob/main/LICENSE" rel="license">MIT</a>. <a href="https://github.com/ruarxive/russia-blocked">Исходный код</a> · <a href="#feedback">Обратная связь</a></p>`,
    dl: {
      domains: "Сводная таблица по сайтам (CSV)", registry: "Реестр доменов (CSV)", probe: "Проверка доступности {month} (JSONL)", probe_ru: "Проверка из России {month} (JSONL)",
      snapshots: "Классификация снимков Wayback (JSONL)", cc: "Статистика Common Crawl по хостам (CSV)", summary: "Сводка (JSON)"
    }
  },
  en: {
    brand: "Off the Archive",
    nav_archive: "Archiving", nav_access: "Access", nav_domains: "Sites", nav_method: "Method & data", nav_feedback: "Feedback",
    title: "Russian government websites are disappearing from web archives",
    lede: "Since 2022 many websites of Russian federal government bodies and their regional offices, courts, election commissions and state information systems have been hidden behind geoblocking, DDoS filters and WAFs. Foreign web archives, first of all the Internet Archive, cannot preserve them, and Russia has no mandatory archiving of public government websites. Every month we check {n} sites from abroad and compare the result with what archives have kept since 2019.",
    hero_label: "of government sites do not open for a crawler abroad: {n} of {total} live domains",
    kpi_gap: "No longer archived",
    kpi_gap_note: "{n} of {total} sites archived by the Wayback Machine in 2021 have no successful capture in the last 12 months",
    kpi_content: "Archived with content in {year}",
    kpi_content_note: "for the rest, the year's last capture is a WAF page, an empty page, a JS shell, or there is none ({checked} of {total} checked)",
    kpi_ruca: "Russian Trusted CA certificate",
    kpi_ruca_note: "sites with a certificate that browsers and most crawlers do not trust",
    kpi_waf: "Behind DDoS protection or a WAF",
    kpi_waf_note: "sites with DDoS-Guard, Qrator, Servicepipe, StormWall, Ngenix and others",
    kpi_pending: "capture checks in progress: {checked} of {total}",
    kpi_lost: "Government domains taken over",
    kpi_lost_note: "expired government domains registered again by third parties: casinos, loans, clones of government sites; {free} more are free to register",
    d_lost: "Domain lost", d_whois: "WHOIS",
    lost_spam: "the domain serves spam or a casino (“{m}”)", lost_rereg: "domain registered again on {date}",
    whois_created: "created {date}",
    owner: { person: "owner is a private person", org: "owner is an organization" },
    asof: "Access check: {month}, vantage point: {vantage}. Archive data updated {date}.",
    asof_noprobe: "Archive data updated {date}. No access check has run yet.",
    asof_ru: " Check from Russia: {month}, {vantage}.",
    hero_label_ru: "{pct} of them open from Russia ({n} of {total}): they are closed to foreign visitors only",
    f_category: "Category", f_region: "Region", all: "All", all_regions: "All regions",
    scope: "{n} sites selected",
    h_archive: "Archiving in the Wayback Machine",
    archive_lede: "The homepage of every site: how often the Internet Archive captured it each month and what it actually saved. Shares are computed over sites archived in 2021, that is, sites that worked and were reachable for the archive before 2022.",
    c_timeline: "Share of sites captured by the Wayback Machine, by month",
    c_timeline_sub: "Sites with at least one HTTP 200 capture in 2021: share with such a capture in the given month. The last 2–3 months may still rise: the archive indexes captures with a delay.",
    s_cohort: "Captured in month",
    annot_war: "24 Feb 2022",
    c_quality: "What was saved: the year's last homepage capture",
    c_quality_sub: "The last HTTP 200 capture of each year is downloaded from the archive and classified by content",
    c_gaps: "Months since the site was last archived",
    c_gaps_sub: "Months from the last HTTP 200 capture to {month}",
    gap_0: "0", gap_never: "none since 2019",
    c_heat: "Every site is a row, every month a cell",
    c_heat_sub: "Rows are ordered by the date of the last successful capture. Hover to see the site, click to open its card.",
    c_cc: "Common Crawl: sites fetched successfully in each crawl",
    c_cc_sub: "Share of sites with at least one HTTP 200 page fetched by Common Crawl, among those fetched in December 2021 – January 2022",
    s_cc: "Fetched in crawl",
    cc_pending: "Common Crawl data is still being collected.",
    h_access: "Access from abroad",
    h_access_ru: "Access from abroad and from Russia",
    access_lede_ru: "The same sites are checked from a Russian network ({vantage}, {month}) to tell blocking of foreign addresses apart from a site that works for no one.",
    c_geo: "From abroad and from Russia",
    c_geo_sub: "Live sites checked from both sides of the border",
    geo_matrix: "Status from abroad (rows) by status from Russia (columns)",
    geo: {
      open: "Open from abroad and from Russia", geoblock: "Closed only to foreign visitors",
      closed: "Does not open from Russia either", ru_fail: "Does not open only from Russia"
    },
    access_lede: "Check of {month} from {vantage}: DNS, connection to ports 443 and 80, TLS certificate, homepage response and robots.txt. This is how crawlers of foreign web archives see the sites.",
    access_lede_none: "No access check has run yet.",
    c_live: "Check result by category",
    c_live_sub: "Share of domains in each category",
    c_reasons: "Why sites are unreachable",
    c_reasons_sub: "Detailed status of the domains that did not open",
    c_barriers: "Other barriers to archiving",
    c_barriers_sub: "Among live domains; a site can appear in several rows",
    c_vendors: "DDoS protection, WAF and CDN",
    c_vendors_sub: "Detected from headers, cookies, CNAMEs and the hosting network",
    c_hosting: "Where the sites are hosted",
    c_hosting_sub: "Autonomous systems (networks) with the most domains; {ru} are hosted in Russian networks",
    tableview: "Table",
    h_domains: "All sites",
    search_ph: "Domain or organization",
    th_site: "Site", th_category: "Category", th_live: "From abroad", th_live_ru: "From Russia", th_vendor: "Protection",
    th_last: "Last capture", th_years: "Captures by year",
    more: "Show more",
    shown: "Showing {shown} of {n}",
    any_status: "Any status",
    arch_any: "Any archiving", arch_recent: "Captured in last 12 mo.", arch_stale: "Not captured 12+ mo.", arch_never: "No successful capture since 2019",
    never: "none",
    month: "Month", share: "Share", count: "Count", year: "Year", crawl: "Crawl", total: "Total", category: "Category",
    sites: "sites",
    cat: {
      federal: "Federal government", regional: "Regional offices", courts: "Courts",
      elections: "Election commissions", gis: "State information systems", institution: "State institutions",
      all: "All categories"
    },
    group: {
      ok: "Accessible", waf: "WAF, stub or empty response", noconn: "No connection (likely geofilter)",
      error: "Server error", gone: "Site is gone: domain deleted or taken over"
    },
    status: {
      ok: "Accessible", challenge: "WAF JS challenge", blocked: "Block page", empty: "Empty response",
      timeout: "Ports do not answer", refused: "Connection refused", http_timeout: "No HTTP response",
      http_error: "Connection/TLS error", server_error: "5xx error", client_error: "4xx error",
      dns: "Domain does not resolve", lost: "Domain taken over"
    },
    snap: {
      c: "Content", s: "JS shell without text", bad: "WAF, block or error", n: "No HTTP 200 capture that year",
      u: "Not checked", j: "WAF JS challenge", b: "Block page", e: "Empty page", x: "Error"
    },
    wb: { "2": "HTTP 200 capture", "3": "Redirects only", "4": "Errors only", "5": "Errors only", "0": "No captures" },
    barrier: {
      ruca: "Russian Trusted CA certificate", tls: "TLS chain does not verify", https: "HTTPS closed, only HTTP open",
      robots_all: "robots.txt disallows everything", robots_ia: "robots.txt disallows the Internet Archive crawler",
      shell: "Homepage is a JS app without text in HTML", offsite: "Redirects to another domain",
      free: "Domain expired and is free to register"
    },
    d_live: "Check from abroad", d_live_ru: "Check from Russia", d_geo: "Comparison",
    d_archive: "Wayback Machine", d_years: "Last HTTP 200 capture by year",
    d_cc: "Common Crawl by crawl", d_links: "Links",
    d_status: "Status", d_ip: "IP / network", d_ports: "Ports 443 / 80", d_tls: "TLS certificate", d_http: "HTTP response",
    d_title: "Title", d_vendors: "Protection / CDN", d_robots: "robots.txt", d_region: "Region", d_org: "Organization",
    d_captures: "Homepage captures, total", d_lastok: "Last HTTP 200 capture", d_cohort: "Archived in 2021",
    d_open_site: "Open site", d_calendar: "Wayback calendar", d_report: "Report an error", d_close: "Close",
    yes: "yes", no: "no", verified: "chain verified", not_verified: "chain not verified",
    cc_codes: { "2": "Fetched (200)", "3": "Redirects only", e: "Errors only", u: "Known, not fetched", "0": "Not in crawl" },
    h_method: "Method & data",
    h_downloads: "Open data",
    h_feedback: "Feedback",
    feedback_lede: "Found an error in the data about a site, know a government site missing from the registry, or have a suggestion? Write to us: send the message as a public GitHub issue or by email.",
    fb_type: "Topic", fb_types: { error: "Error in the data", idea: "Suggestion", other: "Other" },
    fb_site: "Site, if the message is about a specific site", fb_site_ph: "e.g. minjust.gov.ru", fb_site_short: "Site",
    fb_message: "Message", fb_contact: "How to reach you (optional, email only)", fb_contact_ph: "email or Telegram", fb_contact_short: "Contact",
    fb_github: "Open a GitHub issue", fb_email: "Send an email",
    fb_note_1: "GitHub issues are public and need a GitHub account. The email opens in your mail app; if it does not, write to",
    fb_note_2: ".",
    fb_err_empty: "Write a message.",
    fb_context: "Data: check of {month} · {url} · page language: {lang}",
    fb_pasted: "(The message text was copied to the clipboard: paste it here.)",
    fb_copied: "The message is too long for a link, so it was copied to the clipboard. Open the form and paste the text.",
    fb_too_long: "The message is too long for a link and could not be copied. Shorten the text.",
    fb_open: "Open the form",
    method_html: `
<h3>Which sites</h3>
<p>The registry holds {n} significant domains: sites of federal government bodies and their regional offices, courts of the regional level and above, the Central Election Commission and the election commissions of the regions, state information systems and portals, state institutions and programmes. It is based on the federal part of the <a href="https://github.com/infoculture/govdomains">govdomains</a> base, about 7,700 hosts as of 2020–2022, before mass blocking began.</p>
<p>Left out are mirrors and alternative names of one site, technical hosts (mail, test and service servers, personal account logins, APIs), language, mobile and accessibility versions, sites that were already inactive, empty, password-protected or marked as not worth archiving, district courts and magistrates, and units below the regional level (district police departments, branches of institutions). Sites of the regional governments are almost absent from this base and are not monitored.</p>
<h3>Access check</h3>
<ul>
<li>Once a month from a data center outside Russia; the vantage point is shown on the page. This is how crawlers of foreign archives see the sites.</li>
<li>DNS is resolved with the public resolvers 8.8.8.8 and 1.1.1.1. Then the check covers TCP connections to ports 443 and 80, the TLS certificate and its chain of trust (Mozilla store), the homepage fetched with a browser User-Agent, and robots.txt.</li>
<li>The response is classified as content, JS shell, WAF JS challenge, block page, empty response or error. A small page without text that only sets a cookie or reloads itself also counts as a JS challenge: crawlers that do not run JavaScript never get past it. Protection is detected from headers, cookies, CNAMEs and the hosting network.</li>
<li>Domains with transient errors are checked twice.</li>
</ul>
<h3>Check from Russia</h3>
<p>On the same days the same sites are checked a second time from a Russian network through a VPN tunnel, with the same classification rules; names are resolved through Yandex DNS. A site that does not open from abroad but opens from Russia is closed specifically to foreign visitors: geoblocking or a WAF rule for foreign addresses. A site that does not open from either side is down or closed to everyone. The network of the Russian vantage point is shown on the page.</p>
<p><b>Limitations.</b> Each vantage point is a single network. Data center and VPN addresses are often blocked more strictly than residential ones, so some sites may not open from Russia either even though they work for ordinary Russian users. When there was no check from Russia in a month, the comparison is not shown; geoblocking can then only be inferred: DNS works, the IP is in a Russian network and the ports do not answer.</p>
<h3>Lost domains</h3>
<p>Some registry domains no longer belong to the state: they expired and were registered again by third parties for casinos, loans or copies of old government sites. A domain counts as lost when it serves spam, is parked or offered for sale, or its WHOIS record (whois.tcinet.ru) shows it was created after the registry's last update (November 2022). Domains created in 2021–2022 count as lost only if the owner is a private person or the site is hosted outside Russia. Lost and non-existent domains are left out of the access and archiving shares: archives keep capturing them, but they are no longer government sites.</p>
<h3>Archives</h3>
<ul>
<li><b>Wayback Machine.</b> For each homepage: captures per month and the best HTTP status of the month (since 2019). A month counts as captured when there is at least one HTTP 200 capture.</li>
<li><b>Content check.</b> HTTP 200 does not mean the content was saved: often it is a WAF page, an empty response or a JS shell without text. So for sites of the 2021 cohort (see below) the last HTTP 200 capture of each year is downloaded and classified with the same classifier as the live response.</li>
<li><b>2021 cohort.</b> Headline shares are computed over sites with a successful capture in 2021 that still exist as government sites. These sites worked and were archived before 2022; closed and lost domains do not affect the result.</li>
<li><b>Common Crawl.</b> The <a href="https://github.com/commoncrawl/cc-host-index">Host Index</a> gives the number of pages fetched with HTTP 200 per host and crawl. It covers December 2021 – April 2025.</li>
</ul>
<h3>Updates</h3>
<p>Data is collected monthly: the access check, Wayback Machine history, checks of this year's captures and new Common Crawl crawls. Monthly access snapshots are kept to show change over time.</p>`,
    footer: `<p>A <a href="https://ruarxive.org">Ruarxive</a> project. Data: Internet Archive Wayback Machine, Common Crawl, govdomains, iptoasn.com.</p>
<p>All materials and data on this site are available under <a href="https://creativecommons.org/licenses/by/4.0/" rel="license">CC BY 4.0</a>; the site code is under the <a href="https://github.com/ruarxive/russia-blocked/blob/main/LICENSE" rel="license">MIT</a> license. <a href="https://github.com/ruarxive/russia-blocked">Source code</a> · <a href="#feedback">Feedback</a></p>`,
    dl: {
      domains: "Per-site summary table (CSV)", registry: "Domain registry (CSV)", probe: "Access check {month} (JSONL)", probe_ru: "Check from Russia {month} (JSONL)",
      snapshots: "Wayback capture classification (JSONL)", cc: "Common Crawl host statistics (CSV)", summary: "Summary (JSON)"
    }
  }
};
