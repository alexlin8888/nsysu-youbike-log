"use strict";
// The scenes of the final video. Each scene is a function (ctx, t, T) of its own time t in seconds (T = its length).
// The narration lines are timed by video/script.py and read from CUES, so an animation can start exactly when the
// narrator starts a sentence: LS(id, k) is the start of line k of scene id, in seconds from the scene start.
// Layout rule: nothing important below y = 930 in the middle of the frame, where the subtitles are burnt in.
window.IMAGES = ["rider_1640.jpg", "rider_1740.jpg", "policy_top.jpg", "policy_table.jpg", "policy_map.jpg", "sim_0.jpg", "sim_50.jpg", "sim_50t.jpg", "brief.jpg"];

function sceneOf(id) { return CUES.scenes.find((s) => s.id === id); }
function linesOf(id) { return CUES.lines.filter((l) => l.scene === id); }
function LS(id, k) { return linesOf(id)[k].start - sceneOf(id).start; }
function LE(id, k) { return linesOf(id)[k].end - sceneOf(id).start; }

// ---------- shared pieces ----------
const CEN = [22.6272, 120.2655];
const KX = Math.cos(CEN[0] * Math.PI / 180);
function proj(lat, lng, scale, cx, cy) { return [cx + (lng - CEN[1]) * KX * scale, cy - (lat - CEN[0]) * scale]; }
const MAP = { scale: 130000, cx: 800, cy: 560 };          // the campus map of the data and idea scenes
function slotAt(m) { const s = DATA.slots; let k = 0; while (k + 1 < s.length && s[k + 1] <= m) k++; return k; }
function slotOf(m) { return DATA.slots.indexOf(m); }
function bg(ctx, a, b) { const g = ctx.createLinearGradient(0, 0, 0, H); g.addColorStop(0, a); g.addColorStop(1, b); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H); }
const NAVY_BG = (ctx) => bg(ctx, "#0E1C2B", "#13283D");
const PAPER_BG = (ctx) => { ctx.fillStyle = C.paper; ctx.fillRect(0, 0, W, H); };
const LIGHT = "#C7D6E6", DIM = "#8FA6BD";
const MATES = [{ hoodie: "#7A8A99", hoodieD: "#66737F", pack: "#B9C4CC", hair: "#3A2E28" }, { hoodie: "#C9705A", hoodieD: "#AE5D49", pack: "#E5C07B", hair: "#232634" }];

// a statement card: a big number with a label and a smaller line beside it, revealed at time a
function statCard(ctx, t, a, x, y, w, num, label, sub, o = {}) {
  const k = easeOut(prog(t, a, a + 0.5)); if (k <= 0) return;
  const h = o.h || 190, ns = o.numSize || 100;
  ctx.save(); ctx.translate(0, (1 - k) * 40); ctx.globalAlpha *= k * (o.alpha == null ? 1 : o.alpha);
  card(ctx, x, y, w, h, { fill: o.fill || "rgba(255,255,255,0.97)", r: 24 });
  text(ctx, num, x + 36, y + h / 2 + ns * 0.34, { size: ns, weight: 900, color: o.numColor || C.orange });
  const lx = x + 66 + textW(ctx, num, ns, 900);
  text(ctx, label, lx, y + h / 2 - 8, { size: o.labelSize || 36, weight: 700, color: C.ink });
  if (sub) text(ctx, sub, lx, y + h / 2 + 44, { size: 28, weight: 400, color: C.ink2 });
  ctx.restore();
}
function headline(ctx, s, x, y, t, a, o = {}) {
  const k = easeOut(prog(t, a, a + 0.45)); if (k <= 0) return;
  text(ctx, s, x, y + (1 - k) * 30, { size: o.size || 64, weight: o.weight || 900, color: o.color || C.ink, align: o.align || "left", alpha: k * (o.alpha == null ? 1 : o.alpha) });
}
function bellIcon(ctx, x, y, s, swing = 0, color = C.yellow) {
  ctx.save(); ctx.translate(x, y); ctx.rotate(swing); ctx.fillStyle = color;
  ctx.beginPath(); ctx.moveTo(-0.5 * s, 0.35 * s); ctx.quadraticCurveTo(-0.45 * s, -0.55 * s, 0, -0.6 * s); ctx.quadraticCurveTo(0.45 * s, -0.55 * s, 0.5 * s, 0.35 * s); ctx.lineTo(0.62 * s, 0.48 * s); ctx.lineTo(-0.62 * s, 0.48 * s); ctx.closePath(); ctx.fill();
  ctx.beginPath(); ctx.arc(0, 0.58 * s, 0.13 * s, 0, 7); ctx.fill(); ctx.beginPath(); ctx.arc(0, -0.68 * s, 0.09 * s, 0, 7); ctx.fill(); ctx.restore();
}
function clockIcon(ctx, x, y, r, color = C.blue) {
  ctx.save(); ctx.strokeStyle = color; ctx.lineWidth = r * 0.16; ctx.beginPath(); ctx.arc(x, y, r, 0, 7); ctx.stroke();
  ctx.lineCap = "round"; ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x, y - r * 0.55); ctx.moveTo(x, y); ctx.lineTo(x + r * 0.42, y + r * 0.2); ctx.stroke(); ctx.restore();
}
function personIcon(ctx, x, y, s, color) {
  if (s <= 0) return;
  ctx.save(); ctx.fillStyle = color; ctx.beginPath(); ctx.arc(x, y - 1.15 * s, 0.32 * s, 0, 7); ctx.fill();
  rrect(ctx, x - 0.42 * s, y - 0.75 * s, 0.84 * s, 0.95 * s, 0.3 * s); ctx.fill(); ctx.restore();
}
function chair(ctx, x, y, s) { ctx.fillStyle = "#59616D"; ctx.fillRect(x - 0.55 * s, y - 0.66 * s, 0.6 * s, 0.08 * s); ctx.fillRect(x - 0.55 * s, y - 0.66 * s, 0.07 * s, 0.66 * s); ctx.fillRect(x - 0.02 * s, y - 0.66 * s, 0.07 * s, 0.66 * s); ctx.fillRect(x - 0.6 * s, y - 1.5 * s, 0.08 * s, 0.9 * s); }
function desk(ctx, x, y, s) { ctx.fillStyle = "#A9805A"; ctx.fillRect(x - 0.1 * s, y - 1.25 * s, 1.5 * s, 0.12 * s); ctx.fillStyle = "#8A6646"; ctx.fillRect(x + 1.2 * s, y - 1.2 * s, 0.1 * s, 1.2 * s); ctx.fillRect(x, y - 1.2 * s, 0.1 * s, 1.2 * s); }

// The campus map: the sea of Sizihwan to the west (a schematic coast) and the eight campus stations at their real
// coordinates, each a dot sized by its docks with the logged count inside.
const COAST = [[22.6420, 120.2560], [22.6330, 120.2602], [22.6305, 120.2614], [22.6283, 120.2612], [22.6262, 120.2603], [22.6244, 120.2622], [22.6232, 120.2648], [22.6205, 120.2667], [22.6120, 120.2640]];
function campusMap(ctx, scale, cx, cy, o = {}) {
  NAVY_BG(ctx);
  const pts = COAST.map((p) => proj(p[0], p[1], scale, cx, cy));
  ctx.save(); ctx.fillStyle = "#16314A"; ctx.beginPath();
  ctx.moveTo(-60, pts[0][1] - 4000); pts.forEach((p) => ctx.lineTo(p[0], p[1])); ctx.lineTo(-60, pts[pts.length - 1][1] + 4000); ctx.closePath(); ctx.fill();
  ctx.strokeStyle = "rgba(120,180,230,0.35)"; ctx.lineWidth = 3; ctx.beginPath(); pts.forEach((p, i) => (i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]))); ctx.stroke();
  ctx.restore();
  const la = o.labelAlpha == null ? 1 : o.labelAlpha;
  if (la > 0) text(ctx, "西子灣", 118, 528, { size: 40, weight: 700, color: "rgba(150,200,240,0.6)", align: "center", alpha: la });
}
const STR = (c) => 20 + Math.sqrt(c.cap) * 3.2;                 // dot radius
const SIDE = { "圖資": "up", "西灣藝廊": "left", "材料大樓": "right", "工學院": "right", "社科院": "left", "體育館": "right", "海工館": "right", "海資館": "right" };
function stationDot(ctx, x, y, r, color, label, o = {}) {
  ctx.save(); ctx.globalAlpha *= o.alpha == null ? 1 : o.alpha;
  ctx.fillStyle = color; ctx.beginPath(); ctx.arc(x, y, r, 0, 7); ctx.fill();
  ctx.lineWidth = 4; ctx.strokeStyle = "#0E1C2B"; ctx.stroke();
  if (o.num != null) text(ctx, String(o.num), x, y + r * 0.36, { size: r * 1.0, weight: 900, color: color === C.yellow || color === "#A9B4FF" ? C.ink : C.white, align: "center" });
  if (label) {
    const side = o.side || "down", st = { size: 32, weight: 700, color: "rgba(255,255,255,0.93)" };
    if (side === "up") text(ctx, label, x, y - r - 14, { ...st, align: "center" });
    else if (side === "left") text(ctx, label, x - r - 12, y + 11, { ...st, align: "right" });
    else if (side === "right") text(ctx, label, x + r + 12, y + 11, { ...st, align: "left" });
    else text(ctx, label, x, y + r + 40, { ...st, align: "center" });
  }
  ctx.restore();
}
const bikeColor = (n) => (n == null ? C.muted : n === 0 ? C.red : n < 5 ? C.yellow : C.green);
const dockColor = (n) => (n == null ? C.muted : n === 0 ? "#6E7BFF" : n < 5 ? "#A9B4FF" : C.green);
function gauge(ctx, x, y, r, v) {
  ctx.save();
  ctx.fillStyle = "rgba(14,28,43,0.85)"; ctx.beginPath(); ctx.arc(x, y, r * 1.32, 0, 7); ctx.fill();
  ctx.lineWidth = r * 0.28; ctx.lineCap = "round";
  ctx.strokeStyle = "rgba(255,255,255,0.18)"; ctx.beginPath(); ctx.arc(x, y, r, Math.PI * 0.75, Math.PI * 2.25); ctx.stroke();
  ctx.strokeStyle = v >= 0.5 ? C.orange : "#7FB3E8"; ctx.beginPath(); ctx.arc(x, y, r, Math.PI * 0.75, Math.PI * (0.75 + 1.5 * clamp(v)) + 1e-3); ctx.stroke();
  const ta = Math.PI * 1.5; ctx.strokeStyle = "rgba(255,255,255,0.85)"; ctx.lineWidth = 3;
  ctx.beginPath(); ctx.moveTo(x + Math.cos(ta) * r * 0.7, y + Math.sin(ta) * r * 0.7); ctx.lineTo(x + Math.cos(ta) * r * 1.3, y + Math.sin(ta) * r * 1.3); ctx.stroke();
  text(ctx, Math.round(v * 100) + "%", x, y + r * 0.24, { size: r * 0.6, weight: 900, color: C.white, align: "center" });
  ctx.restore();
}
function badge30(ctx, x, y, s) {
  if (s <= 0) return;
  ctx.save(); ctx.translate(x, y); ctx.scale(s, s);
  ctx.shadowColor = "rgba(0,0,0,0.3)"; ctx.shadowBlur = 12; ctx.shadowOffsetY = 4;
  rrect(ctx, -80, -30, 160, 60, 30); ctx.fillStyle = C.white; ctx.fill(); ctx.shadowColor = "transparent";
  ctx.lineWidth = 4; ctx.strokeStyle = C.blue; ctx.stroke();
  clockIcon(ctx, -46, 0, 15, C.blue);
  text(ctx, "+30分", 14, 12, { size: 32, weight: 900, color: C.blue, align: "center" });
  ctx.restore();
}
// outdoor campus street: sky by phase (0 afternoon, 1 sunset, 2 dusk), mountains, buildings, palms, ground at y = 880
function campusStreet(ctx, t, phase) {
  sky(ctx, phase, 0, 900);
  if (phase > 0.3 && phase < 1.5) sun(ctx, 300, 330 + phase * 120, 55, phase);
  cloud(ctx, 1460 + Math.sin(t * 0.1) * 20, 100, 1.4, 0.7); cloud(ctx, 600, 120, 1, 0.6);
  mountains(ctx, 760, 120, clamp(phase - 0.6));
  const lit = phase > 1.1 ? 0.6 : 0;
  building(ctx, 1180, 880, 420, 330, { lit });
  building(ctx, 1640, 880, 300, 250, { fill: "#E3DACB", lit });
  building(ctx, 760, 880, 360, 210, { fill: "#EDE6DA", lit });
  palm(ctx, 140, 880, 1.25, t); palm(ctx, 1110, 880, 1.05, t + 1);
  ground(ctx, 880);
  ctx.fillStyle = "#C9C2B5"; for (let x = 0; x < W; x += 160) ctx.fillRect(x, 940, 90, 6);
  if (phase > 0.9) { ctx.fillStyle = rgba("#2F3F6B", clamp((phase - 0.9) * 0.4)); ctx.fillRect(0, 0, W, H); }
}
function seaside(ctx, t, phase) {
  sky(ctx, phase, 0, 700); sun(ctx, 1480, 580, 72, 1); sea(ctx, 610, 830, t, 0.6);
  ctx.fillStyle = "#3E4A5C"; ctx.fillRect(0, 830, W, 250);
  ctx.fillStyle = "#59616D"; for (let x = 0; x < W; x += 120) ctx.fillRect(x, 800, 10, 60); ctx.fillRect(0, 800, W, 8);
}
// a dark panel that keeps white text readable over a busy background
function panel(ctx, x, y, w, h, a = 1) { card(ctx, x, y, w, h, { fill: "rgba(14,28,43,0.82)", r: 26, alpha: a, shadow: false }); }

// ---------- 1. hook: the 17:00 bell, and an empty station ----------
function sceneHook(ctx, t, T) {
  const tName = LS("hook", 0), tRun = LS("hook", 1), tEmpty = LS("hook", 2);
  const tOut = tRun + 1.5;                 // the wipe to the station
  if (t < tOut) {
    // the classroom, seen from the side: a window onto the sea on the left, the whiteboard on the right
    ctx.fillStyle = C.wall; ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = "#CDBA9A"; ctx.fillRect(0, 860, W, H - 860); ctx.fillStyle = "#B9A585"; ctx.fillRect(0, 860, W, 10);
    ctx.save(); rrect(ctx, 90, 140, 560, 420, 10); ctx.clip(); sky(ctx, 0.45, 140, 560); mountains(ctx, 470, 300, 0); sea(ctx, 430, 560, t, 0.1); ctx.restore();
    ctx.lineWidth = 16; ctx.strokeStyle = "#FFFFFF"; rrect(ctx, 90, 140, 560, 420, 10); ctx.stroke(); ctx.beginPath(); ctx.moveTo(370, 140); ctx.lineTo(370, 560); ctx.stroke();
    card(ctx, 820, 170, 860, 400, { fill: "#FBFBFA", r: 8 }); ctx.lineWidth = 10; ctx.strokeStyle = "#9AA3AD"; rrect(ctx, 820, 170, 860, 400, 8); ctx.stroke();
    ctx.strokeStyle = "#3C6FB0"; ctx.lineWidth = 5; ctx.beginPath(); ctx.moveTo(900, 520); ctx.lineTo(900, 250); ctx.moveTo(900, 520); ctx.lineTo(1300, 520); ctx.stroke();
    ctx.strokeStyle = "#D9483B"; ctx.beginPath(); ctx.moveTo(910, 500); ctx.bezierCurveTo(1000, 480, 1080, 300, 1280, 280); ctx.stroke();
    text(ctx, "P(沒車) = ?", 1350, 330, { size: 46, weight: 700, color: "#3C6FB0" }); text(ctx, "λ  μ", 1390, 420, { size: 46, weight: 700, color: "#3C6FB0" });
    const minutes = 16 * 60 + 59 + prog(t, 0, 0.45);
    clock(ctx, 1770, 130, 62, minutes);
    if (t > 0.45) { const k = prog(t, 0.45, 1.6); if (k < 1) { ctx.save(); ctx.strokeStyle = rgba(C.orange, 1 - k); ctx.lineWidth = 8; ctx.beginPath(); ctx.arc(1770, 130, 70 + 120 * k, 0, 7); ctx.stroke(); ctx.restore(); } }
    pill(ctx, "17:00 下課", 1770, 258, { size: 34, fill: C.orange, scale: pop(t, 0.5), alpha: prog(t, 0.5, 0.6) });
    // two classmates, and 阿哲 in front
    [[300, 0], [1450, 1]].forEach(([x, i]) => {
      const up = t > tRun + 0.4 + i * 0.3, s = 70;
      chair(ctx, x, 860, s); student(ctx, up ? x + (t - tRun - 0.4 - i * 0.3) * 260 : x, 860, s, { pose: up ? "walk" : "sit", t, pal: MATES[i], expr: up ? "happy" : "neutral", shadow: up }); desk(ctx, x + 0.25 * s, 860, s);
    });
    const s = 120, x0 = 720;
    chair(ctx, x0, 860, s);
    if (t < tName + 0.6) { student(ctx, x0, 860, s, { pose: "sit", t, expr: t > 0.6 ? "surprised" : "neutral" }); desk(ctx, x0 + 0.25 * s, 860, s); }
    else if (t < tRun) { desk(ctx, x0 + 0.25 * s, 860, s); student(ctx, x0 - 20, 860, s, { pose: "stand", t, expr: "happy" }); }
    else { desk(ctx, x0 + 0.25 * s, 860, s); const k = t - tRun; student(ctx, x0 - 20 + k * 900 + 300 * k * k, 860, s, { pose: "run", t: t * 1.2, expr: "happy" }); }
    // name tag above him, pointing down
    const nk = fadeIO(t, tName, tRun + 0.6, 0.35);
    if (nk > 0) {
      ctx.save(); ctx.globalAlpha = nk; ctx.translate(0, (1 - nk) * 20);
      card(ctx, 360, 330, 470, 150, { fill: C.navy, r: 22 });
      ctx.fillStyle = C.navy; ctx.beginPath(); ctx.moveTo(660, 478); ctx.lineTo(700, 478); ctx.lineTo(690, 520); ctx.closePath(); ctx.fill();
      text(ctx, "阿哲", 396, 410, { size: 60, weight: 900, color: C.white }); text(ctx, "中山大學資管系", 548, 404, { size: 36, weight: 500, color: LIGHT });
      text(ctx, "虛構角色", 398, 458, { size: 26, weight: 400, color: DIM });
      ctx.restore();
    }
  } else {
    // the station, a few seconds later
    campusStreet(ctx, t, 0.75);
    const light = station(ctx, 1100, 880, 95, { docks: 7, bikes: 0, name: "圖資站", empty: true });
    if (t > tEmpty) { const blink = 0.5 + 0.5 * Math.sin((t - tEmpty) * 10); ctx.save(); ctx.globalAlpha = blink * 0.6; ctx.fillStyle = "#FF5A4A"; for (let k = 0; k < 7; k++) { const [lx, ly] = light(k); ctx.beginPath(); ctx.arc(lx, ly, 18, 0, 7); ctx.fill(); } ctx.restore(); }
    const arrive = tOut + 1.5, s = 115;
    if (t < arrive) { const k = easeOut(prog(t, tOut + 0.1, arrive)); student(ctx, lerp(-150, 860, k), 880, s, { pose: "run", t: t * 1.2, expr: "happy" }); }
    else student(ctx, 860, 880, s, { pose: "stand", t, expr: t > tEmpty - 0.4 ? "sad" : "surprised" });
    [[0.7, 520, 0], [1.4, 360, 1]].forEach(([d, xe, i]) => {
      const a = arrive + d, k = easeOut(prog(t, a - 1.2, a));
      if (t > a - 1.2) student(ctx, lerp(-150, xe, k), 880, 100, { pose: t < a ? "walk" : "stand", t, pal: MATES[i], expr: t > tEmpty ? "sad" : "neutral" });
    });
    if (t > tEmpty - 0.05) { const p = pop(t, tEmpty); ctx.save(); ctx.translate(1530, 470); ctx.scale(p, p); card(ctx, -150, -95, 300, 190, { fill: C.white, r: 30 }); text(ctx, "0", -40, 55, { size: 150, weight: 900, color: C.red, align: "center" }); text(ctx, "台", 70, 45, { size: 64, weight: 900, color: C.ink, align: "center" }); ctx.restore(); }
    if (t > arrive + 0.2 && t < tEmpty) { const p = pop(t, arrive + 0.2); text(ctx, "?", 975, 540, { size: 110 * p, weight: 900, color: C.navy, align: "center" }); }
    sourceTag(ctx, "示意動畫：17:00 下課後的校內站", t, tOut + 0.5, C.ink2);
  }
  wipe(ctx, t, tOut - 0.4, tOut + 0.4);
}

// ---------- 2. title ----------
function sceneTitle(ctx, t, T) {
  NAVY_BG(ctx);
  ctx.save(); ctx.strokeStyle = "rgba(120,170,220,0.12)"; ctx.lineWidth = 3;
  for (let i = 0; i < 9; i++) { ctx.beginPath(); for (let x = 0; x <= W; x += 30) { const y = 760 + i * 36 + Math.sin(x / 140 + t * 1.5 + i) * 10; x ? ctx.lineTo(x, y) : ctx.moveTo(x, y); } ctx.stroke(); }
  ctx.restore();
  const k = easeOut(prog(t, 0.1, 0.8));
  bellIcon(ctx, 600, 420, 90 * k, Math.sin(t * 9) * 0.35 * (1 - prog(t, 0.4, 2.2)));
  text(ctx, "Beat the Bell", 720, 470, { size: 150, weight: 900, color: C.white, alpha: k });
  text(ctx, "搶在下課鐘響前", 726, 580, { size: 66, weight: 700, color: C.yellow, alpha: easeOut(prog(t, 0.6, 1.2)) });
  text(ctx, "中山大學 YouBike 缺車預測與騎乘時數獎勵", 726, 660, { size: 44, weight: 500, color: LIGHT, alpha: easeOut(prog(t, 0.9, 1.5)) });
  text(ctx, "人工智慧導論　第 54 組", 726, 740, { size: 34, weight: 400, color: DIM, alpha: easeOut(prog(t, 1.2, 1.8)) });
  fadeTo(ctx, t, T, 0.3);
}

// ---------- 3. data: 309 stations, the campus empties at 17:00, full racks in the morning ----------
function sceneData(ctx, t, T) {
  const l1 = LS("data", 1), l2 = LS("data", 2), l3 = LS("data", 3);
  const zoom = easeInOut(prog(t, l1 - 1.6, l1 - 0.2));
  const scale = lerp(9800, MAP.scale, zoom), cx = lerp(960, MAP.cx, zoom), cy = MAP.cy;
  campusMap(ctx, scale, cx, cy, { labelAlpha: zoom });
  if (zoom < 1) {
    // every logged station pops in, from the campus outwards
    ctx.save(); ctx.globalAlpha = 1 - zoom;
    let n = 0;
    DATA.all.forEach((p) => {
      const [x, y] = proj(p[0], p[1], scale, cx, cy), d = Math.hypot(p[0] - CEN[0], (p[1] - CEN[1]) * KX);
      const a = 0.3 + 4.4 * d / 0.05, k = prog(t, a, a + 0.4); if (k <= 0) return;
      n++; ctx.fillStyle = rgba("#7FB3E8", 0.85 * k); ctx.beginPath(); ctx.arc(x, y, 7 * k, 0, 7); ctx.fill();
    });
    const ring = (t % 2) / 2; ctx.strokeStyle = rgba("#7FB3E8", 1 - ring); ctx.lineWidth = 5; ctx.beginPath(); ctx.arc(cx, cy, 40 + 520 * ring, 0, 7); ctx.stroke();
    text(ctx, "中山大學", cx - 30, cy + 12, { size: 34, weight: 700, color: C.yellow, align: "right" });
    text(ctx, String(n), 110, 250, { size: 150, weight: 900, color: C.white });
    text(ctx, "個站", 130 + textW(ctx, String(n), 150, 900), 238, { size: 56, weight: 700, color: C.white });
    text(ctx, "中山大學 5 公里內", 114, 330, { size: 40, weight: 500, color: LIGHT });
    text(ctx, "每 10 分鐘記錄一次，10 月 1 日起", 114, 390, { size: 40, weight: 500, color: LIGHT });
    ctx.restore();
  }
  // the campus stations through the evening (or in the morning), with the count logged on 11 Nov
  const morning = t > l3 - 0.2;
  const m = morning ? 9 * 60 + 20 : lerp(16 * 60, 18 * 60, prog(t, l1 + 0.2, l2));       // hold at 18:00 (5 of 8 empty) for "17:30–18:30"
  const k = slotAt(m);
  let zero = 0;
  DATA.campus.forEach((c) => {
    const [x, y] = proj(c.lat, c.lng, scale, cx, cy), v = morning ? c.docks[k] : c.bikes[k];
    if (v === 0) zero++;
    stationDot(ctx, x, y, STR(c) * (0.3 + 0.7 * zoom), morning ? dockColor(v) : bikeColor(v), zoom > 0.9 ? c.name : "", { alpha: clamp(zoom * 1.5), num: zoom > 0.9 ? v : null, side: SIDE[c.name] });
  });
  if (zoom > 0.95) {
    const ck = prog(zoom, 0.95, 1);
    card(ctx, 1150, 70, 710, 160, { fill: "rgba(255,255,255,0.97)", r: 24, alpha: ck });
    text(ctx, morning ? "11/11（三）早上　空位數" : "11/11（三）傍晚　車數", 1190, 118, { size: 30, weight: 500, color: C.ink2, alpha: ck });
    text(ctx, hhmm(DATA.slots[k]), 1190, 202, { size: 80, weight: 900, color: C.ink, alpha: ck });
    text(ctx, (morning ? "停滿 " : "沒車 ") + zero + " / 8 站", 1820, 200, { size: 44, weight: 900, color: morning ? "#4C5BE0" : C.red, align: "right", alpha: ck });
    const lg = morning ? [["#6E7BFF", "停滿"], ["#A9B4FF", "空位 1–4"], [C.green, "空位 5 以上"]] : [[C.red, "沒車"], [C.yellow, "1–4 台"], [C.green, "5 台以上"]];
    lg.forEach(([c, s], i) => { ctx.save(); ctx.globalAlpha = ck; ctx.fillStyle = c; ctx.beginPath(); ctx.arc(1170 + i * 210, 270, 13, 0, 7); ctx.fill(); ctx.restore(); text(ctx, s, 1194 + i * 210, 281, { size: 28, weight: 500, color: LIGHT, alpha: ck }); });
  }
  if (!morning) {
    const out = 1 - prog(t, l3 - 0.5, l3 - 0.2);
    statCard(ctx, t, l1 + 0.3, 1150, 320, 710, "40%", "17:00–20:00 校內站沒車", "29 個上課日平均", { alpha: out });
    statCard(ctx, t, l2, 1150, 540, 710, "56%", "17:30–18:30 超過一半", "12 個測試日平均", { alpha: out });
  } else {
    statCard(ctx, t, l3 + 0.2, 1150, 320, 710, "28%", "09:00–11:00 停滿", "還不了車，29 個上課日平均", { numColor: "#4C5BE0" });
  }
  sourceTag(ctx, "資料：YouBike 開放資料，本組紀錄器每 10 分鐘記錄；海岸線為示意", t, 0.5, DIM);
  fadeFrom(ctx, t, 0.3);
}

// ---------- 4. app: most stations are empty at once; bikes have to come back before the bell ----------
function sceneApp(ctx, t, T) {
  const l0 = LS("app", 0), l1 = LS("app", 1), l2 = LS("app", 2);
  const out = easeInOut(prog(t, l2 - 0.4, l2 + 0.3));
  if (out < 1) {
    campusStreet(ctx, t, 1.6);
    student(ctx, 330, 880, 125, { pose: "phone", t, expr: "sad" });
    const img = IMG["rider_1740.jpg"], R = RECTS["rider_1740"];
    const ph = phone(ctx, 560, 60, 420, img), s = ph.w / img.width, P = (r) => [ph.x + r[0] * s, ph.y + r[1] * s, r[2] * s, r[3] * s];
    R.glyphs.filter((g) => g.text.startsWith("0")).forEach((g, i) => {
      const k = prog(t, l0 + 0.8 + i * 0.22, l0 + 1.2 + i * 0.22); if (k <= 0) return;
      const q = P(g.rect), pulse = 0.5 + 0.5 * Math.sin(t * 6 + i);
      ctx.save(); ctx.strokeStyle = rgba("#FF5A4A", 0.95 * k); ctx.lineWidth = 5; ctx.beginPath(); ctx.arc(q[0] + q[2] / 2, q[1] + q[3] / 2, q[2] * 0.6 + 6 * pulse, 0, 7); ctx.stroke(); ctx.restore();
    });
    hilite(ctx, ...P(R.tip), t, l1 + 0.2, C.yellow);
    const pk = easeOut(prog(t, l0 + 0.6, l0 + 1.1));
    panel(ctx, 1040, 200, 820, 470, pk);
    headline(ctx, "17:40", 1090, 320, t, l0 + 0.8, { size: 96, color: C.white });
    headline(ctx, "校內 8 站有 5 站是 0", 1090, 410, t, l0 + 1.2, { size: 54, color: C.white });
    headline(ctx, "App 只能叫你", 1090, 530, t, l1, { size: 50, color: C.yellow });
    headline(ctx, "走 9 分鐘到海資館借", 1090, 610, t, l1 + 0.3, { size: 50, color: C.yellow });
    sourceTag(ctx, "畫面：本組網站的借車分頁，重播 11/11（三）17:40", t, l0 + 0.5, LIGHT);
  }
  if (out > 0) {
    // the way out: bikes have to be back on campus before 17:00
    ctx.save(); ctx.globalAlpha = out; PAPER_BG(ctx); ctx.restore();
    ctx.save(); ctx.globalAlpha = out;
    text(ctx, "車必須在下課前回到校內", 960, 250, { size: 72, weight: 900, color: C.ink, align: "center" });
    const x0 = 260, x1 = 1660, y = 600, m0 = 14 * 60, m1 = 20 * 60, X = (m) => lerp(x0, x1, (m - m0) / (m1 - m0));
    ctx.fillStyle = rgba(C.blue, 0.14); ctx.fillRect(X(15 * 60), y - 46, X(17 * 60) - X(15 * 60), 92);
    ctx.fillStyle = rgba(C.red, 0.12); ctx.fillRect(X(17 * 60), y - 46, X(19 * 60) - X(17 * 60), 92);
    ctx.strokeStyle = C.ink2; ctx.lineWidth = 6; ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(x1, y); ctx.stroke();
    [14, 15, 16, 17, 18, 19, 20].forEach((hh) => { ctx.fillStyle = C.ink2; ctx.fillRect(X(hh * 60) - 2, y - 12, 4, 24); text(ctx, hh + ":00", X(hh * 60), y + 60, { size: 30, weight: 500, color: C.ink2, align: "center" }); });
    bellIcon(ctx, X(17 * 60), y - 90, 34, Math.sin(t * 8) * 0.25, C.orange);
    text(ctx, "下課", X(17 * 60), y - 145, { size: 32, weight: 700, color: C.orange, align: "center" });
    text(ctx, "車要在這段時間回來", (X(15 * 60) + X(17 * 60)) / 2, y + 140, { size: 38, weight: 700, color: C.blue, align: "center" });
    text(ctx, "大家要借車", (X(17 * 60) + X(19 * 60)) / 2, y + 140, { size: 38, weight: 700, color: C.red, align: "center" });
    for (let i = 0; i < 4; i++) { const kk = prog(t, l2 + 0.4 + i * 0.35, l2 + 1.5 + i * 0.35); if (kk > 0) { ctx.save(); ctx.translate(lerp(X(15 * 60) - 160, X(15 * 60 + 5 + i * 28), easeOut(kk)), y - 6); bike(ctx, 0, 0, 34, { color: "#FFFFFF", accent: C.blue }); ctx.restore(); } }
    ctx.restore();
  }
  fadeFrom(ctx, t, 0.3);
}

// ---------- 5. timing: most returns arrive before 17:00, and today's reward pays 3% of them ----------
function sceneTiming(ctx, t, T) {
  const l1 = LS("timing", 1), l2 = LS("timing", 2), l3 = LS("timing", 3);
  PAPER_BG(ctx);
  text(ctx, "每半小時還到校內 8 站的車", 140, 150, { size: 56, weight: 900, color: C.ink });
  text(ctx, "12 個測試日平均，模型估計（台／天）", 140, 205, { size: 32, weight: 400, color: C.ink2 });
  const rows = DATA.timing, x0 = 180, x1 = 1760, y0 = 830, top = 330, n = rows.length, step = (x1 - x0) / n, bw = step * 0.72;
  const Y = (v) => y0 - (y0 - top) * v / 50;
  ctx.strokeStyle = C.line; ctx.lineWidth = 2; [25, 50].forEach((g) => { ctx.beginPath(); ctx.moveTo(x0 - 20, Y(g)); ctx.lineTo(x1, Y(g)); ctx.stroke(); text(ctx, String(g), x0 - 34, Y(g) + 10, { size: 26, color: C.muted, align: "right" }); });
  const paidK = easeOut(prog(t, l2 + 0.2, l2 + 1.0)), glow = prog(t, l3 + 0.2, l3 + 0.6);
  rows.forEach((r, i) => {
    const k = easeOut(prog(t, 0.4 + i * 0.12, 1.0 + i * 0.12)); if (k <= 0) return;
    const x = x0 + i * step + (step - bw) / 2, ret = r[2] * k, paid = r[3];
    const pre = i < 6;
    ctx.fillStyle = pre && t > l1 ? mix(C.grey, "#9DB8D6", prog(t, l1, l1 + 0.5)) : C.grey;
    rrect(ctx, x, Y(ret), bw, y0 - Y(ret), 6); ctx.fill();
    if (paidK > 0 && paid > 0.05) {
      ctx.fillStyle = C.ink2; rrect(ctx, x, Y(paid * paidK), bw, y0 - Y(paid * paidK), 4); ctx.fill();
      if (pre && glow > 0) { ctx.save(); ctx.strokeStyle = rgba(C.orange, glow); ctx.lineWidth = 5; rrect(ctx, x - 5, Y(paid) - 5, bw + 10, y0 - Y(paid) + 5, 6); ctx.stroke(); ctx.restore(); }
    }
    if (r[0].endsWith(":00")) text(ctx, r[0], x + bw / 2, y0 + 46, { size: 30, weight: 500, color: C.ink2, align: "center" });
  });
  const xb = x0 + 6 * step;
  ctx.save(); ctx.globalAlpha = prog(t, 1.2, 1.6); ctx.strokeStyle = C.ink; ctx.lineWidth = 4; ctx.setLineDash([12, 10]); ctx.beginPath(); ctx.moveTo(xb, top - 40); ctx.lineTo(xb, y0); ctx.stroke(); ctx.setLineDash([]);
  text(ctx, "17:00 下課", xb + 16, top - 12, { size: 32, weight: 700, color: C.ink }); ctx.restore();
  if (t > l1 + 0.6) {
    const k = easeOut(prog(t, l1 + 0.6, l1 + 1.3));
    ctx.save(); ctx.globalAlpha = k; ctx.strokeStyle = C.blue; ctx.lineWidth = 6;
    ctx.beginPath(); ctx.moveTo(x0 + 10, top - 22); ctx.lineTo(x0 + 10, top - 42); ctx.lineTo(xb - 20, top - 42); ctx.lineTo(xb - 20, top - 22); ctx.stroke(); ctx.restore();
    pill(ctx, "69% 在 17:00 前就到了", (x0 + xb) / 2, top - 84, { size: 38, fill: C.blue, scale: pop(t, l1 + 0.7), alpha: k });
  }
  // the rule card, then the 3% card, in the empty space above the evening bars
  const rk = easeOut(prog(t, l2 + 0.5, l2 + 1.0)) * (1 - prog(t, l3, l3 + 0.3));
  if (rk > 0) {
    card(ctx, 1040, 330, 760, 200, { fill: C.white, r: 24, alpha: rk });
    ctx.save(); ctx.globalAlpha = rk; ctx.fillStyle = C.ink2; rrect(ctx, 1080, 378, 40, 40, 8); ctx.fill(); ctx.restore();
    text(ctx, "現行友愛接力付的車", 1140, 410, { size: 40, weight: 900, color: C.ink, alpha: rk });
    text(ctx, "站空了才送 5 元：八成以上", 1080, 470, { size: 32, weight: 500, color: C.ink2, alpha: rk });
    text(ctx, "付在 17:00 以後", 1080, 512, { size: 32, weight: 500, color: C.ink2, alpha: rk });
  }
  if (t > l3) {
    const p = pop(t, l3 + 0.2);
    ctx.save(); ctx.translate(1420, 430); ctx.scale(p, p);
    card(ctx, -380, -110, 760, 220, { fill: C.white, r: 28 });
    text(ctx, "3%", -230, 52, { size: 150, weight: 900, color: C.orange, align: "center" });
    text(ctx, "17:00 前到的車", 110, -8, { size: 40, weight: 700, color: C.ink, align: "center" }); text(ctx, "拿到獎勵", 110, 52, { size: 40, weight: 700, color: C.ink, align: "center" });
    ctx.restore();
  }
  sourceTag(ctx, "來源：本組分析（報告 3.10 節）；友愛接力規則：中央社 2026-06-24", t, 0.5);
  fadeFrom(ctx, t, 0.3, C.paper);
}

// ---------- 6. sitting all day; nearly half of adults under 150 minutes a week; cycling to class counts ----------
function sceneSitting(ctx, t, T) {
  const l1 = LS("sitting", 1), l2 = LS("sitting", 2);
  PAPER_BG(ctx);
  const up = easeInOut(prog(t, l1 - 0.6, l1 + 0.2));
  [["上課", "08:10", "#F1ECE3"], ["圖書館", "13:20", "#E8EEF4"], ["宿舍", "22:40", "#EDE7F2"]].forEach(([lab, hm, bgc], i) => {
    const k = easeOut(prog(t, 0.2 + i * 0.7, 0.8 + i * 0.7)); if (k <= 0 || up >= 1) return;
    const w = 560, h = 620, x = 90 + i * 590, y = lerp(190, -760, up) + (1 - k) * 60, fy = y + h - 120;
    ctx.save(); ctx.globalAlpha = k; card(ctx, x, y, w, h, { fill: bgc, r: 26 });
    ctx.save(); rrect(ctx, x, y, w, h, 26); ctx.clip();
    ctx.fillStyle = "#D7CDBD"; ctx.fillRect(x, fy, w, 120);
    if (i === 0) { ctx.fillStyle = "#FBFBFA"; rrect(ctx, x + 300, y + 90, 220, 150, 8); ctx.fill(); ctx.strokeStyle = "#9AA3AD"; ctx.lineWidth = 6; ctx.stroke(); }
    if (i === 1) { for (let r = 0; r < 3; r++) for (let c = 0; c < 5; c++) { ctx.fillStyle = ["#C46A4A", "#4A7FB0", "#E2B04A", "#6E9C6B"][(r + c) % 4]; ctx.fillRect(x + 300 + c * 36, y + 100 + r * 90, 26, 70); } ctx.fillStyle = "#A9805A"; for (let r = 0; r < 3; r++) ctx.fillRect(x + 290, y + 170 + r * 90, 200, 8); }
    if (i === 2) { ctx.fillStyle = "#2F3F6B"; rrect(ctx, x + 330, y + 90, 170, 140, 10); ctx.fill(); ctx.fillStyle = "#F6E7A7"; ctx.beginPath(); ctx.arc(x + 450, y + 135, 22, 0, 7); ctx.fill(); }
    const sx = x + 220, s = 105;
    chair(ctx, sx, fy, s);
    student(ctx, sx, fy, s, { pose: "sit", t, expr: "neutral", phonePose: i === 2 });
    if (i < 2) desk(ctx, sx + 0.25 * s, fy, s);
    if (i === 1) { ctx.fillStyle = "#3A4250"; rrect(ctx, sx + 0.55 * s, fy - 1.72 * s, 0.85 * s, 0.48 * s, 6); ctx.fill(); }
    ctx.restore();
    text(ctx, lab, x + 34, y + 70, { size: 40, weight: 900, color: C.ink });
    pill(ctx, "坐著　" + hm, x + w - 110, y + 58, { size: 28, fill: C.ink2 });
    ctx.restore();
  });
  if (t > l1 - 0.4) {
    const k = easeOut(prog(t, l1 - 0.2, l1 + 0.5));
    ctx.save(); ctx.globalAlpha = k;
    text(ctx, "近五成國人", 140, 250, { size: 100, weight: 900, color: C.orange });
    text(ctx, "每週身體活動不到 150 分鐘", 140, 335, { size: 54, weight: 700, color: C.ink });
    for (let i = 0; i < 10; i++) personIcon(ctx, 220 + i * 150, 600, 82 * pop(t, l1 + 0.4 + i * 0.12), i < 5 ? C.orange : "#B9C4CC");
    text(ctx, "資料：國民健康署調查，公視新聞網 2020-06-11", 140, 680, { size: 28, weight: 400, color: C.ink2 });
    ctx.restore();
  }
  if (t > l2 - 0.2) {
    const k = easeOut(prog(t, l2, l2 + 0.6));
    ctx.save(); ctx.globalAlpha = k; ctx.translate(0, (1 - k) * 40);
    card(ctx, 140, 720, 1640, 190, { fill: C.navy, r: 28 });
    ctx.save(); ctx.translate(290, 893); rider(ctx, 0, 0, 50, { t, expr: "happy" }); ctx.restore();
    text(ctx, "騎腳踏車通勤也算運動", 440, 800, { size: 52, weight: 900, color: C.white });
    text(ctx, "世界衛生組織建議每週 150–300 分鐘中等強度身體活動，騎車代步算在內", 442, 858, { size: 30, weight: 500, color: LIGHT });
    text(ctx, "WHO 2020 身體活動指引", 1750, 790, { size: 24, weight: 400, color: DIM, align: "right" });
    ctx.restore();
  }
  fadeFrom(ctx, t, 0.3, C.paper);
}

// ---------- 7. idea: predict, pay before the bell, pay in ride time ----------
const WATCH = { "海資館": { g: [-150, 0], b: [0, 100] }, "材料大樓": { g: [20, -135], b: [0, -100] }, "體育館": { g: [-170, 10], b: [-170, 0] } };
// the map shows the 16:20 forecast, then the model's next run (16:30) arrives at tSnap and the gauges move to it
const ideaSnap = () => LS("idea", 1) + 2.4;
function ideaClock(t) { return t < ideaSnap() ? 16 * 60 + 20 : 16 * 60 + 30; }
function ideaChance(c, t) { const k = slotOf(16 * 60 + 20); return lerp(c.empty40[k] || 0, c.empty40[k + 1] || 0, easeInOut(prog(t, ideaSnap(), ideaSnap() + 0.9))); }
function crossAt(c) {
  const t0 = LS("idea", 1) + 0.6;
  for (let s = 0; s <= 900; s++) { const tt = t0 + s * 0.01; if (ideaChance(c, tt) >= 0.5) return tt; }
  return 999;
}
function sceneIdea(ctx, t, T) {
  const l0 = LS("idea", 0), l1 = LS("idea", 1), l2 = LS("idea", 2), l3 = LS("idea", 3), l4 = LS("idea", 4);
  if (t < l3 - 0.3) {
    // the campus map, 16:20 -> 16:30 on 11 Nov, with each watched station's chance of running empty within 40 min
    campusMap(ctx, MAP.scale, MAP.cx, MAP.cy);
    const m = ideaClock(t), k = slotAt(m), gk = prog(t, l1 + 0.1, l1 + 0.5), snap = prog(t, ideaSnap(), ideaSnap() + 0.7);
    DATA.campus.forEach((c) => {
      const [x, y] = proj(c.lat, c.lng, MAP.scale, MAP.cx, MAP.cy), v = c.bikes[k];
      const wch = WATCH[c.name];
      if (wch && gk > 0) {
        const gx = x + wch.g[0], gy = y + wch.g[1];
        ctx.save(); ctx.globalAlpha = gk; ctx.strokeStyle = "rgba(255,255,255,0.45)"; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(gx, gy); ctx.stroke(); gauge(ctx, gx, gy, 50, ideaChance(c, t)); ctx.restore();
      }
      stationDot(ctx, x, y, STR(c), bikeColor(v), c.name, { num: v, side: SIDE[c.name] });
    });
    Object.keys(WATCH).forEach((name) => {
      const c = DATA.campus.find((d) => d.name === name), [x, y] = proj(c.lat, c.lng, MAP.scale, MAP.cx, MAP.cy), w = WATCH[name];
      badge30(ctx, x + w.g[0] + w.b[0], y + w.g[1] + w.b[1], pop(t, crossAt(c)));
    });
    const tk = easeOut(prog(t, l0, l0 + 0.5));
    card(ctx, 1150, 70, 710, 250, { fill: "rgba(255,255,255,0.97)", r: 24, alpha: tk });
    pill(ctx, "提案", 1225, 126, { size: 30, fill: C.orange, alpha: tk });
    text(ctx, "預測型友愛接力", 1290, 144, { size: 54, weight: 900, color: C.ink, alpha: tk });
    const sk = easeOut(prog(t, l1, l1 + 0.5));
    text(ctx, "每 10 分鐘預測一次", 1190, 222, { size: 34, weight: 700, color: C.ink, alpha: sk });
    text(ctx, "40 分鐘內借空機率 ≥ 50%，就開放還車獎勵", 1190, 276, { size: 30, weight: 500, color: C.ink2, alpha: sk });
    card(ctx, 1150, 350, 710, 140, { fill: "rgba(255,255,255,0.97)", r: 24, alpha: tk });
    text(ctx, "11/11（三）", 1190, 452, { size: 32, weight: 500, color: C.ink2, alpha: tk });
    text(ctx, hhmm(m), 1820, 452, { size: 80, weight: 900, color: C.ink, align: "right", alpha: tk });
    if (snap > 0 && snap < 1) { ctx.save(); ctx.strokeStyle = rgba(C.orange, 1 - snap); ctx.lineWidth = 6; rrect(ctx, 1150 - 14 * snap, 350 - 14 * snap, 710 + 28 * snap, 140 + 28 * snap, 30); ctx.stroke(); ctx.restore(); }
    text(ctx, t < ideaSnap() ? "模型這一輪的預測" : "下一輪預測，10 分鐘後", 1190, 390, { size: 26, weight: 500, color: C.muted, alpha: tk });
    if (t > l2) pill(ctx, "17:00 下課前就開放", 1505, 570, { size: 38, fill: C.blue, scale: pop(t, l2 + 0.2) });
    sourceTag(ctx, "11/11 的實際預測（網站重播資料的 reward 欄位）；海岸線為示意", t, l1, DIM);
    wipe(ctx, t, l3 - 0.7, l3 + 0.1);
    fadeFrom(ctx, t, 0.3);
    return;
  }
  if (t < l4 - 0.1) {
    // cash out, ride time in
    PAPER_BG(ctx);
    const k = easeOut(prog(t, l3, l3 + 0.5));
    text(ctx, "不送現金，送騎乘時數", 960, 190, { size: 66, weight: 900, color: C.ink, align: "center", alpha: easeOut(prog(t, l3 + 0.2, l3 + 0.7)) });
    ctx.save(); ctx.translate(560, 500); ctx.scale(k, k);
    ctx.fillStyle = "#E8B83A"; ctx.beginPath(); ctx.arc(0, 0, 170, 0, 7); ctx.fill(); ctx.fillStyle = "#F6CF5C"; ctx.beginPath(); ctx.arc(0, 0, 140, 0, 7); ctx.fill();
    text(ctx, "5 元", 0, 32, { size: 96, weight: 900, color: "#9A6B12", align: "center" });
    const sk = easeOut(prog(t, l3 + 0.9, l3 + 1.3)); if (sk > 0) { ctx.strokeStyle = C.red; ctx.lineWidth = 22; ctx.lineCap = "round"; ctx.beginPath(); ctx.moveTo(-150, -150); ctx.lineTo(-150 + 300 * sk, -150 + 300 * sk); ctx.stroke(); }
    ctx.restore();
    text(ctx, "現金", 560, 750, { size: 46, weight: 700, color: C.ink2, align: "center", alpha: k });
    const ak = easeOut(prog(t, l3 + 1.4, l3 + 1.9));
    ctx.save(); ctx.globalAlpha = ak; ctx.strokeStyle = C.ink; ctx.lineWidth = 10; ctx.lineCap = "round"; ctx.lineJoin = "round"; ctx.beginPath(); ctx.moveTo(820, 500); ctx.lineTo(1040, 500); ctx.moveTo(1000, 460); ctx.lineTo(1040, 500); ctx.lineTo(1000, 540); ctx.stroke(); ctx.restore();
    const bk = pop(t, l3 + 1.8);
    if (bk > 0) {
      ctx.save(); ctx.translate(1360, 500); ctx.scale(bk, bk);
      card(ctx, -250, -190, 500, 380, { fill: C.white, r: 40, stroke: C.blue, lw: 8 });
      clockIcon(ctx, 0, -60, 76, C.blue);
      text(ctx, "30 分鐘", 0, 104, { size: 80, weight: 900, color: C.blue, align: "center" });
      text(ctx, "騎乘時數", 0, 160, { size: 42, weight: 700, color: C.ink, align: "center" });
      ctx.restore();
    }
    text(ctx, "30 分鐘＝高雄 YouBike 一個計費時段＝每週建議運動量的五分之一", 960, 820, { size: 36, weight: 500, color: C.ink2, align: "center", alpha: easeOut(prog(t, l3 + 2.4, l3 + 2.9)) });
    fadeFrom(ctx, t - (l3 - 0.3), 0.3, C.navy);
    return;
  }
  // he rides back before the bell and is paid; on the weekend he spends the half hour along the sea
  const tl = t - l4;
  if (tl < 2.6) {
    campusStreet(ctx, t, 0.2);
    const light = station(ctx, 380, 880, 90, { docks: 6, bikes: tl > 1.6 ? 5 : 4, name: "海資館站" }), [bx, by] = light(4);
    badge30(ctx, bx + 40, by - 150, 1);
    const k = easeOut(prog(tl, 0, 1.6));
    if (tl < 1.6) rider(ctx, lerp(1900, 1060, k), 880, 105, { t, face: -1, expr: "happy" });
    else student(ctx, 1040, 880, 110, { pose: "phone", t, face: -1, expr: "happy", screen: C.blue });
    if (tl > 1.7) {
      const nk = easeOut(prog(tl, 1.7, 2.1)), dy = -(1 - nk) * 140;
      card(ctx, 1210, 80 + dy, 620, 150, { fill: C.white, r: 26 }); clockIcon(ctx, 1290, 155 + dy, 34, C.blue);
      text(ctx, "+30 分鐘騎乘時數", 1350, 146 + dy, { size: 42, weight: 900, color: C.blue }); text(ctx, "已存入帳戶　16:32 海資館站", 1350, 196 + dy, { size: 28, weight: 500, color: C.ink2 });
    }
    pill(ctx, "16:32　下課前", 200, 120, { size: 38, fill: C.navy });
    sourceTag(ctx, "示意動畫", t, l4, C.ink2);
  } else {
    seaside(ctx, t, 1.05);
    const k = tl - 2.6;
    rider(ctx, 300 + k * 260, 940, 110, { t, expr: "happy" });
    const ring = clamp(k / 2.4);
    card(ctx, 1240, 90, 600, 200, { fill: "rgba(255,255,255,0.95)", r: 30 });
    ctx.save(); ctx.lineWidth = 22; ctx.lineCap = "round"; ctx.strokeStyle = C.greenL; ctx.beginPath(); ctx.arc(1340, 190, 58, 0, 7); ctx.stroke(); ctx.strokeStyle = C.green; ctx.beginPath(); ctx.arc(1340, 190, 58, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * ring + 1e-3); ctx.stroke(); ctx.restore();
    text(ctx, "週末用掉 30 分鐘", 1430, 175, { size: 40, weight: 900, color: C.ink }); text(ctx, "沿著西子灣多騎一段", 1430, 232, { size: 32, weight: 500, color: C.ink2 });
  }
  wipe(ctx, t, l4 + 2.2, l4 + 3.0);
}

// ---------- 8. method: record, estimate, look ahead; New York and Paris ----------
function sceneMethod(ctx, t, T) {
  const l = [0, 1, 2, 3, 4, 5].map((k) => LS("method", k));
  PAPER_BG(ctx);
  const cardsUp = easeInOut(prog(t, l[3] - 0.4, l[3] + 0.3));
  [["1", "記錄", "每 10 分鐘的車數"], ["2", "估計", "每 10 分鐘借、還的速度"], ["3", "推算", "40 分鐘內借空的機率"]].forEach(([n, h, sub], i) => {
    const k = easeOut(prog(t, 0.2 + i * 0.25, 0.7 + i * 0.25)), act = t < l[3] && i === (t < l[1] ? 0 : t < l[2] ? 1 : 2);
    const x = 90 + i * 590, y = 70 - cardsUp * 400;
    if (y < -260) return;
    card(ctx, x, y + (1 - k) * 40, 560, 170, { fill: act ? C.navy : C.white, r: 26, alpha: k });
    text(ctx, n, x + 50, y + 125, { size: 96, weight: 900, color: act ? C.yellow : C.grey, alpha: k });
    text(ctx, h, x + 140, y + 85, { size: 50, weight: 900, color: act ? C.white : C.ink, alpha: k });
    text(ctx, sub, x + 140, y + 135, { size: 30, weight: 500, color: act ? LIGHT : C.ink2, alpha: k });
  });
  const lib = DATA.campus.find((c) => c.name === "圖資"), eng = DATA.campus.find((c) => c.name === "工學院");
  const gx0 = 190, gx1 = 1750, gy0 = 830, gy1 = 340, below = 1 - cardsUp;
  const axis = (X, hours, a = 1) => { ctx.save(); ctx.globalAlpha *= a; ctx.strokeStyle = C.line; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(gx0, gy0); ctx.lineTo(gx1, gy0); ctx.stroke(); hours.forEach((hh) => text(ctx, hh + ":00", X(hh * 60), gy0 + 46, { size: 28, color: C.ink2, align: "center" })); ctx.restore(); };
  if (below > 0 && t < l[3]) {
    ctx.save(); ctx.globalAlpha = below;
    if (t < l[1]) {
      // step 1: what the logger recorded at the library station on 11 Nov
      const X = (m) => lerp(gx0, gx1, (m - 6 * 60) / (16 * 60)), Y = (v) => lerp(gy0, gy1, v / 25);
      const upto = lerp(6 * 60, 23 * 60, prog(t, 0.6, l[1] - 0.2));
      axis(X, [8, 12, 16, 20]);
      ctx.strokeStyle = C.blue; ctx.lineWidth = 6; ctx.lineJoin = "round"; ctx.beginPath(); let first = true;
      DATA.slots.forEach((m, i) => { if (m > upto) return; const x = X(m), y = Y(lib.bikes[i]); first ? ctx.moveTo(x, y) : ctx.lineTo(x, y); first = false; }); ctx.stroke();
      ctx.fillStyle = C.blue; DATA.slots.forEach((m, i) => { if (m > upto) return; ctx.beginPath(); ctx.arc(X(m), Y(lib.bikes[i]), 5, 0, 7); ctx.fill(); });
      text(ctx, "圖資站的車數，11/11（三）", gx0, gy1 - 30, { size: 34, weight: 700, color: C.ink });
    } else if (t < l[2]) {
      // step 2: rentals and returns per hour at the library, by 10-minute slot
      const X = (s) => lerp(gx0, gx1, (s - 36) / 102), mid = 620, k = easeOut(prog(t, l[1] + 0.2, l[1] + 1.4)), u = 5.2;
      DATA.rates_lib.forEach(([s, lr, lq]) => { const x = X(s); ctx.fillStyle = C.orange; ctx.fillRect(x, mid, 11, lr * u * k); ctx.fillStyle = C.blue; ctx.fillRect(x, mid - lq * u * k, 11, lq * u * k); });
      ctx.strokeStyle = C.ink2; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(gx0, mid); ctx.lineTo(gx1, mid); ctx.stroke();
      [8, 12, 16, 20].forEach((hh) => text(ctx, hh + ":00", X(hh * 6), gy0 + 46, { size: 28, color: C.ink2, align: "center" }));
      text(ctx, "▲ 還車（每小時）", gx0, gy1 - 30, { size: 34, weight: 700, color: C.blue });
      text(ctx, "▼ 借車（每小時）", gx0 + 330, gy1 - 30, { size: 34, weight: 700, color: C.orange });
      text(ctx, "只從車數的變化估出來，不需要騎乘紀錄", gx1, gy1 - 30, { size: 30, weight: 500, color: C.ink2, align: "right" });
      text(ctx, "圖資站，用 10 月 29 日以前的上課日估計", gx1, gy1 + 14, { size: 26, weight: 400, color: C.muted, align: "right" });
    } else {
      // step 3: the chance that 工學院 runs empty within 40 minutes, 15:30 -> 18:00 on 11 Nov; it passes 50% at
      // 16:50 with 11 bikes left and the station runs empty at 17:40
      const X = (m) => lerp(gx0, gx1, (m - 15.5 * 60) / 150), Y = (v) => lerp(gy0, gy1, v);
      const upto = lerp(15.5 * 60, 18 * 60, prog(t, l[2] + 0.2, l[3] - 0.6));
      axis(X, [16, 17, 18]);
      ctx.setLineDash([14, 10]); ctx.strokeStyle = C.orange; ctx.lineWidth = 4; ctx.beginPath(); ctx.moveTo(gx0, Y(0.5)); ctx.lineTo(gx1, Y(0.5)); ctx.stroke(); ctx.setLineDash([]);
      text(ctx, "50%：提前開放獎勵", gx0 + 10, Y(0.5) - 16, { size: 32, weight: 700, color: C.orange });
      ctx.strokeStyle = C.navy; ctx.lineWidth = 7; ctx.lineJoin = "round"; ctx.beginPath(); let first = true;
      DATA.slots.forEach((m, i) => { if (m < 15.5 * 60 || m > upto || eng.empty40[i] == null) return; const x = X(m), y = Y(eng.empty40[i]); first ? ctx.moveTo(x, y) : ctx.lineTo(x, y); first = false; }); ctx.stroke();
      const iC = DATA.slots.findIndex((m, i) => m >= 15.5 * 60 && eng.empty40[i] >= 0.5), iE = DATA.slots.findIndex((m, i) => m > DATA.slots[iC] && eng.bikes[i] === 0);
      if (upto >= DATA.slots[iC]) { const x = X(DATA.slots[iC]), y = Y(eng.empty40[iC]), p = pop(t, l[2] + 0.2 + (DATA.slots[iC] - 15.5 * 60) / 150 * (l[3] - 0.8 - l[2])); ctx.fillStyle = C.orange; ctx.beginPath(); ctx.arc(x, y, 12 * p, 0, 7); ctx.fill(); pill(ctx, hhmm(DATA.slots[iC]) + " 過 50%，還有 " + eng.bikes[iC] + " 台", x - 40, y - 64, { size: 30, fill: C.orange, scale: p }); }
      if (upto >= DATA.slots[iE]) { const x = X(DATA.slots[iE]), p = pop(t, l[2] + 0.2 + (DATA.slots[iE] - 15.5 * 60) / 150 * (l[3] - 0.8 - l[2])); ctx.fillStyle = C.red; ctx.beginPath(); ctx.arc(x, gy0, 14 * p, 0, 7); ctx.fill(); pill(ctx, hhmm(DATA.slots[iE]) + " 借空", x, gy0 - 50, { size: 30, fill: C.red, scale: p }); }
      text(ctx, "工學院站 40 分鐘內借空的機率，11/11（三）", gx0, gy1 - 30, { size: 34, weight: 700, color: C.ink });
    }
    ctx.restore();
  }
  if (t > l[3] - 0.3) {
    const k1 = easeOut(prog(t, l[3], l[3] + 0.6)), k2 = easeOut(prog(t, l[4], l[4] + 0.6)), merge = easeInOut(prog(t, l[5], l[5] + 0.8));
    const hh = lerp(540, 420, merge), y0 = lerp(220, 170, merge), base = lerp(300, 240, merge);
    const at = (x, k, draw) => { if (k <= 0) return; ctx.save(); ctx.globalAlpha = k; ctx.translate(x, y0 + (1 - k) * 60); draw(); ctx.restore(); };
    at(110, k1, () => {
      card(ctx, 0, 0, 800, hh, { fill: C.white, r: 30 });
      [[40, 140, 60], [104, 220, 74], [182, 170, 58], [244, 250, 70], [318, 200, 64], [386, 120, 80]].forEach(([x, h, w]) => {
        const hh2 = h * (base / 300), x2 = x + 40; ctx.fillStyle = "#33465C"; ctx.fillRect(x2, base - hh2, w, hh2);
        ctx.fillStyle = "#F6D58A"; for (let wy = base - hh2 + 14; wy < base - 16; wy += 26) for (let wx = x2 + 10; wx < x2 + w - 14; wx += 20) if (rnd(wx * 7 + wy) > 0.45) ctx.fillRect(wx, wy, 9, 12);
      });
      text(ctx, "紐約 Citi Bike", 40, base + 100, { size: 50, weight: 900, color: C.ink });
      text(ctx, "照各站「接下來」缺多少車給點數", 40, base + 160, { size: 34, weight: 500, color: C.ink2 });
      pill(ctx, "預測", 690, 70, { size: 34, fill: C.blue });
    });
    at(1010, k2, () => {
      card(ctx, 0, 0, 800, hh, { fill: C.white, r: 30 });
      ctx.fillStyle = "#7A9C6E"; ctx.beginPath(); ctx.moveTo(40, base); ctx.quadraticCurveTo(300, base - base * 0.85, 560, base); ctx.closePath(); ctx.fill();
      ctx.save(); ctx.translate(200, base - base * 0.3); ctx.rotate(-0.38); bike(ctx, 0, 0, 34, { color: "#FFFFFF", accent: C.green }); ctx.restore();
      text(ctx, "巴黎 Vélib'", 40, base + 100, { size: 50, weight: 900, color: C.ink });
      text(ctx, "把車騎上坡的站，送 15 分鐘", 40, base + 160, { size: 34, weight: 500, color: C.ink2 });
      pill(ctx, "送時間", 670, 70, { size: 34, fill: C.green });
    });
    if (merge > 0) {
      ctx.save(); ctx.globalAlpha = merge; ctx.translate(0, (1 - merge) * 40);
      card(ctx, 360, 650, 1200, 230, { fill: C.navy, r: 34 });
      bellIcon(ctx, 470, 770, 60, Math.sin(t * 7) * 0.2, C.yellow);
      text(ctx, "用在中山的上下課", 580, 750, { size: 58, weight: 900, color: C.white });
      text(ctx, "預測會空的站，下課前送 30 分鐘騎乘時數", 580, 826, { size: 38, weight: 500, color: LIGHT });
      ctx.restore();
    }
    sourceTag(ctx, "來源：Citi Bike Bike Angels 說明頁；Big Medium 2008-10-17（Vélib' 山上站送 15 分鐘）", t, l[3]);
  }
  fadeFrom(ctx, t, 0.3, C.paper);
}

// ---------- 9. demo: the web app, with the part being talked about magnified ----------
// a crop of a screenshot shown large at box [x, y, maxW, maxH], with a light wedge back to where it sits on the phone
function magnify(ctx, img, src, ph, box, a) {
  if (a <= 0) return null;
  const s = ph.w / img.width, sc = Math.min(box[2] / src[2], box[3] / src[3]), w = src[2] * sc, h = src[3] * sc, x = box[0], y = box[1];
  const px = ph.x + src[0] * s, py = ph.y + src[1] * s, pw = src[2] * s, phh = src[3] * s;
  ctx.save(); ctx.globalAlpha *= a;
  ctx.fillStyle = "rgba(255,255,255,0.07)"; ctx.beginPath(); ctx.moveTo(px + pw, py); ctx.lineTo(x, y); ctx.lineTo(x, y + h); ctx.lineTo(px + pw, py + phh); ctx.closePath(); ctx.fill();
  ctx.strokeStyle = "rgba(255,255,255,0.75)"; ctx.lineWidth = 3; rrect(ctx, px - 3, py - 3, pw + 6, phh + 6, 8); ctx.stroke();
  ctx.shadowColor = "rgba(0,0,0,0.4)"; ctx.shadowBlur = 40; ctx.shadowOffsetY = 14; rrect(ctx, x, y, w, h, 20); ctx.fillStyle = C.white; ctx.fill(); ctx.shadowColor = "transparent";
  ctx.save(); rrect(ctx, x, y, w, h, 20); ctx.clip(); ctx.drawImage(img, src[0], src[1], src[2], src[3], x, y, w, h); ctx.restore();
  ctx.restore();
  return (r) => [x + (r[0] - src[0]) * sc, y + (r[1] - src[1]) * sc, r[2] * sc, r[3] * sc];
}
function sceneDemo(ctx, t, T) {
  const d = [0, 1, 2, 3, 4, 5, 6, 7].map((k) => LS("demo", k));
  bg(ctx, "#0E1C2B", "#1C3D63");
  const tPolicy = d[2] + 0.45, tMap = d[4] + 2.2, t50 = d[5] + 1.5, tTruck = d[7] + 0.9;
  let key = "rider_1640";
  if (t > tPolicy) key = "policy_top";
  if (t > d[3]) key = "policy_table";
  if (t > tMap) key = "policy_map";
  if (t > d[5]) key = "sim_0";
  if (t > t50) key = "sim_50";
  if (t > tTruck) key = "sim_50t";
  const img = IMG[key + ".jpg"];
  const enter = easeOut(prog(t, 0.1, 0.9));
  const ph = phone(ctx, 90, 50 + (1 - enter) * 1000, 420, img);
  const s = ph.w / img.width, P = (r) => [ph.x + r[0] * s, ph.y + r[1] * s, r[2] * s, r[3] * s];
  const box = [620, 290, 1240, 590];
  const say = (a, b, title, sub, color = C.white) => {
    const k = fadeIO(t, a, b, 0.3); if (k <= 0) return;
    text(ctx, title, 620, 160 + (1 - k) * 20, { size: 60, weight: 900, color, alpha: k });
    if (sub) text(ctx, sub, 622, 228 + (1 - k) * 20, { size: 36, weight: 500, color: LIGHT, alpha: k });
  };
  const win = (a, b) => fadeIO(t, a, b, 0.3);
  // the site
  say(0.4, d[1], "Beat the Bell 網站", "alexlin8888.github.io/nsysu-youbike-log");
  { const k = win(0.6, d[1]); if (k > 0) { text(ctx, "手機打開就能用，每 10 分鐘自動更新", 622, 330, { size: 36, weight: 500, color: LIGHT, alpha: k }); ["借車", "還車", "政策", "調度"].forEach((s2, i) => pill(ctx, s2, 700 + i * 170, 430, { size: 36, fill: i === 2 ? C.orange : C.blue, alpha: k, scale: pop(t, 0.9 + i * 0.15) })); } }
  // rider tab
  say(d[1], tPolicy, "借車：去哪一站、最晚幾點走", "16:40 從圖資大樓出發");
  { const a = win(d[1] + 0.1, tPolicy); const M = magnify(ctx, IMG["rider_1640.jpg"], [24, 1262, 732, 290], ph, box, key === "rider_1640" ? a : 0);
    if (M) { hilite(ctx, ...M(RECTS.rider_1640.best), t, d[1] + 0.6, C.yellow); hilite(ctx, ...M(RECTS.rider_1640.tip), t, d[1] + 1.8, C.yellow); } }
  if (key === "rider_1640") { const tp = P(RECTS.rider_1640.tabPolicy); tap(ctx, tp[0] + tp[2] / 2, tp[1] + tp[3] / 2, t, d[2] + 0.05); }
  // policy tab
  say(tPolicy, d[3], "政策：寫給學校和營運商", "為什麼現行獎勵太晚，提案怎麼改");
  magnify(ctx, IMG["policy_top.jpg"], [24, 1080, 732, 330], ph, box, key === "policy_top" ? win(tPolicy, d[3]) : 0);
  // the table at 16:30
  say(d[3], d[4], "16:30　現行規則：0 站", "這些站還有車，現行友愛接力不付");
  say(d[4], tMap, "提案：3 站送 30 分鐘", "海資館 68%、體育館 61%、材料 59%", C.yellow);
  { const M = magnify(ctx, IMG["policy_table.jpg"], [24, 304, 732, 446], ph, box, key === "policy_table" ? win(d[3], tMap) : 0);
    if (M) { const T0 = RECTS.policy_table; hilite(ctx, ...M([T0.ruleHead[0], T0.ruleHead[1], T0.ruleHead[2], T0.rows[4].rule[1] + T0.rows[4].rule[3] - T0.ruleHead[1]]), t, d[3] + 0.8, "#9AA3AD");
      [0, 1, 2].forEach((i) => hilite(ctx, ...M(T0.rows[i].pred), t, d[4] + 0.4 + i * 0.35, C.orange)); } }
  // the map
  say(tMap, d[5], "地圖上標出「+30分」", "預測型規則這時會付的站", C.yellow);
  { const M = magnify(ctx, IMG["policy_map.jpg"], [120, 300, 560, 440], ph, box, key === "policy_map" ? win(tMap, d[5]) : 0);
    if (M) RECTS.policy_map.glyphs.filter((g) => g.mark && g.rect[1] > 300 && g.rect[1] < 740).forEach((g, i) => { const q = M(g.rect), pulse = 0.5 + 0.5 * Math.sin(t * 6 + i); ctx.save(); ctx.strokeStyle = rgba(C.orange, prog(t, tMap + 0.3 + i * 0.2, tMap + 0.6 + i * 0.2)); ctx.lineWidth = 7; ctx.beginPath(); ctx.arc(q[0] + q[2] / 2, q[1] + q[3] / 2, q[2] * 0.85 + 10 * pulse, 0, 7); ctx.stroke(); ctx.restore(); }); }
  // what-if: half as many riders again bring a bike back to campus
  say(d[5], d[6], "試算：騎回校內的人多一半", "按下「多 50%」");
  { const k = key === "sim_0" || key === "sim_50" ? win(d[5], d[6]) : 0, M = magnify(ctx, IMG[key === "sim_0" ? "sim_0.jpg" : "sim_50.jpg"], [24, 180, 732, 348], ph, box, k);
    if (M) { const c = M(RECTS.sim_0.chip50); tap(ctx, c[0] + c[2] / 2, c[1] + c[3] / 2, t, t50 - 0.3); } }
  if (key === "sim_0") { const c = P(RECTS.sim_0.chip50); tap(ctx, c[0] + c[2] / 2, c[1] + c[3] / 2, t, t50 - 0.3); }
  say(d[6], d[7] + 0.3, "傍晚借不到車　少 11%", "每天多 25 趟騎車回校內，多送約 34 小時騎乘時數", C.yellow);
  { const M = magnify(ctx, IMG["sim_50.jpg"], [40, 680, 700, 290], ph, box, key === "sim_50" ? win(d[6], tTruck) : 0);
    if (M) { hilite(ctx, ...M(RECTS.sim_50.simBig), t, d[6] + 0.3, C.orange); hilite(ctx, ...M(RECTS.sim_50.simMeta), t, d[6] + 1.6, C.orange); } }
  if (key === "sim_50") { const c = P(RECTS.sim_50.chipTruck2); tap(ctx, c[0] + c[2] / 2, c[1] + c[3] / 2, t, tTruck - 0.3); }
  // and the trucks before the bell
  say(d[7] + 0.3, T + 1, "再加上下課前補車　少 27%", "16:50、17:50 各送 20 台到校內");
  { const M = magnify(ctx, IMG["sim_50t.jpg"], [40, 680, 700, 290], ph, box, key === "sim_50t" ? prog(t, tTruck, tTruck + 0.3) : 0);
    if (M) hilite(ctx, ...M(RECTS.sim_50t.simBig), t, tTruck + 0.4, C.orange); }
  sourceTag(ctx, "畫面：本組網站，重播 2026/11/11（三）", t, 0.6, DIM);
  fadeFrom(ctx, t, 0.3);
}

// ---------- 10. results, the brief, the trial, and the next bell ----------
function sceneResults(ctx, t, T) {
  const l = [0, 1, 2, 3, 4].map((k) => LS("results", k));
  if (t < l[4] - 0.2) {
    PAPER_BG(ctx);
    if (t < l[2] - 0.2) {
      const days = DATA.test_days, k0 = prog(t, 0.2, 0.7);
      text(ctx, "12 個測試日", 140, 150, { size: 56, weight: 900, color: C.ink, alpha: k0 });
      text(ctx, "模型估計時沒有用到這些日子", 140, 200, { size: 32, weight: 400, color: C.ink2, alpha: k0 });
      ["一", "二", "三", "四", "五", "六", "日"].forEach((d, i) => text(ctx, d, 192 + i * 120, 262, { size: 28, color: C.muted, align: "center", alpha: k0 }));
      for (let i = 0; i < 28; i++) {
        const dt = new Date(Date.UTC(2026, 9, 26 + i)), col = i % 7, row = Math.floor(i / 7), x = 140 + col * 120, y = 285 + row * 120;
        const iso = dt.toISOString().slice(0, 10), order = days.indexOf(iso), kk = order >= 0 ? pop(t, 0.6 + order * 0.15) : 0;
        ctx.save(); ctx.globalAlpha = k0; rrect(ctx, x, y, 104, 104, 16); ctx.fillStyle = col > 4 ? "#ECE8E0" : C.white; ctx.fill(); ctx.restore();
        if (kk > 0) { ctx.save(); ctx.translate(x + 52, y + 52); ctx.scale(kk, kk); rrect(ctx, -52, -52, 104, 104, 16); ctx.fillStyle = C.blue; ctx.fill(); ctx.restore(); }
        text(ctx, (dt.getUTCDate() === 1 ? "11/" : "") + dt.getUTCDate(), x + 52, y + 66, { size: dt.getUTCDate() === 1 ? 32 : 38, weight: 700, color: kk > 0.5 ? C.white : C.ink2, align: "center", alpha: k0 });
      }
      if (t > l[1] - 0.3) {
        const k = easeOut(prog(t, l[1] - 0.2, l[1] + 0.4));
        ctx.save(); ctx.globalAlpha = k;
        text(ctx, "91%", 1060, 400, { size: 200, weight: 900, color: C.blue });
        text(ctx, "的借空事先被標出", 1070, 480, { size: 50, weight: 700, color: C.ink });
        text(ctx, "中位數提早 40 分鐘；被標出的站，", 1070, 556, { size: 34, weight: 500, color: C.ink2 });
        text(ctx, "62% 在 40 分鐘內真的借空（平均 25%）", 1070, 604, { size: 34, weight: 500, color: C.ink2 });
        const x0 = 1070, x1 = 1780, y = 770;
        ctx.strokeStyle = C.ink2; ctx.lineWidth = 4; ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(x1, y); ctx.stroke();
        [[0.42, 0], [0.86, 1]].forEach(([f, i]) => {
          const xe = lerp(x0, x1, f), xf = xe - 200, kk = prog(t, l[1] + 0.8 + i * 0.6, l[1] + 1.2 + i * 0.6);
          ctx.fillStyle = C.red; ctx.beginPath(); ctx.arc(xe, y, 16, 0, 7); ctx.fill(); text(ctx, "借空", xe, y + 52, { size: 28, weight: 700, color: C.red, align: "center" });
          if (kk > 0) { ctx.save(); ctx.globalAlpha *= kk; ctx.strokeStyle = C.blue; ctx.lineWidth = 5; ctx.beginPath(); ctx.moveTo(xf, y); ctx.lineTo(xf, y - 70); ctx.stroke(); ctx.fillStyle = C.blue; ctx.beginPath(); ctx.moveTo(xf, y - 70); ctx.lineTo(xf + 44, y - 58); ctx.lineTo(xf, y - 46); ctx.fill(); text(ctx, "提早 40 分鐘", (xf + xe) / 2 + 10, y - 18, { size: 24, weight: 700, color: C.blue, align: "center" }); ctx.restore(); }
        });
        ctx.restore();
      }
      sourceTag(ctx, "來源：報告 3.10 節，219 次借空事件", t, l[1]);
    } else {
      const img = IMG["brief.jpg"], k = easeOut(prog(t, l[2] - 0.2, l[2] + 0.5));
      ctx.save(); ctx.translate(470, 530 + (1 - k) * 200); ctx.rotate(-0.035); ctx.globalAlpha = k;
      ctx.shadowColor = "rgba(16,32,47,0.3)"; ctx.shadowBlur = 40; ctx.shadowOffsetY = 16;
      const bw = 540, bh = bw * img.height / img.width; ctx.drawImage(img, -bw / 2, -bh / 2, bw, bh); ctx.restore();
      text(ctx, "一頁建議書", 900, 200, { size: 64, weight: 900, color: C.ink, alpha: k });
      ["國立中山大學總務處", "高雄市政府交通局", "微笑單車高雄營運團隊"].forEach((s2, i) => pill(ctx, s2, 1180, 300 + i * 90, { size: 36, fill: [C.blue, C.green, C.orange][i], scale: pop(t, l[2] + 0.6 + i * 0.3) }));
      if (t > l[3] - 0.2) {
        const kk = easeOut(prog(t, l[3] - 0.1, l[3] + 0.4));
        text(ctx, "還不知道：多少人會因此提早還車", 900, 600, { size: 36, weight: 700, color: C.orange, alpha: kk });
        const k2 = easeOut(prog(t, LS("results", 3) + 4.0, LS("results", 3) + 4.5));
        text(ctx, "建議：校內 8 站試辦四週", 900, 680, { size: 54, weight: 900, color: C.ink, alpha: k2 });
        ["現行", "預測型", "現行", "預測型"].forEach((s2, i) => { const p = pop(t, l[3] + 4.2 + i * 0.2); if (p <= 0) return; ctx.save(); ctx.translate(1000 + i * 210, 790); ctx.scale(p, p); rrect(ctx, -95, -60, 190, 120, 18); ctx.fillStyle = i % 2 ? C.blue : "#9AA3AD"; ctx.fill(); text(ctx, "第 " + (i + 1) + " 週", 0, -12, { size: 28, weight: 500, color: C.white, align: "center" }); text(ctx, s2, 0, 34, { size: 34, weight: 900, color: C.white, align: "center" }); ctx.restore(); });
        text(ctx, "單雙週輪流，用紀錄器比較沒車的時間和還車的人數", 900, 900, { size: 30, weight: 500, color: C.ink2, alpha: k2 });
      }
    }
    wipe(ctx, t, l[4] - 0.6, l[4] + 0.2);
    fadeFrom(ctx, t, 0.3);
    return;
  }
  // the next bell: there are bikes, and 阿哲 rides off along the sea
  const tl = t - l[4];
  if (tl < 4.2) {
    campusStreet(ctx, t, 0.8);
    station(ctx, 860, 880, 90, { docks: 7, bikes: tl > 2.2 ? 6 : 7, skip: tl > 2.2 ? 1 : 0, name: "圖資站" });
    pill(ctx, "17:00", 170, 120, { size: 40, fill: C.orange });
    bellIcon(ctx, 290, 118, 26, Math.sin(t * 9) * 0.3 * (1 - prog(tl, 0, 1.5)), C.orange);
    if (tl < 1.4) student(ctx, lerp(-100, 1020, easeOut(prog(tl, 0, 1.4))), 880, 115, { pose: "walk", t, expr: "happy" });
    else if (tl < 2.2) student(ctx, 1020, 880, 115, { pose: "cheer", t, expr: "happy" });
    else rider(ctx, 1000 + (tl - 2.2) * 600, 880, 108, { t, expr: "happy" });
    [[0.4, 600, 0], [0.9, 420, 1]].forEach(([dd, xe, i]) => { const k = easeOut(prog(tl, dd, dd + 1.4)); student(ctx, lerp(-160, xe, k), 880, 100, { pose: k < 1 ? "walk" : "stand", t, pal: MATES[i], expr: "happy" }); });
    sourceTag(ctx, "示意動畫", t, l[4], C.ink2);
    wipe(ctx, t, l[4] + 3.8, l[4] + 4.6);
  } else {
    seaside(ctx, t, 1.15);
    rider(ctx, -100 + (tl - 4.2) * 300, 950, 115, { t, expr: "happy" });
    pill(ctx, "17:05　騎去西子灣", 230, 120, { size: 38, fill: C.navy, alpha: prog(tl, 4.5, 4.9) });
    fadeTo(ctx, t, T, 0.8);
  }
}

// ---------- 11. end card ----------
function sceneEnd(ctx, t, T) {
  NAVY_BG(ctx);
  const k = easeOut(prog(t, 0.1, 0.7));
  bellIcon(ctx, 960, 200, 60, Math.sin(t * 5) * 0.15, C.yellow);
  text(ctx, "Beat the Bell", 960, 350, { size: 110, weight: 900, color: C.white, align: "center", alpha: k });
  text(ctx, "alexlin8888.github.io/nsysu-youbike-log", 960, 440, { size: 46, weight: 700, color: C.yellow, align: "center", alpha: k });
  text(ctx, "國立中山大學　人工智慧導論（TAICA）第 54 組", 960, 550, { size: 38, weight: 500, color: LIGHT, align: "center", alpha: easeOut(prog(t, 0.4, 1.0)) });
  text(ctx, "林沛霆　陳佳晨　林詩穎", 960, 615, { size: 44, weight: 700, color: C.white, align: "center", alpha: easeOut(prog(t, 0.5, 1.1)) });
  ["資料：YouBike 官方開放資料（本組紀錄器）；臺大周邊騎乘資料（tses89214/youbike-historical-data）",
    "地圖：OpenStreetMap 貢獻者；健康數據：WHO 2020、國民健康署；國外案例：Citi Bike、Vélib'",
    "動畫、音樂與音效：本組自製；阿哲為虛構角色"].forEach((s, i) => text(ctx, s, 960, 770 + i * 50, { size: 28, weight: 400, color: DIM, align: "center", alpha: easeOut(prog(t, 0.9 + i * 0.15, 1.5 + i * 0.15)) }));
  fadeFrom(ctx, t, 0.4);
  fadeTo(ctx, t, T, 0.6, "#000000");
}

const SCENES = { hook: sceneHook, title: sceneTitle, data: sceneData, app: sceneApp, timing: sceneTiming, sitting: sceneSitting, idea: sceneIdea, method: sceneMethod, demo: sceneDemo, results: sceneResults, end: sceneEnd };

// Sound effects, in seconds from the video start, placed on the same timeline as the picture they belong to.
// audio.py reads this list through the browser.
window.sfxEvents = function () {
  const E = [], at = (scene, t, name, gain = 1) => E.push({ t: +(sceneOf(scene).start + t).toFixed(3), name, gain });
  const tOut = LS("hook", 1) + 1.5;
  at("hook", 0.45, "school_bell", 0.85);
  at("hook", LS("hook", 1) + 0.1, "whoosh", 0.45); at("hook", tOut - 0.4, "whoosh", 0.7);
  for (let k = 0; k < 6; k++) at("hook", tOut + 0.1 + k * 0.24, "step", 0.3);
  at("hook", LS("hook", 2), "bonk", 0.8);
  at("title", 0.05, "whoosh", 0.6); at("title", 0.25, "ding", 0.55);
  at("data", 0.3, "sparkle", 0.3); at("data", LS("data", 1) - 1.6, "zoom", 0.55);
  at("data", LS("data", 1) + 0.3, "pop", 0.55); at("data", LS("data", 2), "pop", 0.55); at("data", LS("data", 3) - 0.2, "whoosh", 0.45); at("data", LS("data", 3) + 0.2, "pop", 0.55);
  at("app", LS("app", 0) + 0.8, "alert", 0.4); at("app", LS("app", 1) + 0.2, "pop", 0.4); at("app", LS("app", 2) - 0.4, "whoosh", 0.5);
  for (let i = 0; i < 4; i++) at("app", LS("app", 2) + 0.4 + i * 0.35, "tick", 0.35);
  for (let i = 0; i < 12; i++) at("timing", 0.4 + i * 0.12, "blip", 0.16);
  at("timing", LS("timing", 1) + 0.7, "pop", 0.55); at("timing", LS("timing", 2) + 0.5, "pop", 0.45); at("timing", LS("timing", 3) + 0.2, "bonk", 0.55);
  for (let i = 0; i < 3; i++) at("sitting", 0.2 + i * 0.7, "pop", 0.35);
  for (let i = 0; i < 10; i++) at("sitting", LS("sitting", 1) + 0.4 + i * 0.12, "blip", 0.18);
  at("sitting", LS("sitting", 2), "bike_bell", 0.55);
  Object.keys(WATCH).forEach((n) => { const x = crossAt(DATA.campus.find((c) => c.name === n)); if (x < 900) at("idea", x, "ding", 0.5); });
  at("idea", LS("idea", 2) + 0.2, "pop", 0.45);
  at("idea", LS("idea", 3) - 0.7, "whoosh", 0.55); at("idea", LS("idea", 3) + 0.9, "scratch", 0.45); at("idea", LS("idea", 3) + 1.8, "chime", 0.65);
  at("idea", LS("idea", 4), "freewheel", 0.4); at("idea", LS("idea", 4) + 1.7, "notify", 0.65); at("idea", LS("idea", 4) + 2.2, "whoosh", 0.5); at("idea", LS("idea", 4) + 3.0, "bike_bell", 0.45);
  for (let i = 0; i < 3; i++) at("method", 0.2 + i * 0.25, "pop", 0.3);
  at("method", LS("method", 1), "whoosh", 0.3); at("method", LS("method", 2), "whoosh", 0.3); at("method", LS("method", 3) - 0.4, "whoosh", 0.45); at("method", LS("method", 4), "pop", 0.45); at("method", LS("method", 5), "chime", 0.45);
  const d = (k) => LS("demo", k);
  at("demo", 0.1, "whoosh", 0.55); at("demo", d(2) + 0.05, "tap", 0.65); at("demo", d(3), "swipe", 0.35); at("demo", d(4) + 2.2, "swipe", 0.35); at("demo", d(5), "swipe", 0.35);
  at("demo", d(5) + 1.2, "tap", 0.65); at("demo", d(6) + 0.3, "pop", 0.45); at("demo", d(7) + 0.6, "tap", 0.65); at("demo", d(7) + 1.3, "pop", 0.45);
  at("results", 0.5, "sparkle", 0.25); for (let i = 0; i < 12; i++) at("results", 0.6 + i * 0.15, "blip", 0.16);
  at("results", LS("results", 1) - 0.2, "pop", 0.55); at("results", LS("results", 2) - 0.2, "whoosh", 0.45); at("results", LS("results", 3) + 4.2, "pop", 0.35);
  at("results", LS("results", 4) - 0.6, "whoosh", 0.55); at("results", LS("results", 4), "school_bell_soft", 0.65); at("results", LS("results", 4) + 2.2, "bike_bell", 0.65); at("results", LS("results", 4) + 3.8, "whoosh", 0.45);
  at("end", 0.1, "ding", 0.45);
  return E.sort((a, b) => a.t - b.t);
};
