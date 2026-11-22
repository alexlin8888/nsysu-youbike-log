// Final report, CVPR two-column layout: the midterm report (build_hw3.js) plus the work done since.
// Blue = new or changed since the midterm report (HW3). Text that was already in HW3, black or blue there, is black.
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, ExternalHyperlink, Table, TableRow, TableCell, WidthType, Tab, TabStopType,
  AlignmentType, SectionType, BorderStyle, ShadingType, VerticalAlign,
} = require("docx");

const FIG = process.env.FIG_DIR || "figs/";
const PAGE = { width: 12240, height: 15840 };
const MARGIN = { top: 1440, right: 902, bottom: 1622, left: 1440, header: 431, footer: 431, gutter: 0 };
const COL_SPACE = 544;
const COL_W = (PAGE.width - MARGIN.left - MARGIN.right - COL_SPACE) / 2; // 4677 twips
const COL_PX = Math.floor((COL_W / 1440) * 96) - 2;
const BLUE = undefined;   // HW3 text keeps its helpers (nb, bodyB, capB, ...) and prints black
const NEW = "0000FF";     // new or changed since HW3
const KAI = "標楷體";   // all Chinese text in 標楷體 (DFKai-SB)
const FONT = { ascii: "Times New Roman", hAnsi: "Times New Roman", cs: "Times New Roman", eastAsia: KAI };
const MONO = { ascii: "Courier New", hAnsi: "Courier New", cs: "Courier New", eastAsia: KAI };

// ---------- runs ----------
const run = (text, o = {}) => new TextRun({ text, font: FONT, size: 20, ...o });
const bold = (t, o = {}) => run(t, { bold: true, ...o });
const ital = (t, o = {}) => run(t, { italics: true, ...o });
const sub = (t, o = {}) => run(t, { subScript: true, ...o });
const nb = (t, o = {}) => run(t, { color: BLUE, ...o });
const nbi = (t, o = {}) => run(t, { color: BLUE, italics: true, ...o });
const nbb = (t, o = {}) => run(t, { color: BLUE, bold: true, ...o });
const nsub = (t) => run(t, { subScript: true, color: BLUE });
const nsup = (t) => run(t, { superScript: true, color: BLUE });
// final-report runs (blue)
const fb = (t, o = {}) => run(t, { color: NEW, ...o });
const fbi = (t, o = {}) => run(t, { color: NEW, italics: true, ...o });
const fbb = (t, o = {}) => run(t, { color: NEW, bold: true, ...o });
const fsub = (t) => run(t, { subScript: true, color: NEW });
const fsup = (t) => run(t, { superScript: true, color: NEW });
// "{{...}}" inside a string marks the new part: mix("as in {{Fig. 9}}") gives a black run and a blue run
const mix = (text, o = {}) => text.split(/(\{\{.*?\}\})/).filter((s) => s.length).map((s) => (s.startsWith("{{") ? fb(s.slice(2, -2), o) : run(s, o)));
const plain = (text) => text.replace(/\{\{|\}\}/g, "");

// ---------- paragraphs ----------
const tagKeep = (p, keep = true, label = null) => { if (keep) p.__keep = true; if (label) p.__label = label; return p; };   // a figure may not be placed right after this
const P = (children, o = {}) => tagKeep(new Paragraph({ alignment: AlignmentType.JUSTIFIED, indent: { firstLine: 288 }, spacing: { after: 0, line: 240 }, children, ...o }), !!o.keepNext);
const body = (parts, o = {}) => P(typeof parts === "string" ? mix(parts) : parts, o);
const bodyB = (text, o = {}) => P(mix(text), text.trim().endsWith(":") ? { keepNext: true, ...o } : o);
// a paragraph that is new in the final report
const bodyF = (parts, o = {}) => P(typeof parts === "string" ? [fb(parts)] : parts, o);
const h1 = (t, blue = false) => tagKeep(new Paragraph({ keepNext: true, spacing: { before: 120, after: 40, line: 240 }, children: [run(t, { bold: true, size: 24, color: blue ? BLUE : undefined })] }), true, t);
const h2 = (t, blue = false) => tagKeep(new Paragraph({ keepNext: true, spacing: { before: 90, after: 30, line: 240 }, children: [run(t, { bold: true, size: 22, color: blue ? BLUE : undefined })] }), true, t);
// heading that keeps the HW1 words in black and marks changed numbers / words in blue: h2mix([["2.3.", true], [" Demand reconstruction", false], ...])
const h2mix = (parts) => tagKeep(new Paragraph({ keepNext: true, spacing: { before: 90, after: 30, line: 240 },
  children: parts.map(([t, b]) => run(t, { bold: true, size: 22, color: b ? BLUE : undefined })) }), true, parts.map((x) => x[0]).join(""));
const h3 = (t, blue = true) => tagKeep(new Paragraph({ keepNext: true, spacing: { before: 60, after: 20, line: 240 }, children: [run(t, { bold: true, italics: true, size: 20, color: blue ? BLUE : undefined })] }), true, t);
// headings of the final report; "{{...}}" marks the new words
const hF = (size, before, after, italics) => (t) => tagKeep(new Paragraph({ keepNext: true, spacing: { before, after, line: 240 }, children: mix(t, { bold: true, italics, size }) }), true, plain(t));
const h1F = hF(24, 120, 40, false), h2F = hF(22, 90, 30, false), h3F = hF(20, 60, 20, true);
// bullet: hanging indent with a dash
function bullet(parts, { blue = true, last = false } = {}) {
  const ch = typeof parts === "string" ? [blue ? nb(parts) : run(parts)] : parts;
  return tagKeep(new Paragraph({ alignment: AlignmentType.JUSTIFIED, indent: { left: 300, hanging: 180 }, spacing: { after: last ? 40 : 0, line: 240 },
    children: [run("– ", { color: blue ? BLUE : undefined }), ...ch] }), !last);   // no figure inside a list
}
// numbered equation: centred with the number at the right margin
function eq(parts, num, color = BLUE) {
  return new Paragraph({ alignment: AlignmentType.LEFT, indent: { left: 600 }, spacing: { before: 40, after: 40, line: 240 },
    tabStops: [{ type: TabStopType.RIGHT, position: COL_W }], children: [...parts, new TextRun({ children: [new Tab(), `(${num})`], font: FONT, size: 20, color })] });
}
const eqF = (parts, num) => eq(parts, num, NEW);
// Figures are placed as markers first; LAYOUT (env, JSON {file: {shift, frac}}) may move a figure `shift`
// elements later (negative = earlier) and scale it, so that no column ends with a large blank.
const LAYOUT = process.env.LAYOUT ? JSON.parse(process.env.LAYOUT) : (fs.existsSync("layout_final.json") ? JSON.parse(fs.readFileSync("layout_final.json", "utf8")) : {});
function figure(file, caption, { widthFrac = 1.0 } = {}) {
  return [{ __fig: true, file, caption, widthFrac }];
}
function expandFigure(m) {
  const buf = fs.readFileSync(FIG + m.file);
  const w = buf.readUInt32BE(16), h = buf.readUInt32BE(20);
  const frac = (LAYOUT[m.file] && LAYOUT[m.file].frac) || m.widthFrac;
  const W = Math.round(COL_PX * frac), H = Math.round((W * h) / w);
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 40 }, keepNext: true,
      children: [new ImageRun({ type: "png", data: buf, transformation: { width: W, height: H } })] }),
    new Paragraph({ alignment: AlignmentType.JUSTIFIED, keepLines: true, spacing: { before: 0, after: 140, line: 200 }, children: m.caption }),
  ];
}
function placeFigures(items) {
  // base = all non-figure elements; a figure is emitted right after base element `after`
  const base = [], figs = [];
  for (const x of items) {
    if (x && x.__fig) figs.push({ m: x, def: base.length - 1 });
    else base.push(x);
  }
  for (const f of figs) {
    const L = LAYOUT[f.m.file] || {};
    f.after = L.after !== undefined ? L.after : f.def;
  }
  if (process.env.DUMP) {
    base.forEach((x, i) => console.log("EL " + i + " " + (x.__keep ? "KEEP " : "") + (x.__label || x.constructor.name)
      + figs.filter((f) => f.def === i).map((f) => "   <-- default " + f.m.file).join("")));
  }
  for (let k = 1; k < figs.length; k++) if (figs[k].after < figs[k - 1].after) console.log("ORDER_VIOLATION");
  for (const f of figs) if (f.after >= 0 && base[f.after].__keep) console.log("ORDER_VIOLATION");
  console.log("FIGS:" + JSON.stringify(figs.map((f) => f.m.file)));
  // table groups (caption, table, spacer) may be moved as a block: LAYOUT["Table N"] = {after: element id}
  let order = base.map((_, i) => i);
  base.forEach((x, i) => {
    const key = x.__label && x.__label.startsWith("Table ") ? x.__label.trim().replace(/\.$/, "") : null;
    if (!key || !LAYOUT[key] || LAYOUT[key].after === undefined) return;
    const grp = [i, i + 1].concat(base[i + 2] && base[i + 2].__spacer ? [i + 2] : []);
    const tgt = LAYOUT[key].after;
    if (base[tgt].__keep || grp.includes(tgt)) { console.log("ORDER_VIOLATION"); return; }
    order = order.filter((k) => !grp.includes(k));
    order.splice(order.indexOf(tgt) + 1, 0, ...grp);
  });
  const out = [];
  figs.filter((f) => f.after < 0).forEach((f) => out.push(...expandFigure(f.m)));
  order.forEach((i) => { out.push(base[i]); figs.filter((f) => f.after === i).forEach((f) => out.push(...expandFigure(f.m))); });
  return out;
}
const cap = (label, text) => [bold(label, { size: 17 }), run(text, { size: 17 })];
const capB = (label, text) => [bold(label, { size: 17, color: BLUE }), run(text, { size: 17, color: BLUE })];
const capNum = (label, text) => [bold(label, { size: 17, color: BLUE }), run(text, { size: 17 })];   // HW1 caption, figure renumbered
// caption with "{{...}}" markup: capM("{{Figure 9. }}", "old words {{new words}}")
const capM = (label, text) => [...mix(label, { bold: true, size: 17 }), ...mix(text, { size: 17 })];

// ---------- tables ----------
function cell(text, { width, bold: b = false, shade = false, align = AlignmentType.LEFT, blue = true, size = 15, keep = true, mono = false } = {}) {
  const lines = Array.isArray(text) ? text : [text];
  return new TableCell({
    width: { size: width, type: WidthType.DXA }, margins: { top: 14, bottom: 14, left: 50, right: 50 },
    shading: shade ? { type: ShadingType.CLEAR, fill: "EDEDED", color: "auto" } : undefined, verticalAlign: VerticalAlign.CENTER,
    children: lines.map((ln) => new Paragraph({ alignment: align, keepNext: keep, keepLines: true, spacing: { after: 0, line: 210 },
      children: String(ln).split(/(\{\{.*?\}\})/).filter((s) => s.length).map((s) => new TextRun({ text: plain(s), font: mono ? MONO : FONT, size, bold: b, color: s.startsWith("{{") ? NEW : undefined })) })),
  });
}
function table(widths, header, rows, { aligns = null, size = 15 } = {}) {
  const border = { style: BorderStyle.SINGLE, size: 4, color: "999999" };
  const none = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
  const al = (i) => (aligns ? aligns[i] : (i === 0 ? AlignmentType.LEFT : AlignmentType.CENTER));
  return new Table({
    width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA }, columnWidths: widths,
    borders: { top: border, bottom: border, left: none, right: none, insideHorizontal: { style: BorderStyle.SINGLE, size: 2, color: "BBBBBB" }, insideVertical: none },
    rows: [
      new TableRow({ tableHeader: true, cantSplit: true, children: header.map((t, i) => cell(t, { width: widths[i], bold: true, shade: true, align: al(i), size })) }),
      ...rows.map((r, ri) => new TableRow({ cantSplit: true, children: r.map((t, i) => cell(t, { width: widths[i], align: al(i), size, keep: ri < rows.length - 1 })) })),   // tables never split across columns
    ],
  });
}
const tableCaption = (label, text) => tagKeep(new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { before: 100, after: 50, line: 220 }, keepNext: true, keepLines: true, children: capB(label, text) }), true, label);
const tableCaptionM = (label, text) => tagKeep(new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { before: 100, after: 50, line: 220 }, keepNext: true, keepLines: true, children: capM(label, text) }), true, plain(label));
const allNew = (rows) => rows.map((r) => r.map((c) => "{{" + c + "}}"));
const spacer = () => { const p = new Paragraph({ spacing: { before: 0, after: 80, line: 120 }, children: [run("", { size: 6 })] }); p.__spacer = true; return p; };
// one-cell box (changes summary, algorithm)
function box(lines, { mono = false, size = 16, fill = "F4F7FD", line = 220, color = BLUE } = {}) {
  const border = { style: BorderStyle.SINGLE, size: 4, color: "7F9CCB" };
  return new Table({
    width: { size: COL_W, type: WidthType.DXA }, columnWidths: [COL_W],
    borders: { top: border, bottom: border, left: border, right: border, insideHorizontal: border, insideVertical: border },
    rows: [new TableRow({ cantSplit: true, children: [new TableCell({
      width: { size: COL_W, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 90, right: 90 },
      shading: { type: ShadingType.CLEAR, fill, color: "auto" },
      children: lines.map((ln) => new Paragraph({ alignment: AlignmentType.LEFT, keepLines: true, spacing: { after: 0, line },
        indent: mono ? { left: 0 } : { left: 200, hanging: 200 },
        children: typeof ln === "string" ? [new TextRun({ text: ln, font: mono ? MONO : FONT, size, color })] : ln })),
    })] })],
  });
}

// ---------- references ----------
const REFS = [
  "臺北市政府交通局. 臺北市公共自行車 2.0 租借紀錄, 2020–2026, data.taipei.",
  "C.-X. Jian. youbike-historical-data (10-min Taipei YouBike 2.0 inventory snapshots), GitHub, 2024–2025.",
  "報導者 The Reporter. 台北市 YouBike 多熱門？數據告訴你, Apr. 2024.",
  "T. Raviv et al. Static repositioning in a bike-sharing system: models and solution approaches. EURO J. Transp. Logist., 2(3):187–229, 2013.",
  "J. Liu et al. Rebalancing bike sharing systems: A multi-source data smart optimization. In KDD, 2016.",
  "S. Ghosh et al. Dynamic repositioning to reduce lost demand in bike sharing systems. J. Artif. Intell. Res., 58:387–430, 2017.",
  "Y. Li, Y. Zheng, and Q. Yang. Dynamic bike reposition: A spatio-temporal reinforcement learning approach. In KDD, 2018.",
  "A. Negahban. Simulation-based estimation of the real demand in bike-sharing systems in the presence of censoring. Eur. J. Oper. Res., 277(1):317–332, 2019.",
  "D. Gammelli et al. Estimating latent demand of shared mobility through censored Gaussian processes. Transp. Res. Part C, 120:102775, 2020.",
  "H. Luo et al. Estimating rebalancing activities and vehicle use for existing station-based bike share systems. Transportation, 2026.",
  "周欣儀. 臺大校總區周遭 YouBike 2.0 使用行為與調度優化研究. 碩士論文, 國立臺灣大學機械工程學系, 2025.",
  "YouBike 即時站點資料 (apis.youbike.com.tw); 交通部 TDX (tdx.transportdata.tw); 高雄市開放資料 kcgoa-00000595-e5c.",
];
const NEW_REFS = [
  "G. Ke et al. LightGBM: A highly efficient gradient boosting decision tree. In NeurIPS, 2017.",
  "M. P. Naeini, G. Cooper, and M. Hauskrecht. Obtaining well calibrated probabilities using Bayesian binning. In AAAI, 2015.",
  "G. W. Brier. Verification of forecasts expressed in terms of probability. Monthly Weather Review, 78(1):1–3, 1950.",
  "S. Kirkpatrick, C. D. Gelatt, and M. P. Vecchi. Optimization by simulated annealing. Science, 220(4598):671–680, 1983.",
  "Group 54. nsysu-youbike-log: logger, analysis code and results, github.com/alexlin8888/nsysu-youbike-log, 2026.",
  "J. Schuijbroek, R. C. Hampshire, and W.-J. van Hoeve. Inventory rebalancing and vehicle routing in bike sharing systems. Eur. J. Oper. Res., 257(3):992–1004, 2017.",
  "C. Fricker and N. Gast. Incentives and redistribution in homogeneous bike-sharing systems with stations of finite capacity. EURO J. Transp. Logist., 5(3):261–291, 2016.",
  "D. K. George and C. H. Xia. Fleet-sizing and service availability for a vehicle rental system via closed queueing networks. Eur. J. Oper. Res., 211(1):198–207, 2011.",
  "B. Zadrozny and C. Elkan. Transforming classifier scores into accurate multiclass probability estimates. In KDD, 2002.",
  "B. Efron and R. J. Tibshirani. An Introduction to the Bootstrap. Chapman & Hall, 1993.",
  "L. Chen et al. Dynamic cluster-based over-demand prediction in bike sharing systems. In UbiComp, 2016.",
  "E. O’Mahony and D. B. Shmoys. Data analysis and optimization for (Citi)Bike sharing. In AAAI, 2015.",
  "Y. Li, Y. Zheng, H. Zhang, and L. Chen. Traffic prediction in a bike-sharing system. In ACM SIGSPATIAL, 2015.",
  "嚴文廷. 維繫台北街道的微笑風景──YouBike 調度員與維修員的工作日常. 報導者, 6 Apr. 2024.",
  "國立中山大學. 課程查詢系統, 115 學年度第 1 學期, selcrs.nsysu.edu.tw, accessed 17 Oct. 2026.",
];
const FINAL_REFS = [
  "OpenStreetMap contributors. OpenStreetMap, openstreetmap.org; map data under the Open Database License.",
  "V. Agafonkin. Leaflet: an open-source JavaScript library for mobile-friendly interactive maps, leafletjs.com.",
  "中央社. 高雄YouBike推「友愛接力」 單次最高可獲10元回饋, 2026-06-24.",
  "柯皓翔. 台北市YouBike多熱門？重啟「前30分鐘免費」後更難借嗎？數據告訴你. 報導者, 2024-04-01.",
  "李欣恩. 基於CPSS之共享自行車存量調度分析系統. 碩士論文, 國立臺灣大學工程科學及海洋工程學系, 2023.",
  "詹詠迪. 共享單車系統之即時需求預測與運補決策. 碩士論文, 國立臺灣大學工業工程學研究所, 2025.",
  "H. Chung, D. Freund, and D. B. Shmoys. Bike Angels: An analysis of Citi Bike’s incentive program. In ACM COMPASS, 2018.",
  "M. Kay, T. Kola, J. Hullman, and S. Munson. When(ish) is my bus? User-centered visualizations of uncertainty in everyday, mobile predictive systems. In CHI, 2016.",
  "M. Fernandes, L. Walls, S. Munson, J. Hullman, and M. Kay. Uncertainty displays using quantile dotplots or CDFs improve transit decision-making. In CHI, 2018.",
  "F. C. Bull et al. WHO 2020 guidelines on physical activity and sedentary behaviour. Br. J. Sports Med., 54(24):1451–1462, 2020.",
  "C. A. Celis-Morales et al. Association between active commuting and incident cardiovascular disease, cancer, and mortality. BMJ, 357:j1456, 2017.",
  "YouBike 微笑單車. 高雄市收費方式, youbike.com.tw/region/kcg/rate, accessed 22 Nov. 2026.",
];
function references() {
  const all = [...REFS.map((t) => [t, false]), ...NEW_REFS.map((t) => [t, false]), ...FINAL_REFS.map((t) => [t, true])];
  return all.map(([t, blue], i) => new Paragraph({
    alignment: /[\u3400-\u9fff]/.test(t) ? AlignmentType.LEFT : AlignmentType.JUSTIFIED, indent: { left: 260, hanging: 260 }, spacing: { after: 0, line: 190 },   // CJK entries left-aligned: justification spreads their characters
    children: [run(`[${i + 1}] `, { size: 15, color: blue ? NEW : undefined }), run(t, { size: 15, color: blue ? NEW : undefined })],
  }));
}

// ---------- title block ----------
// The video link comes from VIDEO_URL or from video_url.txt next to this file; until the video is uploaded a placeholder is printed.
const VIDEO = (process.env.VIDEO_URL || (fs.existsSync("video_url.txt") ? fs.readFileSync("video_url.txt", "utf8").trim() : "")) || "link to be added after upload";
// Results on the teaching days logged after the evaluation was frozen (analysis/code/final_prospective.py); rerun it
// before the last build so that the report covers the logger up to the deadline.
const PRO = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "analysis", "results", "final", "prospective", "prospective.json"), "utf8"));
const PW = PRO.warning, PA = PRO.advice.leave;
const pct = (x) => `${Math.round(100 * x)}%`;
const WORD = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"];
const words = (n) => (n <= 10 ? WORD[n] : String(n));
const span = (days) => { const a = +days[0].slice(8), b = +days[days.length - 1].slice(8); return a === b ? `${a} Nov` : `${a}–${b} Nov`; };
const m1 = (x) => x.toFixed(1);
const PRO_ABSTRACT = ` On the ${words(PW.n_days)} teaching days logged after this evaluation was frozen, the same rule flagged ${pct(PW.flagged)} of the stockouts a median of ${PW.lead_median_min} minutes ahead.`;
const PRO_ADVICE = (() => {
  const same = m1(PA.min_pick) === m1(PA.min_near) && m1(PA.min_pick) === m1(PA.min_alt);
  const mins = same ? `the station the page named, the station in front and the nearest one the live counts showed all took ${m1(PA.min_pick)} minutes`
    : `the station the page named took ${m1(PA.min_pick)} minutes, the station in front ${m1(PA.min_near)} and the live counts ${m1(PA.min_alt)}`;
  const verdict = Math.abs(PA.min_pick - PA.min_alt) <= 0.2 ? ": as on the held-out days, the page did as well as the live counts and no better" : "";
  return `On the ${words(PA.n_days)} teaching days scored so far (${span(PA.days)}, ${PA.cases} evening departures from campus), ${mins}${verdict}. Its first station had a bike ${pct(PA.ok_pick)} of the time, and the minutes it expected at the moment of leaving were off by ${m1(PA.err0)} on average (${m1(PA.err30)} when asked 30 minutes before). `;
})();
const PRO_REWARD = (() => {
  const cut = PW.evening_cut["0.5"];
  const same = Math.abs(cut - 0.11) <= 0.02 ? ", as on the held-out days" : ", against 11% on the held-out days";
  return `The evaluation was frozen on 16 Nov, and the logger kept running. On the ${words(PW.n_days)} teaching days logged since (${span(PW.days)}), with the chain still fitted to data up to 29 Oct, the rule flagged ${pct(PW.flagged)} of ${PW.events} stockouts, a median of ${PW.lead_median_min} minutes ahead, and ${pct(PW.precision)} of its flags were followed by an empty station, against ${pct(PW.base)}. Of the returns between 14:00 and 20:00, ${pct(PW.returns_before_17_share)} came before 17:00 and today’s reward paid ${pct(PW.paid_now_before_17_share)} of those; returns raised by half cut refused rentals by ${pct(cut)}${same} (final_prospective.py).`;
})();
const DEMO_URL = "https://alexlin8888.github.io/nsysu-youbike-log/";
const REPO_URL = "https://github.com/alexlin8888/nsysu-youbike-log";
const link = (url) => new ExternalHyperlink({ link: url, children: [fb(url.replace(/^https:\/\//, "").replace(/\/$/, ""), { underline: {} })] });
const titleBlock = [
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 30, line: 270 },
    children: [run("Beat the Bell: Class-Schedule-Aware Stockout Prediction and Pre-emptive YouBike Rebalancing for Campus Stations", { bold: true, size: 28 })] }),
  // the course asks for the YouTube link below the title and above the authors
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 10, line: 240 },
    children: [fbb("Demo video (YouTube): "), VIDEO.startsWith("http") ? link(VIDEO) : fb(VIDEO)] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 30, line: 240 },
    children: [fbb("Live demo: "), link(DEMO_URL), fb("   "), fbb("Code and data: "), link(REPO_URL)] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60, line: 240 },
    children: [fb("HW5 Final Report · Introduction to Artificial Intelligence (TAICA, Fall 2026) · Group 54 · "), fbi("blue text = new or changed since the midterm report (HW3)")] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 0, line: 240 }, children: [run("Team members", { bold: true, size: 21 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80, line: 240 },
    children: [run("國立中山大學 B124020041 林沛霆 · 國立中山大學 B134020002 陳佳晨 · 國立中山大學 B134020008 林詩穎", { size: 21 })] }),
];

// ---------- main text ----------
const main = [
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 40, line: 240 }, children: [run("Abstract", { bold: true, size: 24 })] }),
  new Paragraph({ alignment: AlignmentType.JUSTIFIED, indent: { firstLine: 202 }, spacing: { after: 80, line: 240 }, children: [
    ital("Docks near a university empty within minutes of a class ending. Because the timetable makes this surge predictable, we cast rebalancing as an AI decision problem: one truck moves bikes before the bell instead of after the stockout. We (i) reconstruct censored demand and the operator’s actual truck moves from public trip records and inventory snapshots, (ii) learn a schedule-aware, calibrated predictor of P(stockout within h min) per station, and (iii) plan truck routes by rolling-horizon search that minimizes expected unmet rentals plus travel cost. "),
    fbi("The three stages now run on real data, and the system is live at NSYSU. "),
    ital("A logger has recorded the 309 stations within 5 km of NSYSU every 10 minutes since 1 October; "),
    fbi("over 29 teaching weekdays the eight campus stations fall from 190 bikes at 10:00 to 10 at 18:00, and 53% of the campus stock leaves within 20 minutes of the 12:00 bell. "),
    ital("On 10 months of Taipei trips and 295 days of 10-minute inventory for 144 stations around NTU, our reconciliation recovers the operator’s truck moves (R² = 0.98) and shows that observed rentals understate demand by up to 2× at campus stations in the evening. A gradient-boosting predictor reaches AUC 0.93 and ECE 0.012 at a 30-minute horizon on three held-out months, keeps AUC 0.90 at two hours, and transfers to NSYSU zero-shot (AUC 0.93 on 309 stations, 0.94 on campus). The course catalogue explains which bells drain the campus (ρ = 0.59) but adds no measurable AUC as a feature. The proposal’s Poisson roll-out, implemented exactly as a birth–death chain, ranks below the classifier (AUC 0.895) because it misses that an empty station rarely refills, but it prices every stock level: in a replay of real trips, a route search built on it avoids 13%, 30% and 45% of unmet rentals with 1, 3 and 6 trucks, against at most 27% for greedy policies. "),
    fbi("Since the midterm the chain has been fitted at NSYSU from logged stock changes alone, with one rate per 10 minutes of a teaching day at the 19 stations between campus and the metro. On 12 held-out teaching days it forecasts the stock of a campus station 20 minutes after a bell with a mean error of 3.3 bikes, against 4.2 with hourly rates and 3.9 for the seasonal mean. The system is recomputed after every snapshot and feeds a public web app built around the three periods in which riders fail. Replayed on the held-out days and scored in minutes until a rider is on a bike, the app’s advice does as well as the operator’s live counts and no better (3.7 minutes for an evening departure from campus). The forecast helps earlier: 10 to 30 minutes before a departure it tells apart the searches that will take more than eight minutes with AUC 0.86 to 0.90, against 0.69 to 0.78 for the current counts. In simulation, one truck kept on the campus corridor avoids 34% of the evening’s unmet rentals there, and three avoid 66%. The operator’s NT$5 rider reward, paid only at an empty rack, reaches 3% of the bikes returned to campus before the 17:00 bell. Paid in ride time where the chain expects a station to empty within 40 minutes, it flags 91% of stockouts a median of 40 minutes ahead; if half again as many riders respond, the chain gives 11% fewer refused rentals in the evening, 27% with two pre-bell truck loads." + PRO_ABSTRACT),
  ] }),

  // ----- changes box -----
  box([
    [fbb("What is new since the midterm report (HW3)", { size: 16 })],
    "1. Six weeks of logging (6,335 snapshots); the stockout pattern re-measured on 29 teaching weekdays (Secs. 2.2.1, 3.2).",
    "2. Logger outages traced to refused runners and answered with a hand-over between runs (Sec. 2.2.1).",
    "3. Chain rates at NSYSU from stock changes alone, per hour and per 10 minutes (Sec. 2.7).",
    "4. After-class forecast tested on 12 held-out teaching days (Sec. 3.7).",
    "5. Transfer by weeks of local data; zero-shot accuracy week by week (Secs. 2.5, 3.5).",
    "6. Lost demand at NTU sized from the corrected rates (Sec. 3.6).",
    "7. Live system; web app built around the three periods in which riders fail (Secs. 2.8, 3.8).",
    "8. The app’s advice scored in minutes on 12 held-out days, and from 18 Nov on a record written before the outcome (Sec. 3.8).",
    "9. Truck simulation at NSYSU with one to three trucks (Sec. 3.9).",
    "10. Live predictor fine-tuned on local data; a learned correction of the chain tested, not adopted (Secs. 3.5, 3.7).",
    "11. The operator’s rider reward (since July 2026): where the page marks it, and why it should be paid before the bell (Secs. 2.8, 3.8, 3.10).",
    "12. The warning and the reward re-scored, unchanged, on the teaching days logged after 16 Nov (Sec. 3.10).",
    "Not done: a policy replay that includes the lost demand; a field trial; a user test (Sec. 4).",
  ], { size: 15, line: 205, color: NEW }),
  spacer(),

  h1("1. Introduction"),
  h2("1.1. Motivation"),
  body([
    run("Taipei’s YouBike 2.0 alone served 46 million trips in 2023 [3]. Around universities it fails in one specific way: bikes are plentiful during lectures and vanish when class ends. Fig. 1(a) quantifies this for the 59 NTU campus stations over 20 weekdays [2]: the campus count drops from 584 to 392 bikes within 20 minutes of the 12:10 bell and by 41% after the 17:20 bell; after 18:00 about 30% of stations are empty. Fig. 1(b) is our campus: twelve minutes after NSYSU’s 17:00 bell on 28 Sep 2026, 4 of the 25 stations within 1.5 km were empty, all on the KRT side, while the gymnasium held 48 bikes. The bikes exist; they stand at the wrong stations at a moment the timetable predicts. "),
    nb("Two weeks of our own logging show that the snapshot was typical: on eight teaching weekdays the eight campus stations (231 docks) averaged 193 bikes at 10:00, 49 at 17:00 and 7 at 18:00, with 64% of them empty at 18:00, while the two KRT Sizihwan exits were empty in 36% of morning slots and held 51 bikes at 18:00 (Sec. 3.2). The problem is a tide between campus and the metro, in both directions, every teaching day."),
    fb(" Six weeks of logging confirm it: over 29 teaching weekdays the same stations averaged 190 bikes at 10:00, 50 at 17:00 and 10 at 18:00, and the 12:00 bell took at least 45 bikes within 20 minutes on each of the 25 days with snapshots around noon (Sec. 3.2)."),
  ]),
  h2("1.2. Problem definition"),
  body([run("Station "), ital("i"), run(" has capacity "), ital("c"), sub("i"), run(" and inventory "), ital("s"), sub("i"), run("("), ital("t"), run("); rentals "), ital("r"), sub("i"), run("("), ital("t"), run(") and returns "), ital("q"), sub("i"), run("("), ital("t"), run(") are counts whose rates depend on time of day, day of week and, our key assumption, the time to the next bell "), ital("b"), run("("), ital("t"), run("). Rentals are censored: when "), ital("s"), sub("i"), run("("), ital("t"), run(") = 0, lost rentals are unrecorded. One truck of capacity "), ital("Q"), run(" visits stations with travel times "), ital("d"), sub("ij"), run(". Before each bell we choose a route and load plan "), ital("π"), run(" minimizing expected unmet rentals over a horizon "), ital("H"), run(" plus "), ital("β"), run("·travel time under capacity and deadline constraints. This is the course’s rational-agent view: acting under uncertainty to maximize expected utility, coupling probabilistic reasoning, learning and search.")]),
  body([nb("Two sub-problems are now defined precisely. "), nbb("Stockout prediction: "), nb("for every station "), nbi("i"), nb(" and 10-minute slot "), nbi("t"), nb(", output")]),
  eq([nbi("p"), nsub("i"), nb("("), nbi("t"), nb(", "), nbi("h"), nb(") = P( min"), nsub("τ∈(t, t+h]"), nbi(" s"), nsub("i"), nb("(τ) = 0 )")], 1),
  body([nb("for horizons "), nbi("h"), nb(" ∈ {30, 60, 90, 120} min. "), nbb("Rebalancing: "), nb("with "), nbi("K"), nb(" trucks, choose routes and loads that minimize this objective, and evaluate every policy by replaying the real trips of held-out days (Sec. 2.6).")]),
  ...figure("fig1_motivation.png", cap("Figure 1. ", "Class-end stockouts are real and predictable. (a) Mean bikes available at 59 NTU campus stations over 20 weekdays, Mar 2025 [2]; orange = period ends; strip = share of empty stations. (b) NSYSU at 17:12, 28 Sep 2026 [12].")),
  h2("1.3. Existing solutions and literature"),
  body([run("Static repositioning is a routing-and-inventory problem [4]; dynamic repositioning combines forecasts with heuristics or mixed-integer programs [5, 6]; recent work uses spatio-temporal reinforcement learning [7]. Two ingredients matter on a campus yet are rarely combined: censored-demand estimation by simulation [8] or censored Gaussian processes [9], and inferring the operator’s unpublished truck moves by subtracting trip flows from inventory changes [10]; on Taipei data this reveals 18–20 thousand unexplained bike moves on 12 Mar 2025, peaking at 07–09 and 18–20. A 2025 NTU thesis optimized dispatch near NTU with survival-model demand on one month of trips [11]. No published work, to our knowledge, (a) uses the class timetable as an explicit signal, (b) outputs calibrated stockout probabilities rather than point forecasts, or (c) tests transfer between campuses; NSYSU has never been studied and Kaohsiung publishes no trip data, so transfer is the practical question. "),
    nb("Station-level availability has been forecast hierarchically from city to cluster to station [25] and as over-demand prediction with dynamic station clusters [23]; the view of a station as a finite-capacity birth–death process, which the proposal’s Poisson roll-out computes, underlies service-level rebalancing [18, 19] and fleet sizing [20]; data-driven rebalancing at system scale was demonstrated for Citi Bike [24]. For the predictor we use gradient-boosted decision trees [13], which handle mixed count and categorical features natively, and we measure probability quality with the Brier score [15] and the expected calibration error [14] rather than accuracy, because the planner consumes probabilities."),
    fb(" Two further NTU theses forecast YouBike demand in Taipei and plan rebalancing from it. One uses gradient boosting and a risk index per station [32]; the other estimates flows from changes in station stock, as our chain rates at NSYSU do, and plans the trucks with a queueing model [33]. Since July 2026 the operator also pays riders to rebalance, with a NT$5 voucher for borrowing at a full station or returning a bike to an empty one [30]. A study of Citi Bike’s points for such trips found that offers based on current counts work better than fixed patterns and should hold for about half an hour while riders respond [34]. Bus riders read the chance of a late bus well from twenty dots [35] and choose when to leave better with them than with one predicted time [36].")]),
  h2mix([["1.4. Proposed solution", false], [" and status", true]]),
  body([run("Fig. 2 shows the pipeline. Open NTU data (hourly trips [1]; 10-minute inventory over 416 days [2]) serve to reconstruct demand and operator moves, to train a schedule-aware gradient-boosting predictor with reliability checks, and to drive a rolling-horizon route planner; policies are compared in a replay simulator fed with real trips. The predictor is then ported to NSYSU with a few weeks of locally logged inventory [12] for a live web demo that recommends a pre-bell truck plan ("), fb("Fig. 19"), run("). Contributions: (1) an uncertainty-aware pre-emptive rebalancing method reproducible from open data; (2) the first quantification of class-end stockouts at NTU and NSYSU; (3) an NTU→NSYSU transfer study. "),
    nb("Status: (2) is complete for both campuses; (1) is implemented end to end, including the route search, and evaluated in the simulator; (3) is complete for the predictor. Code, tables and results are public [17]."),
    fb(" Since the midterm the demo has gone live (Secs. 2.8, 3.8), the planner has its rates at NSYSU (Sec. 2.7), and the transfer study covers one to four weeks of local data (Sec. 3.5). The app’s advice to riders is checked against what the logger recorded (Sec. 3.8), and the truck is simulated at NSYSU (Sec. 3.9).")]),

  // ===================== METHOD =====================
  h1("2. Method"),
  h2("2.1. System overview", true),
  bodyB("Fig. 3 shows the system as built. The NTU lane turns two open data sets into three tables (hourly flows, a 10-minute inventory panel, an hourly reconciliation table) that feed demand reconstruction, the predictor and the simulator; the NSYSU lane builds the same inventory panel from our logger, so the inventory-only predictor and the planner run unchanged on either campus. Each module is one script in the repository [17], named in the subsection headings. {{For the final report the NSYSU lane was completed: chain rates fitted to the logged stock (Sec. 2.7) stand in for the trip-based rates, and a live web app (Sec. 2.8) turns the chain’s forecasts into advice for a rider and a route for a truck.}}"),

  h2("2.2. Data acquisition and panel construction", true),
  h3("2.2.1. NSYSU logger (fetch_youbike.py)"),
  bodyB("YouBike publishes a JSON of every station (bikes, free docks, status, update time) but no history, so our logger runs in GitHub Actions and commits one CSV row per station and 10-minute slot for the 309 stations within 5 km of NSYSU; the eight campus stations and eleven gateway stations between campus and the KRT are tagged for analysis. {{By 16 Nov it had stored 6,335 of the 6,624 possible snapshots (95.6%), and 35 of the 46 days are complete;}} out-of-service stations are stored as such and never counted as stockouts."),
  bodyF("Of the 289 missing snapshots, 246 have one cause. A logger run is a loop of 5.7 hours on one GitHub-hosted runner that starts its successor before it ends, and the YouBike API answers some runners with HTTP 503 for as long as they live. Seven such runs account for the 246, five of them since 10 Nov. Since 17 Nov a run whose fetch fails hands over to a new runner after one to three attempts, a schedule that fires every 20 minutes restarts the chain when the newest snapshot is older than 25 minutes, and a run that finds commits of an older run stands down, so two loops never write at once (logger/loop.sh, should_run.py)."),
  ...figure("fig2_pipeline.png", cap("Figure 2. ", "Proposed pipeline and the course unit each stage exercises.")),
  h3("2.2.2. NTU trip flows (ntu_pipeline.py trips)"),
  bodyB("The Taipei trip records [1] give rent and return time (truncated to the hour), the two stations by name and the duration of every ride. Each monthly zip (6–7 M rows) is streamed in chunks, rides with either end among the study stations are kept, names are matched to station ids through the station table of [2], and rentals and returns are summed per station and hour: 10.2 M rides over ten months (Sep 2024–Jun 2025), 15 s per month."),
  h3("2.2.3. NTU inventory panel (ntu_pipeline.py snapshots)"),
  bodyB("The snapshot repository [2] stores one row per station update. Stations report only when something changes, so values are forward-filled onto a 10-minute grid and marked unknown when the last report is older than 120 min during 07:00–23:00 or 600 min otherwise: 6.1 M station-slots, 7.9% unknown, mostly from a collection outage on 1–16 Oct 2024."),
  h3("2.2.4. Study area and calendars"),
  bodyB("The NTU study area is the 144 stations within 1.2 km of the campus centroid (59 on campus, 85 in the surrounding ring). Bell times are the period ends of each campus (NTU: 09:00, 10:00, 11:10, 12:10, 13:10, 14:10, 15:10, 16:20, 17:20, 18:20, 19:15, 20:10; NSYSU, from the official period table: 07:50, 09:00, on the hour from 10:00 to 18:00, then 19:10, 20:05, 21:00, 21:55). Taiwanese public holidays and the semester calendars (NTU: 2 Sep 2024–10 Jan 2025 and 17 Feb–13 Jun 2025; NSYSU: from 7 Sep 2026) define the off-day and semester-week features. The major bells of feature group B are 12:10, 15:10 and 17:20 at NTU and 12:00, 16:00 and 17:00 at NSYSU. {{Two days were corrected after the midterm: Monday 26 Oct 2026 was a day off in lieu of Retrocession Day, and on 23 Oct every station in Kaohsiung was out of service all day, so that day is left out of every analysis.}}"),

  ...figure("fig_architecture_final.png", capM("Figure 3. ", "Architecture as implemented: sources (grey), tables (light blue), learning (blue), decision and evaluation (orange); numbers are sections of this report. {{Redrawn for the final report: the NSYSU lane now ends in the chain rates and the live app.}}")),

  h2mix([["2.3.", true], [" Demand reconstruction", false], [" and operator inference", true]]),
  body([run("Per station-hour, Δ"), ital("s"), sub("i"), run(" = "), ital("q"), sub("i"), run(" − "), ital("r"), sub("i"), run(" + "), ital("m"), sub("i"), run(" + ε, with "), ital("m"), sub("i"), run(" the operator’s net truck move; residuals |Δ"), ital("s"), run(" − ("), ital("q"), run(" − "), ital("r"), run(")| ≥ 5 over 3-hour windows are labelled as moves [10], giving an observed operator policy. For censoring, minutes with "), ital("s"), sub("i"), run(" = 0 are dropped from the exposure of a Poisson rate model, so λ"), sub("r"), run(" reflects only time when a rental was possible [8, 9].")]),
  bodyB("Both steps are now implemented as written. The inventory identity per station-hour is"),
  eq([nb("Δ"), nbi("s"), nsub("i"), nb("("), nbi("h"), nb(") = "), nbi("q"), nsub("i"), nb("("), nbi("h"), nb(") − "), nbi("r"), nsub("i"), nb("("), nbi("h"), nb(") + "), nbi("m"), nsub("i"), nb("("), nbi("h"), nb(") + ε")], 2),
  body([nb("and a 3-hour window whose summed residual Σ(Δ"), nbi("s"), nb(" − ("), nbi("q"), nb(" − "), nbi("r"), nb(")) reaches 5 bikes in absolute value is labelled as a truck move. The censoring-corrected rental rate per station "), nbi("i"), nb(", day type "), nbi("d"), nb(" (teaching day or off-day) and hour-of-day "), nbi("τ"), nb(" is")]),
  eq([nb("λ̂"), nsub("i"), nb("("), nbi("d"), nb(", "), nbi("τ"), nb(") = Σ"), nsub("h"), nbi(" r"), nsub("i"), nb("("), nbi("h"), nb(") / Σ"), nsub("h"), nbi(" e"), nsub("i"), nb("("), nbi("h"), nb(")")], 3),
  body([nb("where the sums run over all hours "), nbi("h"), nb(" of that type and "), nbi("e"), nsub("i"), nb("("), nbi("h"), nb(") is the share of the hour during which the station had a bike. In the implementation (ntu_pipeline.py reconcile, ntu_demand.py) the stock at the start of an hour is the panel value at hh:00, "), nbi("e"), nsub("i"), nb(" is the share of the six slots with a bike, and rates are estimated per station, day type and hour. The two validity checks the proposal asked for, the R² of Δ"), nbi("s"), nb(" against ("), nbi("q"), nb(" − "), nbi("r"), nb(") on hours without inferred moves and the R² for reproducing the next-hour stock once moves are added (required to exceed 0.8), are reported in Sec. 3.3.")]),
  bodyB("Fig. 4(a) shows both steps at the 30-dock library station on 25 Sep 2024: trips alone would have stacked 60 bikes there by 11:00, so the residual flags a 40-bike pick-up at 10:00 and a 40-bike drop-off at 17:00, when 74 rentals emptied the station around the 17:20 bell; its 19 empty snapshots after 18:00 are removed from the exposure of Eq.\u00A0(3)."),
  ...figure("fig_method.png", capB("Figure 4. ", "Method at one NTU station (library, 30 docks, 25 Sep 2024). (a) Observed stock, stock implied by trips alone, empty snapshots (grey, removed from the exposure) and inferred truck moves; dotted: bells. (b) The roll-out of Sec. 2.4.1: p(t, h) is the chance of reaching 0 within h.")),
  h3("2.3.1. Inference checks (validate_moves.py)"),
  bodyB("The move labels are a by-product of thresholding, so four checks that do not use the threshold were added:", { keepNext: true }),
  bullet("Conservation: per day, the change in area stock equals net trips plus flagged moves plus the unflagged residual; the unflagged part must be small and unbiased."),
  bullet("Sensitivity: the labels are recomputed for thresholds of 3, 5 and 8 bikes and windows of 1, 3 and 6 hours; volume, timing and R² must not hinge on the choice."),
  bullet("Jumps: a truck visit appears as a change of ≥ 8 bikes between consecutive 10-minute snapshots, which trips rarely produce; flagged windows should contain such jumps far more often than unflagged ones, and the jump total is a second estimate of the truck volume."),
  bullet([nb("Rates: on test-period station-hours that start with at least 8 bikes and half the docks full, demand is observed in full, so actual rentals should match the corrected training-period rate of Eq. (3) rather than the naive rate "), nb("Σ"), nbi("r"), nb("/hours.")], { last: true }),

  h2mix([["2.4.", true], [" Schedule-aware stockout prediction", false]]),
  body([run("Features per station and 10-minute slot: minutes to the next and since the last bell (NTU periods end at 12:10, 15:10, 17:20; NSYSU on the hour), day of week, week of semester, lagged flows (1–3 h, same slot last week), current stock, capacity and stock at the three nearest stations. Baselines: persistence and seasonal mean; then LightGBM with Poisson objectives for rentals and returns; Monte-Carlo roll-out of the inventory over "), ital("h"), run(" ∈ {15, 30, 60} min, giving P("), ital("s"), sub("i"), run("("), ital("t"), run("+"), ital("h"), run(") = 0). Metrics: Brier score, AUC and expected calibration error (ECE), since the planner consumes probabilities. Transfer: train on NTU, test on NSYSU with 0–4 weeks of local data.")]),
  body([nbb("What was implemented. "), nb("The label of Eq. (1) is predicted in two ways that are compared on the same test rows: directly, by a classifier on the 28 features of Table 1 (the first 22 need only inventory and form the set used for transfer), and by the Poisson roll-out of the proposal, implemented as described in Sec. 2.4.1. One choice changed against the proposal: the horizons are 30, 60, 90 and 120 min; 15 min was dropped because at 10-minute resolution it leaves a single slot of lead time, too short for a truck to act on, and 90 and 120 min were added because a pre-bell plan needs the longer view. On the NTU test months the label is positive for 21% of station-slots at "), nbi("h"), nb(" = 30 min and 38% at "), nbi("h"), nb(" = 120 min; at NSYSU, for 9% at "), nbi("h"), nb(" = 30 min (17% at the campus stations). The predictor is built for 06:00–23:00 (code: features.py, train_predictor.py, horizon_sweep.py).")]),
  tableCaption("Table 1. ", "Feature groups. The inventory-only set (groups A–D) is used at NSYSU; the full NTU model adds group E and the station id."),
  table([980, 2497, 1200], ["Group", "Features (per station and 10-min slot)", "Source"], [
    ["A time", "hour of day, day of week, off-day flag, semester week, in-semester flag", "calendar"],
    ["B bell", "minutes to the next and since the last period end; the same for the three major bells (12:10, 15:10, 17:20 at NTU)", "timetable"],
    ["C state", "bikes, free docks, capacity, fill ratio, change over 10 / 30 / 60 min, minimum over the last hour, empty-now flag, minutes empty in the last hour", "inventory panel"],
    ["D neighbours", "bikes and empty count at the 3 nearest stations, mean fill of the 5 nearest", "inventory panel"],
    ["E flows", "rentals and returns in the last two complete hours, rentals in the same hour last week, mean rentals for this station and hour-of-week on the training period", "trip records"],
  ], { aligns: [AlignmentType.LEFT, AlignmentType.LEFT, AlignmentType.LEFT] }),
  spacer(),
  h3("2.4.1. Poisson roll-out (horizon_sweep.py)"),
  bodyB("This is the method the proposal described, made exact:", { keepNext: true }),
  bullet([nb("Rates: rentals and returns per station, day type and hour-of-day from the training period, each divided by its own exposure as in Eq. (3) (slots with a bike for rentals, with a free dock for returns) and shrunk toward the hour-of-day mean over all stations with the weight of three hours of exposure; a naive variant uses "), nb("Σ"), nbi("r"), nb("/hours.")]),
  bullet([nb("Dynamics: in each 10-minute step the station rents Poisson(λ"), nsub("r"), nb("/6) bikes, capped by the "), nbi("s"), nb(" present, and receives Poisson(λ"), nsub("q"), nb("/6) returns, capped by the "), nbi("c"), nb(" − "), nbi("s"), nb(" free docks, so the inventory is a birth–death chain on {0, …, "), nbi("c"), nb("} [18–20] (Fig. 4b). State 0 is made absorbing after the first step, because Eq. (1) asks whether the station is empty at any later slot; a station that is empty now may still be refilled in the first step.")]),
  bullet([nb("Exact evaluation: with "), nbi("K"), nsub("j"), nb(" the transition matrix of the hour in which step "), nbi("j"), nb(" falls, "), nbi("p"), nsub("i"), nb("("), nbi("t"), nb(", "), nbi("h"), nb(") is entry ("), nbi("s"), nsub("i"), nb("("), nbi("t"), nb("), 0) of "), nbi("K"), nsub("1"), nbi("K"), nsub("2"), nb("⋯"), nbi("K"), nsub("h/10"), nb(", computed once per station, day type and slot (29 k groups, 8 s). This is the limit of the Monte-Carlo estimate the proposal described; a sampler with 400 draws was run on 3,000 test rows as a check.")]),
  bullet("Calibration: the roll-out models demand only, not the operator who refills stations, so a second version passes its probabilities through isotonic regression [21] fitted on the validation weeks, which changes the values but not the ranking."),
  bullet("Stacking: the roll-out probability is added as a 30th feature to the full classifier, to test whether the chain adds information the trees lack.", { last: true }),
  bodyB("Training and evaluation:", { keepNext: true }),
  bullet("Model: LightGBM [13] binary classifier, 63 leaves, learning rate 0.05, 80% feature and row subsampling, L2 = 1, trained on a 40% random subsample of the training slots with early stopping on the last three training weeks; one model per horizon and feature set (inventory-only, full)."),
  bullet([nb("Baselines: persistence ("), nbi("p"), nb(" = 1 if the station is empty now), the seasonal mean of the label per station, day type and slot, and a logistic regression on the inventory-only features (standardized, with one-hot hour of day and day of week) as a linear reference.")]),
  bullet([nb("Metrics: Brier score = mean ("), nbi("p"), nb(" − "), nbi("y"), nb(")² [15]; AUC; expected calibration error ECE = Σ"), nsub("b"), nb(" ("), nbi("n"), nsub("b"), nb("/"), nbi("N"), nb(") |mean "), nbi("y"), nsub("b"), nb(" − mean "), nbi("p"), nsub("b"), nb("| over ten equal-width probability bins [14]. Reliability curves are reported because the planner multiplies "), nbi("p"), nb(" by demand.")]),
  bullet("Uncertainty: 95% intervals from a block bootstrap [22] over test days (NTU) or station-days (NSYSU, six test days), 250 resamples, with the same draws for every model so that differences are paired; the simulator’s 28 days are resampled 1,000 times for paired policy differences."),
  bullet("Ablation: the same model without group B, to measure what the explicit timetable adds beyond hour of day.", { last: true }),

  h2("2.5. Transfer to NSYSU", true),
  bodyB("Kaohsiung publishes no trip data, so only the inventory-only variant can run at NSYSU. The NSYSU panel is built from the logger with NSYSU bells and calendar and the same feature code is applied (transfer_nsysu.py). No feature identifies a station, so the NTU model can score any logged station; capacity and neighbours come from the NSYSU station list. Five models are compared on six held-out days (10–15 Oct): persistence; a seasonal baseline fitted on the six training days (2–7 Oct); the NTU inventory-only model applied zero-shot; the same model fine-tuned by continuing boosting on the NSYSU training days (learning rate 0.02, early stopping on 8–9 Oct); and a model trained on NSYSU days only. Results are reported for all 309 stations, the 19 stations of the campus–KRT corridor and the 8 campus stations."),
  bodyF("With six weeks logged, the question the proposal asked, how many weeks of local data the predictor needs, can be answered (final_transfer.py). The test set is the 14 days of 3–16 Nov. Training windows end on 29 Oct and reach back one, two, three or four weeks (6, 13, 20 and 27 logged days); 30–31 Oct serve for early stopping. Each window gives a fine-tuned model and a local-only model, compared with the zero-shot model on the same rows. The zero-shot model is also scored on every logging week since 2 Oct, to see whether its accuracy drifts."),
  h3("2.5.1. Timetable intensity (timetable.py)"),
  bodyB("The public course query [27] lists each course of semester 115-1 with weekday, periods, room and enrolment: 2,475 courses, 116 of them off campus or online. Merging consecutive periods leaves 2,589 class sessions per week. Five features count the students (in hundreds) whose class ends within the next 30 or 60 min, ended within the last 30 min, starts within the next 30 min, or is under way; they are zero on holidays and outside the 19 corridor stations. Each of the ten teaching days of 2–16 Oct is predicted by two otherwise identical models trained on the other fourteen complete days, with and without the five features, both given the station role (campus, gateway, other) (timetable_nsysu.py); differences are bootstrapped over days."),

  h2mix([["2.6.", true], [" Pre-emptive planner and ", false], ["replay simulator", true]]),
  body([run("State: truck position and load, station stocks and predicted rates; actions: (station, ±"), ital("k"), run(" bikes); objective "), ital("J"), run("("), ital("π"), run(") = Σ"), sub("i"), run(" E[max(0, "), ital("D"), sub("i"), run(" − "), ital("s"), sub("i"), run(")] + "), ital("β"), run("·"), ital("T"), run("("), ital("π"), run("), with "), ital("D"), sub("i"), run(" the predicted demand. Every 10 minutes we rank stations by expected unmet rentals, build a greedy surplus-to-deficit route under capacity "), ital("Q"), run(" and the bell deadline, and improve it by 2-opt local search and simulated annealing. A discrete-event replay simulator consumes real held-out trips (Apr–Jun 2025): a rental is served only if stock > 0, otherwise it counts as unmet, while the truck follows the policy under test. We compare none, reactive (after an observed stockout), predictive-point and predictive-probabilistic (ours), plus the inferred operator moves, which must first reproduce observed inventories ("), ital("R"), run("2", { superScript: true }), run(" > 0.8). Metrics: unmet rentals, empty station-minutes, truck-km.")]),
  bodyB("The simulator, three greedy baselines (Sec. 2.6.2) and the route search with 2-opt and simulated annealing (Sec. 2.6.3) are implemented. The operator-move check passed with R² = 0.984 (Sec. 3.3)."),
  h3("2.6.1. Replay simulator (replay_sim.py)"),
  body([nb("Each day runs from 06:00 to 23:00 from the 06:00 snapshot. Recorded rentals at the 144 stations are placed uniformly at random within their recorded hour (seeded); a served rental generates the return of that ride after its recorded duration, an unserved one disappears, and rides from outside the area arrive as recorded. A full station redirects a return to the nearest station with a free dock. Trucks: "), nbi("K"), nb(" ∈ {1, 3, 6}, capacity 20, 15 km/h on 1.3× straight-line distance, 3 min per stop and 6 s per bike. Outputs per day: unmet rentals, empty station-minutes (counted every 10 min), bikes moved, truck-km.")]),
  h3("2.6.2. Greedy planner and the three policies"),
  body([nb("Every 10 minutes each idle truck receives one move chosen by Algorithm 1. Candidate targets, their need and the weight "), nbi("v"), nb(" differ by policy:")]),
  bullet([nbb("reactive: "), nb("targets are stations that are empty now; need = max(5, λ); "), nbi("v"), nb(" = 1.")]),
  bullet([nbb("predictive-point: "), nb("targets are stations whose next-hour demand exceeds stock, λ − "), nbi("s"), nb(" ≥ 2; need = λ − "), nbi("s"), nb(" + 2; "), nbi("v"), nb(" = 1.")]),
  bullet([nbb("predictive-probabilistic: "), nb("targets are stations with "), nbi("p"), nsub("i"), nb("("), nbi("t"), nb(", 60) ≥ 0.3, where "), nbi("p"), nb(" is computed on the simulated inventory by the inventory-only predictor at every decision; need = max(5, λ − "), nbi("s"), nb(" + 3); "), nbi("v"), nb(" = "), nbi("p"), nsub("i"), nb("; stations with "), nbi("p"), nb(" > 0.2 are never used as sources.")], { last: true }),
  box([
    [nbb("Algorithm 1  Greedy move selection for one idle truck", { size: 16 })],
    "input: stocks s, hourly demand λ, position, need, v",
    "surplus_j = s_j − λ_j − 2",
    "S = {j : surplus_j ≥ 3, unclaimed}",
    "T = {i : need_i > 0, unclaimed}, 8 best by v·need",
    "for i in T, j in S:",
    "  k = min(Q, surplus_j, cap_i − s_i, need_i)",
    "  if k < 3: continue",
    "  t = drive(pos→j→i) + 2·stop + k·handle",
    "  score = v_i · min(k, max(λ_i, 1)) / t",
    "return (i, j, k) with max score; claim i, j",
  ], { mono: true, size: 14 }),
  spacer(),
  bodyB("The operator reference injects the inferred hourly moves of Sec. 2.3 directly, without truck constraints."),
  h3("2.6.3. Route search (route_planner.py)"),
  body([nb("Algorithm 1 serves one target per trip and does not ask how many rentals a delivered bike will serve. The route search prices every stock level with the birth–death chain of Sec. 2.4.1, run with its corrected rates and without the absorbing state. A backward pass over the horizon "), nbi("H"), nb(" gives "), nbi("V"), nsub("a"), nb("("), nbi("s"), nb("), the expected unmet rentals from step "), nbi("a"), nb(" to "), nbi("H"), nb(" if the station holds "), nbi("s"), nb(" bikes at step "), nbi("a"), nb(", and a forward pass from the current stock gives the distribution "), nbi("P"), nsub("a"), nb(" of the stock at step "), nbi("a"), nb(". Changing the stock of station "), nbi("i"), nb(" by "), nbi("d"), nb(" bikes in step "), nbi("a"), nb(" then saves")]),
  eq([nbi("B"), nsub("i"), nb("("), nbi("a"), nb(", "), nbi("d"), nb(") = Σ"), nsub("s"), nbi(" P"), nsub("a"), nb("("), nbi("s"), nb(") ["), nbi("V"), nsub("a"), nb("("), nbi("s"), nb(") − "), nbi("V"), nsub("a"), nb("(["), nbi("s"), nb(" + "), nbi("d"), nb("]"), nsub("0..c"), nb(")]")], 4),
  body([nb("expected unmet rentals, where [·]"), nsub("0..c"), nb(" clips to the station’s capacity: positive for a drop-off, negative for a pick-up, and larger for a bike that arrives before a bell than after it. For a sequence of up to six stations the loads follow exactly from dynamic programming over the truck load 0…"), nbi("Q"), nb(", and the sequence scores "), nbi("J"), nb(" = Σ"), nsub("l"), nbi(" B"), nsub("l"), nb("("), nbi("a"), nsub("l"), nb(", "), nbi("d"), nsub("l"), nb(") − "), nbi("β"), nb("·"), nbi("T"), nb(", with "), nbi("a"), nsub("l"), nb(" the arrival step and "), nbi("T"), nb(" the minutes the route takes.")], { spacing: { after: 70, line: 240 } }),
  body([nb("Each idle truck starts from the best pick-up–drop-off pair among the 12 most valuable targets and the 12 cheapest sources, adds stations by greedy insertion, improves the sequence by 400 steps of simulated annealing [16] (insert, remove, swap or replace a station, reverse a segment) and a final 2-opt pass, drives the first "), nbi("C"), nb(" stops and plans again (Algorithm 2); stations on another truck’s route are skipped. On the validation weekdays (Sec. 3.1) we set "), nbi("H"), nb(" = 90 min, "), nbi("β"), nb(" = 0.25 unmet rentals per minute and "), nbi("C"), nb(" = 2; a plan takes about 20 ms. A single-move variant with the same values (one pick-up and one drop-off, no annealing) separates the effect of the values from that of the routes.")], { spacing: { after: 70, line: 240 } }),
  box([
    [nbb("Algorithm 2  Route search for one idle truck", { size: 16 })],
    "input: stock s, position, load L, values B (4)",
    "T = 12 stations with the largest drop-off value",
    "S = 12 stations with the cheapest pick-up",
    "r = best pair (j in S, i in T)        if L < 3",
    "repeat: insert the station that most raises J",
    "  until no gain or |r| = 6",
    "for n = 1..400:                  # annealing",
    "  r' = insert / remove / swap / replace /",
    "       reverse a segment of r",
    "  keep r' if J(r') > J(r) or u < exp(ΔJ/τ_n)",
    "r = 2-opt(best r)",
    "loads = argmax J(r) over loads   # DP, 0..Q",
    "drive the first C stops, then plan again",
  ], { mono: true, size: 14 }),
  spacer(),

  h2F("{{2.7. Chain rates at NSYSU without trip data}}"),
  bodyF([fb("The planner prices bikes with rental and return rates, and Kaohsiung publishes no trips. The rates are therefore fitted to the logged stock itself (nsysu_rates.py). For one station, day type and hour of day the data are the transitions "), fbi("s"), fb(" → "), fbi("s′"), fb(" between consecutive 10-minute snapshots. The chain of Sec. 2.4.1 gives every transition a probability "), fbi("K"), fb("("), fbi("s"), fb(", "), fbi("s′"), fb("; λ"), fsub("r"), fb(", λ"), fsub("q"), fb(") that already contains the caps at 0 and at capacity, so the two rates are chosen to maximize")]),
  eqF([fb("Σ"), fsub("n"), fb(" log "), fbi("K"), fb("("), fbi("s"), fsub("n"), fb(", "), fbi("s′"), fsub("n"), fb("; λ"), fsub("r"), fb(", λ"), fsub("q"), fb(") + log "), fbi("π"), fb("(λ"), fsub("r"), fb(", λ"), fsub("q"), fb(")")], 5),
  bodyF([fb("over the transitions "), fbi("n"), fb(" of the cell, where "), fbi("π"), fb(" is a Gamma prior worth three hours of exposure at the hour-of-day mean over all stations, the same shrinkage as at NTU. A station at 0 gives no information about its rental rate, and a full one none about its return rate; the likelihood accounts for both, which the gross decreases and increases of the stock do not. Transitions to which the fitted chain gives a probability below 10"), fsup("−5"), fb(" are taken as truck visits and left out, in two rounds (5,923 of 1.30 M transitions up to 16 Nov).")]),
  bodyF("An hourly rate spreads an hour’s rentals evenly. At a campus station they come right after the bell: in the fitted rates, 54% of the rentals of 12:00–13:00 at the eight campus stations fall in the first 20 minutes (Fig. 5). For the 19 corridor stations on teaching days a pair of rates is therefore fitted for every 10-minute slot of the day (1,938 cells) in the same way, with the station’s own hourly rates as the prior. The prior weight, half an hour of exposure, was chosen on five validation days (Sec. 3.7). Planner and forecasts use the 10-minute rates where they exist and the hourly rates elsewhere."),
  ...figure("fig_final_rates.png", capM("{{Figure 5. }}", "{{Rates fitted at the eight campus stations on teaching days, summed over the stations: one rate per hour (grey) and one per 10 minutes (colour); dashed: 09:00, 12:00, 16:00 and 17:00.}}")),

  h2F("{{2.8. Live system and web app}}"),
  body([run("The logger already writes latest.json, a compact snapshot of the 309 stations, on every run."), fb(" After each snapshot the same job now computes the state of the system (demo_state.py, about 6 s). The chain with the rates of Sec. 2.7 is run forward from the current stock of every station. For each of the next nine 10-minute steps it gives the chance that the station holds at least one bike, the chance that it has a free dock, and the expected stock. The inventory-only predictor, fine-tuned on the logged days (Sec. 3.5), gives P(empty within 30 min) and P(empty within 60 min). The route search of Sec. 2.6.3, with the settings of the NTU replay ("), fbi("H"), fb(" = 90 min, "), fbi("β"), fb(" = 0.25, "), fbi("Q"), fb(" = 20, up to six stops), plans the next trip of one truck that may collect bikes anywhere and delivers only to the 19 corridor stations (Sec. 3.9). All of this is written to one JSON file of about 160 kB and committed next to the data, so the page needs no server. For the corridor stations the file also holds the forecast for every stock a station can have, which the page uses when it reads a newer count itself.")]),
  bodyF("The page (Fig. 19) is a static web app on GitHub Pages, laid out for a phone. It is built around the three periods in which the logger shows riders failing (Sec. 3.8), so its first two tabs are Borrow and Return. On Borrow a rider chooses where the trip starts, among 14 campus buildings, the metro station, the ferry pier, the phone’s position or a point on the map, and may add a destination and a class end to leave after. Walking and cycling times come from path lengths in OpenStreetMap [28] at 80 and 200 m per minute (demo_places.py). A path counts as at most 1.7 straight lines, because some campus footpaths are missing from the map, and slopes are not modelled."),
  bodyF("For each station within 2 km the page computes the expected minutes until the rider is on a bike: the walk there, plus the chance of finding no bike times the cost of walking on to the best next station, which is charged 12 minutes if it fails too. It names the station with the fewest expected minutes or, among those within half a minute of it, the one with the best chance. Sec. 3.8 gives the reason this rule replaced the first one, the nearest station with a chance of at least 0.9. With a destination the docks within 0.6 km of it are treated the same way, and the page compares the minutes door to door with walking. Return applies the rule to docks alone. For departures at 10-minute steps over the next hour, ten dots show how often the first station has a bike, another station is needed but the rider rides within 8 minutes, or the search takes longer [35, 36]; one line turns them into the latest time to leave or names the station to try after a miss. For a later departure the rider is taken to look again on leaving, and the chance that none of the n nearest stations shows a bike is the product of their chances of showing none raised to θ = 0.6, because campus stations empty together (Sec. 3.8). Every station in the list and on the map carries one of four labels for its chance at the minute of arrival, in words rather than percentages, with the time at which that chance falls below one half."),
  bodyF("While it is open the page also reads the counts of the corridor stations from the operator’s API once a minute and takes, for each, the forecast that belongs to the new count. Its counts are then at most a minute old, where the logger’s snapshot can be ten. The page also marks where the operator’s reward is likely to be on offer [30]: a station is marked when the chain gives a chance of at least 0.6 that it will still be empty, for a return, or full, for a rental, at the minute of arrival (Sec. 3.8). A mark stays until the chance falls below 0.5, so that it holds while the rider is on the way [34], and a filter shows the marked stations alone. A station’s card says how often it is empty, or full, in that half hour of a usual teaching day. A form writes a weekly calendar event five minutes before a chosen class ends, linking to the page at that building, and the installed page opens offline from a service worker."),
  bodyF("The Dispatch tab lists the next trip of the truck with loads and arrival times, and the expected shortfall of the corridor; a Policy tab shows the case of Sec. 3.10. A replay mode steps through each of the last seven days. The map is drawn with Leaflet [29] on OpenStreetMap tiles [28]. Before a release the page is checked in a browser at six window sizes (site/test_page.py)."),

  // ===================== EXPERIMENTS =====================
  h1("3. Experiments", true),
  h2("3.1. Datasets, splits and environment", true),
  bodyB("Table 2 lists the data. NTU rows are split by time: training 1 Sep 2024–9 Mar 2025, validation 10–31 Mar 2025 (early stopping), test 1 Apr–22 Jun 2025 (1.22 M station-slots never seen by the model). NSYSU uses 2–7 Oct for training, 8–9 Oct for validation and 10–15 Oct for testing; the timetable test leaves out one teaching day of 2–16 Oct at a time. {{The experiments added for the final report use later data: the chain rates are fitted on the 17 teaching days of 2–29 Oct and tested on the 12 teaching days of 30 Oct–16 Nov (Secs. 3.7 to 3.9), and the transfer study trains on windows that end on 29 Oct and tests on 3–16 Nov (Sec. 3.5).}} The replay simulator uses the 28 in-semester weekdays of the test period with ≥ 95% snapshot coverage; the route-search settings were chosen on the 16 such weekdays of 10–31 Mar 2025. On a 2-vCPU, 7 GB container (Python 3.11, LightGBM 4.7) every experiment runs in under 20 min; one simulated day takes about 3 s. All random steps use fixed seeds."),
  tableCaption("Table 2. ", "Data used in this report."),
  table([1500, 1877, 1300], ["Source", "Coverage / resolution", "Rows used"], [
    ["Taipei YouBike 2.0 trip records [1]", "Sep 2024–Jun 2025, hourly, 1,519 stations", "10.2 M rides touching the 144 NTU-area stations"],
    ["Taipei inventory snapshots [2]", "1 Sep 2024–22 Jun 2025 (295 days), 10 min", "2.97 M station records → 6.1 M station-slots"],
    ["NSYSU logger [17]", "{{2 Oct–16 Nov 2026}}, 10 min, 309 stations ≤ 5 km", "{{1.96 M station-slots (46 days, 35 complete)}}"],
    ["Calendars", "period ends of both campuses, holidays, semesters", "bell and off-day features"],
    ["NSYSU course catalogue [27]", "semester 115-1, 2,475 courses, by period", "2,589 weekly class sessions"],
  ], { aligns: [AlignmentType.LEFT, AlignmentType.LEFT, AlignmentType.LEFT] }),
  spacer(),

  h2("3.2. Class-end stockouts at NSYSU", true),
  bodyB("{{Figs. 6 and 7}} summarize the eight teaching weekdays of 2–14 Oct 2026 (9–10 Oct are holidays). Campus and KRT exits are the two ends of a tide: campus stations fill between 08:00 and 10:00 while both KRT exits run empty; after the 12:00 bell the campus loses 93 bikes (55%) in 20 minutes, recovers over lunch, then drains through the 16:00 and 17:00 bells (−68 and −47 bikes within 40 minutes), and within an hour of the 17:00 bell 88% of the remaining campus stock is gone."),
  bodyB("The 246 stockout episodes at campus stations amount to 3.8 per station and day, with a median length of 20 min and a 90th percentile of 60 min; in total the eight campus stations spend 934 station-minutes empty per weekday. The morning has the mirror problem: the engineering and library stations have no free dock in 44% and 25% of 08:00–11:00 slots. On weekends the campus holds 40–130 bikes all day and the pattern disappears, which confirms the timetable as the cause."),
  bodyB("The course catalogue shows which bells matter ({{Fig. 6}}, bottom). On weekdays the 12:00 bell releases 3,700–4,600 students and the 16:00 bell 2,400–4,100, against at most 1,600 at any other period end; on Wednesdays no class ends at 17:00. Averaged over weekdays, 12:00, 16:00 and 17:00 are the three largest, the major bells already used by the NSYSU features. Over the 97 daytime bells (09:00–18:00) of the ten teaching days of 2–16 Oct, the bikes leaving the campus stations in the 20 minutes after a bell rise with the number of students released (Spearman ρ = 0.59, {{Fig. 8}}), against ρ = 0.33 for the 20 minutes that start half an hour before the same bells. Between weekdays, the size of the same bell relates only weakly to its outflow (ρ = 0.27, p = 0.008)."),
  ...figure("fig_nsysu_tide_a.png", capM("{{Figure 6. }}", "NSYSU, eight teaching weekdays in Oct 2026: bikes at the 8 campus stations and the 2 KRT Sizihwan exits (mean, band = IQR; dashed = weekend campus). Bottom: students whose class ends at each period end, Mon–Fri mean of the 115-1 catalogue [27].")),
  ...figure("fig_nsysu_tide_b.png", capM("{{Figure 7. }}", "Probability that a station is empty, by time of day on teaching weekdays, for the campus stations, the KRT exits and the four busiest gateway stations.")),
  ...figure("fig_bells.png", capM("{{Figure 8. }}", "Students released by each daytime bell against bikes leaving the 8 campus stations in the next 20 min (97 bells, 2–16 Oct 2026); open: windows starting 30 min earlier.")),
  bodyF("Six weeks of logging give the same picture with more days behind it (Fig. 9). On the 29 teaching weekdays of 2 Oct–16 Nov the campus stations hold 190 bikes at 10:00, 140 at 12:00, 50 at 17:00 and 10 at 18:00 (median 6). Within 20 minutes of the 12:00 bell 84 bikes (53%) leave on average, and at least 45 on each of the 25 days with snapshots around noon; week by week the mean stays between 68 and 97 bikes. After the 16:00 and 17:00 bells 61 and 50 bikes leave within 40 minutes. On the 23 days with complete snapshots there are 752 stockout episodes at campus stations, 4.1 per station and day, again with a median of 20 min, and the campus stations spend 993 station-minutes empty per weekday. At the KRT exits the mean stock is 6 bikes at 10:00 and 45 at 18:00, so the two-week figures of the midterm were typical."),
  ...figure("fig_final_weeks.png", capM("{{Figure 9. }}", "{{Every teaching weekday from 2 Oct to 16 Nov 2026. (a) Bikes at the eight campus stations at 10:00 and 18:00. (b) Bikes that left them within 20 min of the 12:00 bell; dashed: mean. Grey: days off and the closure of 23 Oct; gaps: weekends and missing snapshots.}}")),

  h2("3.3. Demand reconstruction and operator moves at NTU", true),
  bodyB("Reconciliation covers 917 k station-hours (144 stations, 295 days). On hours without inferred moves, trips alone explain inventory changes with R² = 0.87; adding the inferred moves reproduces the next-hour stock with R² = 0.984 (0.63 without them), so the inferred operator policy passes the proposal’s threshold. At the 144 stations the operator drops off about 2,550 and picks up about 2,160 bikes per day, 10% of the 25,700 daily rentals. {{Fig. 10}} shows a reactive pattern: pick-ups from campus peak at 08:00–09:00 after the morning inflow, drop-offs at campus peak at 16:00–17:00, and only 19% of campus drop-offs happen in the hour before a major bell."),
  bodyB("The censoring correction is large where it matters: at campus stations on weekdays, observed rentals understate demand by 8% at 12:00, 17% at 17:00, 39% at 18:00 and 2.1× at 22:00, because campus stations are empty 46% of the time at 17:00–19:00. These corrected rates are the demand input of the planner."),
  bodyB("The checks of Sec. 2.3.1 ({{Fig. 11}}) support the inference with one qualification. Conservation: the area loses 600 bikes per day through trips, the flagged moves bring back 394 and the unflagged residual 185, so small top-ups below the threshold are missed and the 2,550 drop-offs are a lower bound. Sensitivity: across thresholds of 3–8 bikes and windows of 1–6 h the drop-off volume stays within 2,150–2,975 bikes per day, the share before a major bell within 18–20%, the peak hour at 17:00 and the reproduction R² above 0.977. Jumps: 56% of flagged windows contain a ≥ 8-bike jump in the flagged direction against 8% of unflagged ones. Rates: on 14.6 k well-stocked campus station-hours of the test period, actual rentals are 12% above the naive rate but only 4% above the corrected one. The volume is plausible: 4,700 bike-moves per day is about 240 truck loads of 20, and a press report on the operator’s crews describes over a thousand bikes collecting at riverside stations in a single day and being trucked back overnight [26]."),
  ...figure("fig_ntu_moves.png", capM("{{Figure 10. }}", "Inferred truck moves per hour and day at the 59 campus and 85 ring stations (drop-offs above the axis, pick-ups below); dashed: 12:10 and 17:20 bells.")),
  ...figure("fig_moves_check.png", capM("{{Figure 11. }}", "Checks on the operator inference. (a) Inferred drop-offs per day by threshold and window; dashed: bikes arriving in ≥ 8-bike jumps. (b) Actual rentals over the training-period rate on well-stocked campus station-hours; dashed: 12:10 and 17:20 bells.")),

  h2("3.4. Stockout prediction", true),
  bodyB("Table 3 and {{Figs. 12–13}} give the test results on the 1.09 M test slots whose current stock is observed. At the 30-minute horizon the full model reaches AUC 0.932 and Brier 0.080, against 0.819 / 0.126 for the seasonal baseline and 0.744 / 0.124 for persistence; the inventory-only model is close behind (0.922 / 0.084), so trip flows add little once the current stock and its trend are known, at this horizon. A constant forecast of the 21% base rate would score Brier 0.165, so the full model removes half of that error. Calibration is good without post-processing: ECE 0.012 and a reliability curve on the diagonal up to p = 0.9 ({{Fig. 12}}a), while the seasonal baseline under-predicts at high probabilities. The day-level bootstrap gives half-widths of about 0.005 AUC for the GBMs, and every paired difference has an interval that excludes zero: full against inventory-only +0.010 [0.009, 0.011], inventory-only against logistic +0.007 [0.006, 0.007] and against the corrected roll-out +0.027 [0.025, 0.029]."),
  tableCaption("Table 3. ", "NTU test period (Apr–Jun 2025), all 144 stations, h = 30 min; 95% intervals from the day-level bootstrap. GBM + flows also uses the station id; stacked = GBM + flows + the roll-out probability."),
  table([1477, 500, 1500, 550, 650], ["Model", "Brier", "AUC [95% CI]", "ECE", "trees"], [
    ["persistence", "0.124", "0.744 [0.740, 0.748]", "0.124", "–"],
    ["seasonal mean", "0.126", "0.819 [0.807, 0.829]", "0.016", "–"],
    ["roll-out, naive rates", "0.105", "0.893 [0.888, 0.900]", "0.059", "–"],
    ["roll-out, corrected", "0.102", "0.895 [0.890, 0.902]", "0.039", "–"],
    ["roll-out + isotonic", "0.100", "0.895 [0.890, 0.902]", "0.012", "–"],
    ["logistic regression", "0.086", "0.915 [0.911, 0.921]", "0.008", "–"],
    ["GBM inventory only", "0.084", "0.922 [0.917, 0.928]", "0.012", "170"],
    ["GBM + flows", "0.080", "0.932 [0.928, 0.937]", "0.012", "951"],
    ["stacked GBM", "0.079", "0.933 [0.929, 0.938]", "0.012", "670"],
  ]),
  spacer(),
  bodyB("The Poisson roll-out of the proposal ranks stockouts far better than the seasonal baseline (AUC 0.895 against 0.819) but below the linear model (0.915) and the GBMs (0.922 / 0.932). Its deficit is specific: for a station that is empty now it predicts a 61% chance of being empty again within 30 min, against 82% observed, because returns are not independent of the state: an empty station usually sits in a drained neighbourhood and the first bike returned is rented at once. On stations holding 1–3 bikes its AUC is 0.67 against 0.74–0.78 for the classifiers. The censoring correction helps the chain at every horizon (AUC +0.002 to +0.013, ECE 0.039 against 0.059 at 30 min), the first direct evidence that Eq. (3) improves a downstream prediction. As a 30th feature the chain raises the full model’s AUC by only 0.001–0.003 while taking 24–54% of the split gain: real information, almost all of it already in the features. The proposal’s 400-draw sampler matches the exact chain to within 0.01 (correlation 0.999)."),
  ...figure("fig_model.png", capM("{{Figure 12. }}", "(a) Reliability of the 30-minute predictions on the NTU test months. (b) AUC on all stations, campus stations, and campus slots within 40 min after a major bell.")),
  bodyB("Every model loses accuracy as the horizon grows, at different rates ({{Fig. 13}}): from 30 to 120 min the full GBM falls from 0.932 to 0.899, the inventory-only GBM to 0.871, the logistic model to 0.849, the steepest fall, and the roll-out to 0.857, while the seasonal baseline stays near 0.81. For a two-hour view the recent trip flows are worth 0.028 AUC, three times their value at 30 min, and the roll-out overtakes the linear model. For a pre-bell plan made 60–90 minutes ahead the full model keeps AUC ≥ 0.90 and ECE ≤ 0.014."),
  ...figure("fig_horizon.png", capM("{{Figure 13. }}", "Ranking (a) and probability quality (b) by horizon on the NTU test months, all 144 stations; bands: 95% day-bootstrap intervals for the full GBM and the calibrated roll-out.")),
  bodyB("By gain, the current stock (49%), its one-hour minimum (20%), the station id (8%) and the fill ratio (5%) dominate the 30-minute full model. The bell features contribute almost nothing: the ablation without group B changes AUC by at most 0.002 on every subset, including campus slots 0–30 min before a bell, because hour of day already encodes a fixed timetable. The hard cases are stations that are still well stocked 30 minutes before a bell (AUC 0.79 at h = 30); Sec. 3.5 tests whether the course catalogue helps there."),

  h2("3.5. Transfer to NSYSU", true),
  bodyB("{{Fig. 14}}(a) shows that the inventory-only NTU model works at NSYSU without any local data: zero-shot AUC 0.934 on all 309 Kaohsiung stations and 0.943 on the 8 campus stations at h = 30, with Brier 0.049 / 0.068 and ECE 0.023 / 0.019. Fine-tuning on six NSYSU days adds 0.006 [0.005, 0.007] AUC and improves ECE to 0.003 on all stations; a model trained only on those six days is equally good (0.940), while the seasonal baseline from six days is poor (0.651). The proposal expected a zero-shot drop that local data would close; instead the dynamics of a station emptying generalize across cities almost perfectly, and the only transfer gap is in calibration, which six days of local data remove. At h = 60 the figures are 0.894 zero-shot and 0.906 fine-tuned. On campus the three learned models differ by at most 0.003, against station-day intervals of about ±0.010."),
  body([nbb("Timetable intensity. "), nb("Tested on each teaching day after training on the other fourteen days, the local inventory-only model reaches AUC 0.941 on all stations and 0.947 on campus at h = 30, 0.010 [0.009, 0.011] above zero-shot (0.021 at h = 60). The five catalogue features ("), fb("Fig. 14"), nb("b) change AUC by at most 0.001 on all and on campus stations and take 1% of the split gain. For the hard case of Sec. 3.4, campus stations still holding ≥ 5 bikes 30 min before a bell (2.2 k slots, 103 stockouts), AUC moves from 0.881 to 0.886 at h = 30 and from 0.888 to 0.895 at h = 60, with intervals that include zero, and training on 2–11 Oct to test on 12–16 Oct gives effects of opposite sign at the two horizons. In the leave-one-day-out test the only significant effect is a lower Brier score at the gateway stations (−0.0008 [−0.0012, −0.0005]). Hour, weekday and bell times already encode a timetable that repeats every week; the catalogue should matter when the timetable changes, as it will next semester.")]),
  ...figure("fig_nsysu.png", capM("{{Figure 14. }}", "NSYSU. (a) Test days 10–15 Oct, h = 30 min: AUC with 95% station-day intervals. (b) AUC change from the five catalogue features, leave-one-day-out, 95% day intervals; pre-bell: campus, ≥ 5 bikes, 30 min before a bell; AM: 07:00–10:00.")),
  body([fbb("Weeks of local data. "), fb("On the 14 test days of 3–16 Nov the zero-shot model scores AUC 0.933 [0.929, 0.940] on all stations and 0.945 on campus, the same as on the six test days of the midterm (0.934 and 0.943), with ECE 0.028 and 0.010. Local data help a little, and early (Fig. 15a). One week of fine-tuning adds 0.004 [0.003, 0.006] AUC on all stations and four weeks add 0.006 [0.004, 0.008]; a model trained on the local window alone reaches the same value from the third week (0.939). On campus four weeks add 0.003 [0.000, 0.005]. What local data change is calibration: ECE on all stations falls from 0.028 to 0.003 after one week. At h = 60 min the zero-shot AUC is 0.894 and four weeks of fine-tuning give 0.908, with ECE down from 0.052 to 0.004. Week by week the zero-shot AUC stays between 0.929 and 0.935 on all stations and between 0.936 and 0.946 on campus over seven weeks (Fig. 15b), so the NTU model has not drifted. The proposal expected a gap that two to four weeks of data would close. In ranking there is almost no gap, and one week closes the gap in calibration. The live system therefore runs the NTU model after further boosting on every logged day (nsysu_finetune.py): on the three most recent days, which also set the stopping point, AUC rises from 0.923 to 0.933 at h = 30 min and from 0.881 to 0.899 at 60 min, and ECE falls from 0.030 to 0.006 and from 0.052 to 0.013.")]),
  ...figure("fig_final_transfer.png", capM("{{Figure 15. }}", "{{NSYSU, test days 3–16 Nov, h = 30 min. (a) AUC against weeks of local training data ending on 29 Oct; week 0 is the zero-shot NTU model; bars: 95% day-bootstrap intervals. (b) Zero-shot AUC on each logging week (semester weeks 4–10).}}")),

  h2("3.6. Replay simulation", true),
  bodyB("Over the 28 replayed weekdays the area records 32,100 rentals per day; without rebalancing 3,390 of them (10.5%) find an empty station and the 144 stations spend 17,800 station-minutes empty per day. {{Fig. 16}} gives the results per policy. With the greedy step, one truck avoids 5–7% of unmet rentals, three trucks 16–17% and six trucks 25–27%; per day the probabilistic policy beats the point policy by 2.0–2.4 points (95% intervals exclude zero) but not the reactive one (0.0–0.4 points), and the point policy, which waits for a forecast deficit instead of acting on an empty station, cuts empty station-minutes least (14% against 41% with six trucks). Replaying the inferred operator moves, which inject about 5,100 bikes per day without any truck constraint, avoids 61%; it is an upper reference, not a policy."),
  ...figure("fig_sim_ci.png", capM("{{Figure 16. }}", "Replay of 28 NTU weekdays: share of (a) unmet rentals and (b) empty station-minutes avoided against no rebalancing, with 95% day-bootstrap intervals; trucks drive 55–70, 192–232 and 396–456 km per day with 1, 3 and 6 trucks.")),
  bodyB("The route search avoids 13%, 30% and 45% of unmet rentals with 1, 3 and 6 trucks and drives about as far as the greedy policies (65, 219 and 430 km per day). Per day it beats the greedy probabilistic policy by 6.1 [5.2, 7.0], 14.0 [12.0, 16.0] and 19.3 [17.4, 21.2] points, on all 28 days at every fleet size. Most of the gain comes from how moves are priced: the single-move variant with the same values already avoids 12%, 28% and 44%. The routes add 0.7–2.1 points of unmet rentals (the one-truck interval includes zero) and 1.6–8.4 points of empty station-minutes; with one truck the route search cuts empty minutes less than the greedy probabilistic and reactive policies (6% against 7–8%), because its values count rentals, not empty time. Annealing and 2-opt improve the route found by greedy insertion in 40–49% of the plans and raise the total planned value by 8–9%. On the validation days the time cost mattered most: without it the search builds long routes that collect more value at a lower rate, and driving whole six-stop routes was the worst setting tried (2,814 against 2,567 unmet rentals per day with three trucks)."),
  body([fbb("Lost demand. "), fb("The replay contains only rentals that were recorded. The corrected rates of Eq. (3) size the ones that were not (final_lost_demand.py): the rate of each station and hour times the share of that hour the station stood empty, summed over the same 28 weekdays, gives 4,585 lost rentals per day, 14.3% on top of the 32,141 recorded. Of these, 2,185 are at campus stations (16.8% of their recorded rentals) and 42% fall between 17:00 and 22:00, with 621 in the hour from 18:00. This is an estimate under the Poisson-rate model for days on which the operator’s trucks were at work. None of the replayed policies could serve this demand, because it is not in the trip file; the 3,389 unmet rentals of the no-truck replay are recorded rentals that fail once the operator’s moves are taken away.")]),

  h2F("{{3.7. After-class forecast at NSYSU}}"),
  bodyF("Everything the app tells a rider rests on the chain’s forecast of a station’s stock, so that forecast was tested on days the rates had not seen (final_forecast.py). Rates were fitted on the 17 teaching days of 2–29 Oct. The prior weight of the 10-minute rates was chosen on the last five of those days, where they reach a log-likelihood of −1.922 per transition against −2.058 for the hourly rates. On the 12 teaching days of 30 Oct–16 Nov a forecast was made 30 minutes before each of the 15 bells of the day for the stock 20 minutes after it, at every station (157 bells, 46,921 forecasts). The chain forecast is the mean of its stock distribution. Persistence keeps the current stock, and the seasonal mean is the station’s average stock at that time of day on the fitting days."),
  tableCaptionM("{{Table 4. }}", "{{Stock 20 min after a bell, forecast 30 min before it, on 12 held-out teaching days at NSYSU: mean absolute error in bikes per station, and AUC of P(empty) at the campus stations.}}"),
  table([1477, 750, 850, 700, 900], ["{{Method}}", "{{campus (8)}}", "{{corridor (19)}}", "{{all 309}}", "{{AUC, campus}}"], allNew([
    ["persistence", "5.80", "4.60", "2.43", "0.658"],
    ["seasonal mean", "3.88", "3.96", "3.35", "0.873"],
    ["chain, hourly rates", "4.17", "3.52", "2.09", "0.885"],
    ["chain, 10-minute rates", "3.30", "3.04", "2.05", "0.897"],
  ])),
  spacer(),
  bodyF("Table 4 and Fig. 17(a) give the result. At the eight campus stations the chain with 10-minute rates misses by 3.30 bikes on average, against 4.17 with hourly rates (paired difference −0.86 [−1.04, −0.72], bootstrap over test days), 3.88 for the seasonal mean (−0.58 [−0.77, −0.36]) and 5.80 for persistence (−2.50 [−2.71, −2.30]). With hourly rates the chain was worse than the seasonal mean on campus; the 10-minute rates are what make a forecast from the current stock better than the average day. The gain comes at the bells with the largest flows. At 12:00 the hourly chain is off by 9.6 bikes with a bias of +8.2, because it spreads the rush after the bell over the whole hour, and the 10-minute chain by 4.9 with a bias of −0.5. At 09:00, when the campus fills, the error falls from 6.4 to 2.5. Over all 309 stations, most of which hear no bell, the two chains are close (2.05 and 2.09) and both beat persistence (2.43) and the seasonal mean (3.35). Ten minutes before the bell the campus error is 3.06 bikes and an hour before it 3.65, still below the seasonal mean (−0.26 [−0.43, −0.08])."),
  ...figure("fig_final_forecast.png", capM("{{Figure 17. }}", "{{After-class forecast at NSYSU, 12 held-out teaching days. (a) Mean absolute error of the stock of a campus station 20 min after each bell, forecast 30 min before it. (b) Forecast chance that a station is empty then, against the share that was.}}")),
  bodyF("The same distribution gives the chance that the station is empty after the bell: AUC 0.881 on all stations (Brier 0.051, ECE 0.016) and 0.897 on campus (Brier 0.077, ECE 0.024), against 0.873 on campus for the seasonal frequency and 0.658 for persistence. On all stations the forecast runs four to ten points above the observed share up to 0.55 and further above it beyond: stations given 0.6–0.8 were empty about half the time (Fig. 17b). The chance of a full station, which matters to a rider who returns a bike, is ranked well (AUC 0.943 on all stations and 0.921 on campus, against 0.859 with hourly rates) but is too low on campus, 0.041 on average where 0.080 of the cases were full."),

  bodyF("A learned correction of the chain was also tried (final_avail.py): a LightGBM model on the chain’s chances for the station and its nearest neighbours, the current stock and its change over 10 and 30 minutes, the time of day and the number of steps ahead, cross-fitted on two blocks of nine days from 30 Oct to 16 Nov. Calibration improves and ranking barely moves: for a free dock at a campus station 10 to 30 minutes ahead, ECE goes from 0.029 to 0.004 and AUC from 0.951 to 0.957; for a bike, from 0.015 to 0.008 and from 0.940 to 0.942. In a replay of first choices (final_rider.py) it does no better than the chain, so the app keeps the chain alone."),

  h2F("{{3.8. The app’s advice against logged outcomes}}"),
  bodyF("The logger shows where riders fail (final_rider.py). On the 29 teaching weekdays up to 16 Nov the eight campus stations had no bike in 40% of their snapshots between 17:00 and 20:00 (29% to 54% by station), against 2% between 07:00 and 17:00. They had no free dock in 28% of the snapshots between 09:00 and 11:00, against 3% from 11:00 to 22:00. Mornings are also hard at the eleven gateway stations at the foot of the campus, which include the two KRT exits: no bike in 25% of the snapshots between 08:30 and 11:00. By the measure that cities publish, the share of the time between 06:00 and 24:00 in which a station has a bike [31], the campus looks close to ordinary (final_city.py): 88.5% on these days, against 94.0% over all logged stations. Between 17:00 and 20:00 the campus figure is 59.7%. In the morning the campus is short of docks only station by station: between 09:00 and 11:00 it keeps 39 docks free on average as a whole, while at least one of its eight stations is full in 81% of them. The College of Engineering is full 55% of the time, the Gymnasium with its 63 docks 15%. Riders sent to the free racks, or docks moved where the racks fill, would answer this. In the chain (final_docks.py), which finds full stations too rarely (Sec. 3.7), four docks moved from the Gymnasium to Engineering cut the share of 09:00–11:00 in which Engineering is full from 0.47 to 0.20 and save two refused returns a morning, but the best twelve single-dock moves cut the campus’s refused rentals and returns by only 2.6% a day: in the evening the whole campus is short of bikes."),
  bodyF("The advice was first tested by asking whether the first station a rule names has a bike on arrival (final_rider.py), on the 12 teaching days of 30 Oct–16 Nov with rates fitted up to 29 Oct. The app then named the nearest station with a chance of at least 0.9, which had a bike for 93% of evening departures from campus, against 64% for the nearest station. The comparison left out the 4.6 minutes of extra walking per rider and counted a miss as final, although a rider who finds an empty rack walks on."),
  bodyF("The test was repeated in minutes until riding (final_time.py). Every 10 minutes a rider stands two minutes from each station of a group and leaves. A rule names a station and the rider walks there along the paths of Sec. 2.8. If the logger shows a bike at the minute of arrival, interpolated between the two snapshots around it, the clock stops. If not, the rule is asked again from that station with the counts of that moment, up to three stations; after a third miss the rider gives up and 15 minutes are added. For a dock the rider rides to the chosen station, and the clock runs from reaching the area until the rider stands at the destination without the bike. Four rules are compared. A rider can walk to the nearest station and look again only after a miss, or go to the nearest station that shows a bike or a dock, which the operator’s app allows. The other two are the app’s first rule and its present one, the station with the fewest expected minutes (Sec. 2.8)."),
  ...figure("fig_final_time.png", capM("{{Figure 18. }}", "{{Twelve held-out teaching days at NSYSU. (a) Mean minutes until a rider is on a bike, or has docked one and reached the destination, by the rule that names the station; bars: 95% day-bootstrap intervals. Chance ≥ 0.9 is the app’s first rule, fewest minutes its present one. (b) Evening departures from campus by time of leaving. (c) AUC for telling in advance which evening searches take more than 8 minutes: the app’s forecast, the same formula with the counts held as they are, and the usual value for that place and minute.}}")),
  bodyF("Fig. 18(a) gives the means. Leaving campus between 17:00 and 19:50 (1,560 cases), a rider needs 3.7 minutes [3.0, 4.7] with the nearest station and 3.7 [3.0, 4.6] with the live counts. The first rule needs 5.3 [4.2, 6.7], which is 1.6 minutes more than the live counts [1.0, 2.3], and 16% of its riders search for more than ten minutes, against 5%. Its first station does have a bike 96% of the time, but the walk past nearer stations costs more than the misses it avoids. The present rule needs 3.7 minutes [3.0, 4.7] (+0.02 against the live counts [−0.04, 0.08]) and finds a bike at the first station 89% of the time. The mornings give the same order with smaller gaps: a bike at the foot of the campus takes 2.8 to 2.9 minutes, 3.1 with the first rule, and a dock on campus 1.4 to 1.5 minutes. Outside the three periods a bike takes 2.0 to 2.2 minutes. The first rule was withdrawn on 18 Nov."),
  bodyF("The present rule gains only when the station must be chosen early. Chosen 10 minutes before leaving, the live counts need 4.5 minutes in the evening and the present rule 3.9 (−0.5 [−0.8, −0.3]); for a dock chosen 10 minutes before riding in, 1.9 against 1.5 (−0.4 [−0.6, −0.3]). A rider who decides nothing in advance does as well, at 3.7 and 1.4. The time of leaving matters more than the rule (Fig. 18b): the search takes 2.8 minutes at 17:00, 5.2 on average between 17:30 and 18:10, when one rider in eight needs more than ten, and about 2.4 from 19:10."),
  bodyF("The forecast is of more use before the trip. The page was asked 0, 10, 20 and 30 minutes before each evening departure how long the search would take, against what a rider following the live counts on leaving then needed. Of these searches 8% took more than eight minutes. The page’s number tells them apart with an AUC of 0.90, 0.87 and 0.86 at 10, 20 and 30 minutes ahead. The same formula fed with the counts at the time of asking, as if nothing would change, reaches 0.78, 0.73 and 0.69, and the usual value for that place and minute on the fitting days 0.76 (Fig. 18c). In mean absolute error it is no closer than the counts (1.5 against 1.3 minutes at 10 minutes ahead). On the 11 evenings with full logs (final_spread.py), 9% of the departures drawn 10 to 60 minutes ahead with one red dot took more than eight minutes, 18% with two, 28% with three and 1% with none; the Brier score of the red share is 0.028–0.037, against 0.043 for the usual share. The coupling θ was chosen by leaving one day out; with θ = 1 long searches are under-predicted. Of the stations labelled as having bikes, 99% had one on arrival (final_labels.py)."),
  bodyF("From a campus station to KRT exit 1, borrowing a bike and riding takes 11.6 minutes door to door on average in the evening, against 17.3 on foot, and the bike is faster in 94% of the cases."),
  bodyF("The reward of Sec. 1.3 is judged at the moment of returning or borrowing [30], and the operator’s app shows which stations are empty or full now. On the held-out days (final_relay.py), a corridor station that is empty now is still empty 10 minutes later in 65% of the cases and 20 minutes later in 53%; a station that the page marks is empty in 71% and 61%, but the mark finds fewer of the empty stations (42% against 65% at 10 minutes). For full stations the mark is right more often (74% against 59%) but finds only 16% of them, because the chain underestimates full stations (Sec. 3.7). The logger started after the reward did, so what the reward changed cannot be measured here."),
  bodyF("The logger sees a station every 10 minutes. Scored by the later snapshot around an arrival, the worst case for a rider who trusts a count, the evening means are 4.3 minutes for the nearest station, 4.7 for the live counts, 5.9 for the first rule and 4.6 for the present one; by the earlier snapshot 3.2, 3.2, 5.1 and 3.3. The test rider is alone, and many riders following the same advice would empty the suggested station faster than the chain expects. All of this was computed after the fact. Since 18 Nov the logger therefore commits, at every snapshot and before the outcome exists, the station the page names for a rider near each corridor station and the minutes it expects (demo_track.py); the page shows the scored totals. " + PRO_ADVICE + "No rider has yet been asked whether the page changed a decision."),
  bodyF("Fig. 19 shows the page replaying Wednesday 11 Nov. At 16:40 from the library it names the library station; its dots show no long search before 17:40, when one departure in ten takes more than eight minutes. At 17:30, for a trip from the College of Management to the metro, it names the Social Sciences station to borrow at and KRT exit 1 to return at, and gives about 10 minutes door to door against 16 on foot."),
  ...figure("fig_demo_app.png", capM("{{Figure 19. }}", "{{The web app replaying Wednesday 11 Nov 2026 on a phone. Left: Borrow at 16:40 from the library. Right: 17:30, a trip from the College of Management to the metro.}}")),

  h2F("{{3.9. A truck for the campus corridor}}"),
  bodyF("Recomputed for every snapshot of 23 teaching weekdays (final_planner.py), a trip planned for the whole district saves 15 of 252 expected unmet rentals on average, 6%. One truck of 20 bikes is small against a shortfall spread over 309 stations, and the figure says little about the campus. The 10-minute rates do change where the truck goes before the noon bell: between 11:00 and 12:00, 63% of the delivered bikes go to campus stations, against 25% when the same days are planned with hourly rates."),
  bodyF("What a truck does for the campus over a whole shift was measured in a simulation (nsysu_sim.py), since Kaohsiung publishes no trips to replay as in Sec. 3.6. In every 10-minute step each station receives Poisson rental requests and returns at rates fitted on 30 Oct–16 Nov; a request at an empty station is an unmet rental, and a return at a full station is refused. The planner works with rates fitted up to 29 Oct, so it does not know the rates that generate the demand. A morning shift (07:00–11:00) and an evening shift (15:00–20:00) are simulated on the teaching days of the period with complete snapshots (11 and 9 days, five random seeds each), each from the stock the logger recorded at its first minute, and the last three hours are scored. A truck holds 20 bikes, drives at 15 km/h, spends four minutes per stop and plans again after two stops. Without a truck the simulated number of bikes on campus stays, on average over a shift, within 3.9 bikes of the logged number in the morning and within 7.0 in the evening."),
  ...figure("fig_final_sim.png", capM("{{Figure 20. }}", "{{Simulation at NSYSU: share of failed attempts avoided by one to three trucks that deliver only to the campus corridor, against no truck. Bars: 95% day-bootstrap intervals.}}")),
  bodyF("Without a truck, 56% of the rental requests on campus between 17:00 and 20:00 find no bike, 166 per evening. One truck that delivers only to the 19 corridor stations avoids 33.6% of them [30.6, 36.2], two avoid 54.3% [52.3, 56.4] and three 66.4% [64.2, 68.9] (Fig. 20). A truck free to deliver anywhere in the district avoids 20.9% [15.9, 25.4] on campus. The live planner is restricted to the corridor for that reason. A corridor truck collects its bikes elsewhere: unmet rentals in the rest of the district rise by about 1%, six per evening against 56 fewer on campus."),
  bodyF("In the morning 31% of the requests at the gateway stations find no bike (79 per morning); one, two and three corridor trucks avoid 70.2%, 86.5% and 90.0%. The same trucks take bikes out of the campus as it fills, and refused returns there (18.6% of returns, 64 per morning) fall by 39.3%, 50.4% and 51.7%."),
  bodyF("In this model world demand follows the fitted rates and does not react: a rider who finds no bike does not try the next station, and the operator’s own trucks are absent. The replay of Sec. 3.6 remains the only test on recorded trips."),

  h2F("{{3.10. A reward paid before the bell}}"),
  bodyF("Sec. 3.8 showed that in the evening the whole campus is short of bikes, so no advice can find one: bikes have to come back before the bell. The operator already pays riders who move bikes, a NT$5 voucher for returning a standard bike to an empty station or borrowing from a full one, judged at that moment [30]. On campus it pays too late (final_reward.py). On the 12 held-out teaching days the chain’s return rates put 285 returns a day at the eight campus stations between 14:00 and 20:00, 197 of them (69%) before 17:00 (Fig. 21a), when the stations still have bikes (Fig. 21b). Today’s rule pays for 5.6 of these 197 returns (3%), yet they are worth almost as much as later ones: by the backward pass of the planner, one more bike at a campus station at 16:30 avoids 0.92 refused rentals over the next two hours, and at 17:30 0.94."),
  bodyF("A predictive rule pays where the chain gives a station at least an even chance of running empty within 40 minutes, much as Citi Bike’s points follow the bikes a station will need [34]. We pay it in an hour of ride time per return: students with an iPass student ID and pass holders (TPASS, MeNGo) already ride the first 30 minutes free and other members pay NT$5 for them [39], so 30 minutes would add little and an hour helps the first group only on rides over 30 minutes. An hour is two-fifths of the weekly 150 minutes the WHO recommends [37]; cycling to work has been associated with a 41% lower risk of death [38]. Of 219 campus stockouts between 15:00 and 20:00 on the held-out days, 91% were flagged a median of 40 minutes ahead. Of the flags raised while a station still had bikes, 62% were followed by an empty station within 40 minutes, against 25% of all such snapshots. Before 17:00 it pays for 24.0 returns a day instead of 5.6, each worth 1.00 avoided refusals, against 0.50 for a return it leaves unpaid."),
  bodyF("How many riders the reward moves cannot be read from the logs. The chain is therefore run from the logged stock at 15:00 to 20:00 with returns raised by 25%, 50% or 100% in the states the rule pays, and from 08:00 to 11:00 with rentals raised likewise at stations about to fill (final_policy.py). Two other measures run in the same chain: a truck bringing 20 bikes at 16:50 and 20 more at 17:50 (taking 20 away at 09:00 in the morning), and half of the classes that end at 17:00 or 18:00 ending 10 minutes early. Without the operator’s trucks after 15:00 the levels are high (204 refused rentals a day), so the cuts are the result (Fig. 21c). With a 50% response the reward cuts refused rentals by 11% and refused morning returns by 6%, at 69 more rewards (69 hours of ride time) a day in the evening; 25 returns are new rides to campus, and 44 of the extra rewards go to returns that would have happened anyway. The trucks cut 16% and 20%, trucks and reward together 27% and 25%. Ending classes early cuts 2%, because the campus is short of bikes all evening."),
  bodyF(PRO_REWARD),
  bodyF("The logger started after the reward did, so the response is the least certain number here. A one-page brief to the school, the city and the operator proposes a trial that alternates the two rules week by week at the campus stations (docs/policy_brief.pdf)."),
  ...figure("fig_final_reward.png", capM("{{Figure 21. }}", "{{The operator’s reward on the 12 held-out teaching days at NSYSU. (a) Returns to the eight campus stations per half hour in the chain, by whether today’s rule pays them (station empty), only the predictive rule does (chance ≥ 0.5 of emptying within 40 min) or neither. (b) Share of station-time the campus stations were empty, from the logger. (c) Cut in rentals refused at campus stations from 15:00 to 20:00, and in returns refused from 08:00 to 11:00; the response is the rise in returns (morning: rentals) where the predictive rule pays.}}")),

  // ===================== CONCLUSION =====================
  h1F("4. {{Conclusion and limits}}"),
  bodyB("{{Table 5}} sets the numbers the proposal expected against what the midterm experiments gave{{ and what the final weeks added}}. The predictor met every target, and transfer was easier than expected. The route search raised the simulator numbers to 13%, 30% and 45% with 1, 3 and 6 trucks, approaching the proposal’s 50% with six trucks. The replay also understates what rebalancing can do, because it contains only recorded rentals: the demand that was lost at empty stations, which rebalancing would serve, is not yet counted{{; Sec. 3.6 puts it at 14% of the recorded rentals}}. The operator replay (61%) injects about 5,100 bikes per day without any truck constraint and is a reference, not a reachable target."),
  tableCaptionM("{{Table 5. }}", "Proposal expectations (HW1, Sec. 3) against midterm {{and final}} results."),
  table([1077, 800, 1400, 1400], ["Quantity", "Expected (HW1)", "Midterm", "{{Final}}"], [
    ["Predictor AUC, h = 30 min", "> 0.85", "0.93 (NTU), 0.93 (NSYSU zero-shot); 0.90 at 120 min", "{{0.933 zero-shot on 14 later days; no drift in seven weeks}}"],
    ["Poisson + Monte-Carlo roll-out", "the predictor of Sec. 2.4", "built exactly; AUC 0.895, so the classifier (0.922–0.932) predicts and the chain prices bikes for the planner", "{{fitted without trips; stock after a bell within 3.3 bikes (4.2 with hourly rates)}}"],
    ["Predictor ECE, h = 30 min", "< 0.05", "0.012 (NTU), 0.023 (NSYSU zero-shot)", "{{0.028 zero-shot, 0.003 after one local week}}"],
    ["NSYSU transfer", "zero-shot drop, closed within 5 AUC points after 2–4 weeks", "no drop: 0.934 zero-shot vs. 0.940 with 6 local days", "{{+0.004 AUC after one week, +0.006 after four}}"],
    ["Unmet rentals avoided, reactive", "about 20%", "7% / 17% / 26% with 1 / 3 / 6 trucks", "{{unchanged}}"],
    ["Unmet rentals avoided, point forecast", "about 40%", "5% / 16% / 25%", "{{unchanged}}"],
    ["Unmet rentals avoided, probabilistic", "about 50%", "13% / 30% / 45% (route search); greedy 7% / 17% / 27%", "{{unchanged at NTU (lost demand, 14%, not in the replay); NSYSU simulation: 34% / 54% / 66% with 1 / 2 / 3 trucks}}"],
    ["{{Live demo at NSYSU}}", "{{web demo with a pre-bell truck plan}}", "{{mock-up}}", "{{live since 30 Oct; advice as fast as the live counts (3.7 min); slow departures foreseen with AUC 0.86–0.90}}"],
  ], { aligns: [AlignmentType.LEFT, AlignmentType.LEFT, AlignmentType.LEFT, AlignmentType.LEFT] }),
  spacer(),
  bodyF("Of the items the midterm report left open, the rates for the planner at NSYSU (Sec. 2.7), the live demo (Secs. 2.8, 3.8) and the transfer study by weeks of local data (Sec. 3.5) are done. The censored demand is sized (Sec. 3.6), but no policy has been replayed on it. A two-sided label was not trained; in the app the chain’s chance of a free dock takes its place. It is too high on campus (Sec. 3.7), so the Return tab calls a dock sure only from a chance of 0.95."),
  bodyF("The timetable makes campus stockouts regular enough to act on: at NSYSU the noon bell took at least 45 bikes from the campus within 20 minutes on every teaching day measured. A predictor trained on Taipei data ranks stockouts in Kaohsiung as well as at home (AUC 0.93) without local data. A birth–death chain fitted to nothing but 10-minute stock counts forecasts the stock of a campus station after a bell within about three bikes, once its rates follow the bell. In the replay of real NTU trips, pricing each bike with that chain and searching routes avoids 13% to 45% of unmet rentals with one to six trucks, against 7% to 27% for greedy rules. For a rider at NSYSU the forecast does not shorten the search for a bike. Measured in minutes, following it equals walking to the nearest station and looking again after a miss, and a rule tuned for first-try success made the search longer. It does say 10 to 60 minutes ahead how often a departure will be slow, which the current counts say poorly, and its chances come true about as often as stated. The shortage behind those departures can only be met by moving bikes, by truck (Sec. 3.9) or by riders paid with the operator’s reward. Paid at an empty rack, the reward reaches 3% of the bikes that come back before the 17:00 bell; paid in ride time where the chain expects a rack to empty within 40 minutes, it would reach four times as many and can only be spent on more riding (Sec. 3.10)."),
  bodyF("The truck results at NSYSU come from a simulation driven by fitted rates; measuring a real reduction needs trip records or a trial with the operator. How many riders a reward paid before the bell would move is assumed in Sec. 3.10, not measured. The rider test scores one rider at a time on days already logged, and cannot show what happens when many follow the same advice. No rider has been asked whether the page changed a decision. On the days logged after the evaluation was frozen, the warning and the advice gave the same results (Secs. 3.8, 3.10), but that record covers only " + words(PW.n_days) + " teaching days."),
  body([run("Work division: 林沛霆 (PL) built the logger, the NTU pipeline, the replay simulator, the route search and this report; 陳佳晨 (JC) owns demand reconstruction, operator inference and its checks, the calibration and transfer studies and the bootstrap; 林詩穎 (SL) owns the predictor, the roll-out comparison, the horizon sweep, the ablations and the demo. All code, tables, model files, metrics and figures are in the public repository [17] under analysis/, with a README that rebuilds every table from the raw sources."), fb(" For the final report PL rebuilt the logger and fitted the chain rates, JC ran the transfer study by weeks and the lost-demand estimate, and SL built the web app with its browser checks and ran the forecast and rider tests; PL also ran the truck simulation.")]),

  h1("References"),
  ...references(),
];

const doc = new Document({
  creator: "NSYSU Group 54",
  title: "Beat the Bell: Final Report",
  styles: { default: { document: { run: { font: FONT, size: 20 } } } },
  sections: [
    { properties: { page: { size: PAGE, margin: MARGIN }, column: { count: 1 } }, children: titleBlock },
    { properties: { type: SectionType.CONTINUOUS, page: { size: PAGE, margin: MARGIN }, column: { count: 2, space: COL_SPACE, equalWidth: true } }, children: placeFigures(main) },
    // a continuous section break after the two-column text balances the two columns of the last page
    { properties: { type: SectionType.CONTINUOUS, page: { size: PAGE, margin: MARGIN }, column: { count: 1 } },
      children: [new Paragraph({ spacing: { before: 0, after: 0, line: 20 }, children: [run("", { size: 2 })] })] },
  ],
});
const OUT = process.env.OUT_DOCX || "HW5_54.docx";
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(OUT, buf); console.log("wrote " + OUT, buf.length); });
