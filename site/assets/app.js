(function () {
  "use strict";

  // ---------- state & i18n ----------
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* storage unavailable */ } },
  };
  const state = {
    lang: store.get("lang") || "ru",
    summary: null, domains: [],
    category: "all", region: "all",
    q: "", status: "all", archived: "all",
    sort: { key: "wl", dir: -1 }, shown: 50,
  };
  const GROUPS = ["ok", "waf", "noconn", "error", "gone"];
  const GROUP_ICON = { ok: "✓", waf: "!", noconn: "×", error: "?", gone: "–" };
  const CATS = ["federal", "regional", "courts", "elections", "gis", "institution"];
  const SITE_URL = "https://ruarxive.org/russia-blocked/";
  const REPO_URL = "https://github.com/ruarxive/russia-blocked";
  const FEEDBACK_EMAIL = "ivan.begtin@infoculture.ru";

  function t(key, vars) {
    const pick = (lang) => key.split(".").reduce((o, k) => (o == null ? o : o[k]), window.I18N[lang]);
    let s = pick(state.lang);
    if (s == null) s = pick("ru");
    if (s == null) s = key;
    if (vars && typeof s === "string") s = s.replace(/\{(\w+)\}/g, (_, k) => (vars[k] != null ? vars[k] : ""));
    return s;
  }
  const locale = () => (state.lang === "ru" ? "ru-RU" : "en-GB");
  const fmtInt = (n) => (n == null ? "—" : n.toLocaleString(locale()));
  const fmtPct = (x) => {
    if (x == null || !isFinite(x)) return "—";
    const p = x * 100;
    return (p > 0 && p < 10 ? p.toFixed(1) : Math.round(p).toString()) + "%";
  };
  const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  function monthLabel(m) {
    const [y, mm] = m.split("-").map(Number);
    return new Date(Date.UTC(y, mm - 1, 1)).toLocaleDateString(locale(), { month: "short", year: "numeric", timeZone: "UTC" });
  }

  // ---------- DOM helpers (untrusted text always via textContent) ----------
  function el(tag, attrs, ...children) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k === "class") node.className = v;
      else if (k === "style") node.style.cssText = v;
      else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v === true ? "" : v);
    }
    for (const c of children.flat()) {
      if (c == null || c === false) continue;
      node.append(c instanceof Node ? c : document.createTextNode(String(c)));
    }
    return node;
  }
  const SVGNS = "http://www.w3.org/2000/svg";
  function s(tag, attrs, ...children) {
    const node = document.createElementNS(SVGNS, tag);
    for (const [k, v] of Object.entries(attrs || {})) if (v != null) node.setAttribute(k, v);
    for (const c of children.flat()) if (c != null) node.append(c instanceof Node ? c : document.createTextNode(String(c)));
    return node;
  }
  // Bar path with a 4px rounded data end and a square base
  function barPath(x, y, w, h, end) {
    const r = Math.min(4, w / 2, h / 2);
    if (w <= 0 || h <= 0) return "";
    if (end === "top") return `M${x},${y + h}V${y + r}Q${x},${y} ${x + r},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h}Z`;
    if (end === "right") return `M${x},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h - r}Q${x + w},${y + h} ${x + w - r},${y + h}H${x}Z`;
    return `M${x},${y}H${x + w}V${y + h}H${x}Z`;
  }

  // ---------- tooltip ----------
  const tip = document.getElementById("tooltip");
  function showTip(evt, nodes) {
    tip.replaceChildren(...nodes);
    tip.hidden = false;
    const pad = 14, rect = tip.getBoundingClientRect();
    let x = evt.clientX + pad, y = evt.clientY + pad;
    if (x + rect.width > window.innerWidth - 8) x = evt.clientX - rect.width - pad;
    if (y + rect.height > window.innerHeight - 8) y = evt.clientY - rect.height - pad;
    tip.style.left = Math.max(8, x) + "px";
    tip.style.top = Math.max(8, y) + "px";
  }
  const hideTip = () => { tip.hidden = true; };
  const tipValue = (v, label, color) => el("div", { class: "row" },
    color ? el("span", { class: "key", style: `background:${color}` }) : null,
    el("span", { class: "tv" }, v), el("span", { class: "tl" }, label));

  // ---------- data scope ----------
  function scoped() {
    return state.domains.filter((d) =>
      (state.category === "all" || d.c === state.category) &&
      (state.region === "all" || d.r === state.region));
  }
  const months = () => state.summary.months.slice(0, state.summary.complete_months);
  // Sites archived in 2021 that are still government sites (not deleted or taken over)
  const activeCohort = (list) => list.filter((d) => d.co && d.act);
  const lastCompleteIdx = () => state.summary.complete_months - 1;
  const snapGroup = (code) => (code === "c" ? "c" : code === "s" ? "s" : "jbex".includes(code) ? "bad" : code === "n" ? "n" : "u");

  // ---------- static text ----------
  function applyStatic() {
    document.documentElement.lang = state.lang;
    document.title = t("brand");
    document.querySelectorAll("[data-i18n]").forEach((n) => { n.textContent = t(n.dataset.i18n, { n: fmtInt(state.domains.length) }); });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((n) => { n.placeholder = t(n.dataset.i18nPlaceholder); });
    document.getElementById("lang-toggle").textContent = state.lang === "ru" ? "EN" : "RU";
    // Methodology and footer are our own trusted markup
    document.getElementById("method-text").innerHTML = t("method_html", { n: fmtInt(state.domains.length) });
    document.getElementById("footer-text").innerHTML = t("footer");
  }

  function vantageText() {
    const v = state.summary.probe && state.summary.probe.vantage;
    if (!v || !v.country) return "—";
    return [v.city, v.country].filter(Boolean).join(", ") + (v.org ? ` (${v.org})` : "");
  }

  // ---------- hero & KPIs (whole registry, not filtered) ----------
  function renderHero() {
    const all = state.domains;
    const alive = all.filter((d) => d.s && d.g !== "gone");
    const unreachable = alive.filter((d) => d.g !== "ok");
    const heroV = document.getElementById("hero-value");
    const heroL = document.getElementById("hero-label");
    if (alive.length) {
      heroV.textContent = fmtPct(unreachable.length / alive.length);
      heroL.textContent = t("hero_label", { n: fmtInt(unreachable.length), total: fmtInt(alive.length) });
    } else {
      heroV.textContent = "—";
      heroL.textContent = t("access_lede_none");
    }
    const ms = months();
    const cutoff = ms[Math.max(0, ms.length - 12)];
    const cohort = activeCohort(all);
    const stale = cohort.filter((d) => !d.wl || d.wl < cutoff);
    const yi = state.summary.years.length - 1;
    const checked = cohort.filter((d) => d.sn[yi] && d.sn[yi] !== "?");
    const content = checked.filter((d) => d.sn[yi] === "c");
    const year = state.summary.years[yi];
    const tiles = [
      [t("kpi_gap"), fmtPct(cohort.length ? stale.length / cohort.length : null),
        t("kpi_gap_note", { n: fmtInt(stale.length), total: fmtInt(cohort.length) })],
      // Until most of this year's captures are classified the share is not meaningful
      [t("kpi_content", { year }), checked.length >= cohort.length * 0.8 && checked.length ? fmtPct(content.length / checked.length) : "…",
        checked.length >= cohort.length * 0.8 ? t("kpi_content_note", { checked: fmtInt(checked.length), total: fmtInt(cohort.length) })
          : t("kpi_pending", { checked: fmtInt(checked.length), total: fmtInt(cohort.length) })],
      [t("kpi_ruca"), fmtInt(alive.filter((d) => d.ruca).length), t("kpi_ruca_note")],
      [t("kpi_lost"), fmtInt(all.filter((d) => d.s === "lost").length),
        t("kpi_lost_note", { free: fmtInt(all.filter((d) => d.free).length) })],
    ];
    document.getElementById("kpis").replaceChildren(...tiles.map(([l, v, n]) =>
      el("div", { class: "tile" }, el("div", { class: "label" }, l), el("div", { class: "value" }, v), el("div", { class: "note" }, n))));
    const date = new Date(state.summary.generated_at).toLocaleDateString(locale(), { day: "numeric", month: "long", year: "numeric" });
    document.getElementById("asof").textContent = state.summary.probe && state.summary.probe.month
      ? t("asof", { month: monthLabel(state.summary.probe.month), vantage: vantageText(), date })
      : t("asof_noprobe", { date });
    document.querySelector(".lede").textContent = t("lede", { n: fmtInt(all.length) });
  }

  // ---------- filters ----------
  function renderFilters() {
    const cat = document.getElementById("f-category");
    cat.replaceChildren(el("option", { value: "all" }, t("cat.all")), ...CATS.map((c) => el("option", { value: c }, t("cat." + c))));
    cat.value = state.category;
    const regions = [...new Set(state.domains.filter((d) => state.category === "all" || d.c === state.category).map((d) => d.r).filter(Boolean))]
      .sort((a, b) => (a === "Российская Федерация" ? -1 : b === "Российская Федерация" ? 1 : a.localeCompare(b, "ru")));
    if (state.region !== "all" && !regions.includes(state.region)) state.region = "all";
    const reg = document.getElementById("f-region");
    reg.replaceChildren(el("option", { value: "all" }, t("all_regions")), ...regions.map((r) => el("option", { value: r }, r)));
    reg.value = state.region;
    document.getElementById("scope-note").textContent = t("scope", { n: fmtInt(scoped().length) });

    const st = document.getElementById("f-status");
    st.replaceChildren(el("option", { value: "all" }, t("any_status")),
      ...GROUPS.map((g) => el("option", { value: "g:" + g }, t("group." + g))));
    st.value = state.status;
    const ar = document.getElementById("f-archived");
    ar.replaceChildren(...["any", "recent", "stale", "never"].map((k) => el("option", { value: k === "any" ? "all" : k }, t("arch_" + k))));
    ar.value = state.archived;
  }

  // ---------- generic line chart ----------
  function lineChart(container, opts) {
    const W = Math.max(300, container.clientWidth), H = opts.height || 280;
    const m = { top: 14, right: 16, bottom: 26, left: 42 };
    const iw = W - m.left - m.right, ih = H - m.top - m.bottom;
    const [x0, x1] = opts.xDomain;
    const xs = (x) => m.left + ((x - x0) / (x1 - x0 || 1)) * iw;
    const ys = (v) => m.top + ih - v * ih;
    const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": opts.label });
    for (const v of [0, 0.25, 0.5, 0.75, 1]) {
      svg.append(s("line", { class: v === 0 ? "baseline" : "gridline", x1: m.left, x2: W - m.right, y1: ys(v), y2: ys(v) }));
      svg.append(s("text", { x: m.left - 8, y: ys(v) + 4, "text-anchor": "end" }, Math.round(v * 100) + "%"));
    }
    for (const tk of opts.xTicks) svg.append(s("text", { x: xs(tk.x), y: H - 6, "text-anchor": "middle" }, tk.label));
    for (const a of opts.annotations || []) {
      svg.append(s("line", { class: "annot", x1: xs(a.x), x2: xs(a.x), y1: m.top, y2: m.top + ih }));
      svg.append(s("text", { x: xs(a.x) + 5, y: m.top + 10, class: "label-ink" }, a.label));
    }
    for (const ser of opts.series) {
      const pts = ser.points.filter((p) => p.v != null);
      if (!pts.length) continue;
      const line = pts.map((p, i) => `${i ? "L" : "M"}${xs(p.x).toFixed(1)},${ys(p.v).toFixed(1)}`).join("");
      if (ser.area) svg.append(s("path", { d: `${line}L${xs(pts[pts.length - 1].x)},${ys(0)}L${xs(pts[0].x)},${ys(0)}Z`, fill: ser.color, "fill-opacity": 0.1 }));
      svg.append(s("path", { d: line, fill: "none", stroke: ser.color, "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round" }));
      if (ser.dots) for (const p of pts) svg.append(s("circle", { cx: xs(p.x), cy: ys(p.v), r: 4, fill: ser.color, stroke: css("--surface"), "stroke-width": 2 }));
      const last = pts[pts.length - 1];
      svg.append(s("circle", { cx: xs(last.x), cy: ys(last.v), r: 4, fill: ser.color, stroke: css("--surface"), "stroke-width": 2 }));
      // The end label sits left of the point, or right of it when the point is near the y axis
      const nearAxis = xs(last.x) < m.left + 48;
      svg.append(s("text", { x: nearAxis ? xs(last.x) + 8 : Math.min(xs(last.x), W - m.right) - 6, y: ys(last.v) - 9,
        "text-anchor": nearAxis ? "start" : "end", class: "label-strong" }, fmtPct(last.v)));
    }
    const cross = s("line", { class: "crosshair", y1: m.top, y2: m.top + ih, visibility: "hidden" });
    svg.append(cross);
    const hit = s("rect", { x: m.left, y: m.top, width: iw, height: ih, fill: "transparent" });
    svg.append(hit);
    const xsAll = opts.series[0].points.map((p) => p.x);
    hit.addEventListener("pointermove", (e) => {
      const r = svg.getBoundingClientRect();
      const px = ((e.clientX - r.left) / r.width) * W;
      const xv = x0 + ((px - m.left) / iw) * (x1 - x0);
      let best = 0;
      xsAll.forEach((x, i) => { if (Math.abs(x - xv) < Math.abs(xsAll[best] - xv)) best = i; });
      cross.setAttribute("x1", xs(xsAll[best])); cross.setAttribute("x2", xs(xsAll[best]));
      cross.setAttribute("visibility", "visible");
      showTip(e, opts.tooltip(best));
    });
    hit.addEventListener("pointerleave", () => { cross.setAttribute("visibility", "hidden"); hideTip(); });
    container.replaceChildren(svg);
  }

  function dataTable(container, head, rows) {
    container.replaceChildren(el("table", { class: "datatable" },
      el("thead", {}, el("tr", {}, head.map((h, i) => el("th", { class: i ? "num" : null }, h)))),
      el("tbody", {}, rows.map((r) => el("tr", {}, r.map((c, i) => el("td", { class: i ? "num" : null }, c)))))));
  }

  // ---------- Wayback timeline ----------
  function renderTimeline() {
    const ms = months();
    const cohort = activeCohort(scoped());
    const box = document.getElementById("chart-timeline");
    const vals = ms.map((_, i) => (cohort.length ? cohort.filter((d) => d.wb[i] === "2").length : 0));
    const points = ms.map((m, i) => ({ x: i, v: cohort.length ? vals[i] / cohort.length : null }));
    const ticks = [];
    ms.forEach((m, i) => { if (m.endsWith("-01")) ticks.push({ x: i, label: m.slice(0, 4) }); });
    const warIdx = ms.indexOf("2022-02");
    lineChart(box, {
      label: t("c_timeline"), xDomain: [0, ms.length - 1], xTicks: box.clientWidth < 520 ? ticks.filter((_, i) => i % 2 === 0) : ticks,
      annotations: warIdx >= 0 ? [{ x: warIdx, label: t("annot_war") }] : [],
      series: [{ points, color: css("--a-content"), area: true }],
      tooltip: (i) => [el("div", { class: "tl" }, monthLabel(ms[i])),
        tipValue(fmtPct(points[i].v), `${fmtInt(vals[i])} / ${fmtInt(cohort.length)}`, css("--a-content"))],
    });
    dataTable(document.getElementById("tv-timeline"), [t("month"), t("s_cohort"), t("share")],
      ms.map((m, i) => [m, fmtInt(vals[i]), fmtPct(points[i].v)]).reverse());
  }

  // ---------- snapshot quality per year ----------
  const QUALITY = [
    { key: "c", color: "--a-content" }, { key: "s", color: "--a-shell" }, { key: "bad", color: "--a-bad" },
    { key: "n", color: "--a-none" }, { key: "u", color: "--a-unknown" },
  ];
  function renderQuality() {
    const years = state.summary.years;
    const cohort = activeCohort(scoped());
    const counts = years.map((_, yi) => {
      const c = { c: 0, s: 0, bad: 0, n: 0, u: 0 };
      for (const d of cohort) c[snapGroup(d.sn[yi] || "?")]++;
      return c;
    });
    document.getElementById("legend-quality").replaceChildren(...QUALITY.map((q) =>
      el("span", {}, el("span", { class: "sw", style: `background:${css(q.color)};${q.key === "u" ? "box-shadow:inset 0 0 0 1px " + css("--axis") : ""}` }), t("snap." + q.key))));
    const box = document.getElementById("chart-quality");
    const W = Math.max(300, box.clientWidth), H = 260;
    const m = { top: 18, right: 8, bottom: 24, left: 38 };
    const iw = W - m.left - m.right, ih = H - m.top - m.bottom;
    const band = iw / years.length, bw = Math.min(24 * 1.6, band * 0.6);
    const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": t("c_quality") });
    for (const v of [0, 0.5, 1]) {
      svg.append(s("line", { class: v === 0 ? "baseline" : "gridline", x1: m.left, x2: W - m.right, y1: m.top + ih - v * ih, y2: m.top + ih - v * ih }));
      svg.append(s("text", { x: m.left - 8, y: m.top + ih - v * ih + 4, "text-anchor": "end" }, Math.round(v * 100) + "%"));
    }
    years.forEach((y, yi) => {
      const x = m.left + band * yi + (band - bw) / 2;
      let acc = 0;
      const total = cohort.length || 1;
      const segs = QUALITY.filter((q) => counts[yi][q.key] > 0);
      segs.forEach((q, si) => {
        const v = counts[yi][q.key] / total;
        const h = v * ih;
        const top = m.top + ih - (acc + v) * ih;
        const gap = si < segs.length - 1 ? 2 : 0;
        const path = s("path", {
          class: "mark", d: barPath(x, top + gap, bw, Math.max(0, h - gap), si === segs.length - 1 ? "top" : null),
          fill: css(q.color), tabindex: 0,
        });
        if (q.key === "u") path.setAttribute("stroke", css("--axis"));
        const show = (e) => showTip(e, [el("div", { class: "tl" }, String(y)),
          tipValue(fmtPct(v), `${t("snap." + q.key)} · ${fmtInt(counts[yi][q.key])}`, css(q.color))]);
        path.addEventListener("pointermove", show);
        path.addEventListener("focus", (e) => { const r = e.target.getBoundingClientRect(); show({ clientX: r.right, clientY: r.top }); });
        path.addEventListener("pointerleave", hideTip);
        path.addEventListener("blur", hideTip);
        svg.append(path);
        acc += v;
      });
      const cshare = counts[yi].c / total;
      if (cshare * ih > 18) svg.append(s("text", { x: x + bw / 2, y: m.top + ih - 6, "text-anchor": "middle", fill: "#fff", style: "fill:#fff;font-weight:600" }, fmtPct(cshare)));
      svg.append(s("text", { x: x + bw / 2, y: H - 6, "text-anchor": "middle" }, String(y)));
    });
    box.replaceChildren(svg);
    dataTable(document.getElementById("tv-quality"), [t("year"), ...QUALITY.map((q) => t("snap." + q.key))],
      years.map((y, yi) => [String(y), ...QUALITY.map((q) => fmtInt(counts[yi][q.key]))]));
  }

  // ---------- months since last capture ----------
  function renderGaps() {
    const ms = months();
    const ref = ms[ms.length - 1];
    const [ry, rm] = ref.split("-").map(Number);
    const buckets = [["0", 0, 0], ["1–3", 1, 3], ["4–6", 4, 6], ["7–12", 7, 12], ["13–24", 13, 24], ["25+", 25, 1e9]];
    const cohort = activeCohort(scoped());
    const counts = buckets.map(() => 0);
    for (const d of cohort) {
      if (!d.wl) { counts[5]++; continue; }
      const [y, mm] = d.wl.split("-").map(Number);
      const gap = Math.max(0, (ry - y) * 12 + (rm - mm));
      counts[buckets.findIndex(([, lo, hi]) => gap >= lo && gap <= hi)]++;
    }
    document.querySelector('[data-i18n="c_gaps_sub"]').textContent = t("c_gaps_sub", { month: monthLabel(ref) });
    const box = document.getElementById("chart-gaps");
    const W = Math.max(300, box.clientWidth), H = 260;
    const m = { top: 22, right: 8, bottom: 24, left: 8 };
    const iw = W - m.left - m.right, ih = H - m.top - m.bottom;
    const band = iw / buckets.length, bw = Math.min(40, band * 0.6);
    const max = Math.max(1, ...counts);
    const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": t("c_gaps") });
    svg.append(s("line", { class: "baseline", x1: m.left, x2: W - m.right, y1: m.top + ih, y2: m.top + ih }));
    buckets.forEach(([label], i) => {
      const h = (counts[i] / max) * ih;
      const x = m.left + band * i + (band - bw) / 2;
      const p = s("path", { class: "mark", d: barPath(x, m.top + ih - h, bw, h, "top"), fill: css("--accent"), tabindex: 0 });
      const show = (e) => showTip(e, [el("div", { class: "tl" }, label),
        tipValue(fmtInt(counts[i]), fmtPct(cohort.length ? counts[i] / cohort.length : null))]);
      p.addEventListener("pointermove", show);
      p.addEventListener("pointerleave", hideTip);
      svg.append(p);
      svg.append(s("text", { x: x + bw / 2, y: m.top + ih - h - 6, "text-anchor": "middle", class: "label-strong" }, fmtInt(counts[i])));
      svg.append(s("text", { x: x + bw / 2, y: H - 6, "text-anchor": "middle" }, label));
    });
    box.replaceChildren(svg);
    dataTable(document.getElementById("tv-gaps"), [t("c_gaps"), t("count"), t("share")],
      buckets.map(([l], i) => [l, fmtInt(counts[i]), fmtPct(cohort.length ? counts[i] / cohort.length : null)]));
  }

  // ---------- heatmap ----------
  let heatRows = [];
  function renderHeat() {
    const ms = months();
    const wrap = document.getElementById("heatwrap");
    const canvas = document.getElementById("heat");
    const color = { "2": css("--a-content"), "3": css("--a-shell"), "4": css("--a-bad"), "5": css("--a-bad"), "0": css("--a-none") };
    document.getElementById("legend-heat").replaceChildren(...["2", "3", "4", "0"].map((k) =>
      el("span", {}, el("span", { class: "sw", style: `background:${color[k]}` }), t("wb." + k))));
    heatRows = scoped().filter((d) => d.wb).sort((a, b) => (b.wl || "").localeCompare(a.wl || "") || a.h.localeCompare(b.h));
    const W = wrap.clientWidth;  // the scrollbar gutter is reserved, so this stays stable
    const rowH = heatRows.length <= 150 ? 5 : heatRows.length <= 500 ? 2 : 1;
    const H = Math.max(1, heatRows.length * rowH);
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.round(W * dpr);
    canvas.height = Math.round(H * dpr);
    canvas.style.width = W + "px";
    canvas.style.height = H + "px";
    const ctx = canvas.getContext("2d");
    ctx.scale(dpr, dpr);
    const cw = W / ms.length;
    heatRows.forEach((d, r) => {
      for (let i = 0; i < ms.length; i++) {
        ctx.fillStyle = color[d.wb[i]] || color["0"];
        ctx.fillRect(i * cw, r * rowH, Math.ceil(cw), rowH);
      }
    });
    const axis = document.getElementById("heat-axis");
    axis.replaceChildren(...ms.map((m, i) => (m.endsWith("-01") && (W > 520 || Number(m.slice(0, 4)) % 2 === 1)
      ? el("span", { style: `position:absolute;left:${i * cw}px;font-size:11.5px;color:var(--muted)` }, m.slice(0, 4)) : null)).filter(Boolean));
    canvas.onpointermove = (e) => {
      const r = canvas.getBoundingClientRect();
      const row = Math.floor((e.clientY - r.top) / rowH), col = Math.floor((e.clientX - r.left) / cw);
      const d = heatRows[row];
      if (!d || col < 0 || col >= ms.length) return hideTip();
      showTip(e, [el("div", { class: "tv" }, d.d), el("div", { class: "tl" }, d.n || ""),
        tipValue(monthLabel(ms[col]), t("wb." + (d.wb[col] || "0")), color[d.wb[col]] || color["0"])]);
    };
    canvas.onpointerleave = hideTip;
    canvas.onclick = (e) => {
      const r = canvas.getBoundingClientRect();
      const d = heatRows[Math.floor((e.clientY - r.top) / rowH)];
      if (d) openDetail(d);
    };
  }

  // ---------- Common Crawl ----------
  function renderCC() {
    const crawls = state.summary.crawls || [];
    const box = document.getElementById("chart-cc");
    const base = scoped().filter((d) => d.ccb && d.ccs && d.act);
    const done = crawls.map((c, i) => base.length && base.every((d) => d.ccs[i] !== "?"));
    if (!crawls.length || !base.length) {
      box.replaceChildren(el("p", { class: "sub" }, t("cc_pending")));
      document.getElementById("tv-cc").replaceChildren();
      return;
    }
    const time = (c) => new Date(c.date + "T00:00:00Z").getTime();
    const vals = crawls.map((c, i) => (done[i] ? base.filter((d) => d.ccs[i] === "2").length : null));
    const points = crawls.map((c, i) => ({ x: time(c), v: vals[i] == null ? null : vals[i] / base.length }));
    const x0 = time(crawls[0]), x1 = time(crawls[crawls.length - 1]);
    const ticks = [];
    for (let y = new Date(x0).getUTCFullYear() + 1; y <= new Date(x1).getUTCFullYear(); y++) ticks.push({ x: Date.UTC(y, 0, 1), label: String(y) });
    lineChart(box, {
      label: t("c_cc"), xDomain: [x0, x1], xTicks: ticks, height: 240,
      annotations: [{ x: Date.UTC(2022, 1, 24), label: t("annot_war") }],
      series: [{ points, color: css("--a-content"), dots: true }],
      tooltip: (i) => [el("div", { class: "tl" }, `${crawls[i].crawl} · ${crawls[i].date}`),
        tipValue(fmtPct(points[i].v), `${fmtInt(vals[i])} / ${fmtInt(base.length)}`, css("--a-content"))],
    });
    dataTable(document.getElementById("tv-cc"), [t("crawl"), t("s_cc"), t("share")],
      crawls.map((c, i) => [`${c.crawl} (${c.date})`, fmtInt(vals[i]), fmtPct(points[i].v)]));
  }

  // ---------- live access ----------
  function renderLive() {
    const probe = state.summary.probe || {};
    document.getElementById("access-lede").textContent = probe.month
      ? t("access_lede", { month: monthLabel(probe.month), vantage: vantageText() }) : t("access_lede_none");
    document.getElementById("legend-live").replaceChildren(...GROUPS.map((g) =>
      el("span", {}, el("span", { class: "sw", style: `background:${css("--g-" + g)}` }), t("group." + g))));
    const base = state.domains.filter((d) => d.s && (state.region === "all" || d.r === state.region));
    const rows = [["all", base], ...CATS.map((c) => [c, base.filter((d) => d.c === c)])].filter(([, ds]) => ds.length);
    const box = document.getElementById("chart-live");
    const W = Math.max(300, box.clientWidth);
    const labelW = Math.min(230, W * 0.36), rowH = 22, gapY = 14;
    const H = rows.length * (rowH + gapY) + 4;
    const iw = W - labelW - 12;
    const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": t("c_live") });
    const table = [];
    rows.forEach(([cat, ds], ri) => {
      const y = ri * (rowH + gapY) + 2;
      const dim = state.category !== "all" && cat !== state.category && cat !== "all";
      const g = s("g", { class: dim ? "dim" : null });
      g.append(s("text", { x: 0, y: y + rowH / 2 + 4, class: cat === "all" ? "label-strong" : "label-ink" }, `${t("cat." + cat)} · ${fmtInt(ds.length)}`));
      let acc = 0;
      const cnt = Object.fromEntries(GROUPS.map((k) => [k, ds.filter((d) => d.g === k).length]));
      table.push([t("cat." + cat), ...GROUPS.map((k) => `${fmtInt(cnt[k])} (${fmtPct(cnt[k] / ds.length)})`)]);
      const segs = GROUPS.filter((k) => cnt[k] > 0);
      segs.forEach((k, si) => {
        const w = (cnt[k] / ds.length) * iw;
        const x = labelW + acc;
        const p = s("path", { class: "mark", d: barPath(x, y, Math.max(0, w - (si < segs.length - 1 ? 2 : 0)), rowH, si === segs.length - 1 ? "right" : null), fill: css("--g-" + k), tabindex: 0 });
        p.addEventListener("pointermove", (e) => showTip(e, [el("div", { class: "tl" }, t("cat." + cat)),
          tipValue(fmtPct(cnt[k] / ds.length), `${t("group." + k)} · ${fmtInt(cnt[k])}`, css("--g-" + k))]));
        p.addEventListener("pointerleave", hideTip);
        g.append(p);
        if (w > 44) g.append(s("text", { x: x + 6, y: y + rowH / 2 + 4, style: "fill:#fff;font-weight:600;pointer-events:none" }, fmtPct(cnt[k] / ds.length)));
        acc += w;
      });
      svg.append(g);
    });
    box.replaceChildren(svg);
    dataTable(document.getElementById("tv-live"), [t("category"), ...GROUPS.map((k) => t("group." + k))], table);
  }

  function barList(container, items, colorFor) {
    const max = Math.max(1, ...items.map((i) => i.n));
    container.replaceChildren(...items.map((i) => el("div", { class: "barrow" },
      el("span", { class: "name", title: i.label }, i.label),
      el("span", { class: "track" }, el("span", { class: "fill", style: `display:block;width:${(i.n / max) * 100}%;background:${colorFor(i)}` })),
      el("span", { class: "val" }, fmtInt(i.n)))));
    if (!items.length) container.replaceChildren(el("p", { class: "sub" }, "—"));
  }

  function renderAccessLists() {
    const sc = scoped().filter((d) => d.s);
    const alive = sc.filter((d) => d.g !== "gone");
    const statusCounts = {};
    for (const d of sc) if (d.s !== "ok") statusCounts[d.s] = (statusCounts[d.s] || 0) + 1;
    const groupOf = (st) => ({ challenge: "waf", blocked: "waf", empty: "waf", timeout: "noconn", refused: "noconn", http_timeout: "noconn", http_error: "noconn", server_error: "error", client_error: "error", dns: "gone", lost: "gone" }[st]);
    barList(document.getElementById("list-reasons"),
      Object.entries(statusCounts).sort((a, b) => b[1] - a[1]).map(([st, n]) => ({ label: t("status." + st), n, g: groupOf(st) })),
      (i) => css("--g-" + i.g));
    const barriers = [
      ["ruca", alive.filter((d) => d.ruca).length],
      ["tls", alive.filter((d) => d.tlsok === false).length],
      ["https", alive.filter((d) => d.p443 !== "open" && d.p80 === "open").length],
      ["shell", alive.filter((d) => d.hk === "shell").length],
      ["robots_all", alive.filter((d) => d.rb === "all").length],
      ["robots_ia", alive.filter((d) => d.rb === "ia").length],
      ["offsite", alive.filter((d) => d.fh).length],
      ["free", sc.filter((d) => d.free).length],
    ].sort((a, b) => b[1] - a[1]);
    barList(document.getElementById("list-barriers"), barriers.map(([k, n]) => ({ label: t("barrier." + k), n })), () => css("--accent"));
    const vend = {};
    for (const d of alive) for (const v of d.v || []) vend[v] = (vend[v] || 0) + 1;
    barList(document.getElementById("list-vendors"),
      Object.entries(vend).sort((a, b) => b[1] - a[1]).map(([v, n]) => ({ label: v, n })), () => css("--accent"));
    const asn = {};
    for (const d of alive) if (d.asn) asn[d.asn] = (asn[d.asn] || 0) + 1;
    const ru = alive.filter((d) => d.ac === "RU").length;
    document.querySelector('[data-i18n="c_hosting_sub"]').textContent = t("c_hosting_sub", { ru: fmtPct(alive.length ? ru / alive.length : null) });
    barList(document.getElementById("list-asn"),
      Object.entries(asn).sort((a, b) => b[1] - a[1]).slice(0, 12).map(([a, n]) => ({ label: a, n })), () => css("--accent"));
  }

  // ---------- table ----------
  function statusBadge(d) {
    if (!d.s) return el("span", { class: "statusbadge" }, "—");
    return el("span", { class: "statusbadge", title: d.hr || "" },
      el("i", { style: `background:${css("--g-" + d.g)}` }, GROUP_ICON[d.g] || ""), t("status." + d.s));
  }
  function minis(d) {
    const map = { c: "--a-content", s: "--a-shell", bad: "--a-bad", n: "--a-none", u: "--a-unknown" };
    return el("span", { class: "minis" }, state.summary.years.map((y, i) => {
      const code = d.sn[i] || "?";
      const g = snapGroup(code);
      return el("b", { title: `${y}: ${t("snap." + (g === "bad" ? code : g))}`, style: `background:${css(map[g])};${g === "u" ? "box-shadow:inset 0 0 0 1px " + css("--axis") : ""}` });
    }));
  }
  function filteredTable() {
    const ms = months();
    const cutoff = ms[Math.max(0, ms.length - 12)];
    const q = state.q.trim().toLowerCase();
    let rows = scoped().filter((d) => {
      if (q && !(d.h.includes(q) || d.d.toLowerCase().includes(q) || (d.n || "").toLowerCase().includes(q) || (d.o || "").toLowerCase().includes(q))) return false;
      if (state.status.startsWith("g:") && d.g !== state.status.slice(2)) return false;
      if (state.archived === "recent" && !(d.wl && d.wl >= cutoff)) return false;
      if (state.archived === "stale" && !(d.wl && d.wl < cutoff)) return false;
      if (state.archived === "never" && d.wl) return false;
      return true;
    });
    const { key, dir } = state.sort;
    rows.sort((a, b) => {
      const av = a[key] || "", bv = b[key] || "";
      return (av < bv ? -1 : av > bv ? 1 : 0) * dir || a.h.localeCompare(b.h);
    });
    return rows;
  }
  function renderTable() {
    const rows = filteredTable();
    const tbody = document.querySelector("#domains-table tbody");
    tbody.replaceChildren(...rows.slice(0, state.shown).map((d) => el("tr", {},
      el("td", {}, el("a", { class: "host", href: "#site=" + encodeURIComponent(d.h), onclick: (e) => { e.preventDefault(); openDetail(d); } }, d.d),
        el("div", { class: "org" }, d.n || d.o || "")),
      el("td", { class: "hide-sm" }, t("cat." + d.c)),
      el("td", {}, statusBadge(d)),
      el("td", { class: "hide-sm" }, (d.v || []).join(", ")),
      el("td", {}, d.wl ? d.wl : t("never")),
      el("td", { class: "hide-sm" }, minis(d)))));
    document.getElementById("table-count").textContent = t("shown", { shown: fmtInt(Math.min(state.shown, rows.length)), n: fmtInt(rows.length) });
    document.getElementById("more").hidden = rows.length <= state.shown;
  }

  // ---------- detail card ----------
  function openDetail(d) {
    const dlg = document.getElementById("detail");
    const ms = months();
    const wbColor = { "2": css("--a-content"), "3": css("--a-shell"), "4": css("--a-bad"), "5": css("--a-bad"), "0": css("--a-none") };
    const kv = (pairs) => el("dl", { class: "kv" }, pairs.filter((p) => p[1] != null && p[1] !== "").flatMap(([k, v]) => [el("dt", {}, k), el("dd", {}, v)]));
    const link = (href, text) => el("a", { href, target: "_blank", rel: "noopener noreferrer" }, text);
    const strip = el("div", { class: "strip" }, ms.map((m, i) => el("b", { title: `${m}: ${t("wb." + (d.wb[i] || "0"))}`, style: `background:${wbColor[d.wb[i]] || wbColor["0"]}` })));
    const yearsRow = el("div", { class: "strip-years" }, ms.map((m) => el("span", { style: "width:7px;flex:none;overflow:visible;white-space:nowrap" }, m.endsWith("-01") ? m.slice(0, 4) : "")));
    const snaps = el("ul", {}, state.summary.years.map((y, i) => {
      const code = d.sn[i] || "?";
      const g = snapGroup(code);
      const ts = (d.sts || [])[i];
      const label = t("snap." + (g === "bad" ? code : g));
      return el("li", {}, `${y}: `, ts ? link(`https://web.archive.org/web/${ts}/${d.h}/`, `${label} (${ts.slice(0, 8)})`) : label);
    }));
    const crawls = state.summary.crawls || [];
    const ccStrip = d.ccs ? el("div", { class: "strip" }, crawls.map((c, i) => {
      const code = d.ccs[i] || "?";
      const col = code === "2" ? wbColor["2"] : code === "3" ? wbColor["3"] : code === "e" ? wbColor["4"] : code === "?" ? css("--a-unknown") : wbColor["0"];
      return el("b", { title: `${c.crawl}: ${t("cc_codes." + code) || code}`, style: `width:14px;background:${col}` });
    })) : el("p", { class: "sub" }, t("cc_pending"));
    const tls = d.iss ? `${d.iss}${d.ruca ? " · Russian Trusted CA" : ""} · ${d.tlsok ? t("verified") : t("not_verified")}` : null;
    dlg.replaceChildren(
      el("div", { class: "detail-head" },
        el("div", {}, el("h3", {}, d.d), el("div", { class: "sub" }, [d.n, t("cat." + d.c)].filter(Boolean).join(" · "))),
        el("button", { class: "btn", type: "button", onclick: () => dlg.close() }, t("d_close"))),
      el("div", { class: "detail-body" },
        kv([[t("d_org"), d.o], [t("d_region"), d.r]]),
        el("h4", {}, t("d_live")),
        kv([
          [t("d_status"), statusBadge(d)],
          [t("d_ip"), d.ip ? `${d.ip} · ${d.asn || ""} ${d.ac ? "(" + d.ac + ")" : ""}` : null],
          [t("d_ports"), d.p443 || d.p80 ? `${d.p443 || "—"} / ${d.p80 || "—"}` : null],
          [t("d_tls"), tls],
          [t("d_http"), d.hs ? `${d.hs} · ${d.hk || ""}${d.hr ? " · " + d.hr : ""}` : d.hr],
          [t("d_title"), d.t],
          [t("d_vendors"), (d.v || []).join(", ")],
          [t("d_robots"), d.rb ? t(d.rb === "ia" ? "barrier.robots_ia" : "barrier.robots_all") : null],
          [t("d_lost"), d.lr ? (d.lr.startsWith("spam:") ? t("lost_spam", { m: d.lr.slice(5) }) : t("lost_rereg", { date: d.lr.slice(6) })) : null],
          [t("d_whois"), d.wc || d.wr || d.free ? (d.free ? t("barrier.free") : [d.wc && t("whois_created", { date: d.wc }), d.wr, d.wo && t("owner." + d.wo)].filter(Boolean).join(" · ")) : null],
        ]),
        el("h4", {}, t("d_archive")),
        kv([[t("d_captures"), fmtInt(d.wn)], [t("d_lastok"), d.wl || t("never")], [t("d_cohort"), d.co ? t("yes") : t("no")]]),
        el("div", { class: "stripwrap" }, strip, yearsRow),
        el("h4", {}, t("d_years")), snaps,
        el("h4", {}, t("d_cc")), el("div", { class: "stripwrap" }, ccStrip),
        el("h4", {}, t("d_links")),
        el("p", {}, link(`http://${d.h}/`, t("d_open_site")), " · ", link(`https://web.archive.org/web/*/${d.h}`, t("d_calendar")),
          " · ", el("a", { href: "#feedback", onclick: (e) => { e.preventDefault(); dlg.close(); reportSite(d); } }, t("d_report")))));
    if (!dlg.open) dlg.showModal();
    dlg.querySelectorAll(".stripwrap").forEach((w) => { w.scrollLeft = w.scrollWidth; });  // latest months first
    history.replaceState(null, "", "#site=" + encodeURIComponent(d.h));
  }
  document.getElementById("detail").addEventListener("close", () => {
    if (location.hash.startsWith("#site=")) history.replaceState(null, "", location.pathname + location.search);
  });

  // ---------- downloads ----------
  function renderDownloads() {
    const pm = state.summary.probe && state.summary.probe.month;
    const files = [
      ["data/download/domains.csv.gz", t("dl.domains")],
      ["data/download/registry.csv", t("dl.registry")],
      pm ? [`data/download/probe_${pm}.jsonl.gz`, t("dl.probe", { month: pm })] : null,
      ["data/download/wayback_snapshots.jsonl.gz", t("dl.snapshots")],
      ["data/download/commoncrawl_hosts.csv.gz", t("dl.cc")],
      ["data/summary.json", t("dl.summary")],
    ].filter(Boolean);
    document.getElementById("downloads").replaceChildren(...files.map(([href, label]) => el("li", {}, el("a", { href }, label))));
  }

  // ---------- feedback (prefilled GitHub issue or email, no backend) ----------
  const fbForm = document.getElementById("fb-form");
  const fbMsg = document.getElementById("fb-msg");
  const URL_LIMIT = 7000;  // GitHub and mail clients reject longer prefilled URLs
  function renderFeedback() {
    const note = fbForm.querySelector(".fb-note");
    note.replaceChildren(t("fb_note_1"), " ", el("a", { href: "mailto:" + FEEDBACK_EMAIL }, FEEDBACK_EMAIL), t("fb_note_2"));
    const list = document.getElementById("fb-sites");
    if (!list.childElementCount) list.replaceChildren(...state.domains.map((d) => el("option", { value: d.d })));
  }
  function findSite(text) {
    const v = text.trim().toLowerCase().replace(/^[a-z]+:\/\//, "").replace(/[/?#].*$/, "").replace(/^www\./, "");
    return v ? state.domains.find((d) => d.h === v || d.d.toLowerCase() === v) : null;
  }
  function reportSite(d) {
    fbForm.querySelector('input[name="fb-type"][value="error"]').checked = true;
    document.getElementById("fb-site").value = d.d;
    fbStatus("");
    document.getElementById("feedback").scrollIntoView({ behavior: "smooth" });
    document.getElementById("fb-message").focus({ preventScroll: true });
  }
  function feedbackFields() {
    const type = (fbForm.querySelector('input[name="fb-type"]:checked') || {}).value || "other";
    const siteText = document.getElementById("fb-site").value.trim();
    const site = findSite(siteText);
    const pm = state.summary && state.summary.probe && state.summary.probe.month;
    return {
      type, typeLabel: t("fb_types." + type),
      site: site ? `${site.d} (${SITE_URL}#site=${encodeURIComponent(site.h)})` : siteText,
      siteShort: site ? site.d : siteText,
      message: document.getElementById("fb-message").value.trim(),
      contact: document.getElementById("fb-contact").value.trim(),
      context: t("fb_context", { month: pm || "—", url: SITE_URL, lang: state.lang }),
    };
  }
  function fbStatus(kind, ...nodes) {
    nodes = nodes.filter((n) => n != null);
    fbMsg.className = "fb-msg " + kind;
    fbMsg.replaceChildren(...nodes);
    fbMsg.hidden = !nodes.length;
  }
  // Too long for a URL: copy the full text and let the visitor open a short prefill and paste it
  async function openPrefilled(build, body, sameTab) {
    const url = build(body);
    if (url.length <= URL_LIMIT) {
      if (sameTab) location.href = url;
      else window.open(url, "_blank", "noopener");
      return;
    }
    let copied = true;
    try { await navigator.clipboard.writeText(body); } catch (e) { copied = false; }
    const short = build(t("fb_pasted"));
    fbStatus("info", copied ? t("fb_copied") : t("fb_too_long"), " ",
      copied ? el("a", sameTab ? { href: short } : { href: short, target: "_blank", rel: "noopener" }, t("fb_open")) : null);
  }
  fbForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const f = feedbackFields();
    if (!f.message) {
      fbStatus("error", t("fb_err_empty"));
      document.getElementById("fb-message").focus();
      return;
    }
    fbStatus("");
    const subject = `[${f.typeLabel}] ${f.siteShort || f.message.replace(/\s+/g, " ").slice(0, 60)}`;
    if ((e.submitter && e.submitter.value) === "email") {
      const head = [`${t("fb_type")}: ${f.typeLabel}`, f.site && `${t("fb_site_short")}: ${f.site}`, f.contact && `${t("fb_contact_short")}: ${f.contact}`].filter(Boolean).join("\n");
      openPrefilled((b) => `mailto:${FEEDBACK_EMAIL}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(b)}`,
        `${head}\n\n${f.message}\n\n--\n${f.context}`, true);
    } else {
      const head = [`**${t("fb_type")}:** ${f.typeLabel}`, f.site && `**${t("fb_site_short")}:** ${f.site}`].filter(Boolean).join("\n");
      openPrefilled((b) => `${REPO_URL}/issues/new?title=${encodeURIComponent(subject)}&body=${encodeURIComponent(b)}`,
        `${head}\n\n${f.message}\n\n---\n${f.context}`, false);
    }
  });

  // ---------- orchestration ----------
  function renderScoped() {
    renderFilters();
    renderTimeline(); renderQuality(); renderGaps(); renderHeat(); renderCC();
    renderLive(); renderAccessLists(); renderTable();
  }
  function renderAll() {
    applyStatic();
    renderHero();
    renderScoped();
    renderDownloads();
    renderFeedback();
  }

  document.getElementById("f-category").addEventListener("change", (e) => { state.category = e.target.value; state.shown = 50; renderScoped(); });
  document.getElementById("f-region").addEventListener("change", (e) => { state.region = e.target.value; state.shown = 50; renderScoped(); });
  document.getElementById("q").addEventListener("input", (e) => { state.q = e.target.value; state.shown = 50; renderTable(); });
  document.getElementById("f-status").addEventListener("change", (e) => { state.status = e.target.value; state.shown = 50; renderTable(); });
  document.getElementById("f-archived").addEventListener("change", (e) => { state.archived = e.target.value; state.shown = 50; renderTable(); });
  document.getElementById("more").addEventListener("click", () => { state.shown += 100; renderTable(); });
  document.querySelectorAll("#domains-table th[data-sort]").forEach((th) => th.addEventListener("click", () => {
    const key = th.dataset.sort;
    state.sort = { key, dir: state.sort.key === key ? -state.sort.dir : (key === "wl" ? -1 : 1) };
    renderTable();
  }));
  document.getElementById("lang-toggle").addEventListener("click", () => {
    state.lang = state.lang === "ru" ? "en" : "ru";
    store.set("lang", state.lang);
    renderAll();
  });
  document.getElementById("theme-toggle").addEventListener("click", () => {
    const dark = document.documentElement.dataset.theme
      ? document.documentElement.dataset.theme === "dark"
      : window.matchMedia("(prefers-color-scheme: dark)").matches;
    document.documentElement.dataset.theme = dark ? "light" : "dark";
    store.set("theme", document.documentElement.dataset.theme);
    renderScoped();
  });
  const savedTheme = store.get("theme");
  if (savedTheme === "light" || savedTheme === "dark") document.documentElement.dataset.theme = savedTheme;
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { if (state.summary) renderScoped(); });
  // Charts are drawn for the container width, so redraw when the content width changes
  let resizeTimer, lastWidth = 0;
  new ResizeObserver((entries) => {
    const width = Math.round(entries[0].contentRect.width);
    if (width === lastWidth) return;
    lastWidth = width;
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => state.summary && renderScoped(), 150);
  }).observe(document.querySelector("main"));

  function openFromHash() {
    const m = location.hash.match(/^#site=(.+)$/);
    if (!m) return;
    const d = state.domains.find((x) => x.h === decodeURIComponent(m[1]));
    if (d) openDetail(d);
  }

  Promise.all([fetch("data/summary.json").then((r) => r.json()), fetch("data/domains.json").then((r) => r.json())])
    .then(([summary, domains]) => {
      state.summary = summary;
      state.domains = domains;
      renderAll();
      openFromHash();
      window.addEventListener("hashchange", openFromHash);
    })
    .catch((err) => {
      document.getElementById("hero-label").textContent = "Data failed to load: " + err.message;
    });
})();
