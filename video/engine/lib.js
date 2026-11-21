// Drawing library of the video. Everything is drawn on one 1920x1080 canvas from a time value, so that a frame
// depends only on (scene, t) and the renderer can step through time at 30 frames a second.
"use strict";

const W = 1920, H = 1080;
const C = {
  navy: "#10202F", ink: "#1F2A37", ink2: "#4A5563", muted: "#8A96A3", paper: "#F7F4EE", white: "#FFFFFF",
  blue: "#2A78D6", blueD: "#1E5DAB", blueL: "#DCEAFB", orange: "#EB6834", orangeL: "#FBE1D6", green: "#3BAA6E", greenL: "#DDF2E6",
  yellow: "#F6C343", red: "#D9483B", grey: "#C9C8C3", line: "#E3E0D8",
  skin: "#F2C9A8", skinD: "#E0AE8B", hair: "#232634", hoodie: "#2E5AAC", hoodieD: "#244A8E", pants: "#2F3440", shoe: "#F4F4F4", pack: "#EB6834", packD: "#C9532A",
  sea: "#2F86C2", seaD: "#226A9E", sand: "#EFDDBB", grass: "#9CC98A", mount: "#6E9C6B", mountD: "#4F7D55", wall: "#F1ECE3",
};
const FONT = "'Noto Sans CJK TC', 'Noto Sans CJK HK', sans-serif";

// ---------- numbers and easing ----------
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const lerp = (a, b, k) => a + (b - a) * k;
const prog = (t, a, b) => clamp((t - a) / (b - a));                  // 0 before a, 1 after b
const easeOut = (k) => 1 - Math.pow(1 - k, 3);
const easeIn = (k) => k * k * k;
const easeInOut = (k) => (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2);
const backOut = (k) => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(k - 1, 3) + c1 * Math.pow(k - 1, 2); };
function hex(c) { const n = parseInt(c.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; }
function mix(a, b, k) { const x = hex(a), y = hex(b); return "rgb(" + x.map((v, i) => Math.round(lerp(v, y[i], clamp(k)))).join(",") + ")"; }
function rgba(c, a) { const x = hex(c); return `rgba(${x[0]},${x[1]},${x[2]},${a})`; }
// a deterministic pseudo-random number for index i (no Math.random, so frames repeat exactly)
function rnd(i) { const x = Math.sin(i * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); }

// ---------- text and shapes ----------
function font(size, weight = 500) { return `${weight} ${size}px ${FONT}`; }
function text(ctx, s, x, y, o = {}) {
  ctx.save();
  ctx.globalAlpha *= o.alpha == null ? 1 : o.alpha;
  ctx.font = font(o.size || 40, o.weight || 500);
  ctx.fillStyle = o.color || C.ink;
  ctx.textAlign = o.align || "left";
  ctx.textBaseline = o.base || "alphabetic";
  if (o.shadow) { ctx.shadowColor = o.shadow; ctx.shadowBlur = o.blur || 12; ctx.shadowOffsetY = o.dy == null ? 3 : o.dy; }
  if (o.track) ctx.letterSpacing = o.track + "px";
  ctx.fillText(s, x, y);
  ctx.restore();
}
function textW(ctx, s, size, weight = 500) { ctx.save(); ctx.font = font(size, weight); const w = ctx.measureText(s).width; ctx.restore(); return w; }
function rrect(ctx, x, y, w, h, r) {
  r = Math.min(r, w / 2, h / 2);
  ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
}
function card(ctx, x, y, w, h, o = {}) {
  ctx.save();
  ctx.globalAlpha *= o.alpha == null ? 1 : o.alpha;
  if (o.shadow !== false) { ctx.shadowColor = "rgba(16,32,47,0.18)"; ctx.shadowBlur = 30; ctx.shadowOffsetY = 10; }
  rrect(ctx, x, y, w, h, o.r == null ? 22 : o.r); ctx.fillStyle = o.fill || C.white; ctx.fill();
  ctx.restore();
  if (o.stroke) { ctx.save(); ctx.globalAlpha *= o.alpha == null ? 1 : o.alpha; rrect(ctx, x, y, w, h, o.r == null ? 22 : o.r); ctx.strokeStyle = o.stroke; ctx.lineWidth = o.lw || 3; ctx.stroke(); ctx.restore(); }
}
// a pill label: coloured background, white text, centred on (x, y)
function pill(ctx, s, x, y, o = {}) {
  const size = o.size || 34, w = textW(ctx, s, size, o.weight || 700) + size * 1.1, h = size * 1.6;
  ctx.save(); ctx.globalAlpha *= o.alpha == null ? 1 : o.alpha;
  ctx.translate(x, y); if (o.scale != null) ctx.scale(o.scale, o.scale);
  if (o.shadow !== false) { ctx.shadowColor = "rgba(0,0,0,0.18)"; ctx.shadowBlur = 14; ctx.shadowOffsetY = 4; }
  rrect(ctx, -w / 2, -h / 2, w, h, h / 2); ctx.fillStyle = o.fill || C.blue; ctx.fill(); ctx.shadowColor = "transparent";
  if (o.stroke) { ctx.lineWidth = 3; ctx.strokeStyle = o.stroke; ctx.stroke(); }
  text(ctx, s, 0, size * 0.36, { size, weight: o.weight || 700, color: o.color || C.white, align: "center" });
  ctx.restore();
  return w;
}
// pop-in scale for something that appears at time a
function pop(t, a, d = 0.45) { const k = prog(t, a, a + d); return k <= 0 ? 0 : backOut(k); }
function fadeIO(t, a, b, d = 0.35) { return Math.min(prog(t, a, a + d), 1 - prog(t, b - d, b)); }

// ---------- environment ----------
// sky by time of day: 0 afternoon, 1 sunset, 2 dusk; three colour stops (top, middle, horizon) per key time, so the
// sunset keeps a blue top over an orange horizon instead of a muddy mix of the two
const SKY = [["#79BDEB", "#A8D6F2", "#E3F2FA"], ["#7C8FC6", "#F0A866", "#FFD9A3"], ["#1F2D55", "#4E4A82", "#C77C7C"]];
function sky(ctx, phase, y0 = 0, y1 = H) {
  const p = clamp(phase, 0, 2), i = Math.min(1, Math.floor(p)), k = p - i;
  const g = ctx.createLinearGradient(0, y0, 0, y1);
  [0, 0.55, 1].forEach((at, j) => g.addColorStop(at, mix(SKY[i][j], SKY[i + 1][j], k)));
  ctx.fillStyle = g; ctx.fillRect(0, y0, W, y1 - y0);
}
function sun(ctx, x, y, r, phase) {
  ctx.save(); ctx.globalAlpha = 0.9;
  const g = ctx.createRadialGradient(x, y, 0, x, y, r * 3); g.addColorStop(0, rgba("#FFF4D6", 0.9)); g.addColorStop(0.3, rgba("#FFD27A", 0.5)); g.addColorStop(1, rgba("#FFD27A", 0));
  ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, r * 3, 0, 7); ctx.fill();
  ctx.fillStyle = phase > 0.5 ? "#FFB75E" : "#FFF1C4"; ctx.beginPath(); ctx.arc(x, y, r, 0, 7); ctx.fill(); ctx.restore();
}
function cloud(ctx, x, y, s, a = 0.85) {
  // one path for all the puffs, filled once, so the overlaps do not show through the transparency
  ctx.save(); ctx.globalAlpha *= a; ctx.fillStyle = "#FFFFFF"; ctx.beginPath();
  [[0, 0.1, 0.8], [0.8, -0.3, 0.85], [1.6, 0, 0.9], [2.3, 0.15, 0.65]].forEach(([dx, dy, r]) => { ctx.moveTo(x + dx * 40 * s + r * 40 * s, y + dy * 40 * s); ctx.arc(x + dx * 40 * s, y + dy * 40 * s, r * 40 * s, 0, Math.PI * 2); });
  ctx.rect(x, y, 2.3 * 40 * s, 0.6 * 40 * s);
  ctx.fill("nonzero"); ctx.restore();
}
// the mountain behind the campus (Shoushan) and the sea of Sizihwan, drawn as layered silhouettes
function mountains(ctx, y, shift = 0, tint = 0) {
  ctx.save();
  ctx.fillStyle = mix(C.mount, "#5A5F8A", tint);
  ctx.beginPath(); ctx.moveTo(0, y);
  for (let x = 0; x <= W; x += 40) ctx.lineTo(x, y - 170 - 70 * Math.sin((x + shift) / 260) - 40 * Math.sin((x + shift) / 97));
  ctx.lineTo(W, y); ctx.closePath(); ctx.fill();
  ctx.fillStyle = mix(C.mountD, "#3E4370", tint);
  ctx.beginPath(); ctx.moveTo(0, y);
  for (let x = 0; x <= W; x += 40) ctx.lineTo(x, y - 90 - 50 * Math.sin((x + shift + 400) / 190) - 25 * Math.sin((x + shift) / 61));
  ctx.lineTo(W, y); ctx.closePath(); ctx.fill();
  ctx.restore();
}
function sea(ctx, y0, y1, t, tint = 0) {
  const g = ctx.createLinearGradient(0, y0, 0, y1); g.addColorStop(0, mix(C.sea, "#C2747A", tint)); g.addColorStop(1, mix(C.seaD, "#4B4F7C", tint));
  ctx.fillStyle = g; ctx.fillRect(0, y0, W, y1 - y0);
  ctx.save(); ctx.strokeStyle = rgba("#FFFFFF", 0.35); ctx.lineWidth = 3;
  for (let i = 0; i < 14; i++) {
    const yy = y0 + 12 + (i * 37) % Math.max(20, y1 - y0 - 10), xx = ((i * 263 + t * 30) % (W + 200)) - 100;
    ctx.beginPath(); ctx.moveTo(xx, yy); ctx.lineTo(xx + 60 + 30 * rnd(i), yy); ctx.stroke();
  }
  ctx.restore();
}
function palm(ctx, x, y, s, t = 0) {
  ctx.save(); ctx.translate(x, y); ctx.scale(s, s);
  ctx.strokeStyle = "#8A6A4A"; ctx.lineWidth = 14; ctx.lineCap = "round";
  ctx.beginPath(); ctx.moveTo(0, 0); ctx.quadraticCurveTo(10, -120, -5, -230); ctx.stroke();
  ctx.fillStyle = "#4E8B57";
  for (let k = 0; k < 7; k++) {
    const a = -Math.PI / 2 + (k - 3) * 0.55 + 0.04 * Math.sin(t * 1.5 + k);
    ctx.save(); ctx.translate(-5, -230); ctx.rotate(a);
    ctx.beginPath(); ctx.moveTo(0, 0); ctx.quadraticCurveTo(60, -30, 120, 10); ctx.quadraticCurveTo(60, -5, 0, 0); ctx.fill(); ctx.restore();
  }
  ctx.restore();
}
function building(ctx, x, y, w, h, o = {}) {
  ctx.save();
  ctx.fillStyle = o.fill || "#E8E1D5"; ctx.fillRect(x, y - h, w, h);
  ctx.fillStyle = o.roof || "#C9BFAF"; ctx.fillRect(x - 6, y - h - 12, w + 12, 14);
  const lit = o.lit || 0;
  for (let r = 0; r < Math.floor((h - 40) / 52); r++) for (let c = 0; c < Math.floor((w - 20) / 46); c++) {
    ctx.fillStyle = lit && rnd(r * 13 + c + x) < lit ? "#FFE3A3" : (o.win || "#A8C6DD");
    ctx.fillRect(x + 16 + c * 46, y - h + 26 + r * 52, 28, 32);
  }
  ctx.restore();
}
function ground(ctx, y, o = {}) {
  ctx.fillStyle = o.fill || "#D8D2C7"; ctx.fillRect(0, y, W, H - y);
  ctx.fillStyle = o.edge || "#BDB6A9"; ctx.fillRect(0, y, W, 8);
}

// ---------- the student ----------
// Draws the (fictional) NSYSU student 阿哲 with his feet at (x, y). s is the size of one body unit in pixels (the
// figure is about 3.3 units tall). o.pose: stand | walk | run | sit | phone | ride | cheer; o.t drives the cycles;
// o.face: 1 looks right, -1 left; o.expr: neutral | happy | sad | surprised.
function limb(ctx, x, y, a1, l1, a2, l2, w, color) {
  const kx = x + Math.sin(a1) * l1, ky = y + Math.cos(a1) * l1;
  const ex = kx + Math.sin(a2) * l2, ey = ky + Math.cos(a2) * l2;
  ctx.strokeStyle = color; ctx.lineWidth = w; ctx.lineCap = "round"; ctx.lineJoin = "round";
  ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(kx, ky); ctx.lineTo(ex, ey); ctx.stroke();
  return [ex, ey, kx, ky];
}
// two-bone inverse kinematics: angles (0 = down) reaching from (x, y) to (tx, ty), bending to `bend` side
function ik(x, y, tx, ty, l1, l2, bend) {
  const dx = tx - x, dy = ty - y; let d = Math.hypot(dx, dy); d = Math.min(d, l1 + l2 - 1e-3);
  const base = Math.atan2(dx, dy);
  const c = clamp((l1 * l1 + d * d - l2 * l2) / (2 * l1 * d), -1, 1), a = Math.acos(c);
  const a1 = base + bend * a;
  const kx = x + Math.sin(a1) * l1, ky = y + Math.cos(a1) * l1;
  return [a1, Math.atan2(tx - kx, ty - ky)];
}
function student(ctx, x, y, s, o = {}) {
  const pose = o.pose || "stand", t = o.t || 0, face = o.face || 1, expr = o.expr || "neutral";
  const pal = o.pal || {};
  const hoodie = pal.hoodie || C.hoodie, hoodieD = pal.hoodieD || C.hoodieD, pants = pal.pants || C.pants, hair = pal.hair || C.hair, pack = pal.pack === undefined ? C.pack : pal.pack;
  const thigh = 0.55 * s, shin = 0.55 * s, uarm = 0.46 * s, farm = 0.44 * s, torso = 1.0 * s, headR = 0.42 * s;
  ctx.save(); ctx.translate(x, y); ctx.scale(face, 1);
  if (o.alpha != null) ctx.globalAlpha *= o.alpha;
  if (o.shadow !== false && pose !== "ride" && pose !== "sit") { ctx.fillStyle = "rgba(16,32,47,0.16)"; ctx.beginPath(); ctx.ellipse(0.05 * s, 0.04 * s, 0.6 * s, 0.1 * s, 0, 0, 7); ctx.fill(); }
  let hipY = -(thigh + shin), lean = 0, bob = 0;
  let L = { fa1: 0, fa2: 0, ba1: 0, ba2: 0, fl1: 0, fl2: 0, bl1: 0, bl2: 0 };   // front/back arm and leg angles
  const ph = t * Math.PI * 2;
  if (pose === "stand" || pose === "phone") { bob = Math.sin(t * 2.2) * 0.012 * s; L = { fa1: 0.12, fa2: 0.05, ba1: -0.1, ba2: -0.05, fl1: 0.04, fl2: 0.02, bl1: -0.04, bl2: -0.02 }; }
  if (pose === "walk") {
    const f = Math.sin(ph * 0.95); bob = Math.abs(Math.cos(ph * 0.95)) * 0.05 * s;
    L = { fl1: 0.45 * f, fl2: 0.45 * f - Math.max(0, -Math.cos(ph * 0.95)) * 0.6, bl1: -0.45 * f, bl2: -0.45 * f - Math.max(0, Math.cos(ph * 0.95)) * 0.6, fa1: -0.4 * f, fa2: -0.4 * f - 0.35, ba1: 0.4 * f, ba2: 0.4 * f - 0.35 };
    L.fl2 = L.fl1 - Math.max(0, Math.sin(ph * 0.95 + 1.2)) * 0.7; L.bl2 = L.bl1 - Math.max(0, -Math.sin(ph * 0.95 + 1.2)) * 0.7;
  }
  if (pose === "run") {
    const f = Math.sin(ph * 1.4); lean = 0.22; bob = Math.abs(Math.cos(ph * 1.4)) * 0.12 * s;
    L = { fl1: 0.8 * f, bl1: -0.8 * f, fa1: -0.9 * f, ba1: 0.9 * f };
    L.fl2 = L.fl1 - (0.3 + Math.max(0, Math.sin(ph * 1.4 + 1.3)) * 1.3); L.bl2 = L.bl1 - (0.3 + Math.max(0, -Math.sin(ph * 1.4 + 1.3)) * 1.3);
    L.fa2 = L.fa1 + 1.5; L.ba2 = L.ba1 + 1.5;
  }
  if (pose === "cheer") { bob = Math.abs(Math.sin(t * 6)) * 0.06 * s; L = { fa1: 2.25, fa2: 2.75, ba1: -2.3, ba2: -2.8, fl1: 0.05, fl2: 0.03, bl1: -0.05, bl2: -0.03 }; }
  if (pose === "sit") { hipY = -0.62 * s; L = { fl1: -Math.PI / 2 + 0.05, fl2: 0.05, bl1: -Math.PI / 2 + 0.1, bl2: 0.12, fa1: -0.65, fa2: -1.45, ba1: -0.5, ba2: -1.4 }; }
  const hx = 0, hy = hipY - bob;
  const sx = hx + Math.sin(lean) * torso * 0.98, sy = hy - Math.cos(lean) * torso;      // shoulder
  // ride: legs follow the pedals, hands hold the bar (positions given in o.ride, relative to the feet point)
  let rideFeet = null, rideHands = null;
  if (pose === "ride" && o.ride) { rideFeet = o.ride.feet; rideHands = o.ride.hands; }
  const drawLeg = (a1, a2, back) => limb(ctx, hx + (back ? -0.04 * s : 0.04 * s), hy, a1, thigh, a2, shin, 0.27 * s, back ? mix(pants, "#000000", 0.18) : pants);
  const shoe = (p, back) => { ctx.save(); ctx.fillStyle = back ? "#DADADA" : C.shoe; rrect(ctx, p[0] - 0.1 * s, p[1] - 0.09 * s, 0.32 * s, 0.16 * s, 0.07 * s); ctx.fill(); ctx.fillStyle = "#B9BEC6"; ctx.fillRect(p[0] - 0.1 * s, p[1] + 0.03 * s, 0.32 * s, 0.04 * s); ctx.restore(); };
  const drawArm = (a1, a2, back) => {
    const p = limb(ctx, sx + (back ? -0.08 * s : 0.06 * s), sy + 0.12 * s, a1, uarm, a2, farm, 0.21 * s, back ? hoodieD : hoodie);
    ctx.fillStyle = back ? C.skinD : C.skin; ctx.beginPath(); ctx.arc(p[0], p[1], 0.09 * s, 0, 7); ctx.fill(); return p;
  };
  let fa, ba, fl, bl;
  if (rideFeet) {
    const f0 = ik(hx, hy, rideFeet[1][0], rideFeet[1][1], thigh, shin, -1), f1 = ik(hx, hy, rideFeet[0][0], rideFeet[0][1], thigh, shin, -1);
    bl = [f0[0], f0[1]]; fl = [f1[0], f1[1]];
    const ha = ik(sx, sy + 0.12 * s, rideHands[0], rideHands[1], uarm, farm, 1);
    fa = [ha[0], ha[1]]; ba = [ha[0] - 0.08, ha[1] - 0.05];
  } else { fa = [L.fa1, L.fa2]; ba = [L.ba1, L.ba2]; fl = [L.fl1, L.fl2]; bl = [L.bl1, L.bl2]; }
  if (o.phonePose || pose === "phone") { fa = [-0.55, -2.45]; }
  // back arm and back leg, then the backpack, torso, front leg, front arm, head
  drawArm(ba[0], ba[1], true);
  shoe(drawLeg(bl[0], bl[1], true), true);
  if (pack) { ctx.save(); ctx.translate(sx, sy); ctx.rotate(lean); ctx.fillStyle = pack; rrect(ctx, -0.62 * s, 0.12 * s, 0.36 * s, 0.7 * s, 0.12 * s); ctx.fill(); ctx.fillStyle = C.packD; rrect(ctx, -0.6 * s, 0.5 * s, 0.32 * s, 0.22 * s, 0.07 * s); ctx.fill(); ctx.restore(); }
  ctx.save(); ctx.translate(hx, hy); ctx.rotate(lean);
  ctx.fillStyle = hoodie; rrect(ctx, -0.32 * s, -torso - 0.04 * s, 0.66 * s, torso + 0.18 * s, 0.26 * s); ctx.fill();
  ctx.fillStyle = hoodieD; rrect(ctx, -0.32 * s, -0.18 * s, 0.66 * s, 0.32 * s, 0.14 * s); ctx.fill();       // waistband
  ctx.strokeStyle = rgba("#FFFFFF", 0.7); ctx.lineWidth = 0.04 * s; ctx.beginPath(); ctx.moveTo(0.18 * s, -torso + 0.1 * s); ctx.lineTo(0.15 * s, -torso + 0.42 * s); ctx.stroke();   // hoodie string
  ctx.restore();
  shoe(drawLeg(fl[0], fl[1], false), false);
  const fhand = drawArm(fa[0], fa[1], false);
  if (o.phonePose || pose === "phone") { ctx.save(); ctx.translate(fhand[0] + 0.05 * s, fhand[1] - 0.12 * s); ctx.rotate(-0.25); ctx.fillStyle = "#1B2430"; rrect(ctx, -0.07 * s, -0.16 * s, 0.17 * s, 0.3 * s, 0.04 * s); ctx.fill(); ctx.fillStyle = o.screen || "#7FB3E8"; rrect(ctx, -0.055 * s, -0.14 * s, 0.14 * s, 0.25 * s, 0.03 * s); ctx.fill(); ctx.restore(); }
  // head
  const cx = sx + 0.06 * s, cy = sy - headR - 0.02 * s;
  ctx.fillStyle = C.skin; ctx.fillRect(cx - 0.08 * s, sy - 0.12 * s, 0.16 * s, 0.16 * s);          // neck
  ctx.beginPath(); ctx.arc(cx, cy, headR, 0, 7); ctx.fillStyle = C.skin; ctx.fill();
  ctx.fillStyle = C.skinD; ctx.beginPath(); ctx.arc(cx - 0.12 * s, cy + 0.04 * s, 0.08 * s, 0, 7); ctx.fill();   // ear
  ctx.fillStyle = hair; ctx.beginPath();
  ctx.arc(cx - 0.02 * s, cy - 0.04 * s, headR * 1.04, Math.PI * 0.92, Math.PI * 2.08); ctx.quadraticCurveTo(cx + 0.36 * s, cy - 0.05 * s, cx + 0.2 * s, cy - 0.18 * s);
  ctx.quadraticCurveTo(cx + 0.02 * s, cy - 0.08 * s, cx - 0.16 * s, cy - 0.14 * s); ctx.quadraticCurveTo(cx - 0.3 * s, cy + 0.02 * s, cx - 0.42 * s, cy + 0.06 * s); ctx.closePath(); ctx.fill();
  // face, looking towards +x
  const ex1 = cx + 0.1 * s, ex2 = cx + 0.28 * s, ey = cy + 0.03 * s;
  ctx.fillStyle = C.ink; ctx.strokeStyle = C.ink; ctx.lineWidth = 0.035 * s; ctx.lineCap = "round";
  if (expr === "happy") { [ex1, ex2].forEach((ex) => { ctx.beginPath(); ctx.arc(ex, ey + 0.02 * s, 0.045 * s, Math.PI * 1.1, Math.PI * 1.9); ctx.stroke(); }); }
  else if (expr === "surprised") { [ex1, ex2].forEach((ex) => { ctx.beginPath(); ctx.arc(ex, ey, 0.045 * s, 0, 7); ctx.fill(); }); }
  else { [ex1, ex2].forEach((ex) => { ctx.beginPath(); ctx.ellipse(ex, ey, 0.03 * s, 0.042 * s, 0, 0, 7); ctx.fill(); }); }
  if (expr === "sad") { ctx.beginPath(); ctx.moveTo(ex1 - 0.06 * s, ey - 0.09 * s); ctx.lineTo(ex1 + 0.04 * s, ey - 0.12 * s); ctx.moveTo(ex2 + 0.06 * s, ey - 0.09 * s); ctx.lineTo(ex2 - 0.04 * s, ey - 0.12 * s); ctx.stroke(); }
  if (expr === "surprised") { ctx.beginPath(); ctx.moveTo(ex1 - 0.05 * s, ey - 0.13 * s); ctx.lineTo(ex1 + 0.05 * s, ey - 0.15 * s); ctx.moveTo(ex2 - 0.05 * s, ey - 0.15 * s); ctx.lineTo(ex2 + 0.05 * s, ey - 0.13 * s); ctx.stroke(); }
  const mx = cx + 0.2 * s, my = cy + 0.2 * s;
  ctx.beginPath();
  if (expr === "happy") { ctx.fillStyle = "#B4483C"; ctx.arc(mx, my - 0.02 * s, 0.09 * s, 0.1, Math.PI - 0.1); ctx.closePath(); ctx.fill(); }
  else if (expr === "sad") { ctx.arc(mx, my + 0.06 * s, 0.07 * s, Math.PI * 1.2, Math.PI * 1.8); ctx.stroke(); }
  else if (expr === "surprised") { ctx.fillStyle = "#B4483C"; ctx.ellipse(mx, my, 0.045 * s, 0.06 * s, 0, 0, 7); ctx.fill(); }
  else { ctx.arc(mx, my - 0.03 * s, 0.06 * s, Math.PI * 0.2, Math.PI * 0.8); ctx.stroke(); }
  if (expr === "happy" || expr === "neutral") { ctx.fillStyle = rgba("#F08A7A", 0.35); ctx.beginPath(); ctx.arc(cx + 0.33 * s, cy + 0.13 * s, 0.06 * s, 0, 7); ctx.fill(); }
  ctx.restore();
}

// ---------- the bike ----------
// A generic shared bike seen from the side, ground point (x, y), body unit s, facing right. Returns the points a
// rider needs (seat, pedals, bar) in canvas coordinates, so student() can sit on it.
function bike(ctx, x, y, s, o = {}) {
  const face = o.face || 1, spin = o.spin || 0, r = 0.55 * s;
  ctx.save(); ctx.translate(x, y); ctx.scale(face, 1);
  if (o.alpha != null) ctx.globalAlpha *= o.alpha;
  const rw = [-0.95 * s, -r], fw = [0.95 * s, -r], crank = [-0.12 * s, -0.62 * s], seat = [-0.42 * s, -1.32 * s], head = [0.66 * s, -1.18 * s], bar = [0.62 * s, -1.5 * s];
  const wheel = (c) => {
    ctx.strokeStyle = "#2B2B2B"; ctx.lineWidth = 0.1 * s; ctx.beginPath(); ctx.arc(c[0], c[1], r, 0, 7); ctx.stroke();
    ctx.strokeStyle = "#9AA3AD"; ctx.lineWidth = 0.02 * s;
    for (let k = 0; k < 8; k++) { const a = spin + k * Math.PI / 4; ctx.beginPath(); ctx.moveTo(c[0], c[1]); ctx.lineTo(c[0] + Math.cos(a) * r * 0.92, c[1] + Math.sin(a) * r * 0.92); ctx.stroke(); }
    ctx.fillStyle = "#6B7380"; ctx.beginPath(); ctx.arc(c[0], c[1], 0.06 * s, 0, 7); ctx.fill();
  };
  wheel(rw); wheel(fw);
  ctx.strokeStyle = o.color || "#F7F7F7"; ctx.lineCap = "round"; ctx.lineJoin = "round"; ctx.lineWidth = 0.13 * s;
  ctx.beginPath(); ctx.moveTo(rw[0], rw[1]); ctx.lineTo(crank[0], crank[1]); ctx.lineTo(seat[0] + 0.05 * s, seat[1] + 0.12 * s); ctx.stroke();   // chainstay, seat tube
  ctx.beginPath(); ctx.moveTo(rw[0], rw[1]); ctx.lineTo(seat[0] + 0.04 * s, seat[1] + 0.2 * s); ctx.stroke();                                  // seat stay
  ctx.beginPath(); ctx.moveTo(crank[0], crank[1]); ctx.quadraticCurveTo(0.2 * s, -0.7 * s, head[0], head[1]); ctx.stroke();                 // step-through down tube
  ctx.strokeStyle = o.accent || C.blue; ctx.lineWidth = 0.07 * s; ctx.beginPath(); ctx.moveTo(0.05 * s, -0.68 * s); ctx.quadraticCurveTo(0.28 * s, -0.74 * s, 0.5 * s, -0.96 * s); ctx.stroke();
  ctx.strokeStyle = "#C9CED6"; ctx.lineWidth = 0.08 * s; ctx.beginPath(); ctx.moveTo(head[0], head[1]); ctx.lineTo(fw[0], fw[1]); ctx.stroke();   // fork
  ctx.beginPath(); ctx.moveTo(head[0], head[1]); ctx.lineTo(bar[0], bar[1]); ctx.lineTo(bar[0] - 0.22 * s, bar[1] - 0.02 * s); ctx.stroke();       // stem, bar
  ctx.fillStyle = "#3A4250"; rrect(ctx, seat[0] - 0.2 * s, seat[1] - 0.04 * s, 0.38 * s, 0.1 * s, 0.05 * s); ctx.fill();                          // saddle
  ctx.strokeStyle = "#3A4250"; ctx.lineWidth = 0.035 * s; rrect(ctx, 0.78 * s, -1.42 * s, 0.46 * s, 0.32 * s, 0.05 * s); ctx.stroke();            // basket
  ctx.beginPath(); for (let k = 1; k < 4; k++) { ctx.moveTo(0.78 * s + k * 0.115 * s, -1.42 * s); ctx.lineTo(0.78 * s + k * 0.115 * s, -1.1 * s); } ctx.stroke();
  ctx.strokeStyle = "#8F98A3"; ctx.lineWidth = 0.05 * s;                                                                                            // crank and pedals
  const pa = o.pedal || 0, p1 = [crank[0] + Math.cos(pa) * 0.24 * s, crank[1] + Math.sin(pa) * 0.24 * s], p2 = [crank[0] - Math.cos(pa) * 0.24 * s, crank[1] - Math.sin(pa) * 0.24 * s];
  ctx.beginPath(); ctx.moveTo(p1[0], p1[1]); ctx.lineTo(p2[0], p2[1]); ctx.stroke();
  ctx.fillStyle = "#59616D"; ctx.beginPath(); ctx.arc(crank[0], crank[1], 0.08 * s, 0, 7); ctx.fill();
  ctx.restore();
  const T = (p) => [x + face * p[0], y + p[1]];
  return { seat: T(seat), feet: [T(p1), T(p2)], hands: T([bar[0] - 0.12 * s, bar[1] + 0.02 * s]) };
}
// a rider on a bike: draws the bike, then the student seated on it
function rider(ctx, x, y, s, o = {}) {
  const t = o.t || 0, pa = o.pedal != null ? o.pedal : t * 6;
  const b = bike(ctx, x, y, s, { face: o.face, spin: o.spin != null ? o.spin : t * 8, pedal: pa, alpha: o.alpha, color: o.color, accent: o.accent });
  const face = o.face || 1;
  // student() works in its own frame (feet point = hip minus leg length); convert the bike points to that frame
  const hip = [b.seat[0] - face * 0.05 * s, b.seat[1] + 0.02 * s];
  const footY = hip[1] + 1.1 * s, footX = hip[0];
  const rel = (p) => [face * (p[0] - footX), p[1] - footY];
  student(ctx, footX, footY, s, { pose: "ride", t, face, expr: o.expr, alpha: o.alpha, pal: o.pal, ride: { feet: [rel(b.feet[0]), rel(b.feet[1])], hands: rel(b.hands) } });
}

// ---------- a station (dock rack) seen from the side ----------
// x is the kiosk, y the ground, s the body unit. Docked bikes stand at an angle to the street, so each is a side-view
// bike squeezed to half its length; the post stands in front of its bike and has a light, green with a bike and red
// (o.empty) or grey without. o.skip leaves the first docks empty, for a bike just taken.
function dockedBike(ctx, x, y, s) {
  ctx.save(); ctx.translate(x, y); ctx.scale(0.5, 1); bike(ctx, 0, 0, 0.66 * s, { color: "#F2F2F2" }); ctx.restore();
}
function station(ctx, x, y, s, o = {}) {
  const n = o.docks || 8, gap = 1.0 * s, bikes = o.bikes || 0, skip = o.skip || 0;
  ctx.save();
  ctx.fillStyle = "#7D8590"; rrect(ctx, x - 0.4 * s, y - 0.1 * s, n * gap + 1.4 * s, 0.14 * s, 0.05 * s); ctx.fill();
  // the kiosk with the station name
  ctx.fillStyle = "#4A5563"; ctx.fillRect(x - 0.09 * s, y - 2.6 * s, 0.18 * s, 2.6 * s);
  ctx.fillStyle = C.navy; rrect(ctx, x - 0.8 * s, y - 3.45 * s, 1.6 * s, 0.9 * s, 0.12 * s); ctx.fill();
  ctx.fillStyle = C.yellow; rrect(ctx, x - 0.8 * s, y - 3.45 * s, 1.6 * s, 0.14 * s, 0.07 * s); ctx.fill();
  if (o.name) text(ctx, o.name, x, y - 2.8 * s, { size: 0.4 * s, weight: 900, color: C.white, align: "center" });
  for (let k = 0; k < n; k++) {
    const px = x + 0.9 * s + k * gap, has = k >= skip && k < skip + bikes;
    if (has) dockedBike(ctx, px + 0.3 * s, y, s);
    ctx.fillStyle = "#5A626E"; rrect(ctx, px - 0.1 * s, y - 1.0 * s, 0.2 * s, 1.0 * s, 0.07 * s); ctx.fill();
    ctx.fillStyle = "#3A4250"; rrect(ctx, px - 0.15 * s, y - 1.14 * s, 0.3 * s, 0.24 * s, 0.07 * s); ctx.fill();
    ctx.fillStyle = has ? "#4CD48A" : (o.empty ? "#FF5A4A" : "#9AA3AD"); ctx.beginPath(); ctx.arc(px, y - 1.02 * s, 0.075 * s, 0, 7); ctx.fill();
  }
  ctx.restore();
  return (k) => [x + 0.9 * s + k * gap, y - 1.02 * s];     // where the light of dock k is
}

// ---------- the phone ----------
// draws a phone with an image (or a callback) as its screen; (x, y) is the top-left corner, w the outer width
function phone(ctx, x, y, w, img, o = {}) {
  const h = w * 2.05, bez = w * 0.04, r = w * 0.13;
  ctx.save();
  if (o.alpha != null) ctx.globalAlpha *= o.alpha;
  ctx.shadowColor = "rgba(16,32,47,0.35)"; ctx.shadowBlur = 50; ctx.shadowOffsetY = 20;
  rrect(ctx, x, y, w, h, r); ctx.fillStyle = "#111821"; ctx.fill(); ctx.shadowColor = "transparent";
  ctx.save(); rrect(ctx, x + bez, y + bez, w - 2 * bez, h - 2 * bez, r * 0.8); ctx.clip();
  ctx.fillStyle = "#FFFFFF"; ctx.fillRect(x + bez, y + bez, w - 2 * bez, h - 2 * bez);
  const sw = w - 2 * bez, sh = h - 2 * bez;
  if (img) {
    // o.view: [sx, sy, sw, sh] of the image to show (defaults to the top of the image at full width)
    const v = o.view || [0, 0, img.width, img.width * sh / sw];
    ctx.drawImage(img, v[0], v[1], v[2], v[3], x + bez, y + bez, sw, sh);
  }
  if (o.draw) o.draw(ctx, x + bez, y + bez, sw, sh);
  ctx.restore();
  ctx.fillStyle = "#111821"; rrect(ctx, x + w * 0.36, y + bez + w * 0.015, w * 0.28, w * 0.06, w * 0.03); ctx.fill();   // camera island
  ctx.restore();
  return { x: x + bez, y: y + bez, w: w - 2 * bez, h: h - 2 * bez };
}
// a tap: a ring that grows and fades from time a
function tap(ctx, x, y, t, a) {
  const k = prog(t, a, a + 0.6); if (k <= 0 || k >= 1) return;
  ctx.save(); ctx.strokeStyle = rgba(C.blue, 1 - k); ctx.lineWidth = 6; ctx.beginPath(); ctx.arc(x, y, 18 + 50 * easeOut(k), 0, 7); ctx.stroke();
  ctx.fillStyle = rgba(C.blue, 0.35 * (1 - k)); ctx.beginPath(); ctx.arc(x, y, 22, 0, 7); ctx.fill(); ctx.restore();
}
// a highlight box drawn around a rectangle, revealed from time a
function hilite(ctx, x, y, w, h, t, a, color = C.orange) {
  const k = easeOut(prog(t, a, a + 0.4)); if (k <= 0) return;
  ctx.save(); ctx.strokeStyle = color; ctx.lineWidth = 6; ctx.globalAlpha = k; rrect(ctx, x - 8 * (1 - k), y - 8 * (1 - k), w + 16 * (1 - k), h + 16 * (1 - k), 14); ctx.stroke(); ctx.restore();
}

// ---------- the wall clock ----------
function clock(ctx, x, y, r, minutes, o = {}) {
  ctx.save(); ctx.translate(x, y);
  ctx.fillStyle = C.white; ctx.strokeStyle = o.rim || C.navy; ctx.lineWidth = r * 0.1; ctx.beginPath(); ctx.arc(0, 0, r, 0, 7); ctx.fill(); ctx.stroke();
  ctx.strokeStyle = C.ink2; ctx.lineWidth = r * 0.04;
  for (let k = 0; k < 12; k++) { const a = k * Math.PI / 6; ctx.beginPath(); ctx.moveTo(Math.sin(a) * r * 0.78, -Math.cos(a) * r * 0.78); ctx.lineTo(Math.sin(a) * r * 0.9, -Math.cos(a) * r * 0.9); ctx.stroke(); }
  const ha = ((minutes / 60) % 12) / 12 * Math.PI * 2, ma = (minutes % 60) / 60 * Math.PI * 2;
  ctx.strokeStyle = C.ink; ctx.lineCap = "round";
  ctx.lineWidth = r * 0.09; ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(Math.sin(ha) * r * 0.5, -Math.cos(ha) * r * 0.5); ctx.stroke();
  ctx.lineWidth = r * 0.06; ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(Math.sin(ma) * r * 0.75, -Math.cos(ma) * r * 0.75); ctx.stroke();
  ctx.fillStyle = C.orange; ctx.beginPath(); ctx.arc(0, 0, r * 0.07, 0, 7); ctx.fill();
  ctx.restore();
}
function hhmm(m) { m = Math.round(m); return String(Math.floor(m / 60)).padStart(2, "0") + ":" + String(m % 60).padStart(2, "0"); }

// ---------- transitions drawn inside a scene ----------
// a coloured panel that sweeps across the frame between a and b (covering at the middle)
function wipe(ctx, t, a, b, color = C.navy) {
  const k = prog(t, a, b); if (k <= 0 || k >= 1) return;
  const x = k < 0.5 ? lerp(-W * 1.2, 0, easeInOut(k * 2)) : lerp(0, W * 1.2, easeInOut(k * 2 - 1));
  ctx.save(); ctx.fillStyle = color; ctx.beginPath(); ctx.moveTo(x - 200, 0); ctx.lineTo(x + W + 200, 0); ctx.lineTo(x + W, H); ctx.lineTo(x - 400, H); ctx.closePath(); ctx.fill(); ctx.restore();
}
function fadeFrom(ctx, t, d = 0.4, color = C.navy) { const k = 1 - prog(t, 0, d); if (k <= 0) return; ctx.save(); ctx.globalAlpha = k; ctx.fillStyle = color; ctx.fillRect(0, 0, W, H); ctx.restore(); }
function fadeTo(ctx, t, T, d = 0.4, color = C.navy) { const k = prog(t, T - d, T); if (k <= 0) return; ctx.save(); ctx.globalAlpha = k; ctx.fillStyle = color; ctx.fillRect(0, 0, W, H); ctx.restore(); }

// a small caption tag in the top-left corner ("資料：…")
function sourceTag(ctx, s, t, a = 0, color = C.ink2) { text(ctx, s, 60, H - 22, { size: 22, weight: 400, color, alpha: prog(t, a, a + 0.4) }); }
