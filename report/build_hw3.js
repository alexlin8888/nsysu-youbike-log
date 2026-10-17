// HW3 midterm report, CVPR two-column layout. Blue = new or changed since HW1.
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, Tab, TabStopType,
  AlignmentType, SectionType, BorderStyle, ShadingType, VerticalAlign,
} = require("docx");

const FIG = process.env.FIG_DIR || "figs/";
const PAGE = { width: 12240, height: 15840 };
const MARGIN = { top: 1440, right: 902, bottom: 1622, left: 1440, header: 431, footer: 431, gutter: 0 };
const COL_SPACE = 544;
const COL_W = (PAGE.width - MARGIN.left - MARGIN.right - COL_SPACE) / 2; // 4677 twips
const COL_PX = Math.floor((COL_W / 1440) * 96) - 2;
const BLUE = "0000FF";
const FONT = { ascii: "Times New Roman", hAnsi: "Times New Roman", cs: "Times New Roman", eastAsia: "PMingLiU" };
const MONO = { ascii: "Courier New", hAnsi: "Courier New", cs: "Courier New", eastAsia: "PMingLiU" };

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

// ---------- paragraphs ----------
const tagKeep = (p, keep = true, label = null) => { if (keep) p.__keep = true; if (label) p.__label = label; return p; };   // a figure may not be placed right after this
const P = (children, o = {}) => tagKeep(new Paragraph({ alignment: AlignmentType.JUSTIFIED, indent: { firstLine: 288 }, spacing: { after: 0, line: 240 }, children, ...o }), !!o.keepNext);
const body = (parts, o = {}) => P(typeof parts === "string" ? [run(parts)] : parts, o);
const bodyB = (text, o = {}) => P([nb(text)], text.trim().endsWith(":") ? { keepNext: true, ...o } : o);
const h1 = (t, blue = false) => tagKeep(new Paragraph({ keepNext: true, spacing: { before: 120, after: 40, line: 240 }, children: [run(t, { bold: true, size: 24, color: blue ? BLUE : undefined })] }), true, t);
const h2 = (t, blue = false) => tagKeep(new Paragraph({ keepNext: true, spacing: { before: 90, after: 30, line: 240 }, children: [run(t, { bold: true, size: 22, color: blue ? BLUE : undefined })] }), true, t);
// heading that keeps the HW1 words in black and marks changed numbers / words in blue: h2mix([["2.3.", true], [" Demand reconstruction", false], ...])
const h2mix = (parts) => tagKeep(new Paragraph({ keepNext: true, spacing: { before: 90, after: 30, line: 240 },
  children: parts.map(([t, b]) => run(t, { bold: true, size: 22, color: b ? BLUE : undefined })) }), true, parts.map((x) => x[0]).join(""));
const h3 = (t, blue = true) => tagKeep(new Paragraph({ keepNext: true, spacing: { before: 60, after: 20, line: 240 }, children: [run(t, { bold: true, italics: true, size: 20, color: blue ? BLUE : undefined })] }), true, t);
// bullet: hanging indent with a dash, blue by default
function bullet(parts, { blue = true, last = false } = {}) {
  const ch = typeof parts === "string" ? [blue ? nb(parts) : run(parts)] : parts;
  return tagKeep(new Paragraph({ alignment: AlignmentType.JUSTIFIED, indent: { left: 300, hanging: 180 }, spacing: { after: last ? 40 : 0, line: 240 },
    children: [run("– ", { color: blue ? BLUE : undefined }), ...ch] }), !last);   // no figure inside a list
}
// numbered equation: centred with the number at the right margin
function eq(parts, num) {
  return new Paragraph({ alignment: AlignmentType.LEFT, indent: { left: 600 }, spacing: { before: 40, after: 40, line: 240 },
    tabStops: [{ type: TabStopType.RIGHT, position: COL_W }], children: [...parts, new TextRun({ children: [new Tab(), `(${num})`], font: FONT, size: 20, color: BLUE })] });
}
// Figures are placed as markers first; LAYOUT (env, JSON {file: {shift, frac}}) may move a figure `shift`
// elements later (negative = earlier) and scale it, so that no column ends with a large blank.
const LAYOUT = process.env.LAYOUT ? JSON.parse(process.env.LAYOUT) : (fs.existsSync("layout.json") ? JSON.parse(fs.readFileSync("layout.json", "utf8")) : {});
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

// ---------- tables ----------
function cell(text, { width, bold: b = false, shade = false, align = AlignmentType.LEFT, blue = true, size = 15, keep = true, mono = false } = {}) {
  const lines = Array.isArray(text) ? text : [text];
  return new TableCell({
    width: { size: width, type: WidthType.DXA }, margins: { top: 14, bottom: 14, left: 50, right: 50 },
    shading: shade ? { type: ShadingType.CLEAR, fill: "EDEDED", color: "auto" } : undefined, verticalAlign: VerticalAlign.CENTER,
    children: lines.map((ln) => new Paragraph({ alignment: align, keepNext: keep, keepLines: true, spacing: { after: 0, line: 210 },
      children: [new TextRun({ text: ln, font: mono ? MONO : FONT, size, bold: b, color: blue ? BLUE : undefined })] })),
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
const spacer = () => { const p = new Paragraph({ spacing: { before: 0, after: 80, line: 120 }, children: [run("", { size: 6 })] }); p.__spacer = true; return p; };
// one-cell box (changes summary, algorithm)
function box(lines, { mono = false, size = 16, fill = "F4F7FD", line = 220 } = {}) {
  const border = { style: BorderStyle.SINGLE, size: 4, color: "7F9CCB" };
  return new Table({
    width: { size: COL_W, type: WidthType.DXA }, columnWidths: [COL_W],
    borders: { top: border, bottom: border, left: border, right: border, insideHorizontal: border, insideVertical: border },
    rows: [new TableRow({ cantSplit: true, children: [new TableCell({
      width: { size: COL_W, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 90, right: 90 },
      shading: { type: ShadingType.CLEAR, fill, color: "auto" },
      children: lines.map((ln) => new Paragraph({ alignment: AlignmentType.LEFT, keepLines: true, spacing: { after: 0, line },
        indent: mono ? { left: 0 } : { left: 200, hanging: 200 },
        children: typeof ln === "string" ? [new TextRun({ text: ln, font: mono ? MONO : FONT, size, color: BLUE })] : ln })),
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
function references() {
  const all = [...REFS.map((t) => [t, false]), ...NEW_REFS.map((t) => [t, true])];
  return all.map(([t, blue], i) => new Paragraph({
    alignment: /[\u3400-\u9fff]/.test(t) ? AlignmentType.LEFT : AlignmentType.JUSTIFIED, indent: { left: 260, hanging: 260 }, spacing: { after: 0, line: 190 },   // CJK entries left-aligned: justification spreads their characters
    children: [run(`[${i + 1}] `, { size: 15, color: blue ? BLUE : undefined }), run(t, { size: 15, color: blue ? BLUE : undefined })],
  }));
}

// ---------- title block ----------
const titleBlock = [
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 30, line: 270 },
    children: [run("Beat the Bell: Class-Schedule-Aware Stockout Prediction and Pre-emptive YouBike Rebalancing for Campus Stations", { bold: true, size: 28 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60, line: 240 },
    children: [nb("Midterm Report (HW3) · Introduction to Artificial Intelligence (TAICA, Fall 2026) · Group 54 · "), nbi("blue text = new or changed since the proposal (HW1)")] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 0, line: 240 }, children: [run("Team members", { bold: true, size: 21 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80, line: 240 },
    children: [run("國立中山大學 B124020041 林沛霆 · 國立中山大學 B134020002 陳佳晨 · 國立中山大學 B134020008 林詩穎", { size: 21 })] }),
];

// ---------- main text ----------
const main = [
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 40, line: 240 }, children: [run("Abstract", { bold: true, size: 24 })] }),
  new Paragraph({ alignment: AlignmentType.JUSTIFIED, indent: { firstLine: 202 }, spacing: { after: 80, line: 240 }, children: [
    ital("Docks near a university empty within minutes of a class ending. Because the timetable makes this surge predictable, we cast rebalancing as an AI decision problem: one truck moves bikes before the bell instead of after the stockout. We (i) reconstruct censored demand and the operator’s actual truck moves from public trip records and inventory snapshots, (ii) learn a schedule-aware, calibrated predictor of P(stockout within h min) per station, and (iii) plan truck routes by rolling-horizon search that minimizes expected unmet rentals plus travel cost. "),
    nbi("This midterm report delivers stages (i)–(iii) on real data. A logger has recorded the 309 stations within 5 km of NSYSU every 10 minutes since 1 October; on teaching days the eight campus stations fall from 193 bikes at 10:00 to 7 at 18:00, and 55% of the campus stock leaves within 20 minutes of the 12:00 bell. On 10 months of Taipei trips and 295 days of 10-minute inventory for 144 stations around NTU, our reconciliation recovers the operator’s truck moves (R² = 0.98) and shows that observed rentals understate demand by up to 2× at campus stations in the evening. A gradient-boosting predictor reaches AUC 0.93 and ECE 0.012 at a 30-minute horizon on three held-out months, keeps AUC 0.90 at two hours, and transfers to NSYSU zero-shot (AUC 0.93 on 309 stations, 0.94 on campus). The course catalogue explains which bells drain the campus (ρ = 0.59) but adds no measurable AUC as a feature. The proposal’s Poisson roll-out, implemented exactly as a birth–death chain, reaches AUC 0.895; censoring correction improves it at every horizon, but it misses that an empty station rarely refills, which the classifier learns. A discrete-event replay simulator with greedy truck policies avoids 7%, 17% and 27% of unmet rentals with 1, 3 and 6 trucks. The route-search planner and the live NSYSU demo are the remaining work."),
  ] }),

  // ----- changes box -----
  box([
    [nbb("What has been done since the proposal (HW1)", { size: 16 })],
    "1. NSYSU: a 10-minute logger for 309 stations since 1 Oct; 15 full days analysed (Secs. 2.2, 3.2).",
    "2. NTU: 10.2 M trips and 295 days of inventory turned into three tables (Secs. 2.2, 2.3).",
    "3. Operator-move inference with four independent checks (Secs. 2.3, 3.3).",
    "4. Predictor at 30–120 min against the proposal’s Poisson roll-out and a logistic baseline, with bootstrap intervals (Secs. 2.4, 3.4).",
    "5. NTU→NSYSU transfer and course-catalogue features (Secs. 2.5, 3.5).",
    "6. Replay simulator: four policies, 1/3/6 trucks, 28 days (Secs. 2.6, 3.6).",
    "Not yet done: route search, censored-demand replay, live demo (Sec. 4).",
  ], { size: 15, line: 205 }),
  spacer(),

  h1("1. Introduction"),
  h2("1.1. Motivation"),
  body([
    run("Taipei’s YouBike 2.0 alone served 46 million trips in 2023 [3]. Around universities it fails in one specific way: bikes are plentiful during lectures and vanish when class ends. Fig. 1(a) quantifies this for the 59 NTU campus stations over 20 weekdays [2]: the campus count drops from 584 to 392 bikes within 20 minutes of the 12:10 bell and by 41% after the 17:20 bell; after 18:00 about 30% of stations are empty. Fig. 1(b) is our campus: twelve minutes after NSYSU’s 17:00 bell on 28 Sep 2026, 4 of the 25 stations within 1.5 km were empty, all on the KRT side, while the gymnasium held 48 bikes. The bikes exist; they stand at the wrong stations at a moment the timetable predicts. "),
    nb("Two weeks of our own logging show that the snapshot was typical: on eight teaching weekdays the eight campus stations (231 docks) averaged 193 bikes at 10:00, 49 at 17:00 and 7 at 18:00, with 64% of them empty at 18:00, while the two KRT Sizihwan exits were empty in 36% of morning slots and held 51 bikes at 18:00 (Sec. 3.2). The problem is a tide between campus and the metro, in both directions, every teaching day."),
  ]),
  h2("1.2. Problem definition"),
  body([run("Station "), ital("i"), run(" has capacity "), ital("c"), sub("i"), run(" and inventory "), ital("s"), sub("i"), run("("), ital("t"), run("); rentals "), ital("r"), sub("i"), run("("), ital("t"), run(") and returns "), ital("q"), sub("i"), run("("), ital("t"), run(") are counts whose rates depend on time of day, day of week and, our key assumption, the time to the next bell "), ital("b"), run("("), ital("t"), run("). Rentals are censored: when "), ital("s"), sub("i"), run("("), ital("t"), run(") = 0, lost rentals are unrecorded. One truck of capacity "), ital("Q"), run(" visits stations with travel times "), ital("d"), sub("ij"), run(". Before each bell we choose a route and load plan "), ital("π"), run(" minimizing expected unmet rentals over a horizon "), ital("H"), run(" plus "), ital("β"), run("·travel time under capacity and deadline constraints. This is the course’s rational-agent view: acting under uncertainty to maximize expected utility, coupling probabilistic reasoning, learning and search.")]),
  body([nb("Two sub-problems are now defined precisely. "), nbb("Stockout prediction: "), nb("for every station "), nbi("i"), nb(" and 10-minute slot "), nbi("t"), nb(", output")]),
  eq([nbi("p"), nsub("i"), nb("("), nbi("t"), nb(", "), nbi("h"), nb(") = P( min"), nsub("τ∈(t, t+h]"), nbi(" s"), nsub("i"), nb("(τ) = 0 )")], 1),
  body([nb("for horizons "), nbi("h"), nb(" ∈ {30, 60, 90, 120} min. "), nbb("Rebalancing: "), nb("with "), nbi("K"), nb(" trucks, choose moves (source, target, "), nbi("k"), nb(" bikes) that maximize the expected rentals saved per truck-minute, and evaluate every policy by replaying the real trips of held-out days (Sec. 2.6).")]),
  ...figure("fig1_motivation.png", cap("Figure 1. ", "Class-end stockouts are real and predictable. (a) Mean bikes available at 59 NTU campus stations over 20 weekdays, Mar 2025 [2]; orange = period ends; strip = share of empty stations. (b) NSYSU at 17:12, 28 Sep 2026 [12].")),
  h2("1.3. Existing solutions and literature"),
  body([run("Static repositioning is a routing-and-inventory problem [4]; dynamic repositioning combines forecasts with heuristics or mixed-integer programs [5, 6]; recent work uses spatio-temporal reinforcement learning [7]. Two ingredients matter on a campus yet are rarely combined: censored-demand estimation by simulation [8] or censored Gaussian processes [9], and inferring the operator’s unpublished truck moves by subtracting trip flows from inventory changes [10]; on Taipei data this reveals 18–20 thousand unexplained bike moves on 12 Mar 2025, peaking at 07–09 and 18–20. A 2025 NTU thesis optimized dispatch near NTU with survival-model demand on one month of trips [11]. No published work, to our knowledge, (a) uses the class timetable as an explicit signal, (b) outputs calibrated stockout probabilities rather than point forecasts, or (c) tests transfer between campuses; NSYSU has never been studied and Kaohsiung publishes no trip data, so transfer is the practical question. "),
    nb("Station-level availability has been forecast hierarchically from city to cluster to station [25] and as over-demand prediction with dynamic station clusters [23]; the view of a station as a finite-capacity birth–death process, which the proposal’s Poisson roll-out computes, underlies service-level rebalancing [18, 19] and fleet sizing [20]; data-driven rebalancing at system scale was demonstrated for Citi Bike [24]. For the predictor we use gradient-boosted decision trees [13], which handle mixed count and categorical features natively, and we measure probability quality with the Brier score [15] and the expected calibration error [14] rather than accuracy, because the planner consumes probabilities.")]),
  h2mix([["1.4. Proposed solution", false], [" and status", true]]),
  body([run("Fig. 2 shows the pipeline. Open NTU data (hourly trips [1]; 10-minute inventory over 416 days [2]) serve to reconstruct demand and operator moves, to train a schedule-aware gradient-boosting predictor with reliability checks, and to drive a rolling-horizon route planner; policies are compared in a replay simulator fed with real trips. The predictor is then ported to NSYSU with a few weeks of locally logged inventory [12] for a live web demo that recommends a pre-bell truck plan ("), nb("Fig. 15"), run("). Contributions: (1) an uncertainty-aware pre-emptive rebalancing method reproducible from open data; (2) the first quantification of class-end stockouts at NTU and NSYSU; (3) an NTU→NSYSU transfer study. "),
    nb("Status: (2) is complete for both campuses; (1) is implemented end to end with a greedy planner and evaluated in the simulator; (3) is complete for the predictor. Code, tables and results are public [17].")]),

  // ===================== METHOD =====================
  h1("2. Method"),
  h2("2.1. System overview", true),
  bodyB("Fig. 3 shows the system as built. The NTU lane turns two open data sets into three tables (hourly flows, a 10-minute inventory panel, an hourly reconciliation table) that feed demand reconstruction, the predictor and the simulator; the NSYSU lane builds the same inventory panel from our logger, so the inventory-only predictor and the planner run unchanged on either campus. Each module is one script in the repository [17], named in the subsection headings."),

  h2("2.2. Data acquisition and panel construction", true),
  h3("2.2.1. NSYSU logger (fetch_youbike.py)"),
  bodyB("YouBike publishes a JSON of every station (bikes, free docks, status, update time) but no history, so our logger runs in GitHub Actions and commits one CSV row per station and 10-minute slot for the 309 stations within 5 km of NSYSU; the eight campus stations and eleven gateway stations between campus and the KRT are tagged for analysis. 144 snapshots per day have been recorded since 2 Oct (one 6-hour gap on 12 Oct); out-of-service stations are stored as such and never counted as stockouts."),
  ...figure("fig2_pipeline.png", cap("Figure 2. ", "Proposed pipeline and the course unit each stage exercises.")),
  h3("2.2.2. NTU trip flows (ntu_pipeline.py trips)"),
  bodyB("The Taipei trip records [1] give rent and return time (truncated to the hour), the two stations by name and the duration of every ride. Each monthly zip (6–7 M rows) is streamed in chunks, rides with either end among the study stations are kept, names are matched to station ids through the station table of [2], and rentals and returns are summed per station and hour: 10.2 M rides over ten months (Sep 2024–Jun 2025), 15 s per month."),
  h3("2.2.3. NTU inventory panel (ntu_pipeline.py snapshots)"),
  bodyB("The snapshot repository [2] stores one row per station update. Stations report only when something changes, so values are forward-filled onto a 10-minute grid and marked unknown when the last report is older than 120 min during 07:00–23:00 or 600 min otherwise: 6.1 M station-slots, 7.9% unknown, mostly from a collection outage on 1–16 Oct 2024."),
  h3("2.2.4. Study area and calendars"),
  bodyB("The NTU study area is the 144 stations within 1.2 km of the campus centroid (59 on campus, 85 in the surrounding ring). Bell times are the period ends of each campus (NTU: 09:00, 10:00, 11:10, 12:10, 13:10, 14:10, 15:10, 16:20, 17:20, 18:20, 19:15, 20:10; NSYSU, from the official period table: 07:50, 09:00, on the hour from 10:00 to 18:00, then 19:10, 20:05, 21:00, 21:55). Taiwanese public holidays and the semester calendars (NTU: 2 Sep 2024–10 Jan 2025 and 17 Feb–13 Jun 2025; NSYSU: from 7 Sep 2026) define the off-day and semester-week features."),

  ...figure("fig_architecture.png", capB("Figure 3. ", "Architecture as implemented: sources (grey), tables (light blue), learning (blue), decision and evaluation (orange); numbers are sections of this report.")),

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
  h3("2.5.1. Timetable intensity (timetable.py)"),
  bodyB("The public course query [27] lists each course of semester 115-1 with weekday, periods, room and enrolment: 2,475 courses, 116 of them off campus or online. Merging consecutive periods leaves 2,589 class sessions per week. Five features count the students (in hundreds) whose class ends within the next 30 or 60 min, ended within the last 30 min, starts within the next 30 min, or is under way; they are zero on holidays and outside the 19 corridor stations. Each of the ten teaching days of 2–16 Oct is predicted by two otherwise identical models trained on the other fourteen complete days, with and without the five features, both given the station role (campus, gateway, other) (timetable_nsysu.py); differences are bootstrapped over days."),

  h2mix([["2.6.", true], [" Pre-emptive planner and ", false], ["replay simulator", true]]),
  body([run("State: truck position and load, station stocks and predicted rates; actions: (station, ±"), ital("k"), run(" bikes); objective "), ital("J"), run("("), ital("π"), run(") = Σ"), sub("i"), run(" E[max(0, "), ital("D"), sub("i"), run(" − "), ital("s"), sub("i"), run(")] + "), ital("β"), run("·"), ital("T"), run("("), ital("π"), run("), with "), ital("D"), sub("i"), run(" the predicted demand. Every 10 minutes we rank stations by expected unmet rentals, build a greedy surplus-to-deficit route under capacity "), ital("Q"), run(" and the bell deadline, and improve it by 2-opt local search and simulated annealing. A discrete-event replay simulator consumes real held-out trips (Apr–Jun 2025): a rental is served only if stock > 0, otherwise it counts as unmet, while the truck follows the policy under test. We compare none, reactive (after an observed stockout), predictive-point and predictive-probabilistic (ours), plus the inferred operator moves, which must first reproduce observed inventories ("), ital("R"), run("2", { superScript: true }), run(" > 0.8). Metrics: unmet rentals, empty station-minutes, truck-km.")]),
  bodyB("The simulator, the greedy step and the four policy comparisons are implemented; the 2-opt / simulated-annealing improvement is not yet, so every policy below uses the greedy step alone. The operator-move check passed with R² = 0.984 (Sec. 3.3)."),
  h3("2.6.1. Replay simulator (replay_sim.py)"),
  body([nb("Each day runs from 06:00 to 23:00 from the 06:00 snapshot. Recorded rentals at the 144 stations are placed uniformly at random within their recorded hour (seeded); a served rental generates the return of that ride after its recorded duration, an unserved one disappears, and rides from outside the area arrive as recorded. A full station redirects a return to the nearest station with a free dock. Trucks: "), nbi("K"), nb(" ∈ {1, 3, 6}, capacity 20, 15 km/h on 1.3× straight-line distance, 3 min per stop and 6 s per bike. Outputs per day: unmet rentals, empty station-minutes (counted every 10 min), bikes moved, truck-km.")]),
  h3("2.6.2. Greedy planner and the three policies"),
  body([nb("Every 10 minutes each idle truck receives one move chosen by Algorithm 1. Candidate targets, their need and the weight "), nbi("v"), nb(" differ by policy:")], { keepNext: true }),
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
  bodyB("The operator reference injects the inferred hourly moves of Sec. 2.3 directly, without truck constraints. The route search with 2-opt and simulated annealing [16] is the next step; Algorithm 1 is its initial solution."),

  h2("2.7. Live demo", true),
  bodyB("The logger already writes latest.json, a compact snapshot of the 309 stations, on every run. The demo page will read it, compute the inventory-only features, show P(empty within 30 min) per station on a map and the next-bell truck plan of the planner, as mocked in Fig. 15."),

  // ===================== EXPERIMENTS =====================
  h1("3. Experiments", true),
  h2("3.1. Datasets, splits and environment", true),
  bodyB("Table 2 lists the data. NTU rows are split by time: training 1 Sep 2024–9 Mar 2025, validation 10–31 Mar 2025 (early stopping), test 1 Apr–22 Jun 2025 (1.22 M station-slots never seen by the model). NSYSU uses 2–7 Oct for training, 8–9 Oct for validation and 10–15 Oct for testing; the timetable test leaves out one teaching day of 2–16 Oct at a time. The replay simulator uses the 28 in-semester weekdays of the test period with ≥ 95% snapshot coverage. On a 2-vCPU, 7 GB container (Python 3.11, LightGBM 4.7) every experiment runs in under 20 min; one simulated day takes about 3 s. All random steps use fixed seeds."),
  tableCaption("Table 2. ", "Data used in this report."),
  table([1500, 1877, 1300], ["Source", "Coverage / resolution", "Rows used"], [
    ["Taipei YouBike 2.0 trip records [1]", "Sep 2024–Jun 2025, hourly, 1,519 stations", "10.2 M rides touching the 144 NTU-area stations"],
    ["Taipei inventory snapshots [2]", "1 Sep 2024–22 Jun 2025 (295 days), 10 min", "2.97 M station records → 6.1 M station-slots"],
    ["NSYSU logger [17]", "1–16 Oct 2026, 10 min, 309 stations ≤ 5 km", "660 k station-slots (15 complete days)"],
    ["Calendars", "period ends of both campuses, holidays, semesters", "bell and off-day features"],
    ["NSYSU course catalogue [27]", "semester 115-1, 2,475 courses, by period", "2,589 weekly class sessions"],
  ], { aligns: [AlignmentType.LEFT, AlignmentType.LEFT, AlignmentType.LEFT] }),
  spacer(),

  h2("3.2. Class-end stockouts at NSYSU", true),
  bodyB("Figs. 5 and 6 summarize the eight teaching weekdays of 2–14 Oct 2026 (9–10 Oct are holidays). Campus and KRT exits are the two ends of a tide: campus stations fill between 08:00 and 10:00 while both KRT exits run empty; after the 12:00 bell the campus loses 93 bikes (55%) in 20 minutes, recovers over lunch, then drains through the 16:00 and 17:00 bells (−68 and −47 bikes within 40 minutes), and within an hour of the 17:00 bell 88% of the remaining campus stock is gone."),
  bodyB("The 246 stockout episodes at campus stations amount to 3.8 per station and day, with a median length of 20 min and a 90th percentile of 60 min; in total the eight campus stations spend 934 station-minutes empty per weekday. The morning has the mirror problem: the engineering and library stations have no free dock in 44% and 25% of 08:00–11:00 slots. On weekends the campus holds 40–130 bikes all day and the pattern disappears, which confirms the timetable as the cause."),
  bodyB("The course catalogue shows which bells matter (Fig. 5, bottom). On weekdays the 12:00 bell releases 3,700–4,600 students and the 16:00 bell 2,400–4,100, against at most 1,600 at any other period end; on Wednesdays no class ends at 17:00. Averaged over weekdays, 12:00, 16:00 and 17:00 are the three largest, the major bells already used by the NSYSU features. Over the 97 daytime bells (09:00–18:00) of the ten teaching days of 2–16 Oct, the bikes leaving the campus stations in the 20 minutes after a bell rise with the number of students released (Spearman ρ = 0.59, Fig. 7), against ρ = 0.33 for the 20 minutes that start half an hour before the same bells. Between weekdays, the size of the same bell relates only weakly to its outflow (ρ = 0.27, p = 0.008)."),
  ...figure("fig_nsysu_tide_a.png", capB("Figure 5. ", "NSYSU, eight teaching weekdays in Oct 2026: bikes at the 8 campus stations and the 2 KRT Sizihwan exits (mean, band = IQR; dashed = weekend campus). Bottom: students whose class ends at each period end, Mon–Fri mean of the 115-1 catalogue [27].")),
  ...figure("fig_nsysu_tide_b.png", capB("Figure 6. ", "Probability that a station is empty, by time of day on teaching weekdays, for the campus stations, the KRT exits and the four busiest gateway stations.")),
  ...figure("fig_bells.png", capB("Figure 7. ", "Students released by each daytime bell against bikes leaving the 8 campus stations in the next 20 min (97 bells, 2–16 Oct 2026); open: windows starting 30 min earlier.")),

  h2("3.3. Demand reconstruction and operator moves at NTU", true),
  bodyB("Reconciliation covers 917 k station-hours (144 stations, 295 days). On hours without inferred moves, trips alone explain inventory changes with R² = 0.87; adding the inferred moves reproduces the next-hour stock with R² = 0.984 (0.63 without them), so the inferred operator policy passes the proposal’s threshold. At the 144 stations the operator drops off about 2,550 and picks up about 2,160 bikes per day, 10% of the 25,700 daily rentals. Fig. 8 shows a reactive pattern: pick-ups from campus peak at 08:00–09:00 after the morning inflow, drop-offs at campus peak at 16:00–17:00, and only 19% of campus drop-offs happen in the hour before a major bell."),
  bodyB("The censoring correction is large where it matters: at campus stations on weekdays, observed rentals understate demand by 8% at 12:00, 17% at 17:00, 39% at 18:00 and 2.1× at 22:00, because campus stations are empty 46% of the time at 17:00–19:00. These corrected rates are the demand input of the planner."),
  bodyB("The checks of Sec. 2.3.1 (Fig. 9) support the inference with one qualification. Conservation: the area loses 600 bikes per day through trips, the flagged moves bring back 394 and the unflagged residual 185, so small top-ups below the threshold are missed and the 2,550 drop-offs are a lower bound. Sensitivity: across thresholds of 3–8 bikes and windows of 1–6 h the drop-off volume stays within 2,150–2,975 bikes per day, the share before a major bell within 18–20%, the peak hour at 17:00 and the reproduction R² above 0.977. Jumps: 56% of flagged windows contain a ≥ 8-bike jump in the flagged direction against 8% of unflagged ones. Rates: on 14.6 k well-stocked campus station-hours of the test period, actual rentals are 12% above the naive rate but only 4% above the corrected one. The volume is plausible: 4,700 bike-moves per day is about 240 truck loads of 20, and a press report on the operator’s crews describes over a thousand bikes collecting at riverside stations in a single day and being trucked back overnight [26]."),
  ...figure("fig_ntu_moves.png", capB("Figure 8. ", "Inferred truck moves per hour and day at the 59 campus and 85 ring stations (drop-offs above the axis, pick-ups below); dashed: 12:10 and 17:20 bells.")),
  ...figure("fig_moves_check.png", capB("Figure 9. ", "Checks on the operator inference. (a) Inferred drop-offs per day by threshold and window; dashed: bikes arriving in ≥ 8-bike jumps. (b) Actual rentals over the training-period rate on well-stocked campus station-hours; dashed: 12:10 and 17:20 bells.")),

  h2("3.4. Stockout prediction", true),
  bodyB("Table 3 and Figs. 10–11 give the test results on the 1.09 M test slots whose current stock is observed. At the 30-minute horizon the full model reaches AUC 0.932 and Brier 0.080, against 0.819 / 0.126 for the seasonal baseline and 0.744 / 0.124 for persistence; the inventory-only model is close behind (0.922 / 0.084), so trip flows add little once the current stock and its trend are known, at this horizon. Calibration is good without post-processing: ECE 0.012 and a reliability curve on the diagonal up to p = 0.9 (Fig. 10a), while the seasonal baseline under-predicts at high probabilities. The day-level bootstrap gives half-widths of about 0.005 AUC for the GBMs, and every paired difference has an interval that excludes zero: full against inventory-only +0.010 [0.009, 0.011], inventory-only against logistic +0.007 [0.006, 0.007] and against the corrected roll-out +0.027 [0.025, 0.029]."),
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
  ...figure("fig_model.png", capB("Figure 10. ", "(a) Reliability of the 30-minute predictions on the NTU test months. (b) AUC on all stations, campus stations, and campus slots within 40 min after a major bell.")),
  bodyB("Every model loses accuracy as the horizon grows, at different rates (Fig. 11): from 30 to 120 min the full GBM falls from 0.932 to 0.899, the inventory-only GBM to 0.871, the logistic model to 0.849, the steepest fall, and the roll-out to 0.857, while the seasonal baseline stays near 0.81. For a two-hour view the recent trip flows are worth 0.028 AUC, three times their value at 30 min, and the roll-out overtakes the linear model. For a pre-bell plan made 60–90 minutes ahead the full model keeps AUC ≥ 0.90 and ECE ≤ 0.014."),
  ...figure("fig_horizon.png", capB("Figure 11. ", "Ranking (a) and probability quality (b) by horizon on the NTU test months, all 144 stations; bands: 95% day-bootstrap intervals for the full GBM and the calibrated roll-out.")),
  bodyB("By gain, the current stock (49%), its one-hour minimum (20%), the station id (8%) and the fill ratio (5%) dominate the 30-minute full model. The bell features contribute almost nothing: the ablation without group B changes AUC by at most 0.002 on every subset, including campus slots 0–30 min before a bell, because hour of day already encodes a fixed timetable. The hard cases are stations that are still well stocked 30 minutes before a bell (AUC 0.79 at h = 30); Sec. 3.5 tests whether the course catalogue helps there."),

  h2("3.5. Transfer to NSYSU", true),
  bodyB("Fig. 12(a) shows that the inventory-only NTU model works at NSYSU without any local data: zero-shot AUC 0.934 on all 309 Kaohsiung stations and 0.943 on the 8 campus stations at h = 30, with Brier 0.049 / 0.068 and ECE 0.023 / 0.019. Fine-tuning on six NSYSU days adds 0.006 [0.005, 0.007] AUC and improves ECE to 0.003 on all stations; a model trained only on those six days is equally good (0.940), while the seasonal baseline from six days is poor (0.651). The proposal expected a zero-shot drop that local data would close; instead the dynamics of a station emptying generalize across cities almost perfectly, and the only transfer gap is in calibration, which six days of local data remove. At h = 60 the figures are 0.894 zero-shot and 0.906 fine-tuned. On campus the three learned models differ by at most 0.003, against station-day intervals of about ±0.010."),
  body([nbb("Timetable intensity. "), nb("Tested on each teaching day after training on the other fourteen days, the local inventory-only model reaches AUC 0.941 on all stations and 0.947 on campus at h = 30, 0.010 [0.009, 0.011] above zero-shot (0.021 at h = 60). The five catalogue features (Fig. 12b) change AUC by at most 0.001 on all and on campus stations and take 1% of the split gain. For the hard case of Sec. 3.4, campus stations still holding ≥ 5 bikes 30 min before a bell (2.2 k slots, 103 stockouts), AUC moves from 0.881 to 0.886 at h = 30 and from 0.888 to 0.895 at h = 60, with intervals that include zero, and training on 2–11 Oct to test on 12–16 Oct gives effects of opposite sign at the two horizons. In the leave-one-day-out test the only significant effect is a lower Brier score at the gateway stations (−0.0008 [−0.0012, −0.0005]). Hour, weekday and bell times already encode a timetable that repeats every week; the catalogue should matter when the timetable changes, as it will next semester.")]),
  ...figure("fig_nsysu.png", capB("Figure 12. ", "NSYSU. (a) Test days 10–15 Oct, h = 30 min: AUC with 95% station-day intervals. (b) AUC change from the five catalogue features, leave-one-day-out, 95% day intervals; pre-bell: campus, ≥ 5 bikes, 30 min before a bell; AM: 07:00–10:00.")),

  h2("3.6. Replay simulation", true),
  bodyB("Over the 28 replayed weekdays the area records 32,100 rentals per day; without rebalancing 3,390 of them (10.5%) find an empty station and the 144 stations spend 17,800 station-minutes empty per day. Fig. 13 gives the results per policy. One truck avoids 5–7% of unmet rentals, three trucks 16–17% and six trucks 25–27%. The probabilistic policy is best on every fleet size and the point-forecast policy worst, but the margins on unmet rentals are small. The clearest difference is in empty station-minutes, which the probabilistic and reactive policies cut by 41% with six trucks against 14% for the point policy, because the latter waits for a forecast deficit instead of acting on an empty station. Replaying the inferred operator moves, which inject about 5,100 bikes per day without any truck constraint, avoids 61%; it is an upper reference, not a policy. In paired per-day differences the probabilistic policy beats the point policy by 2.0–2.4 points of unmet rentals with every fleet size (95% intervals exclude zero), but its margin over the reactive policy, 0.0–0.4 points, has intervals that include zero."),
  ...figure("fig_sim_ci.png", capB("Figure 13. ", "Replay of 28 NTU weekdays: share of (a) unmet rentals and (b) empty station-minutes avoided against no rebalancing, with 95% day-bootstrap intervals; trucks drive 55–67, 192–223 and 396–456 km per day with 1, 3 and 6 trucks.")),
  bodyB("The ranking shows that at this stage the forecast is not the bottleneck: Algorithm 1 serves one target per truck at a time, cannot combine a pick-up with several drop-offs, and ignores the deadline structure of the bells. The rolling-horizon route search planned for November attacks exactly this, and the simulator now gives it a fixed benchmark."),

  // ===================== CONCLUSION =====================
  h1("4. Progress, risks and next steps", true),
  bodyB("Table 4 sets the numbers the proposal expected against what the midterm experiments gave. The predictor met every target, and transfer was easier than expected. The simulator numbers fall short of the proposal’s 50%, for three reasons that the next phase addresses: the planner is the greedy initial solution without route search; the replay contains only recorded rentals, so the demand that was lost at empty stations, which rebalancing would serve, is not yet counted; and the operator reference injects bikes without any truck constraint."),
  tableCaption("Table 4. ", "Proposal expectations (HW1, Sec. 3) against midterm results."),
  table([1877, 1300, 1500], ["Quantity", "Expected (HW1)", "Midterm"], [
    ["Predictor AUC, h = 30 min", "> 0.85", "0.93 (NTU), 0.93 (NSYSU zero-shot); 0.90 at 120 min"],
    ["Poisson + Monte-Carlo roll-out", "the predictor of Sec. 2.4", "built exactly; AUC 0.895, so the classifier (0.922–0.932) is used"],
    ["Predictor ECE, h = 30 min", "< 0.05", "0.012 (NTU), 0.023 (NSYSU zero-shot)"],
    ["NSYSU transfer", "zero-shot drop, closed within 5 AUC points after 2–4 weeks", "no drop: 0.934 zero-shot vs. 0.940 with 6 local days"],
    ["Unmet rentals avoided, reactive", "about 20%", "7% / 17% / 26% with 1 / 3 / 6 trucks"],
    ["Unmet rentals avoided, point forecast", "about 40%", "5% / 16% / 25%"],
    ["Unmet rentals avoided, probabilistic", "about 50%", "7% / 17% / 27%; operator replay 61%"],
  ], { aligns: [AlignmentType.LEFT, AlignmentType.LEFT, AlignmentType.LEFT] }),
  spacer(),
  bodyB("Fig. 14 updates the schedule: data pipeline and demand reconstruction are complete, the predictor is trained and transferred ahead of plan, and the simulator exists two weeks early with the planner still greedy. None of the proposal’s three fallbacks was needed. Remaining work:"),
  bullet("the rolling-horizon planner with 2-opt / simulated annealing and multi-stop routes, evaluated in the same simulator;"),
  bullet("a two-sided (empty / full) label for the pre-bell cases where the predictor is weakest;"),
  bullet("imputing the censored demand of Sec. 3.3 into the replay, so that unmet rentals include riders who never found a bike;"),
  bullet("the live NSYSU demo (Fig. 15) and, after four more weeks of logging, a transfer study by week of local data.", { last: true }),
  ...figure("fig_gantt_hw3.png", capB("Figure 14. ", "Schedule with completion at 29 Oct (dark = done; PL 林沛霆, JC 陳佳晨, SL 林詩穎).")),
  bodyB("Work division: 林沛霆 (PL) built the logger, the NTU pipeline, the replay simulator and this report; 陳佳晨 (JC) owns demand reconstruction, operator inference and its checks, the calibration and transfer studies and the bootstrap; 林詩穎 (SL) owns the predictor, the roll-out comparison, the horizon sweep, the ablations and the demo. All code, tables, model files, metrics and figures are in the public repository [17] under analysis/, with a README that rebuilds every table from the raw sources."),
  ...figure("fig3_demo_mock.png", capNum("Figure 15. ", "Mock-up of the live NSYSU demo (real station positions and stock; probabilities and route illustrative).")),

  h1("References"),
  ...references(),
];

const doc = new Document({
  creator: "NSYSU Group 54",
  title: "Beat the Bell — Midterm Report",
  styles: { default: { document: { run: { font: "Times New Roman", size: 20 } } } },
  sections: [
    { properties: { page: { size: PAGE, margin: MARGIN }, column: { count: 1 } }, children: titleBlock },
    { properties: { type: SectionType.CONTINUOUS, page: { size: PAGE, margin: MARGIN }, column: { count: 2, space: COL_SPACE, equalWidth: true } }, children: placeFigures(main) },
  ],
});
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync("HW3_54.docx", buf); console.log("wrote HW3_54.docx", buf.length); });
