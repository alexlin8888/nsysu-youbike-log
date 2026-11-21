"use strict";
// The scenes of the final video. Each scene is a function (ctx, t, T) of its own time t in seconds (T = its length).
// The narration is timed by video/script.py and read from CUES: LS(id, k) is the start of line k of scene id, and
// PT(id, k, j) the start of its phrase j (the text between full-width spaces), in seconds from the scene start, so a
// picture changes on the phrase that talks about it.
// Layout rule: nothing important below y = 930 in the middle of the frame, where the subtitles are burnt in.
window.IMAGES = ["rider_1640.jpg", "dock_0920.jpg", "policy_map.jpg", "policy_table.jpg", "sim_0.jpg", "sim_50.jpg", "brief.jpg"];

function sceneOf(id) { return CUES.scenes.find((s) => s.id === id); }
function linesOf(id) { return CUES.lines.filter((l) => l.scene === id); }
function LS(id, k) { return linesOf(id)[k].start - sceneOf(id).start; }
function LE(id, k) { return linesOf(id)[k].end - sceneOf(id).start; }
function PT(id, k, j) { return linesOf(id)[k].parts[j].start - sceneOf(id).start; }

// ---------- shared pieces ----------
const CEN = [22.6272, 120.2655];
const KX = Math.cos(CEN[0] * Math.PI / 180);
function proj(lat, lng, scale, cx, cy) { return [cx + (lng - CEN[1]) * KX * scale, cy - (lat - CEN[0]) * scale]; }
const MAP = { scale: 130000, cx: 800, cy: 560 };          // the campus map
function slotAt(m) { const s = DATA.slots; let k = 0; while (k + 1 < s.length && s[k + 1] <= m) k++; return k; }
function slotOf(m) { return DATA.slots.indexOf(m); }
function bg(ctx, a, b) { const g = ctx.createLinearGradient(0, 0, 0, H); g.addColorStop(0, a); g.addColorStop(1, b); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H); }
const NAVY_BG = (ctx) => bg(ctx, "#0E1C2B", "#13283D");
const PAPER_BG = (ctx) => { ctx.fillStyle = C.paper; ctx.fillRect(0, 0, W, H); };
const LIGHT = "#C7D6E6", DIM = "#8FA6BD";
const MATES = [{ hoodie: "#7A8A99", hoodieD: "#66737F", pack: "#B9C4CC", hair: "#3A2E28" }, { hoodie: "#C9705A", hoodieD: "#AE5D49", pack: "#E5C07B", hair: "#232634" },
  { hoodie: "#4E8B57", hoodieD: "#3F7247", pack: "#F2D16B", hair: "#2B2420" }, { hoodie: "#8C6BB1", hoodieD: "#755896", pack: "#9AD0C2", hair: "#1E1E28" }];

// the section of the story, in the top-left corner
function chapter(ctx, label, t, dark = false, a = 0.1) {
  const k = easeOut(prog(t, a, a + 0.4)); if (k <= 0) return;
  ctx.save(); ctx.globalAlpha *= k;
  const w = textW(ctx, label, 26, 700) + 40;
  rrect(ctx, 48, 30, w, 46, 23); ctx.fillStyle = dark ? "rgba(255,255,255,0.14)" : "rgba(16,32,47,0.08)"; ctx.fill();
  text(ctx, label, 68, 62, { size: 26, weight: 700, color: dark ? LIGHT : C.ink2 });
  ctx.restore();
}
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
  if (s <= 0) return;
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
// a 5-yuan ride voucher: a ticket with notched sides
function voucher(ctx, x, y, s, o = {}) {
  if (s <= 0) return;
  ctx.save(); ctx.translate(x, y); ctx.scale(s, s); ctx.globalAlpha *= o.alpha == null ? 1 : o.alpha;
  // the value "5 元" sits on the stub, the name and the note on the main part, which grows to fit the note
  const note = o.note || "只能折抵 YouBike 車資", stub = 150, h = 150;
  const w = Math.max(460, stub + textW(ctx, note, 24, 500) + 80), mainX = stub / 2;
  ctx.shadowColor = "rgba(16,32,47,0.25)"; ctx.shadowBlur = 24; ctx.shadowOffsetY = 8;
  ctx.beginPath(); ctx.moveTo(-w / 2, -h / 2); ctx.lineTo(w / 2, -h / 2); ctx.lineTo(w / 2, -18); ctx.arc(w / 2, 0, 18, -Math.PI / 2, Math.PI / 2, true); ctx.lineTo(w / 2, h / 2);
  ctx.lineTo(-w / 2, h / 2); ctx.lineTo(-w / 2, 18); ctx.arc(-w / 2, 0, 18, Math.PI / 2, -Math.PI / 2, true); ctx.closePath();
  ctx.fillStyle = "#FFF6DA"; ctx.fill(); ctx.shadowColor = "transparent"; ctx.lineWidth = 4; ctx.strokeStyle = "#E8B83A"; ctx.stroke();
  ctx.setLineDash([8, 8]); ctx.beginPath(); ctx.moveTo(-w / 2 + stub, -h / 2 + 14); ctx.lineTo(-w / 2 + stub, h / 2 - 14); ctx.stroke(); ctx.setLineDash([]);
  text(ctx, "5", -w / 2 + 62, 32, { size: 92, weight: 900, color: "#B7860F", align: "center" });
  text(ctx, "元", -w / 2 + 112, 26, { size: 38, weight: 900, color: "#B7860F", align: "center" });
  text(ctx, "騎乘券", mainX, 14, { size: 52, weight: 900, color: C.ink, align: "center" });
  text(ctx, note, mainX, 56, { size: 24, weight: 500, color: C.ink2, align: "center" });
  ctx.restore();
}

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
const STR = (c) => 20 + Math.sqrt(c.cap) * 3.2;
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
const stationXY = (c) => proj(c.lat, c.lng, MAP.scale, MAP.cx, MAP.cy);
const station8 = (name) => DATA.campus.find((c) => c.name === name);
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
  rrect(ctx, -92, -30, 184, 60, 30); ctx.fillStyle = C.white; ctx.fill(); ctx.shadowColor = "transparent";
  ctx.lineWidth = 4; ctx.strokeStyle = C.blue; ctx.stroke();
  clockIcon(ctx, -58, 0, 15, C.blue);
  text(ctx, "+1小時", 20, 12, { size: 32, weight: 900, color: C.blue, align: "center" });
  ctx.restore();
}
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
// a crossfade between parts of one scene: draw the next part over the last with alpha k
function over(ctx, k, draw) { if (k <= 0) return; ctx.save(); ctx.globalAlpha = k; draw(); ctx.restore(); }
// a small line chart on light paper: series of [minute, value], drawn up to minute `upto`
function lineChart(ctx, x, y, w, h, series, m0, m1, vmax, upto, o = {}) {
  const X = (m) => x + w * (m - m0) / (m1 - m0), Y = (v) => y + h - h * v / vmax;
  ctx.save();
  ctx.strokeStyle = C.line; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(x, y + h); ctx.lineTo(x + w, y + h); ctx.stroke();
  (o.grid || []).forEach((g) => { ctx.beginPath(); ctx.moveTo(x, Y(g)); ctx.lineTo(x + w, Y(g)); ctx.stroke(); text(ctx, String(g), x - 14, Y(g) + 9, { size: 24, color: C.muted, align: "right" }); });
  (o.hours || []).forEach((hh) => text(ctx, hh + ":00", X(hh * 60), y + h + 40, { size: 26, color: C.ink2, align: "center" }));
  ctx.strokeStyle = o.color || C.blue; ctx.lineWidth = 6; ctx.lineJoin = "round"; ctx.beginPath(); let first = true;
  series.forEach(([m, v]) => { if (m > upto || v == null) return; first ? ctx.moveTo(X(m), Y(v)) : ctx.lineTo(X(m), Y(v)); first = false; }); ctx.stroke();
  ctx.fillStyle = o.color || C.blue; series.forEach(([m, v]) => { if (m > upto || v == null) return; ctx.beginPath(); ctx.arc(X(m), Y(v), 5, 0, 7); ctx.fill(); });
  ctx.restore();
  return { X, Y };
}

// ---------- 1. hook: the 17:00 bell, an empty station, then the whole campus ----------
function sceneHook(ctx, t, T) {
  const tName = PT("hook", 0, 0), tRun = PT("hook", 0, 1), tOut = tRun + 1.2, tMap = PT("hook", 0, 3) - 0.2;
  if (t < tOut) {
    // the classroom, seen from the side
    ctx.fillStyle = C.wall; ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = "#CDBA9A"; ctx.fillRect(0, 860, W, H - 860); ctx.fillStyle = "#B9A585"; ctx.fillRect(0, 860, W, 10);
    ctx.save(); rrect(ctx, 90, 140, 560, 420, 10); ctx.clip(); sky(ctx, 0.45, 140, 560); mountains(ctx, 470, 300, 0); sea(ctx, 430, 560, t, 0.1); ctx.restore();
    ctx.lineWidth = 16; ctx.strokeStyle = "#FFFFFF"; rrect(ctx, 90, 140, 560, 420, 10); ctx.stroke(); ctx.beginPath(); ctx.moveTo(370, 140); ctx.lineTo(370, 560); ctx.stroke();
    card(ctx, 820, 170, 860, 400, { fill: "#FBFBFA", r: 8 }); ctx.lineWidth = 10; ctx.strokeStyle = "#9AA3AD"; rrect(ctx, 820, 170, 860, 400, 8); ctx.stroke();
    ctx.strokeStyle = "#3C6FB0"; ctx.lineWidth = 5; ctx.beginPath(); ctx.moveTo(900, 520); ctx.lineTo(900, 250); ctx.moveTo(900, 520); ctx.lineTo(1300, 520); ctx.stroke();
    ctx.strokeStyle = "#D9483B"; ctx.beginPath(); ctx.moveTo(910, 500); ctx.bezierCurveTo(1000, 480, 1080, 300, 1280, 280); ctx.stroke();
    text(ctx, "P(沒車) = ?", 1350, 330, { size: 46, weight: 700, color: "#3C6FB0" }); text(ctx, "λ  μ", 1390, 420, { size: 46, weight: 700, color: "#3C6FB0" });
    clock(ctx, 1770, 130, 62, 16 * 60 + 59 + prog(t, 0, 0.45));
    if (t > 0.45) { const k = prog(t, 0.45, 1.6); if (k < 1) { ctx.save(); ctx.strokeStyle = rgba(C.orange, 1 - k); ctx.lineWidth = 8; ctx.beginPath(); ctx.arc(1770, 130, 70 + 120 * k, 0, 7); ctx.stroke(); ctx.restore(); } }
    pill(ctx, "17:00 下課", 1770, 258, { size: 34, fill: C.orange, scale: pop(t, 0.5), alpha: prog(t, 0.5, 0.6) });
    [[300, 0], [1450, 1]].forEach(([x, i]) => {
      const up = t > tRun + 0.2 + i * 0.3, s = 70;
      // seated with the hips at the back of the chair, facing the board; the desk stands in front of the knees
      chair(ctx, x, 860, s); student(ctx, x - 0.3 * s + (up ? (t - tRun - 0.2 - i * 0.3) * 260 : 0), 860, s, { pose: up ? "walk" : "sit", t, pal: MATES[i], expr: up ? "happy" : "neutral", shadow: up }); desk(ctx, x + 0.45 * s, 860, s);
    });
    const s = 120, x0 = 720;
    chair(ctx, x0, 860, s);
    if (t < tName + 0.5) { student(ctx, x0 - 0.3 * s, 860, s, { pose: "sit", t, expr: t > 0.6 ? "surprised" : "neutral" }); desk(ctx, x0 + 0.45 * s, 860, s); }
    else if (t < tRun) { desk(ctx, x0 + 0.45 * s, 860, s); student(ctx, x0 - 20, 860, s, { pose: "stand", t, expr: "happy" }); }
    else { desk(ctx, x0 + 0.45 * s, 860, s); const k = t - tRun; student(ctx, x0 - 20 + k * 900 + 300 * k * k, 860, s, { pose: "run", t: t * 1.2, expr: "happy" }); }
    const nk = fadeIO(t, tName, tRun + 0.5, 0.3);
    if (nk > 0) {
      ctx.save(); ctx.globalAlpha = nk; ctx.translate(0, (1 - nk) * 20);
      card(ctx, 360, 330, 470, 150, { fill: C.navy, r: 22 });
      ctx.fillStyle = C.navy; ctx.beginPath(); ctx.moveTo(660, 478); ctx.lineTo(700, 478); ctx.lineTo(690, 520); ctx.closePath(); ctx.fill();
      text(ctx, "阿哲", 396, 410, { size: 60, weight: 900, color: C.white }); text(ctx, "中山大學資管系", 548, 404, { size: 36, weight: 500, color: LIGHT });
      text(ctx, "虛構角色", 398, 458, { size: 26, weight: 400, color: DIM });
      ctx.restore();
    }
  } else if (t < tMap + 0.05) {
    // the station a minute later
    campusStreet(ctx, t, 0.75);
    const light = station(ctx, 1100, 880, 95, { docks: 7, bikes: 0, name: "圖資站", empty: true });
    const tEmpty = PT("hook", 0, 2);
    if (t > tEmpty) { const blink = 0.5 + 0.5 * Math.sin((t - tEmpty) * 10); ctx.save(); ctx.globalAlpha = blink * 0.6; ctx.fillStyle = "#FF5A4A"; for (let k = 0; k < 7; k++) { const [lx, ly] = light(k); ctx.beginPath(); ctx.arc(lx, ly, 18, 0, 7); ctx.fill(); } ctx.restore(); }
    const arrive = tOut + 0.9, s = 115;
    if (t < arrive) student(ctx, lerp(-150, 860, easeOut(prog(t, tOut, arrive))), 880, s, { pose: "run", t: t * 1.2, expr: "happy" });
    else student(ctx, 860, 880, s, { pose: "stand", t, expr: t > tEmpty ? "sad" : "surprised" });
    if (t > tEmpty - 0.05) { const p = pop(t, tEmpty); ctx.save(); ctx.translate(1530, 470); ctx.scale(p, p); card(ctx, -150, -95, 300, 190, { fill: C.white, r: 30 }); text(ctx, "0", -40, 55, { size: 150, weight: 900, color: C.red, align: "center" }); text(ctx, "台", 70, 45, { size: 64, weight: 900, color: C.ink, align: "center" }); ctx.restore(); }
    sourceTag(ctx, "示意動畫", t, tOut + 0.3, C.ink2);
  } else {
    // the whole campus at 17:40 on 11 Nov: most stations are empty at once
    campusMap(ctx, MAP.scale, MAP.cx, MAP.cy);
    const l2 = LS("hook", 2), fill = (c, i) => easeInOut(prog(t, l2 + 1.4 + i * 0.25, l2 + 2.0 + i * 0.25));
    const k = slotOf(17 * 60 + 40);
    const tried = ["工學院", "材料大樓", "體育館"];
    let zero = 0;
    DATA.campus.forEach((c, i) => {
      const [x, y] = stationXY(c), v = c.bikes[k], f = v === 0 ? fill(c, i) : 0;
      if (v === 0) zero++;
      const col = f > 0 ? mix(C.red, C.green, f) : bikeColor(v);
      stationDot(ctx, x, y, STR(c), col, c.name, { num: f > 0.5 ? "+" : v, side: SIDE[c.name] });
      const ti = tried.indexOf(c.name);
      if (ti >= 0) { const rk = prog(t, PT("hook", 0, 3) + ti * 0.35, PT("hook", 0, 3) + ti * 0.35 + 0.3) * (1 - prog(t, l2, l2 + 0.4)); if (rk > 0) { ctx.save(); ctx.strokeStyle = rgba("#FF6B5E", rk); ctx.lineWidth = 6; ctx.beginPath(); ctx.arc(x, y, STR(c) + 8, 0, 7); ctx.stroke(); ctx.restore(); } }
      // bikes arriving before the bell, in the last line
      if (v === 0) { const a = l2 + 0.9 + i * 0.25, kk = prog(t, a, a + 0.8); if (kk > 0 && kk < 1) { ctx.save(); ctx.translate(lerp(W + 80, x, easeInOut(kk)), lerp(y - 160, y, easeInOut(kk))); bike(ctx, 0, 30, 30, { color: "#FFFFFF", accent: C.green }); ctx.restore(); } }
    });
    const before = t < l2 + 0.6;
    card(ctx, 1150, 70, 710, 160, { fill: "rgba(255,255,255,0.97)", r: 24 });
    text(ctx, "11/11（三）傍晚", 1190, 118, { size: 30, weight: 500, color: C.ink2 });
    text(ctx, before ? "17:40" : "16:50", 1190, 202, { size: 80, weight: 900, color: C.ink });
    text(ctx, before ? "8 站有 " + zero + " 站沒車" : "下課以前", 1820, 200, { size: 42, weight: 900, color: before ? C.red : C.green, align: "right" });
    const out = 1 - prog(t, l2 - 0.2, l2 + 0.3);
    over(ctx, out * easeOut(prog(t, PT("hook", 1, 0), PT("hook", 1, 0) + 0.4)), () => {
      card(ctx, 1150, 260, 710, 120, { fill: "rgba(255,255,255,0.97)", r: 24 });
      text(ctx, "我們的紀錄", 1190, 312, { size: 30, weight: 700, color: C.ink });
      text(ctx, "2026 年 10 月 1 日起，每 10 分鐘一筆", 1190, 356, { size: 28, weight: 500, color: C.ink2 });
    });
    statCard(ctx, t, PT("hook", 1, 1), 1150, 410, 710, "56%", "17:30–18:30 沒車", "校內 8 站，12 個上課日平均", { alpha: out });
    headline(ctx, "AI 預測哪一站快沒車", 1150, 330, t, PT("hook", 2, 0) + 0.3, { size: 50, color: C.white });
    headline(ctx, "下課前把車補回來", 1150, 410, t, PT("hook", 2, 1), { size: 50, color: C.yellow });
    sourceTag(ctx, "資料：YouBike 開放資料，本組紀錄器每 10 分鐘記錄；海岸線為示意", t, tMap + 0.4, DIM);
    fadeTo(ctx, t, T, 0.35);
  }
  wipe(ctx, t, tOut - 0.4, tOut + 0.4);
  wipe(ctx, t, tMap - 0.4, tMap + 0.4);
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
  text(ctx, "中山大學 YouBike 缺車預測與預測型友愛接力", 726, 660, { size: 44, weight: 500, color: LIGHT, alpha: easeOut(prog(t, 0.9, 1.5)) });
  text(ctx, "人工智慧導論　第 54 組", 726, 740, { size: 34, weight: 400, color: DIM, alpha: easeOut(prog(t, 1.2, 1.8)) });
  fadeTo(ctx, t, T, 0.3, C.paper);
}

// ---------- 3. cause: the bell empties the racks in half an hour; in the morning they fill up ----------
function sceneCause(ctx, t, T) {
  const p = (k, j) => PT("cause", k, j), l1 = LS("cause", 1);
  PAPER_BG(ctx);
  chapter(ctx, "原因", t);
  const morning = prog(t, l1 - 0.3, l1 + 0.2);
  // left: the station, drawn inside a rounded panel
  const px = 60, py = 110, pw = 880, ph = 790, gy = py + 640;
  ctx.save(); rrect(ctx, px, py, pw, ph, 28); ctx.clip();
  const sg = ctx.createLinearGradient(0, py, 0, gy); sg.addColorStop(0, morning > 0.5 ? "#9CCBEE" : "#F5C08A"); sg.addColorStop(1, morning > 0.5 ? "#E4F2FB" : "#FCE3C2"); ctx.fillStyle = sg; ctx.fillRect(px, py, pw, ph);
  ctx.fillStyle = "#E8E1D5"; ctx.fillRect(px + 520, gy - 300, 300, 300); ctx.fillStyle = "#A8C6DD"; for (let r = 0; r < 5; r++) for (let c = 0; c < 5; c++) ctx.fillRect(px + 545 + c * 54, gy - 270 + r * 54, 30, 34);
  ctx.fillStyle = "#D8D2C7"; ctx.fillRect(px, gy, pw, ph); ctx.fillStyle = "#BDB6A9"; ctx.fillRect(px, gy, pw, 7);
  // how many bikes are left: 7 at 16:58, taken one by one from the bell on, a single return late
  let bikes = 7, clockM = 16 * 60 + 58;
  if (morning < 0.5) {
    const tb = p(0, 1), t0 = p(0, 2) + 0.2, t1 = p(0, 3) + 1.0;
    bikes = 7 - Math.floor(clamp((t - t0) / (t1 - t0)) * 7.999);
    clockM = t < tb ? 16 * 60 + 58 + 2 * prog(t, 0, tb) : 17 * 60 + 30 * prog(t, tb, t1);
    const ret = p(0, 4) + 0.6;
    station(ctx, px + 140, gy, 72, { docks: 7, bikes, name: "圖資站", empty: bikes === 0 });
    // the crowd after the bell
    for (let i = 0; i < 5; i++) {
      const a = tb + 0.3 + i * 0.25, k = easeOut(prog(t, a, a + 1.3)), x = lerp(pw + 160, px + 420 + i * 70, k);
      if (t < a) continue;
      const tk = t0 + (i + 1) * (t1 - t0) / 7;
      if (t > tk && i < 4) { const kk = prog(t, tk, tk + 1.4); if (kk < 1) rider(ctx, lerp(px + 380, px - 260, kk), gy, 62, { t, face: -1, pal: MATES[i % 4], expr: "happy" }); }
      else student(ctx, x, gy, 66, { pose: k < 1 ? "walk" : "stand", t: t + i, face: -1, pal: MATES[i % 4], expr: bikes === 0 && k >= 1 ? "sad" : "neutral" });
    }
    if (t > ret) { const k = easeOut(prog(t, ret, ret + 2.2)); if (k < 1) rider(ctx, lerp(px - 200, px + 300, k), gy, 62, { t, pal: MATES[2], expr: "neutral" }); else text(ctx, "回來的車很少", px + 300, gy - 260, { size: 34, weight: 700, color: C.ink2, align: "center", alpha: prog(t, ret + 2.2, ret + 2.6) }); }
  } else {
    clockM = 9 * 60 + 20;
    station(ctx, px + 140, gy, 72, { docks: 7, bikes: 7, name: "圖資站" });
    const k = easeOut(prog(t, l1, l1 + 1.4));
    ctx.save(); ctx.translate(lerp(pw + 120, px + 760, k), 0); rider(ctx, 0, gy, 66, { t, face: -1, expr: k >= 1 ? "sad" : "neutral", pedal: k >= 1 ? 0.8 : null }); ctx.restore();
    if (k >= 1) text(ctx, "?", px + 700, gy - 250, { size: 90, weight: 900, color: C.navy, align: "center", alpha: prog(t, l1 + 1.4, l1 + 1.7) });
    pill(ctx, "停滿了", px + 420, gy - 330, { size: 36, fill: "#4C5BE0", scale: pop(t, p(1, 2)) });
  }
  ctx.restore();
  card(ctx, px, py, pw, ph, { fill: "rgba(0,0,0,0)", r: 28, shadow: false, stroke: C.line, lw: 3 });
  // the clock and the count
  card(ctx, px + 30, py + 30, 250, 96, { fill: C.white, r: 20 });
  clockIcon(ctx, px + 82, py + 78, 24, C.ink);
  text(ctx, hhmm(clockM), px + 122, py + 98, { size: 48, weight: 900, color: C.ink });
  if (morning < 0.5) { card(ctx, px + pw - 270, py + 30, 240, 96, { fill: C.white, r: 20 }); text(ctx, bikes + " 台", px + pw - 150, py + 99, { size: 56, weight: 900, color: bikes === 0 ? C.red : C.ink, align: "center" }); }
  if (t > p(0, 1) - 0.1 && t < p(0, 1) + 1.6 && morning < 0.5) bellIcon(ctx, px + 320, py + 78, 30, Math.sin(t * 14) * 0.4, C.orange);
  // right: what the logger recorded at that station on 11 Nov
  const cx = 1000, cyy = 150, cw = 840, chh = 560;
  card(ctx, cx - 40, py, cw + 70, ph, { fill: C.white, r: 28 });
  const lib = station8("圖資");
  const eve = DATA.slots.map((m, i) => [m, lib.bikes[i]]).filter(([m]) => m >= 15 * 60 && m <= 19 * 60);
  const mor = DATA.slots.map((m, i) => [m, lib.docks[i]]).filter(([m]) => m >= 7 * 60 && m <= 11 * 60);
  over(ctx, 1 - morning, () => {
    text(ctx, "圖資站的車數", cx, cyy + 30, { size: 38, weight: 900, color: C.ink });
    text(ctx, "11/11（三）傍晚，紀錄器實際記到的", cx, cyy + 76, { size: 26, weight: 500, color: C.ink2 });
    const t1 = p(0, 3) + 1.0, upto = t < t1 ? lerp(15 * 60, 17 * 60 + 30, prog(t, 0.6, t1)) : lerp(17 * 60 + 30, 19 * 60, prog(t, t1, p(0, 4) + 1.4));   // reaches 0 bikes with the drawing on the left
    const G = lineChart(ctx, cx + 30, cyy + 150, cw - 60, chh - 120, eve, 15 * 60, 19 * 60, 25, upto, { grid: [10, 20], hours: [15, 16, 17, 18, 19] });
    ctx.save(); ctx.setLineDash([10, 8]); ctx.strokeStyle = C.orange; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(G.X(17 * 60), cyy + 130); ctx.lineTo(G.X(17 * 60), cyy + chh + 30); ctx.stroke(); ctx.restore();
    text(ctx, "17:00 下課", G.X(17 * 60) + 10, cyy + 140, { size: 26, weight: 700, color: C.orange });
    if (upto >= 17 * 60 + 30) pill(ctx, "17:30 借光", G.X(17 * 60 + 30) + 40, G.Y(0) - 50, { size: 28, fill: C.red, scale: pop(t, p(0, 3)) });
    if (upto >= 18 * 60 + 30) pill(ctx, "18:30 才補回來", G.X(18 * 60 + 30) - 30, G.Y(12) - 50, { size: 28, fill: C.ink2, scale: pop(t, p(0, 4) + 0.8) });
  });
  over(ctx, morning, () => {
    text(ctx, "圖資站的空位", cx, cyy + 30, { size: 38, weight: 900, color: C.ink });
    text(ctx, "11/11（三）早上，紀錄器實際記到的", cx, cyy + 76, { size: 26, weight: 500, color: C.ink2 });
    const upto = lerp(7 * 60, 11 * 60, prog(t, l1, l1 + 3.0));
    const G = lineChart(ctx, cx + 30, cyy + 150, cw - 60, chh - 120, mor, 7 * 60, 11 * 60, 25, upto, { grid: [10, 20], hours: [7, 8, 9, 10, 11], color: "#4C5BE0" });
    if (upto >= 9 * 60) pill(ctx, "09:00 停滿", G.X(9 * 60) + 40, G.Y(0) - 50, { size: 28, fill: "#4C5BE0", scale: pop(t, l1 + 1.6) });
  });
  sourceTag(ctx, "左：示意動畫；右：本組紀錄器，YouBike 開放資料", t, 0.6);
  fadeFrom(ctx, t, 0.3, C.paper);
}

// ---------- 4. the Friendship Relay: what it is, how many used it, and why it pays too late on campus ----------
function sceneRelay(ctx, t, T) {
  const p = (k, j) => PT("relay", k, j), l1 = LS("relay", 1), l2 = LS("relay", 2), l3 = LS("relay", 3);
  PAPER_BG(ctx);
  chapter(ctx, "現在的獎勵：友愛接力", t);
  // what it is
  over(ctx, 1 - prog(t, l1 - 0.4, l1 - 0.1), () => {
    headline(ctx, "友愛接力", 960, 210, t, p(0, 0) + 0.2, { size: 84, align: "center" });
    headline(ctx, "高雄 YouBike　2026 年 7 月起", 960, 268, t, p(0, 1), { size: 34, weight: 500, color: C.ink2, align: "center" });
    const panelAt = (x, a, title, full) => {
      const k = easeOut(prog(t, a, a + 0.5)); if (k <= 0) return;
      ctx.save(); ctx.globalAlpha *= k; ctx.translate(0, (1 - k) * 40);
      card(ctx, x, 320, 640, 360, { fill: C.white, r: 28 });
      text(ctx, title, x + 320, 384, { size: 40, weight: 900, color: C.ink, align: "center" });
      station(ctx, x + 110, 610, 52, { docks: 4, bikes: full ? 4 : 0, name: full ? "停滿" : "空站", empty: !full });
      ctx.strokeStyle = full ? C.green : C.blue; ctx.lineWidth = 8; ctx.lineCap = "round";
      const ax = x + 420, ay = 540; ctx.beginPath();
      if (full) { ctx.moveTo(ax - 40, ay); ctx.lineTo(ax + 60, ay); ctx.lineTo(ax + 30, ay - 26); ctx.moveTo(ax + 60, ay); ctx.lineTo(ax + 30, ay + 26); }
      else { ctx.moveTo(ax + 60, ay); ctx.lineTo(ax - 40, ay); ctx.lineTo(ax - 10, ay - 26); ctx.moveTo(ax - 40, ay); ctx.lineTo(ax - 10, ay + 26); }
      ctx.stroke();
      ctx.save(); ctx.translate(ax + 10, ay + 70); bike(ctx, 0, 0, 30, { face: full ? 1 : -1, color: "#FFFFFF", accent: C.blue }); ctx.restore();
      pill(ctx, "+5 元", x + 540, 440, { size: 36, fill: "#E8B83A", color: C.ink, scale: pop(t, a + 0.5) });
      ctx.restore();
    };
    panelAt(260, p(0, 2), "從停滿的站借車", true);
    panelAt(1020, p(0, 3), "把車還到空的站", false);
    voucher(ctx, 960, 800, pop(t, p(0, 4)), { note: "只能折抵 YouBike 車資，60 天內有效" });
  });
  // how many vouchers the pilot gave out
  over(ctx, easeOut(prog(t, l1 - 0.1, l1 + 0.3)) * (1 - prog(t, l2 - 0.4, l2 - 0.1)), () => {
    text(ctx, "北北桃試辦　發出的騎乘券", 960, 300, { size: 44, weight: 700, color: C.ink2, align: "center" });
    const n = Math.round(406 * easeOut(prog(t, p(1, 1), p(1, 1) + 1.3)));
    text(ctx, n + " 萬張", 960, 520, { size: 200, weight: 900, color: "#B7860F", align: "center" });
    headline(ctx, "44.5 萬人次參與", 960, 650, t, p(1, 2), { size: 60, color: C.ink, align: "center" });
    text(ctx, "累計至 2026 年 5 月底", 960, 720, { size: 30, weight: 500, color: C.muted, align: "center", alpha: prog(t, p(1, 2), p(1, 2) + 0.4) });
  });
  // why it is too late on campus
  over(ctx, easeOut(prog(t, l2 - 0.1, l2 + 0.3)) * (1 - prog(t, l3 - 0.4, l3 - 0.1)), () => {
    const x0 = 230, x1 = 1690, y = 600, X = (m) => lerp(x0, x1, (m - 14 * 60) / 360);
    headline(ctx, t < p(2, 1) ? "要等站空了，才給獎勵" : "對學校來說，太晚了", 960, 230, t, l2, { size: 64, align: "center" });
    const rk = easeOut(prog(t, p(2, 0) + 0.4, p(2, 0) + 0.9)), bk = easeOut(prog(t, p(2, 2), p(2, 2) + 0.5));
    ctx.fillStyle = rgba(C.red, 0.16 * rk); ctx.fillRect(X(17 * 60 + 25), y - 50, (X(19 * 60 + 30) - X(17 * 60 + 25)) * rk, 100);
    ctx.fillStyle = rgba(C.blue, 0.16 * bk); ctx.fillRect(X(15 * 60), y - 50, (X(17 * 60) - X(15 * 60)) * bk, 100);
    ctx.strokeStyle = C.ink2; ctx.lineWidth = 6; ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(x1, y); ctx.stroke();
    [14, 15, 16, 17, 18, 19, 20].forEach((hh) => { ctx.fillStyle = C.ink2; ctx.fillRect(X(hh * 60) - 2, y - 12, 4, 24); text(ctx, hh + ":00", X(hh * 60), y + 60, { size: 30, weight: 500, color: C.ink2, align: "center" }); });
    bellIcon(ctx, X(17 * 60), y - 92, 34, Math.sin(t * 8) * 0.25, C.orange);
    text(ctx, "下課", X(17 * 60), y - 148, { size: 32, weight: 700, color: C.orange, align: "center" });
    text(ctx, "友愛接力發獎勵的時候：站已經空了", (X(17 * 60 + 25) + X(19 * 60 + 30)) / 2, y + 140, { size: 32, weight: 700, color: C.red, align: "center", alpha: rk });
    text(ctx, "車要在這時候回來", (X(15 * 60) + X(17 * 60)) / 2, y + 140, { size: 34, weight: 700, color: C.blue, align: "center", alpha: bk });
    for (let i = 0; i < 6; i++) personIcon(ctx, X(17 * 60 + 22) + i * 36, y - 64, 30 * pop(t, p(2, 3) + i * 0.08), C.ink2);
  });
  // the returns before the bell, and the share the rule pays
  over(ctx, easeOut(prog(t, l3 - 0.1, l3 + 0.3)), () => {
    text(ctx, "每半小時騎回校內 8 站的車", 140, 170, { size: 50, weight: 900, color: C.ink });
    text(ctx, "12 個上課日平均，模型估計（台／天）", 140, 222, { size: 30, weight: 400, color: C.ink2 });
    const rows = DATA.timing, x0 = 180, x1 = 1760, y0 = 820, top = 360, n = rows.length, step = (x1 - x0) / n, bw = step * 0.72;
    const Y = (v) => y0 - (y0 - top) * v / 50, xb = x0 + 6 * step;
    ctx.strokeStyle = C.line; ctx.lineWidth = 2; [25, 50].forEach((g) => { ctx.beginPath(); ctx.moveTo(x0 - 20, Y(g)); ctx.lineTo(x1, Y(g)); ctx.stroke(); text(ctx, String(g), x0 - 34, Y(g) + 10, { size: 26, color: C.muted, align: "right" }); });
    const paidK = easeOut(prog(t, p(3, 3), p(3, 3) + 0.6)), glow = prog(t, p(3, 4), p(3, 4) + 0.4);
    rows.forEach((r, i) => {
      const k = easeOut(prog(t, p(3, 1) + i * 0.08, p(3, 1) + 0.5 + i * 0.08)); if (k <= 0) return;
      const x = x0 + i * step + (step - bw) / 2, ret = r[2] * k, pre = i < 6;
      ctx.fillStyle = pre && t > p(3, 2) ? mix(C.grey, "#9DB8D6", prog(t, p(3, 2), p(3, 2) + 0.4)) : C.grey;
      rrect(ctx, x, Y(ret), bw, y0 - Y(ret), 6); ctx.fill();
      if (paidK > 0 && r[3] > 0.05) { ctx.fillStyle = C.ink2; rrect(ctx, x, Y(r[3] * paidK), bw, y0 - Y(r[3] * paidK), 4); ctx.fill(); if (pre && glow > 0) { ctx.save(); ctx.strokeStyle = rgba(C.orange, glow); ctx.lineWidth = 5; rrect(ctx, x - 5, Y(r[3]) - 5, bw + 10, y0 - Y(r[3]) + 5, 6); ctx.stroke(); ctx.restore(); } }
      if (r[0].endsWith(":00")) text(ctx, r[0], x + bw / 2, y0 + 44, { size: 28, weight: 500, color: C.ink2, align: "center" });
    });
    ctx.save(); ctx.setLineDash([12, 10]); ctx.strokeStyle = C.ink; ctx.lineWidth = 4; ctx.beginPath(); ctx.moveTo(xb, top - 40); ctx.lineTo(xb, y0); ctx.stroke(); ctx.restore();
    text(ctx, "17:00 下課", xb + 16, top - 12, { size: 30, weight: 700, color: C.ink });
    if (t > p(3, 2)) { const k = easeOut(prog(t, p(3, 2), p(3, 2) + 0.5)); ctx.save(); ctx.globalAlpha *= k; ctx.strokeStyle = C.blue; ctx.lineWidth = 6; ctx.beginPath(); ctx.moveTo(x0 + 10, top - 22); ctx.lineTo(x0 + 10, top - 42); ctx.lineTo(xb - 20, top - 42); ctx.lineTo(xb - 20, top - 22); ctx.stroke(); ctx.restore(); pill(ctx, "七成在 17:00 前就到了", (x0 + xb) / 2, top - 84, { size: 36, fill: C.blue, scale: pop(t, p(3, 2)) }); }
    if (t > p(3, 3) && t < p(3, 4) + 0.3) { const k = easeOut(prog(t, p(3, 3), p(3, 3) + 0.5)) * (1 - prog(t, p(3, 4), p(3, 4) + 0.3)); card(ctx, 1040, 360, 760, 150, { fill: C.white, r: 22, alpha: k }); ctx.save(); ctx.globalAlpha *= k; ctx.fillStyle = C.ink2; rrect(ctx, 1076, 400, 36, 36, 8); ctx.fill(); ctx.restore(); text(ctx, "拿到 5 元騎乘券的車", 1130, 430, { size: 36, weight: 900, color: C.ink, alpha: k }); text(ctx, "站空了才給，多半在 17:00 以後", 1076, 482, { size: 30, weight: 500, color: C.ink2, alpha: k }); }
    if (t > p(3, 4)) { const s = pop(t, p(3, 4)); ctx.save(); ctx.translate(1420, 485); ctx.scale(s, s); card(ctx, -380, -100, 760, 200, { fill: C.white, r: 28 }); text(ctx, "3%", -230, 50, { size: 140, weight: 900, color: C.orange, align: "center" }); text(ctx, "17:00 前到的車", 110, -6, { size: 38, weight: 700, color: C.ink, align: "center" }); text(ctx, "拿到獎勵", 110, 50, { size: 38, weight: 700, color: C.ink, align: "center" }); ctx.restore(); }
  });
  sourceTag(ctx, t < l2 ? "友愛接力規則：中央社 2026-06-24；試辦數字：數位時代 2026-08-19（桃園市交通局）" : "來源：本組分析（報告 3.10 節）", t, 0.6);
  fadeFrom(ctx, t, 0.3, C.paper);
}

// ---------- 5. our approach: predict, pay before the bell, in ride time; tested on held-out days ----------
const WATCH = { "海資館": { g: [-150, 0], b: [0, 100] }, "材料大樓": { g: [20, -135], b: [0, -100] }, "體育館": { g: [-170, 10], b: [-170, 0] } };
const ideaSnap = () => PT("idea", 0, 2) + 0.3;
function ideaClock(t) { return t < ideaSnap() ? 16 * 60 + 20 : 16 * 60 + 30; }
function ideaChance(c, t) { const k = slotOf(16 * 60 + 20); return lerp(c.empty40[k] || 0, c.empty40[k + 1] || 0, easeInOut(prog(t, ideaSnap(), ideaSnap() + 0.9))); }
function crossAt(c) {
  const t0 = PT("idea", 0, 1) + 0.6;
  for (let s = 0; s <= 900; s++) { const tt = t0 + s * 0.01; if (ideaChance(c, tt) >= 0.5) return tt; }
  return 999;
}
function sceneIdea(ctx, t, T) {
  const p = (k, j) => PT("idea", k, j), L = [0, 1, 2, 3, 4, 5].map((k) => LS("idea", k));
  const part = t < L[1] - 0.15 ? 0 : t < L[2] - 0.15 ? 1 : t < L[3] - 0.15 ? 2 : t < L[4] - 0.15 ? 3 : t < L[5] - 0.15 ? 4 : 5;
  if (part === 0) {
    campusMap(ctx, MAP.scale, MAP.cx, MAP.cy);
    const m = ideaClock(t), k = slotAt(m), gk = prog(t, p(0, 1), p(0, 1) + 0.4), snap = prog(t, ideaSnap(), ideaSnap() + 0.7);
    DATA.campus.forEach((c) => {
      const [x, y] = stationXY(c), w = WATCH[c.name];
      if (w && gk > 0) { const gx = x + w.g[0], gy = y + w.g[1]; ctx.save(); ctx.globalAlpha = gk; ctx.strokeStyle = "rgba(255,255,255,0.45)"; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(gx, gy); ctx.stroke(); gauge(ctx, gx, gy, 50, ideaChance(c, t)); ctx.restore(); }
      stationDot(ctx, x, y, STR(c), bikeColor(c.bikes[k]), c.name, { num: c.bikes[k], side: SIDE[c.name] });
    });
    Object.keys(WATCH).forEach((n) => { const c = station8(n), [x, y] = stationXY(c), w = WATCH[n]; badge30(ctx, x + w.g[0] + w.b[0], y + w.g[1] + w.b[1], pop(t, Math.max(crossAt(c), p(0, 3) - 0.6))); });
    const tk = easeOut(prog(t, p(0, 0), p(0, 0) + 0.5));
    card(ctx, 1150, 70, 710, 250, { fill: "rgba(255,255,255,0.97)", r: 24, alpha: tk });
    pill(ctx, "提案", 1225, 126, { size: 30, fill: C.orange, alpha: tk });
    text(ctx, "預測型友愛接力", 1290, 144, { size: 54, weight: 900, color: C.ink, alpha: tk });
    text(ctx, "每 10 分鐘預測一次", 1190, 222, { size: 34, weight: 700, color: C.ink, alpha: easeOut(prog(t, p(0, 1), p(0, 1) + 0.4)) });
    text(ctx, "40 分鐘內借光機率 ≥ 50%，就提前開放", 1190, 276, { size: 30, weight: 500, color: C.ink2, alpha: easeOut(prog(t, p(0, 2), p(0, 2) + 0.4)) });
    card(ctx, 1150, 350, 710, 140, { fill: "rgba(255,255,255,0.97)", r: 24, alpha: tk });
    text(ctx, t < ideaSnap() ? "這一輪的預測" : "10 分鐘後，下一輪", 1190, 392, { size: 26, weight: 500, color: C.muted, alpha: tk });
    text(ctx, "11/11（三）", 1190, 452, { size: 32, weight: 500, color: C.ink2, alpha: tk });
    text(ctx, hhmm(m), 1820, 452, { size: 80, weight: 900, color: C.ink, align: "right", alpha: tk });
    if (snap > 0 && snap < 1) { ctx.save(); ctx.strokeStyle = rgba(C.orange, 1 - snap); ctx.lineWidth = 6; rrect(ctx, 1150 - 14 * snap, 350 - 14 * snap, 710 + 28 * snap, 140 + 28 * snap, 30); ctx.stroke(); ctx.restore(); }
    if (t > p(0, 3)) pill(ctx, "17:00 下課前就開放", 1505, 570, { size: 38, fill: C.blue, scale: pop(t, p(0, 3)) });
    chapter(ctx, "我們的做法", t, true);
    sourceTag(ctx, "11/11 的實際預測（網站重播資料的 reward 欄位）；海岸線為示意", t, p(0, 1), DIM);
    fadeFrom(ctx, t, 0.3, C.paper);
  } else if (part === 1) {
    // the data behind it: 309 stations, every 10 minutes since 1 October
    const tl = t - L[1];
    campusMap(ctx, 9800, 960, 560, { labelAlpha: 0 });
    let n = 0;
    DATA.all.forEach((q) => { const [x, y] = proj(q[0], q[1], 9800, 960, 560), d = Math.hypot(q[0] - CEN[0], (q[1] - CEN[1]) * KX), a = p(1, 1) - L[1] + 2.0 * d / 0.05, k = prog(tl, a, a + 0.35); if (k <= 0) return; n++; ctx.fillStyle = rgba("#7FB3E8", 0.85 * k); ctx.beginPath(); ctx.arc(x, y, 7 * k, 0, 7); ctx.fill(); });
    const ring = (tl % 2) / 2; ctx.strokeStyle = rgba("#7FB3E8", 1 - ring); ctx.lineWidth = 5; ctx.beginPath(); ctx.arc(960, 560, 40 + 480 * ring, 0, 7); ctx.stroke();
    text(ctx, "中山大學", 930, 572, { size: 34, weight: 700, color: C.yellow, align: "right" });
    headline(ctx, "我們自己記錄的資料", 110, 200, t, L[1], { size: 50, color: C.white });
    text(ctx, String(n), 110, 380, { size: 150, weight: 900, color: C.white });
    text(ctx, "個站", 130 + textW(ctx, String(n), 150, 900), 368, { size: 56, weight: 700, color: C.white });
    text(ctx, "中山大學 5 公里內", 114, 450, { size: 40, weight: 500, color: LIGHT, alpha: prog(tl, p(1, 1) - L[1], p(1, 1) - L[1] + 0.4) });
    headline(ctx, "10 月 1 日起，每 10 分鐘一筆", 114, 520, t, p(1, 2), { size: 40, weight: 700, color: C.yellow });
    chapter(ctx, "我們的做法", 9, true);
    sourceTag(ctx, "資料：YouBike 官方開放資料，本組紀錄器", t, L[1], DIM);
    fadeFrom(ctx, tl, 0.3);
  } else if (part === 2) {
    // tested on 12 held-out teaching days
    const tl = t - L[2];
    PAPER_BG(ctx);
    const days = DATA.test_days;
    text(ctx, "12 個模型沒看過的上課日", 140, 170, { size: 50, weight: 900, color: C.ink });
    ["一", "二", "三", "四", "五", "六", "日"].forEach((d, i) => text(ctx, d, 192 + i * 120, 262, { size: 28, color: C.muted, align: "center" }));
    for (let i = 0; i < 28; i++) {
      const dt = new Date(Date.UTC(2026, 9, 26 + i)), col = i % 7, row = Math.floor(i / 7), x = 140 + col * 120, y = 285 + row * 120;
      const iso = dt.toISOString().slice(0, 10), order = days.indexOf(iso), kk = order >= 0 ? pop(t, p(2, 0) + 0.3 + order * 0.1) : 0;
      rrect(ctx, x, y, 104, 104, 16); ctx.fillStyle = col > 4 ? "#ECE8E0" : C.white; ctx.fill();
      if (kk > 0) { ctx.save(); ctx.translate(x + 52, y + 52); ctx.scale(kk, kk); rrect(ctx, -52, -52, 104, 104, 16); ctx.fillStyle = C.blue; ctx.fill(); ctx.restore(); }
      text(ctx, (dt.getUTCDate() === 1 ? "11/" : "") + dt.getUTCDate(), x + 52, y + 66, { size: dt.getUTCDate() === 1 ? 32 : 38, weight: 700, color: kk > 0.5 ? C.white : C.ink2, align: "center" });
    }
    const k = easeOut(prog(t, p(2, 1), p(2, 1) + 0.5));
    ctx.save(); ctx.globalAlpha *= k;
    text(ctx, "91%", 1060, 420, { size: 200, weight: 900, color: C.blue });
    text(ctx, "的空站，事先被抓到", 1070, 500, { size: 48, weight: 700, color: C.ink });
    ctx.restore();
    const x0 = 1070, x1 = 1780, y = 720;
    if (t > p(2, 2) - 0.2) {
      ctx.strokeStyle = C.ink2; ctx.lineWidth = 4; ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(x1, y); ctx.stroke();
      [[0.42, 0], [0.86, 1]].forEach(([f, i]) => {
        const xe = lerp(x0, x1, f), xf = xe - 200, kk = prog(t, p(2, 2) + i * 0.5, p(2, 2) + 0.4 + i * 0.5);
        ctx.fillStyle = C.red; ctx.beginPath(); ctx.arc(xe, y, 16, 0, 7); ctx.fill(); text(ctx, "借空", xe, y + 52, { size: 28, weight: 700, color: C.red, align: "center" });
        if (kk > 0) { ctx.save(); ctx.globalAlpha *= kk; ctx.strokeStyle = C.blue; ctx.lineWidth = 5; ctx.beginPath(); ctx.moveTo(xf, y); ctx.lineTo(xf, y - 70); ctx.stroke(); ctx.fillStyle = C.blue; ctx.beginPath(); ctx.moveTo(xf, y - 70); ctx.lineTo(xf + 44, y - 58); ctx.lineTo(xf, y - 46); ctx.fill(); text(ctx, "提早約 40 分鐘", (xf + xe) / 2 + 10, y - 18, { size: 24, weight: 700, color: C.blue, align: "center" }); ctx.restore(); }
      });
    }
    chapter(ctx, "我們的做法", 9);
    sourceTag(ctx, "來源：報告 3.10 節，219 次借空事件，被標出的站 62% 在 40 分鐘內真的借空（平均 25%）", t, L[2]);
    fadeFrom(ctx, tl, 0.3, C.paper);
  } else if (part === 3) {
    // the reward in ride time
    const tl = t - L[3];
    PAPER_BG(ctx);
    text(ctx, "獎勵改成一小時免費騎乘", 960, 170, { size: 64, weight: 900, color: C.ink, align: "center", alpha: easeOut(prog(tl, 0, 0.4)) });
    voucher(ctx, 600, 360, 0.9 * pop(t, L[3] + 0.1), { note: "現在的友愛接力" });
    const ak = easeOut(prog(t, L[3] + 0.8, L[3] + 1.2));
    ctx.save(); ctx.globalAlpha *= ak; ctx.strokeStyle = C.ink; ctx.lineWidth = 10; ctx.lineCap = "round"; ctx.lineJoin = "round"; ctx.beginPath(); ctx.moveTo(870, 360); ctx.lineTo(1030, 360); ctx.moveTo(995, 324); ctx.lineTo(1030, 360); ctx.lineTo(995, 396); ctx.stroke(); ctx.restore();
    const bk = pop(t, L[3] + 1.1);
    if (bk > 0) { ctx.save(); ctx.translate(1330, 360); ctx.scale(bk, bk); card(ctx, -220, -130, 440, 260, { fill: C.white, r: 36, stroke: C.blue, lw: 8 }); clockIcon(ctx, -120, 0, 58, C.blue); text(ctx, "1 小時", 70, 12, { size: 76, weight: 900, color: C.blue, align: "center" }); text(ctx, "免費騎乘", 70, 70, { size: 38, weight: 700, color: C.ink, align: "center" }); ctx.restore(); }
    // who already rides the first 30 minutes free, on a 0-60 minute bar: pass holders gain the second half hour,
    // other members (who pay NT$5 for the first) ride the whole hour free
    const X0 = 620, X1 = 1580, half = (X1 - X0) / 2, bh = 74;
    const row = (y, label, sub, a0, segs) => {
      const k = easeOut(prog(t, a0, a0 + 0.4)); if (k <= 0) return;
      ctx.save(); ctx.globalAlpha *= k;
      text(ctx, label, X0 - 30, y + 12, { size: 40, weight: 900, color: C.ink, align: "right" });
      text(ctx, sub, X0 - 30, y + 52, { size: 24, weight: 500, color: C.ink2, align: "right" });
      segs.forEach(([from, to, fill, txt, col, at]) => {
        const g = easeOut(prog(t, at, at + 0.45)); if (g <= 0) return;
        const x = X0 + from * half, w = (to - from) * half * g;
        rrect(ctx, x + 3, y - bh / 2, Math.max(0, w - 6), bh, 16); ctx.fillStyle = fill; ctx.fill();
        if (g > 0.6) text(ctx, txt, x + (to - from) * half / 2, y + 12, { size: 32, weight: 800, color: col, align: "center", alpha: (g - 0.6) / 0.4 });
      });
      ctx.restore();
    };
    row(600, "月票、學生卡", "TPASS、MeNGo、學生認同卡", p(3, 1), [[0, 1, "#D7DEE5", "本來就免費", C.ink2, p(3, 2)], [1, 2, C.green, "+30 分鐘免費", C.white, p(3, 3)]]);
    row(760, "一般會員", "前 30 分鐘原本付 5 元", p(3, 3) + 0.5, [[0, 2, C.green, "一小時內都免費", C.white, p(3, 3) + 0.7]]);
    const tk = easeOut(prog(t, p(3, 1), p(3, 1) + 0.4));
    if (tk > 0) [["0", 0], ["30 分", 1], ["60 分", 2]].forEach(([s, i]) => text(ctx, s, X0 + i * half, 870, { size: 26, weight: 600, color: C.ink2, align: "center", alpha: tk }));
    chapter(ctx, "我們的做法", 9);
    sourceTag(ctx, "費率：YouBike 高雄官網（TPASS、MeNGo、學生認同卡前 30 分鐘免費；會員前 30 分鐘市府補助 5 元）", t, L[3]);
    fadeFrom(ctx, tl, 0.3, C.paper);
  } else if (part === 4) {
    // and riding is exercise
    const tl = t - L[4];
    PAPER_BG(ctx);
    text(ctx, "將近一半的人", 140, 260, { size: 100, weight: 900, color: C.orange, alpha: easeOut(prog(tl, 0, 0.4)) });
    headline(ctx, "每週身體活動不到 150 分鐘", 140, 350, t, p(4, 1), { size: 56, weight: 700 });
    for (let i = 0; i < 10; i++) personIcon(ctx, 220 + i * 150, 640, 86 * pop(t, p(4, 1) + 0.2 + i * 0.1), i < 5 ? C.orange : "#B9C4CC");
    headline(ctx, "多騎一段路，也算身體活動", 140, 800, t, p(4, 1) + 1.6, { size: 40, weight: 700, color: C.blue });
    chapter(ctx, "我們的做法", 9);
    sourceTag(ctx, "資料：國民健康署調查（公視新聞網 2020-06-11）；WHO 2020 身體活動指引", t, L[4]);
    fadeFrom(ctx, tl, 0.3, C.paper);
  } else {
    // New York and Paris have rewarded riders this way
    const tl = t - L[5];
    PAPER_BG(ctx);
    const k1 = easeOut(prog(tl, 0.1, 0.6)), k2 = easeOut(prog(tl, 0.5, 1.0));
    const cardAt = (x, k, draw) => { if (k <= 0) return; ctx.save(); ctx.globalAlpha *= k; ctx.translate(x, 230 + (1 - k) * 60); draw(); ctx.restore(); };
    cardAt(110, k1, () => {
      card(ctx, 0, 0, 800, 560, { fill: C.white, r: 30 });
      [[40, 140, 60], [104, 220, 74], [182, 170, 58], [244, 250, 70], [318, 200, 64], [386, 120, 80]].forEach(([x, h, w]) => {
        const x2 = x + 40; ctx.fillStyle = "#33465C"; ctx.fillRect(x2, 300 - h, w, h);
        ctx.fillStyle = "#F6D58A"; for (let wy = 300 - h + 14; wy < 284; wy += 26) for (let wx = x2 + 10; wx < x2 + w - 14; wx += 20) if (rnd(wx * 7 + wy) > 0.45) ctx.fillRect(wx, wy, 9, 12);
      });
      text(ctx, "紐約 Citi Bike", 40, 400, { size: 50, weight: 900, color: C.ink });
      text(ctx, "照各站「接下來」缺多少車給點數", 40, 460, { size: 34, weight: 500, color: C.ink2 });
      text(ctx, "點數可換騎乘額度", 40, 510, { size: 30, weight: 500, color: C.muted });
      pill(ctx, "預測", 690, 70, { size: 34, fill: C.blue });
    });
    cardAt(1010, k2, () => {
      card(ctx, 0, 0, 800, 560, { fill: C.white, r: 30 });
      ctx.fillStyle = "#7A9C6E"; ctx.beginPath(); ctx.moveTo(40, 300); ctx.quadraticCurveTo(300, 45, 560, 300); ctx.closePath(); ctx.fill();
      ctx.save(); ctx.translate(200, 210); ctx.rotate(-0.38); bike(ctx, 0, 0, 34, { color: "#FFFFFF", accent: C.green }); ctx.restore();
      text(ctx, "巴黎 Vélib'", 40, 400, { size: 50, weight: 900, color: C.ink });
      text(ctx, "把車還到山上的站，送 15 分鐘", 40, 460, { size: 34, weight: 500, color: C.ink2 });
      text(ctx, "2008 年起", 40, 510, { size: 30, weight: 500, color: C.muted });
      pill(ctx, "送時間", 670, 70, { size: 34, fill: C.green });
    });
    chapter(ctx, "我們的做法", 9);
    sourceTag(ctx, "來源：Citi Bike Bike Angels 說明頁；Big Medium 2008-10-17", t, L[5]);
    fadeFrom(ctx, tl, 0.3, C.paper);
  }
}

// ---------- 6. demo: how to use the site, with the part being talked about magnified ----------
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
  const p = (k, j) => PT("demo", k, j), L = [0, 1, 2, 3, 4].map((k) => LS("demo", k));
  bg(ctx, "#0E1C2B", "#1C3D63");
  const tDock = L[2] - 0.1, tPol = L[3] - 0.1, tTable = p(3, 2), tSim = L[4] - 0.1, t50 = p(4, 1) + 0.5;
  let key = "rider_1640";
  if (t > tDock) key = "dock_0920";
  if (t > tPol) key = "policy_map";
  if (t > tTable) key = "policy_table";
  if (t > tSim) key = "sim_0";
  if (t > t50) key = "sim_50";
  const img = IMG[key + ".jpg"], R = RECTS;
  const enter = easeOut(prog(t, 0.1, 0.9));
  const ph = phone(ctx, 90, 80 + (1 - enter) * 1000, 410, img);
  const s = ph.w / img.width, P = (r) => [ph.x + r[0] * s, ph.y + r[1] * s, r[2] * s, r[3] * s];
  const box = [600, 290, 1260, 600];
  const say = (a, b, title, sub, color = C.white) => { const k = fadeIO(t, a, b, 0.25); if (k <= 0) return; text(ctx, title, 600, 160 + (1 - k) * 20, { size: 58, weight: 900, color, alpha: k }); if (sub) text(ctx, sub, 602, 226 + (1 - k) * 20, { size: 34, weight: 500, color: LIGHT, alpha: k }); };
  const win = (a, b) => fadeIO(t, a, b, 0.25);
  const tapAt = (r, a) => { const q = P(r); tap(ctx, q[0] + q[2] / 2, q[1] + q[3] / 2, t, a); };
  // the site
  say(0.4, L[1], "Beat the Bell 網站", "alexlin8888.github.io/nsysu-youbike-log");
  { const k = win(0.6, L[1]); if (k > 0) { text(ctx, "手機打開就能用，每 10 分鐘自動更新", 602, 330, { size: 36, weight: 500, color: LIGHT, alpha: k }); ["借車", "還車", "政策", "調度"].forEach((s2, i) => pill(ctx, s2, 680 + i * 170, 430, { size: 36, fill: [C.blue, "#4C5BE0", C.orange, C.ink2][i], alpha: k, scale: pop(t, 0.9 + i * 0.15) })); } }
  // rider tab: where am I, then where to go and the latest time to leave
  say(L[1], tDock, "借車：去哪一站、最晚幾點出發", "例：16:40 從圖資大樓出發");
  { const M = magnify(ctx, IMG["rider_1640.jpg"], [24, 985, 732, 150], ph, box, key === "rider_1640" ? win(p(1, 1) - 0.2, p(1, 2) - 0.1) : 0); if (M) hilite(ctx, ...M(R.rider_1640.from), t, p(1, 1) + 0.2, C.yellow); }
  if (key === "rider_1640") tapAt(R.rider_1640.from, p(1, 1));
  { const M = magnify(ctx, IMG["rider_1640.jpg"], [24, 1262, 732, 290], ph, box, key === "rider_1640" ? win(p(1, 2) - 0.1, tDock) : 0); if (M) { hilite(ctx, ...M(R.rider_1640.best), t, p(1, 2) + 0.2, C.yellow); hilite(ctx, ...M(R.rider_1640.tip), t, p(1, 4), C.yellow); } }
  if (key === "rider_1640") tapAt(R.rider_1640.tabDock, tDock - 0.35);
  // dock tab in the morning
  say(tDock, tPol, "還車：哪一站還有位子", "例：09:20 要騎到工學院");
  { const M = magnify(ctx, IMG["dock_0920.jpg"], [24, 1262, 732, 290], ph, box, key === "dock_0920" ? win(tDock + 0.1, tPol) : 0); if (M) { hilite(ctx, ...M(R.dock_0920.best), t, p(2, 1), C.yellow); hilite(ctx, ...M(R.dock_0920.tip), t, p(2, 2), C.yellow); } }
  if (key === "dock_0920") tapAt(R.dock_0920.tabPolicy, tPol - 0.35);
  // policy tab: where the reward should be paid now
  say(tPol, tSim, "政策：現在該發獎勵的站", "11/11（三）16:30");
  { const M = magnify(ctx, IMG["policy_map.jpg"], [120, 300, 560, 440], ph, box, key === "policy_map" ? win(tPol + 0.1, tTable) : 0);
    if (M) R.policy_map.glyphs.filter((g) => g.mark && g.rect[1] > 300 && g.rect[1] < 740).forEach((g, i) => { const q = M(g.rect), pulse = 0.5 + 0.5 * Math.sin(t * 6 + i); ctx.save(); ctx.strokeStyle = rgba(C.orange, prog(t, p(3, 1) + i * 0.2, p(3, 1) + 0.3 + i * 0.2)); ctx.lineWidth = 7; ctx.beginPath(); ctx.arc(q[0] + q[2] / 2, q[1] + q[3] / 2, q[2] * 0.85 + 10 * pulse, 0, 7); ctx.stroke(); ctx.restore(); }); }
  { const M = magnify(ctx, IMG["policy_table.jpg"], [24, 304, 732, 446], ph, box, key === "policy_table" ? win(tTable, tSim) : 0);
    if (M) [0, 1, 2].forEach((i) => hilite(ctx, ...M(R.policy_table.rows[i].pred), t, tTable + 0.3 + i * 0.25, C.orange)); }
  // the what-if below it
  say(tSim, T + 1, "試算：還車的人多一半", "按下「多 50%」，網站算出借不到車的人會少多少", C.yellow);
  { const k = key === "sim_0" || key === "sim_50" ? win(tSim + 0.1, p(4, 4) - 0.1) : 0, M = magnify(ctx, IMG[key === "sim_0" ? "sim_0.jpg" : "sim_50.jpg"], [24, 180, 732, 348], ph, box, k); if (M) { const c = M(R.sim_0.chip50); tap(ctx, c[0] + c[2] / 2, c[1] + c[3] / 2, t, t50 - 0.3); } }
  if (key === "sim_0") tapAt(R.sim_0.chip50, t50 - 0.3);
  { const M = magnify(ctx, IMG["sim_50.jpg"], [40, 680, 700, 290], ph, box, key === "sim_50" ? prog(t, p(4, 4) - 0.1, p(4, 4) + 0.2) : 0); if (M) { hilite(ctx, ...M(R.sim_50.simBig), t, p(4, 4) + 0.3, C.orange); hilite(ctx, ...M(R.sim_50.simBars), t, p(4, 4) + 1.0, C.orange); } }
  chapter(ctx, "怎麼用", t, true);
  sourceTag(ctx, "畫面：本組網站，重播 2026/11/11（三）", t, 0.6, DIM);
  fadeFrom(ctx, t, 0.3);
}

// ---------- 7. impact: how many fewer people are turned away, the extra riding, and the brief ----------
function sceneImpact(ctx, t, T) {
  const p = (k, j) => PT("impact", k, j), L = [0, 1, 2, 3].map((k) => LS("impact", k));
  PAPER_BG(ctx);
  chapter(ctx, "改善多少", t);
  over(ctx, 1 - prog(t, L[2] - 0.35, L[2] - 0.05), () => {
    text(ctx, "每天傍晚借不到車的人次", 140, 190, { size: 52, weight: 900, color: C.ink });
    text(ctx, "校內 8 站，15:00–20:00，模型估計，12 個上課日平均", 140, 242, { size: 28, weight: 400, color: C.ink2 });
    const rows = [["現在", 204, C.grey, p(0, 0)], ["光靠獎勵（還車的人多一半）", 181, C.blue, p(0, 1)], ["獎勵＋下課前補兩趟車", 148, C.orange, p(1, 0)]];
    const x0 = 140, wmax = 1200, sc = wmax / 204;
    rows.forEach(([lab, v, col, a], i) => {
      const k = easeOut(prog(t, a, a + 0.7)); if (k <= 0) return;
      const y = 330 + i * 190;
      text(ctx, lab, x0, y, { size: 34, weight: 700, color: C.ink, alpha: prog(t, a, a + 0.3) });
      rrect(ctx, x0, y + 22, v * sc * k, 90, 14); ctx.fillStyle = col; ctx.fill();
      text(ctx, String(Math.round(v * k)), x0 + v * sc * k + 24, y + 88, { size: 56, weight: 900, color: C.ink });
    });
    if (t > p(0, 2)) pill(ctx, "−23 人次", 140 + 181 * (1200 / 204) + 260, 330 + 190 + 67, { size: 38, fill: C.blue, scale: pop(t, p(0, 2)) });
    if (t > p(1, 1)) pill(ctx, "−56 人次", 140 + 148 * (1200 / 204) + 260, 330 + 380 + 67, { size: 38, fill: C.orange, scale: pop(t, p(1, 1)) });
    if (t > p(1, 2)) { const s = pop(t, p(1, 2)); ctx.save(); ctx.translate(1620, 190); ctx.scale(s, s); card(ctx, -200, -130, 400, 260, { fill: C.white, r: 30 }); text(ctx, "−27%", 0, 20, { size: 110, weight: 900, color: C.orange, align: "center" }); text(ctx, "少了四分之一以上", 0, 86, { size: 32, weight: 700, color: C.ink, align: "center" }); ctx.restore(); }
  });
  over(ctx, easeOut(prog(t, L[2] - 0.05, L[2] + 0.35)) * (1 - prog(t, L[3] - 0.35, L[3] - 0.05)), () => {
    text(ctx, "也多了騎車的人", 960, 220, { size: 60, weight: 900, color: C.ink, align: "center" });
    const k1 = pop(t, p(2, 0)), k2 = pop(t, p(2, 1));
    if (k1 > 0) { ctx.save(); ctx.translate(560, 560); ctx.scale(k1, k1); card(ctx, -330, -230, 660, 460, { fill: C.white, r: 34 }); ctx.save(); ctx.translate(0, -18); rider(ctx, 0, 40, 70, { t, expr: "happy" }); ctx.restore(); text(ctx, "+25 趟", 0, 130, { size: 84, weight: 900, color: C.blue, align: "center" }); text(ctx, "每天多騎回學校", 0, 186, { size: 34, weight: 700, color: C.ink2, align: "center" }); ctx.restore(); }
    if (k2 > 0) { ctx.save(); ctx.translate(1360, 560); ctx.scale(k2, k2); card(ctx, -330, -230, 660, 460, { fill: C.white, r: 34 }); clockIcon(ctx, 0, -70, 90, C.green); text(ctx, "+69 小時", 0, 130, { size: 84, weight: 900, color: C.green, align: "center" }); text(ctx, "每天送出的免費騎乘", 0, 186, { size: 34, weight: 700, color: C.ink2, align: "center" }); ctx.restore(); }
  });
  over(ctx, easeOut(prog(t, L[3] - 0.05, L[3] + 0.35)), () => {
    const img = IMG["brief.jpg"], k = easeOut(prog(t, L[3], L[3] + 0.6));
    ctx.save(); ctx.translate(470, 520 + (1 - k) * 160); ctx.rotate(-0.035); ctx.shadowColor = "rgba(16,32,47,0.3)"; ctx.shadowBlur = 40; ctx.shadowOffsetY = 16; const bw = 540, bh = bw * img.height / img.width; ctx.drawImage(img, -bw / 2, -bh / 2, bw, bh); ctx.restore();
    text(ctx, "一頁建議書", 900, 200, { size: 64, weight: 900, color: C.ink });
    ["國立中山大學總務處", "高雄市政府交通局", "微笑單車高雄營運團隊"].forEach((s2, i) => pill(ctx, s2, 1180, 300 + i * 90, { size: 36, fill: [C.blue, C.green, C.orange][i], scale: pop(t, p(3, 1) + i * 0.25) }));
    const kk = easeOut(prog(t, p(3, 2), p(3, 2) + 0.4));
    text(ctx, "建議：校內 8 站試辦四週", 900, 640, { size: 54, weight: 900, color: C.ink, alpha: kk });
    ["現行", "預測型", "現行", "預測型"].forEach((s2, i) => { const q = pop(t, p(3, 2) + 0.3 + i * 0.18); if (q <= 0) return; ctx.save(); ctx.translate(1000 + i * 210, 770); ctx.scale(q, q); rrect(ctx, -95, -60, 190, 120, 18); ctx.fillStyle = i % 2 ? C.blue : "#9AA3AD"; ctx.fill(); text(ctx, "第 " + (i + 1) + " 週", 0, -12, { size: 28, weight: 500, color: C.white, align: "center" }); text(ctx, s2, 0, 34, { size: 34, weight: 900, color: C.white, align: "center" }); ctx.restore(); });
    text(ctx, "單雙週輪流，量實際有多少人參與、沒車的時間少多少", 900, 890, { size: 30, weight: 500, color: C.ink2, alpha: prog(t, p(3, 3), p(3, 3) + 0.4) });
  });
  sourceTag(ctx, t < L[3] ? "來源：報告 3.10 節；網站「政策」分頁的試算" : "建議書：alexlin8888.github.io/nsysu-youbike-log/policy_brief.pdf", t, 0.6);
  fadeFrom(ctx, t, 0.3, C.paper);
}

// ---------- 8. ending: the next bell, and there is a bike ----------
function sceneEnding(ctx, t, T) {
  const p = (j) => PT("ending", 0, j), tl = t;
  if (tl < p(2) + 2.2) {
    campusStreet(ctx, t, 0.8);
    const took = t > p(2) + 0.6;
    station(ctx, 860, 880, 90, { docks: 7, bikes: took ? 6 : 7, skip: took ? 1 : 0, name: "圖資站" });
    pill(ctx, "17:00", 170, 120, { size: 40, fill: C.orange });
    bellIcon(ctx, 290, 118, 26, Math.sin(t * 9) * 0.3 * (1 - prog(tl, 0, 1.5)), C.orange);
    if (t < p(1) + 1.2) student(ctx, lerp(-100, 1020, easeOut(prog(t, p(1) - 0.6, p(1) + 1.2))), 880, 115, { pose: "walk", t, expr: "happy" });
    else if (!took) student(ctx, 1020, 880, 115, { pose: "cheer", t, expr: "happy" });
    else rider(ctx, 1000 + (t - p(2) - 0.6) * 600, 880, 108, { t, expr: "happy" });
    [[0.6, 600, 0], [1.1, 420, 1]].forEach(([dd, xe, i]) => { const k = easeOut(prog(tl, dd, dd + 1.4)); student(ctx, lerp(-160, xe, k), 880, 100, { pose: k < 1 ? "walk" : "stand", t, pal: MATES[i], expr: "happy" }); });
    sourceTag(ctx, "示意動畫", t, 0.4, C.ink2);
    fadeFrom(ctx, t, 0.3);
    wipe(ctx, t, p(2) + 1.8, p(2) + 2.6);
  } else {
    seaside(ctx, t, 1.15);
    rider(ctx, -100 + (t - p(2) - 2.2) * 300, 950, 115, { t, expr: "happy" });
    pill(ctx, "17:05　騎去西子灣", 230, 120, { size: 38, fill: C.navy, alpha: prog(t, p(2) + 2.5, p(2) + 2.9) });
    fadeTo(ctx, t, T, 0.8);
  }
}

// ---------- 9. end card ----------
function sceneEnd(ctx, t, T) {
  NAVY_BG(ctx);
  const k = easeOut(prog(t, 0.1, 0.7));
  bellIcon(ctx, 960, 200, 60, Math.sin(t * 5) * 0.15, C.yellow);
  text(ctx, "Beat the Bell", 960, 350, { size: 110, weight: 900, color: C.white, align: "center", alpha: k });
  text(ctx, "alexlin8888.github.io/nsysu-youbike-log", 960, 440, { size: 46, weight: 700, color: C.yellow, align: "center", alpha: k });
  text(ctx, "國立中山大學　人工智慧導論（TAICA）第 54 組", 960, 550, { size: 38, weight: 500, color: LIGHT, align: "center", alpha: easeOut(prog(t, 0.4, 1.0)) });
  text(ctx, "林沛霆　陳佳晨　林詩穎", 960, 615, { size: 44, weight: 700, color: C.white, align: "center", alpha: easeOut(prog(t, 0.5, 1.1)) });
  ["資料：YouBike 官方開放資料（本組紀錄器）；臺大周邊騎乘資料（tses89214/youbike-historical-data）",
    "友愛接力：中央社、數位時代；票價：YouBike 高雄；健康數據：國民健康署、WHO；國外案例：Citi Bike、Vélib'；地圖：OpenStreetMap",
    "動畫、音樂與音效：本組自製；阿哲為虛構角色"].forEach((s, i) => text(ctx, s, 960, 770 + i * 50, { size: 28, weight: 400, color: DIM, align: "center", alpha: easeOut(prog(t, 0.9 + i * 0.15, 1.5 + i * 0.15)) }));
  fadeFrom(ctx, t, 0.4);
  fadeTo(ctx, t, T, 0.6, "#000000");
}

const SCENES = { hook: sceneHook, title: sceneTitle, cause: sceneCause, relay: sceneRelay, idea: sceneIdea, demo: sceneDemo, impact: sceneImpact, ending: sceneEnding, end: sceneEnd };

// Sound effects, in seconds from the video start, placed on the same timeline as the picture they belong to.
// audio.py reads this list through the browser.
window.sfxEvents = function () {
  const E = [], at = (scene, t, name, gain = 1) => E.push({ t: +(sceneOf(scene).start + t).toFixed(3), name, gain });
  const H = (k, j) => PT("hook", k, j), tRun = H(0, 1), tOut = tRun + 1.2, tMap = H(0, 3) - 0.2;
  at("hook", 0.45, "school_bell", 0.85);
  at("hook", tRun + 0.05, "whoosh", 0.45); at("hook", tOut - 0.4, "whoosh", 0.7);
  for (let k = 0; k < 4; k++) at("hook", tOut + 0.05 + k * 0.22, "step", 0.3);
  at("hook", H(0, 2), "bonk", 0.8); at("hook", tMap - 0.4, "whoosh", 0.6);
  for (let i = 0; i < 3; i++) at("hook", H(0, 3) + i * 0.35, "alert", 0.3);
  at("hook", H(1, 1), "pop", 0.5);
  for (let i = 0; i < 5; i++) at("hook", LS("hook", 2) + 1.4 + i * 0.25, "blip", 0.25);
  at("hook", LS("hook", 2) + 0.9, "zoom", 0.4);
  at("title", 0.05, "whoosh", 0.6); at("title", 0.25, "ding", 0.55);
  const Cc = (k, j) => PT("cause", k, j);
  at("cause", Cc(0, 1), "school_bell_short", 0.55);
  for (let i = 0; i < 7; i++) at("cause", Cc(0, 2) + 0.2 + (i + 1) * (Cc(0, 3) + 1.0 - Cc(0, 2) - 0.2) / 7, "tick", 0.3);
  at("cause", Cc(0, 3), "pop", 0.45); at("cause", Cc(0, 4) + 0.8, "pop", 0.35);
  at("cause", LS("cause", 1) - 0.3, "whoosh", 0.4); at("cause", Cc(1, 2), "bonk", 0.45);
  const R = (k, j) => PT("relay", k, j);
  at("relay", R(0, 0) + 0.2, "chime", 0.5); at("relay", R(0, 2), "pop", 0.45); at("relay", R(0, 3), "pop", 0.45); at("relay", R(0, 4), "ding", 0.6);
  at("relay", R(1, 1), "sparkle", 0.45); at("relay", R(1, 2), "pop", 0.4);
  at("relay", R(2, 0) + 0.4, "alert", 0.4); at("relay", R(2, 2), "pop", 0.4);
  for (let i = 0; i < 12; i++) at("relay", R(3, 1) + i * 0.08, "blip", 0.14);
  at("relay", R(3, 2), "pop", 0.5); at("relay", R(3, 4), "bonk", 0.55);
  Object.keys(WATCH).forEach((n) => { const x = Math.max(crossAt(station8(n)), PT("idea", 0, 3) - 0.6); if (x < 900) at("idea", x, "ding", 0.5); });
  at("idea", ideaSnap(), "notify", 0.4); at("idea", PT("idea", 0, 3), "pop", 0.45);
  const I = (k) => LS("idea", k);
  at("idea", I(1) - 0.1, "whoosh", 0.45); at("idea", PT("idea", 1, 1), "sparkle", 0.3);
  at("idea", I(2) - 0.1, "whoosh", 0.4); for (let i = 0; i < 12; i++) at("idea", PT("idea", 2, 0) + 0.3 + i * 0.1, "blip", 0.14); at("idea", PT("idea", 2, 1), "pop", 0.55);
  at("idea", I(3) - 0.1, "whoosh", 0.4); at("idea", I(3) + 1.1, "chime", 0.6);
  at("idea", I(4) - 0.1, "whoosh", 0.35); for (let i = 0; i < 10; i++) at("idea", PT("idea", 4, 1) + 0.2 + i * 0.1, "blip", 0.16);
  at("idea", I(5) - 0.1, "whoosh", 0.35); at("idea", I(5) + 0.1, "pop", 0.4); at("idea", I(5) + 0.5, "pop", 0.4);
  const D = (k, j) => PT("demo", k, j), DL = (k) => LS("demo", k);
  at("demo", 0.1, "whoosh", 0.55); at("demo", D(1, 1), "tap", 0.6); at("demo", D(1, 2) - 0.1, "swipe", 0.35);
  at("demo", DL(2) - 0.45, "tap", 0.6); at("demo", DL(3) - 0.45, "tap", 0.6); at("demo", D(3, 2), "swipe", 0.35);
  at("demo", D(4, 1) + 0.2, "tap", 0.65); at("demo", D(4, 4), "pop", 0.45);
  const M = (k, j) => PT("impact", k, j), ML = (k) => LS("impact", k);
  at("impact", M(0, 0), "pop", 0.35); at("impact", M(0, 1), "pop", 0.35); at("impact", M(0, 2), "ding", 0.45); at("impact", M(1, 0), "pop", 0.4); at("impact", M(1, 1), "ding", 0.5); at("impact", M(1, 2), "chime", 0.6);
  at("impact", ML(2) - 0.1, "whoosh", 0.4); at("impact", M(2, 0), "pop", 0.45); at("impact", M(2, 1), "pop", 0.45);
  at("impact", ML(3) - 0.1, "whoosh", 0.45); for (let i = 0; i < 3; i++) at("impact", M(3, 1) + i * 0.25, "pop", 0.3); at("impact", M(3, 2) + 0.3, "pop", 0.35);
  const N = (j) => PT("ending", 0, j);
  at("ending", 0.0, "school_bell_soft", 0.65); at("ending", N(2) + 0.6, "bike_bell", 0.65); at("ending", N(2) + 1.8, "whoosh", 0.45);
  at("end", 0.1, "ding", 0.45);
  return E.sort((a, b) => a.t - b.t);
};
