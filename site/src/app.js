// Beat the Bell: page logic. Reads docs/state.json (live) or docs/replay_YYYY-MM-DD.json and draws the same three
// tabs from either. Strings live in strings.js (T), the look in style.css. No framework; Leaflet draws the map.
(function () {
  "use strict";
  var SHORT = { "501209052": ["圖資", "Library"], "501209070": ["西灣藝廊", "Xiziwan Hall"], "501209051": ["工學院", "Engineering"], "501209054": ["材料", "Materials"],
                "501209039": ["社科院", "Social Sci."], "501209069": ["體育館", "Gym"], "501209040": ["海工館", "Marine Eng."], "501209071": ["海資館", "Marine Res."] };
  var CAMPUS_CENTER = [22.6273, 120.2658];
  var FILL = { g: "--ok-fill", y: "--low-fill", o: "--risk-fill", r: "--out-fill", x: "--gone", n: "--r0" };
  var ICON = {
    play: "<svg width=\"16\" height=\"16\" viewBox=\"0 0 16 16\" aria-hidden=\"true\"><path d=\"M4 2.5v11l9-5.5z\" fill=\"currentColor\"/></svg>",
    pause: "<svg width=\"16\" height=\"16\" viewBox=\"0 0 16 16\" aria-hidden=\"true\"><path d=\"M3.5 2.5h3v11h-3zM9.5 2.5h3v11h-3z\" fill=\"currentColor\"/></svg>",
    close: "<svg width=\"14\" height=\"14\" viewBox=\"0 0 14 14\" aria-hidden=\"true\"><path d=\"M2 2l10 10M12 2 2 12\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\"/></svg>",
    star: "<svg width=\"16\" height=\"16\" viewBox=\"0 0 24 24\" aria-hidden=\"true\"><path d=\"m12 3 2.7 5.6 6.1.8-4.5 4.2 1.1 6-5.4-3-5.4 3 1.1-6L3.2 9.4l6.1-.8z\" fill=\"FILL\" stroke=\"currentColor\" stroke-width=\"1.8\" stroke-linejoin=\"round\"/></svg>",
    walk: "<svg width=\"16\" height=\"16\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><circle cx=\"13\" cy=\"4.5\" r=\"1.8\"/><path d=\"m9 21 2.5-6.5L9 12l1.5-4.5 3.5 1 2 3 3 1M11.5 14.5 15 17l1 4\"/></svg>"
  };

  var lang = "zh", mode = "live", tab = "rider", horizon = 30;
  var live = null, replay = null, replays = {}, replayDays = [], replayDay = null, slot = 0, playing = false, playTimer = null;
  var selected = null, fitted = false, nearN = 8, pendingSno = null, wantSlot = null, errKind = null, daysKey = "";
  var origin = { kind: "campus", lat: CAMPUS_CENTER[0], lng: CAMPUS_CENTER[1] }, dest = { kind: "campus", lat: CAMPUS_CENTER[0], lng: CAMPUS_CENTER[1] }, picking = false, favs = [];
  var when = { rider: { kind: "now" }, dock: { kind: "plus", min: 10 } }, usual = null;      // when the rider leaves (borrow) or rides in (return)
  var KRT = "501209023";                                                                      // the metro station at the foot of the campus (Exit 2), a preset place
  var A64 = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-_";               // state.json packs a chance or a count into one character
  var SURE = { bike: 57, dock: 60 }, MAYBE = { bike: 38, dock: 45 };                          // in 64ths: 0.9 and 0.6 for a bike, 0.95 and 0.7 for a dock
  var map, attrib, glyphLayer, routeLayer, originLayer, markers = {};
  var sheetState = "half", sheetPx = { peek: 158, half: 320, full: 600 }, drag = null, swallowClick = false, toastTimer = null;

  var $ = function (id) { return document.getElementById(id); };
  var root = document.documentElement, shell = $("shell"), panel = $("panel"), scroller = $("scroll");
  var css = getComputedStyle(root);
  function tok(n) { return css.getPropertyValue(n).trim(); }
  function t(k, v) { var s = T[lang][k]; if (s == null) s = k; if (v) Object.keys(v).forEach(function (x) { s = s.split("{" + x + "}").join(v[x]); }); return s; }
  function fmt(x, d) { return x == null ? "–" : Number(x).toFixed(d == null ? 0 : d); }
  function pad(n) { return (n < 10 ? "0" : "") + n; }
  function hm(m) { return pad(Math.floor(m / 60)) + ":" + pad(m % 60); }
  function mins(s) { return parseInt(s.slice(0, 2), 10) * 60 + parseInt(s.slice(3), 10); }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;" }[c]; }); }
  function isCampus(s) { return s.group === "campus"; }
  function nameOf(s) { if (lang === "zh") return s.name; return isCampus(s) && SHORT[s.sno] ? "NSYSU " + SHORT[s.sno][1] : (s.name_en || s.name); }
  function altName(s) { return lang === "zh" ? (isCampus(s) && SHORT[s.sno] ? "NSYSU " + SHORT[s.sno][1] : (s.name_en || "")) : s.name; }
  function taipeiNow() { var n = new Date(); return new Date(n.getTime() + (n.getTimezoneOffset() + 480) * 60000); }
  function distKm(a, b, c, d) { return Math.hypot((a - c) * 111, (b - d) * 102.5); }
  function walkMin(km) { return Math.max(1, Math.round(km * 1.25 * 1000 / 80)); }   // straight line x 1.25 at 80 m/min
  function store(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  function load(k, d) { try { var v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } }
  function isPhone() { return window.matchMedia("(max-width: 767px)").matches; }
  function sep() { return lang === "zh" ? "，" : ", "; }
  favs = load("btb-favs", []); if (!Array.isArray(favs)) favs = [];

  // ---------- will there be a bike (a free dock) when the rider gets there ----------
  // One vocabulary for the list and the map: the number is the count right now, the colour and the words are the
  // answer at the minute of arrival, from the chain forecast in state.json ("ahead").
  function need() { return tab === "dock" ? "dock" : "bike"; }
  function point() { return tab === "dock" ? dest : origin; }
  function have(v, i, kind) { return kind === "bike" ? v.bikes[i] : (v.docks ? v.docks[i] : null); }
  function nowMin(v) { if (mode !== "live") return v.t_min; var n = taipeiNow(), m = n.getHours() * 60 + n.getMinutes(); return m >= v.t_min && m - v.t_min <= 30 ? m : v.t_min; }
  function leaveMin(v) { var w = when[tab === "dock" ? "dock" : "rider"], n = nowMin(v); return w.kind === "bell" ? Math.max(n, w.time + 5) : w.kind === "plus" ? n + w.min : n; }
  function arriveMin(v, i) { var s = v.stations[i], p = point(); return leaveMin(v) + (need() === "bike" ? walkMin(distKm(s.lat, s.lng, p.lat, p.lng)) : 0); }
  function aheadOf(v, i, key) { return v.ahead && v.ahead[key] && v.ahead[key][i] ? v.ahead[key][i] : ""; }
  function stepAt(v, a, at) { return Math.max(1, Math.min(a.length, Math.ceil((at - v.t_min) / 10))); }
  // chance in 64ths that station i has a bike (dock) at minute `at`; without a forecast, a guess from the count now
  function chanceAt(v, i, kind, at) {
    var h = have(v, i, kind); if (v.bikes[i] == null || h == null) return null;
    var a = aheadOf(v, i, kind); if (!a) return h >= 3 ? 63 : h >= 1 ? 40 : 0;
    return A64.indexOf(a.charAt(stepAt(v, a, at) - 1));
  }
  function expectAt(v, i, at) { var a = aheadOf(v, i, "bikes"); return a ? A64.indexOf(a.charAt(stepAt(v, a, at) - 1)) : null; }
  function verdict(v, i, kind, at) {
    if (v.bikes[i] == null) return { cls: "n", text: v.status && v.status[i] === 2 ? t("sOos") : t("sNone") };
    var c = chanceAt(v, i, kind, at), h = have(v, i, kind), bike = kind === "bike";
    if (c == null) return { cls: "n", text: "" };
    if (c >= SURE[kind]) return { cls: "g", text: t(bike ? "cBikeYes" : "cDockYes") };
    if (c >= MAYBE[kind]) return { cls: "y", text: t(bike ? "cBikeMaybe" : "cDockMaybe") };
    return h === 0 ? { cls: "x", text: t(bike ? "sGone" : "sFullNow") } : { cls: "r", text: t(bike ? "cBikeNo" : "cDockNo") };
  }
  function look(v, i) { return verdict(v, i, need(), arriveMin(v, i)); }
  // when the answer changes: "likely out by 17:20", or for an empty station "a bike likely back by 18:10"
  function turnText(v, i, kind) {
    var a = aheadOf(v, i, kind), h = have(v, i, kind), bike = kind === "bike", k; if (!a || h == null) return "";
    var end = hm((v.t_min + 10 * a.length) % 1440), at = function (n) { return hm((v.t_min + 10 * (n + 1)) % 1440); };
    if (h > 0) { for (k = 0; k < a.length; k++) if (A64.indexOf(a.charAt(k)) < 32) return t(bike ? "tGone" : "tFull", { t: at(k) }); return t(bike ? "tKeep" : "tFree", { t: end }); }
    for (k = 0; k < a.length; k++) if (A64.indexOf(a.charAt(k)) >= 32) return t(bike ? "tBack" : "tOpen", { t: at(k) });
    return t(bike ? "tNoBack" : "tNoOpen", { t: end });
  }
  function ramp(p) { if (p == null) return tok("--r0"); return tok(p < 0.1 ? "--r0" : p < 0.3 ? "--r1" : p < 0.5 ? "--r2" : p < 0.75 ? "--r3" : "--r4"); }
  function rampU(u) { if (u == null) return tok("--r0"); return tok(u < 0.5 ? "--r0" : u < 2 ? "--r1" : u < 5 ? "--r2" : u < 10 ? "--r3" : "--r4"); }
  function keyOf() { return horizon === 30 ? "p30" : horizon === 60 ? "p60" : "unmet"; }
  function fillOf(v, i) {
    if (v.bikes[i] == null) return tok("--r0");
    if (tab === "ops") return horizon === 90 ? rampU(v.unmet ? v.unmet[i] : null) : ramp(v[keyOf()][i]);
    return tok(FILL[look(v, i).cls]);
  }
  function inkOn(hex) {
    var c = hex.replace("#", ""); if (c.length === 3) c = c.replace(/(.)/g, "$1$1");
    var r = parseInt(c.slice(0, 2), 16), g = parseInt(c.slice(2, 4), 16), b = parseInt(c.slice(4, 6), 16);
    return 0.299 * r + 0.587 * g + 0.114 * b > 150 ? "#10202f" : "#ffffff";
  }
  function countOf(v, i) { var h = have(v, i, need()); return v.bikes[i] == null || h == null ? "–" : h; }
  function badge(v, i) { return "<span class=\"badge " + look(v, i).cls + "\">" + countOf(v, i) + "</span>"; }

  // ---------- current view: live state or one replay slot, in one shape ----------
  function view() {
    if (mode === "replay" && replay) {
      var sl = replay.slots[slot];
      return { meta: replay, stations: replay.stations, snapshot_at: sl.snapshot_at, t_min: sl.t_min, offday: replay.offday, in_window: true, next_bell: sl.next_bell, ahead: sl.ahead || null,
               totals: sl.totals, plans: sl.plans, bikes: sl.bikes, docks: sl.docks || null, status: null, age: null, p30: sl.p30, p60: sl.p60, unmet: sl.unmet,
               history: function (i) { return replay.slots.slice(0, slot + 1).map(function (x) { return [x.t_min, x.bikes[i]]; }); } };
    }
    if (!live) return null;
    return { meta: live, stations: live.stations, snapshot_at: live.snapshot_at, t_min: live.t_min, offday: live.offday, in_window: live.in_window, next_bell: live.next_bell, ahead: live.ahead || null,
             totals: live.totals, plans: live.plans, bikes: live.bikes, docks: live.docks, status: live.status, age: live.age, p30: live.p30, p60: live.p60, unmet: live.unmet,
             history: function (i) { var t0 = mins(live.history.from), st = live.history.step; return (live.history.bikes[i] || []).map(function (b, k) { return [t0 + k * st, b]; }); } };
  }

  // ---------- the sheet (phones) ----------
  function measureSheet() {
    var H = document.querySelector(".mapwrap").clientHeight;       // the space between the header and the tab bar
    sheetPx.full = Math.max(240, H - 10);
    sheetPx.half = Math.round(Math.min(sheetPx.full, Math.max(240, H * 0.52)));
    sheetPx.peek = Math.min(sheetPx.half, 164);
    root.style.setProperty("--sheet-full", sheetPx.full + "px");
  }
  function placeSheet(up) {
    root.style.setProperty("--sheet-y", (sheetPx.full - up) + "px");
    root.style.setProperty("--sheet-up", up + "px");
    root.style.setProperty("--sheet-vis", Math.max(60, up - 30) + "px");
  }
  function setSheet(state) {
    sheetState = state; shell.setAttribute("data-sheet", state);
    if (isPhone()) placeSheet(sheetPx[state]);
    if (state !== "full") scroller.scrollTop = 0;
  }
  function sheetUp() { return isPhone() ? sheetPx[sheetState === "full" ? "half" : sheetState] : 0; }
  function dragStart(y) { drag = { y0: y, y: y, t: Date.now(), base: sheetPx.full - sheetPx[sheetState], moved: false, vy: 0 }; panel.classList.add("dragging"); }
  function dragMove(y) {
    if (!drag) return;
    var now = Date.now(); drag.vy = (y - drag.y) / Math.max(1, now - drag.t); drag.y = y; drag.t = now;
    if (Math.abs(y - drag.y0) > 6) drag.moved = true;
    var ty = Math.min(sheetPx.full - sheetPx.peek + 40, Math.max(0, drag.base + (y - drag.y0)));
    drag.up = sheetPx.full - ty; placeSheet(drag.up);
  }
  function stepSheet() { setSheet(sheetState === "peek" ? "half" : sheetState === "half" ? "full" : "half"); }
  function dragEnd() {
    if (!drag) return;
    var d = drag; drag = null; panel.classList.remove("dragging");
    if (!d.moved) { setSheet(sheetState); return; }
    swallowClick = true; setTimeout(function () { swallowClick = false; }, 350);
    var up = d.up + (-d.vy * 180), best = "peek", gap = Infinity;      // a flick carries the sheet a bit further
    ["peek", "half", "full"].forEach(function (s) { var g = Math.abs(sheetPx[s] - up); if (g < gap) { gap = g; best = s; } });
    setSheet(best);
  }
  function initSheet() {
    var grip = $("grip");
    grip.addEventListener("pointerdown", function (e) { if (!isPhone()) return; grip.setPointerCapture(e.pointerId); dragStart(e.clientY); });
    grip.addEventListener("pointermove", function (e) { if (drag) dragMove(e.clientY); });
    grip.addEventListener("pointerup", function () { dragEnd(); });
    grip.addEventListener("pointercancel", function () { dragEnd(); });
    grip.addEventListener("click", function () { if (swallowClick) { swallowClick = false; return; } if (isPhone()) stepSheet(); });
    // Swiping on the content moves the sheet until it is fully open; then it scrolls, and pulling down from the top closes it.
    var ts = null;
    scroller.addEventListener("touchstart", function (e) { if (!isPhone() || e.touches.length !== 1) { ts = null; return; } ts = { y: e.touches[0].clientY, x: e.touches[0].clientX, on: false }; }, { passive: true });
    scroller.addEventListener("touchmove", function (e) {
      if (!ts) return;
      var y = e.touches[0].clientY, dy = y - ts.y, dx = e.touches[0].clientX - ts.x;
      if (!ts.on) {
        if (Math.abs(dy) < 8 || Math.abs(dx) > Math.abs(dy)) return;
        if (sheetState === "full" && !(scroller.scrollTop <= 0 && dy > 0)) { ts = null; return; }
        ts.on = true; dragStart(ts.y);
      }
      if (e.cancelable) e.preventDefault();
      dragMove(y);
    }, { passive: false });
    scroller.addEventListener("touchend", function () { if (ts && ts.on) dragEnd(); ts = null; });
    scroller.addEventListener("touchcancel", function () { if (ts && ts.on) dragEnd(); ts = null; });
    scroller.addEventListener("wheel", function (e) { if (isPhone() && sheetState !== "full" && e.deltaY > 0) setSheet("full"); }, { passive: true });
    window.addEventListener("resize", function () { measureSheet(); setSheet(sheetState); if (map) { map.invalidateSize(); attrib.setPosition(isPhone() ? "topright" : "bottomright"); } });
    measureSheet(); setSheet(sheetState);
  }
  function toast(text, ms) {
    var el = $("toast"); el.textContent = text; el.hidden = false;
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { el.hidden = true; }, ms || 2600);
  }

  // ---------- map ----------
  function initMap() {
    map = L.map("map", { zoomControl: false, attributionControl: false }).setView([22.633, 120.29], 13);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, attribution: "&copy; <a href=\"https://www.openstreetmap.org/copyright\" target=\"_blank\" rel=\"noopener\">OpenStreetMap</a>" }).addTo(map);
    attrib = L.control.attribution({ prefix: false, position: isPhone() ? "topright" : "bottomright" }).addTo(map);
    L.control.zoom({ position: "bottomright" }).addTo(map);
    L.control.scale({ imperial: false, position: "bottomleft" }).addTo(map);
    glyphLayer = L.layerGroup().addTo(map);
    routeLayer = L.layerGroup().addTo(map);
    originLayer = L.layerGroup().addTo(map);
    map.on("zoomend", function () { var v = view(); if (v) drawStations(v); });
    map.on("click", function (e) {
      if (picking) { setOrigin("pick", e.latlng.lat, e.latlng.lng); setPicking(false); return; }
      if (selected != null) select(null); else if (isPhone() && sheetState !== "peek") setSheet("peek");
    });
    var mq = window.matchMedia("(prefers-color-scheme: dark)");
    if (mq.addEventListener) mq.addEventListener("change", retheme);
    new MutationObserver(retheme).observe(root, { attributes: true, attributeFilter: ["data-theme"] });
  }
  function retheme() { css = getComputedStyle(root); render(); }
  function glyphR(cap) { var z = map.getZoom(); return z >= 16 ? 8 + Math.sqrt(cap) * 1.1 : z === 15 ? 6.5 + Math.sqrt(cap) * 0.9 : (3 + Math.sqrt(cap) * 0.75) * (z <= 12 ? 0.55 : z <= 13 ? 0.75 : 1); }
  function glyphHtml(s, v, i, sel) {
    var big = map.getZoom() >= 15, R = glyphR(s.cap), S = 2 * R + 6, c = S / 2, observed = v.bikes[i] != null, fill = fillOf(v, i);
    var star = favs.indexOf(s.sno) >= 0 && map.getZoom() >= 14 ? "<span class=\"star\">★</span>" : "";
    var open = "<div class=\"glyph" + (sel ? " sel" : "") + "\"><svg width=\"" + S + "\" height=\"" + S + "\" viewBox=\"0 0 " + S + " " + S + "\">";
    if (!big) {
      // zoomed out: a dot sized by the station; stations with nothing to report stay small and faint
      var calm = !observed || (tab === "ops" && fill === tok("--r0")), r = calm ? R * 0.8 : R;
      return open + "<circle cx=\"" + c + "\" cy=\"" + c + "\" r=\"" + r.toFixed(1) + "\" fill=\"" + fill + "\" fill-opacity=\"" + (observed ? 1 : 0.6) + "\" stroke=\"" + (isCampus(s) ? tok("--accent") : calm ? tok("--line-2") : tok("--surface")) + "\" stroke-width=\"" + (isCampus(s) ? 2 : 1.2) + "\"" + (observed ? "" : " stroke-dasharray=\"2 2\"") + "/></svg>" + star + "</div>";
    }
    var rr = R - 3.5, frac = observed && s.cap > 0 ? Math.max(0, Math.min(1, v.bikes[i] / s.cap)) : 0, arc = "";
    if (frac > 0) {
      var a = frac * 2 * Math.PI - Math.PI / 2, x = c + R * Math.cos(a), y = c + R * Math.sin(a);
      arc = frac >= 0.999 ? "<circle cx=\"" + c + "\" cy=\"" + c + "\" r=\"" + R + "\" fill=\"none\" stroke=\"" + tok("--ink-3") + "\" stroke-width=\"2.5\"/>"
        : "<path d=\"M " + c + " " + (c - R) + " A " + R + " " + R + " 0 " + (frac > 0.5 ? 1 : 0) + " 1 " + x.toFixed(2) + " " + y.toFixed(2) + "\" fill=\"none\" stroke=\"" + tok("--ink-3") + "\" stroke-width=\"2.5\" stroke-linecap=\"round\"/>";
    }
    var num = observed ? "<text x=\"" + c + "\" y=\"" + c + "\" dy=\"0.36em\" text-anchor=\"middle\" font-size=\"" + Math.min(14, Math.max(10, rr * 1.05)).toFixed(1) + "\" fill=\"" + inkOn(fill) + "\">" + (tab === "dock" ? countOf(v, i) : v.bikes[i]) + "</text>" : "";
    var label = isCampus(s) && SHORT[s.sno] ? "<span class=\"lbl\">" + SHORT[s.sno][lang === "zh" ? 0 : 1] + "</span>" : "";
    return open + "<circle cx=\"" + c + "\" cy=\"" + c + "\" r=\"" + (rr + 1.5) + "\" fill=\"" + tok("--surface") + "\"/>" +
      "<circle cx=\"" + c + "\" cy=\"" + c + "\" r=\"" + R + "\" fill=\"none\" stroke=\"" + (isCampus(s) ? tok("--accent") : tok("--line-2")) + "\" stroke-width=\"" + (isCampus(s) ? 2.5 : 1.5) + "\"" + (observed ? "" : " stroke-dasharray=\"3 3\"") + "/>" + arc +
      "<circle cx=\"" + c + "\" cy=\"" + c + "\" r=\"" + rr + "\" fill=\"" + fill + "\" fill-opacity=\"" + (observed ? 1 : 0.7) + "\"/>" + num + "</svg>" + star + label + "</div>";
  }
  function drawStations(v) {
    glyphLayer.clearLayers(); markers = {};
    if (!fitted) { fitted = true; if (tab === "ops") fitArea(v); else fitCampus(v, false); }
    v.stations.forEach(function (s, i) {
      var S = 2 * glyphR(s.cap) + 6;
      var m = L.marker([s.lat, s.lng], { icon: L.divIcon({ className: "", html: glyphHtml(s, v, i, selected === i), iconSize: [S, S], iconAnchor: [S / 2, S / 2] }),
        zIndexOffset: selected === i ? 800 : (isCampus(s) ? 500 : 0), keyboard: false });
      m.on("click", function (e) { L.DomEvent.stopPropagation(e); if (picking) { setOrigin("pick", s.lat, s.lng); setPicking(false); } select(i); });
      m.addTo(glyphLayer); markers[i] = m;
    });
    declutter();
  }
  // Station names sit under their mark. Where two campus stations are close, a name would cover its neighbour's
  // mark or name, so each name tries below, above, right and left of its mark and is left out if none is free.
  function declutter() {
    var names = [].slice.call(document.querySelectorAll("#map .glyph .lbl"));
    if (!names.length) return;
    var marks = [].slice.call(document.querySelectorAll("#map .glyph svg")).map(function (el) { return { el: el, r: el.getBoundingClientRect() }; });
    var hit = function (a, b, pad) { return a.left < b.right - pad && a.right > b.left + pad && a.top < b.bottom - pad && a.bottom > b.top + pad; };
    var placed = [];
    names.forEach(function (el) {
      var own = el.parentNode.querySelector("svg");
      var free = ["", " t", " r", " l"].some(function (pos) {
        el.className = "lbl" + pos;
        var r = el.getBoundingClientRect();
        var blocked = placed.some(function (p) { return hit(r, p, 0); }) || marks.some(function (m) { return m.el !== own && hit(r, m.r, 4); });
        if (!blocked) placed.push(r);
        return !blocked;
      });
      if (!free) el.className = "lbl off";
    });
  }
  function drawRoute(v) {
    routeLayer.clearLayers();
    if (tab !== "ops") return;
    (v.plans || []).forEach(function (pl) {
      var pts = pl.stops.map(function (st) { var s = v.stations[st.i]; return [s.lat, s.lng]; });
      if (pts.length > 1) { L.polyline(pts, { color: tok("--surface"), weight: 8, opacity: 0.92, interactive: false }).addTo(routeLayer); L.polyline(pts, { color: tok("--accent"), weight: 4.5, opacity: 1, className: "route-line", interactive: false }).addTo(routeLayer); }
      pl.stops.forEach(function (st, k) {
        var s = v.stations[st.i];
        L.marker([s.lat, s.lng], { icon: L.divIcon({ className: "", html: "<div class=\"stopicon\">" + (k + 1) + "</div>", iconSize: [24, 24], iconAnchor: [12, 34] }), zIndexOffset: 1000, keyboard: false })
          .on("click", function (e) { L.DomEvent.stopPropagation(e); select(st.i); }).addTo(routeLayer);
      });
    });
  }
  function drawOrigin() {
    originLayer.clearLayers();
    var p = point();
    if (p.kind === "campus" || tab === "ops" || tab === "about") return;
    L.marker([p.lat, p.lng], { icon: L.divIcon({ className: "", html: "<div class=\"originicon\"></div>", iconSize: [18, 18], iconAnchor: [9, 9] }), zIndexOffset: 900, keyboard: false, interactive: false }).addTo(originLayer);
  }
  // Centre a point in the part of the map that the sheet leaves visible.
  function viewTo(lat, lng, zoom, animate) {
    var z = zoom == null ? map.getZoom() : zoom, off = sheetUp() / 2;
    if (!off) { map.setView([lat, lng], z, { animate: animate !== false }); return; }
    var p = map.project([lat, lng], z); p.y += off; map.setView(map.unproject(p, z), z, { animate: animate !== false });
  }
  function fitCampus(v, animate) {
    var c = v.stations.filter(isCampus), mid = function (k) { var a = c.map(function (s) { return s[k]; }).sort(function (x, y) { return x - y; }); return a.length ? (a[Math.floor((a.length - 1) / 2)] + a[Math.ceil((a.length - 1) / 2)]) / 2 : null; };
    if (!c.length) viewTo(CAMPUS_CENTER[0], CAMPUS_CENTER[1], 16, animate); else viewTo(mid("lat"), mid("lng"), 16, animate);
  }
  function focusStation(s) { viewTo(s.lat, s.lng, Math.max(map.getZoom(), 16)); }
  function fitArea(v) {
    var near = v.stations.filter(function (s) { return distKm(s.lat, s.lng, CAMPUS_CENTER[0], CAMPUS_CENTER[1]) <= 2.6; });
    map.fitBounds(L.latLngBounds(near.map(function (s) { return [s.lat, s.lng]; })), { paddingTopLeft: [24, 24], paddingBottomRight: [24, 24 + sheetUp()] });
  }

  // ---------- the bell board ----------
  function untilText(m, long) { return m >= 100 ? t(long ? "bellInH" : "inHour", { h: Math.floor(m / 60), m: m % 60 }) : t(long ? "bellIn" : "inMin", { m: m }); }
  // how the eight campus stations look for someone on campus right now: mostly sure, running low, or nearly out
  function campusStatus(v) {
    if (!v.ahead || !v.in_window) return "";
    var kind = need(), n = 0, sure = 0, at = nowMin(v) + 3;
    v.stations.forEach(function (s, i) { if (!isCampus(s) || v.bikes[i] == null) return; var c = chanceAt(v, i, kind, at); if (c == null) return; n++; if (c >= SURE[kind]) sure++; });
    if (n < 4) return "";
    var k = sure >= 0.6 * n ? "Ok" : sure >= 0.3 * n ? "Low" : "Out";
    return t((kind === "bike" ? "stBike" : "stDock") + k);
  }
  function renderBell(v) {
    var m = v.t_min, nb = v.next_bell, off = !!v.offday;
    if (mode === "live") {
      var n = taipeiNow(); m = n.getHours() * 60 + n.getMinutes(); nb = null;
      if (n.getDay() === 0 || n.getDay() === 6) off = true;
      if (!off) v.meta.bells.forEach(function (b) { var bm = mins(b); if (!nb && bm > m) nb = { time: b, minutes: bm - m }; });
    }
    var at = $("boardAt"), left = $("boardLeft"), note = $("boardNote"), lbl = $("boardLbl"), ml = $("miniLbl"), mleft = $("miniLeft");
    at.className = "at"; mleft.className = "left";
    var st = campusStatus(v);
    if (off) {
      lbl.textContent = t("nowIs", { t: hm(m) }); at.textContent = t("offdayBig"); at.classList.add("calm"); left.textContent = ""; note.textContent = st || t("offdayNote");
      ml.textContent = st || t("offdayNote"); mleft.textContent = t("offdayBig"); mleft.classList.add("calm");
    } else if (!nb) {
      var last = v.meta.bells[v.meta.bells.length - 1];
      lbl.textContent = t("nowIs", { t: hm(m) }); at.textContent = t("overBig"); at.classList.add("calm"); left.textContent = ""; note.textContent = st || t("overNote", { t: last });
      ml.textContent = st || t("overNote", { t: last }); mleft.textContent = t("overBig"); mleft.classList.add("calm");
    } else {
      lbl.textContent = t("bellNext"); at.textContent = nb.time; left.textContent = untilText(nb.minutes, true); note.textContent = st || t("nowIs", { t: hm(m) });
      ml.textContent = st || (t("bellNext") + " " + nb.time); mleft.innerHTML = (st ? "<small class=\"bt\">" + t("wBell", { t: nb.time }) + "</small>" : "") + untilText(nb.minutes, false);
    }
    var lo = 6 * 60, hi = 23 * 60, h = "<div class=\"axis\"></div>", nbm = nb ? mins(nb.time) : null;
    var x = function (mm) { return (100 * (mm - lo) / (hi - lo)).toFixed(2) + "%"; };
    [6, 9, 12, 15, 18, 21].forEach(function (hh) { if (nbm != null && Math.abs(nbm - hh * 60) < 75) return; h += "<span class=\"hr\" style=\"left:" + x(hh * 60) + "\">" + pad(hh) + "</span>"; });
    v.meta.bells.forEach(function (b) {
      var bm = mins(b); if (bm < lo || bm > hi) return;
      var major = v.meta.major_bells.indexOf(b) >= 0, isNext = !off && nb && nb.time === b;
      h += "<span class=\"tick" + (major ? " major" : "") + (isNext ? " next" : (bm <= m || off ? " past" : "")) + "\" style=\"left:" + x(bm) + "\"></span>";
      if (isNext) h += "<span class=\"hr next\" style=\"left:" + x(bm) + "\">" + b + "</span>";
    });
    if (m >= lo && m <= hi) h += "<span class=\"now\" style=\"left:" + x(m) + "\"></span>";
    $("ruler").innerHTML = h;
  }

  // ---------- borrow and return ----------
  function setOrigin(kind, lat, lng) { var p = point(); p.kind = kind; p.lat = lat; p.lng = lng; nearN = 8; if (view()) render(); }
  function setPicking(on) {
    picking = on; $("hint").hidden = !on; $("hint").textContent = t(tab === "dock" ? "pickingDest" : "picking"); $("map").classList.toggle("picking", on); syncOrigin();
    if (isPhone()) setSheet(on ? "peek" : "half");
  }
  function syncOrigin() {
    var k = point().kind;
    $("oCampus").setAttribute("aria-pressed", !picking && k === "campus" ? "true" : "false");
    $("oKrt").setAttribute("aria-pressed", !picking && k === "krt" ? "true" : "false");
    $("oMe").setAttribute("aria-pressed", !picking && k === "me" ? "true" : "false");
    $("oPick").setAttribute("aria-pressed", picking || k === "pick" ? "true" : "false");
    $("fab").setAttribute("aria-pressed", k === "me" ? "true" : "false");
  }
  function locate() {
    var fab = $("fab"), fail = function () { fab.classList.remove("busy"); toast(t("geoFail"), 4000); };
    if (!navigator.geolocation) { fail(); return; }
    fab.classList.add("busy"); if (picking) setPicking(false);
    navigator.geolocation.getCurrentPosition(function (pos) {
      fab.classList.remove("busy");
      var lat = pos.coords.latitude, lng = pos.coords.longitude, v = view();
      var nearest = v ? Math.min.apply(null, v.stations.map(function (s) { return distKm(s.lat, s.lng, lat, lng); })) : 0;
      if (nearest > 5) { toast(t("tooFar"), 4500); return; }
      setOrigin("me", lat, lng); viewTo(lat, lng, Math.max(map.getZoom(), 16));
    }, fail, { timeout: 8000, maximumAge: 60000, enableHighAccuracy: true });
  }
  function walkCell(km, label) { return km > 3 ? "<span class=\"walk\">" + t("walkKm", { k: km.toFixed(1) }) + "<small>" + t("farK") + "</small></span>" : "<span class=\"walk\">" + t("walkMin", { m: walkMin(km) }) + "<small>" + t(label || "walkK") + "</small></span>"; }
  function shortName(s) { return isCampus(s) && SHORT[s.sno] ? SHORT[s.sno][lang === "zh" ? 0 : 1] : nameOf(s); }
  function subLine(v, i) {
    var o = look(v, i), turn = v.bikes[i] == null ? "" : turnText(v, i, need()), h = "";
    if (o.text) h += "<span class=\"state " + o.cls + "\">" + o.text + "</span>";
    if (turn) h += "<span>" + turn + "</span>";
    return h;
  }
  function stationRow(v, i) {
    var s = v.stations[i], p = point(), li = document.createElement("li"); li.className = "row" + (selected === i ? " sel" : ""); li.tabIndex = 0;
    var km = distKm(s.lat, s.lng, p.lat, p.lng);
    li.innerHTML = badge(v, i) + "<span><span class=\"nm\">" + esc(nameOf(s)) + (favs.indexOf(s.sno) >= 0 ? "<span class=\"star\" aria-hidden=\"true\">★</span>" : "") + "</span><span class=\"sub\">" + subLine(v, i) + "</span></span>" + walkCell(km, tab === "dock" ? "walkDest" : "walkK");
    var go = function () { select(i); focusStation(s); };
    li.addEventListener("click", go); li.addEventListener("keydown", function (e) { if (e.key === "Enter") go(); });
    return li;
  }
  function ordered(v) { var p = point(); return v.stations.map(function (s, i) { return [distKm(s.lat, s.lng, p.lat, p.lng), i]; }).sort(function (a, b) { return a[0] - b[0]; }); }
  // The rule checked against the logger (analysis/code/final_rider.py): the nearest station that should still have what
  // the rider needs at the minute of arrival; if none is sure, the best chance in reach. A bike is needed after the walk
  // to the station, a dock when the ride ends.
  function pick(v, ord, kind, leave) {
    var reach = kind === "bike" ? 2 : 0.6, best = null, skipped = null;
    for (var k = 0; k < ord.length; k++) {
      var km = ord[k][0], i = ord[k][1]; if (km > reach) break;
      var c = chanceAt(v, i, kind, leave + (kind === "bike" ? walkMin(km) : 0)); if (c == null) continue;
      if (c >= SURE[kind]) return { i: i, km: km, sure: true, skipped: skipped };
      if (skipped == null && c < MAYBE[kind]) skipped = i;
      if (!best || c > best.c) best = { i: i, km: km, sure: false, c: c, skipped: null };
    }
    return best;
  }
  // "Leave before 16:55 and a bike is 1 min away. Later it is 9 min." The walk to a sure station, for departures in the next hour.
  function leaveTip(v, ord) {
    if (!v.ahead) return "";
    var n = nowMin(v), first = pick(v, ord, "bike", n); if (!first || !first.sure) return "";
    var a = walkMin(first.km), last = 0, later = null;
    for (var d = 10; d <= 60; d += 10) { var p = pick(v, ord, "bike", n + d); if (p && p.sure && walkMin(p.km) <= a + 2) last = d; else { later = p; break; } }
    if (last >= 60) return t("tipCalm", { a: a });
    var by = hm(Math.floor((n + last + 5) / 5) * 5);
    return later && later.sure ? t("tipSoon", { t: by, a: a, b: walkMin(later.km) }) : t("tipLast", { t: by, a: a });
  }
  function renderWhen(v) {
    var el = $("whenChips"), dock = tab === "dock", key = dock ? "dock" : "rider", w = when[key], n = nowMin(v), opts = [];
    if (dock) [0, 10, 20, 30].forEach(function (m) { opts.push(m ? { kind: "plus", min: m, label: t("wPlus", { m: m }) } : { kind: "now", label: t("wNow") }); });
    else {
      opts.push({ kind: "now", label: t("wNow") });
      if (!v.offday) v.meta.bells.forEach(function (b) { var bm = mins(b); if (bm > n && bm - n <= 70 && opts.length < 3) opts.push({ kind: "bell", time: bm, label: t("wBell", { t: b }) }); });
    }
    var same = function (o) { return o.kind === w.kind && (o.kind === "now" || (o.kind === "bell" ? o.time === w.time : o.min === w.min)); };
    if (!opts.some(same)) { when[key] = { kind: "now" }; w = when[key]; }      // the chosen class end has passed
    $("whenK").textContent = t(dock ? "whenDockK" : "whenBikeK");
    el.innerHTML = "";
    opts.forEach(function (o) {
      var b = document.createElement("button"); b.type = "button"; b.className = "opt"; b.textContent = o.label; b.setAttribute("aria-pressed", same(o) ? "true" : "false");
      b.addEventListener("click", function () { when[key] = o.kind === "now" ? { kind: "now" } : o.kind === "bell" ? { kind: "bell", time: o.time } : { kind: "plus", min: o.min }; render(); });
      el.appendChild(b);
    });
  }
  function renderBest(v, ord) {
    var pk = $("best"), tip = $("tip"), kind = need(), dock = kind === "dock", w = when[dock ? "dock" : "rider"], leave = leaveMin(v), p = pick(v, ord, kind, leave);
    pk.hidden = false; pk.innerHTML = ""; tip.hidden = true;
    if (!p) { pk.innerHTML = "<div class=\"pick none\"><span><span class=\"sub\">" + t(dock ? "noneDock" : "noneBike") + "</span></span></div>"; return; }
    var s = v.stations[p.i], at = leave + (dock ? 0 : walkMin(p.km)), o = verdict(v, p.i, kind, at), eb = expectAt(v, p.i, at);
    var why = dock ? t("bestDock") : w.kind === "bell" ? t("bestBikeBell", { t: hm(w.time) }) : t("bestBikeNow");
    var sub = "<span class=\"state " + o.cls + "\">" + o.text + "</span>";
    if (dock) sub += "<span>" + t("docksNow", { d: v.docks && v.docks[p.i] != null ? v.docks[p.i] : "–" }) + "</span>";
    else sub += "<span>" + (eb != null && p.sure ? t("expect", { b: eb }) : t("bikesNow", { b: v.bikes[p.i] })) + "</span>";
    var el = document.createElement("button"); el.type = "button"; el.className = "pick" + (p.sure ? "" : " weak");
    el.innerHTML = badge(v, p.i) + "<span><span class=\"why\">" + why + "</span><span class=\"nm\">" + esc(nameOf(s)) + "</span><span class=\"sub\">" + sub + "</span></span>" + walkCell(p.km, dock ? "walkDest" : "walkK");
    el.addEventListener("click", function () { select(p.i); focusStation(s); });
    pk.appendChild(el);
    var note = !p.sure ? t(dock ? "weakDock" : "weakBike") : p.skipped != null ? t(dock ? "skipDock" : "skipBike", { n: shortName(v.stations[p.skipped]) }) : (!dock && w.kind === "now" ? leaveTip(v, ord) : "");
    if (note) { tip.textContent = note; tip.hidden = false; }
  }
  // The usual day around the starting point (docs/outlook.json): when is it hard to borrow, or to return?
  function renderUsual(v) {
    var sec = $("usualSec"), p = point(), bike = need() === "bike", grp = null, dmin = 9;
    v.stations.forEach(function (s) { if (s.group === "other") return; var d = distKm(s.lat, s.lng, p.lat, p.lng); if (d < dmin) { dmin = d; grp = s.group; } });
    var day = usual ? usual[v.offday ? "off" : "teaching"] : null, arr = day && grp && dmin <= 0.6 && day[grp] ? day[grp][bike ? "no_bike" : "no_dock"] : null;
    if (!arr) { sec.hidden = true; return; }
    sec.hidden = false;
    var a = -1, b = -1; arr.forEach(function (x, k) { if (x >= 0.25) { if (a < 0) a = k; b = k; } });
    $("hUsual").textContent = t("usual" + (bike ? "Bike" : "Dock") + (grp === "campus" ? "Campus" : "Gate"));
    $("hUsualSub").textContent = t(v.offday ? "usualOff" : "usualTeach") + sep() + (a < 0 ? t("usualEasy") : t("usualPeak", { a: hm(360 + 30 * a), b: hm(360 + 30 * (b + 1)) }));
    var W = 340, H = 56, bw = W / arr.length, m = nowMin(v), h = "";
    arr.forEach(function (x, k) { var hh = Math.max(2, Math.min(1, x / 0.6) * 38); h += "<rect x=\"" + (k * bw + 1).toFixed(1) + "\" y=\"" + (40 - hh).toFixed(1) + "\" width=\"" + (bw - 2).toFixed(1) + "\" height=\"" + hh.toFixed(1) + "\" rx=\"2\" fill=\"" + tok(x >= 0.4 ? "--out-fill" : x >= 0.2 ? "--low-fill" : "--line-2") + "\"/>"; });
    [6, 9, 12, 15, 18, 21].forEach(function (hr) { h += "<text x=\"" + ((hr * 60 - 360) / 30 * bw + 1).toFixed(1) + "\" y=\"53\" font-size=\"10.5\" fill=\"" + tok("--ink-3") + "\" font-family=\"Barlow Semi Condensed, sans-serif\">" + pad(hr) + "</text>"; });
    if (m >= 360 && m <= 1380) { var x = ((m - 360) / 30 * bw).toFixed(1); h += "<line x1=\"" + x + "\" x2=\"" + x + "\" y1=\"0\" y2=\"42\" stroke=\"" + tok("--accent") + "\" stroke-width=\"2\"/>"; }
    $("usual").innerHTML = "<svg viewBox=\"0 0 " + W + " " + H + "\" aria-hidden=\"true\">" + h + "</svg>";
  }
  function renderRider(v) {
    var dock = tab === "dock";
    $("q").placeholder = t("search"); $("q").setAttribute("aria-label", t("search"));
    $("originK").textContent = t(dock ? "destK" : "originK"); $("oCampus").textContent = t("oCampus"); $("oKrt").textContent = t("oKrt"); $("oMe").textContent = t("oMe"); $("oPick").textContent = t("oPick"); syncOrigin();
    renderWhen(v);
    $("hFav").textContent = t("fav"); $("hNear").textContent = t("near"); $("hNearSub").textContent = t(dock ? "nearDock" : "nearBike");
    var idx = {}; v.stations.forEach(function (s, i) { idx[s.sno] = i; });
    var fl = $("favs"); fl.innerHTML = "";
    var fi = favs.map(function (sno) { return idx[sno]; }).filter(function (i) { return i != null; });
    $("favSec").hidden = !fi.length;
    fi.forEach(function (i) { fl.appendChild(stationRow(v, i)); });
    $("hFavSub").textContent = fi.length ? String(fi.length) : "";
    var ord = ordered(v), nl = $("near"); nl.innerHTML = "";
    ord.slice(0, nearN).forEach(function (x) { nl.appendChild(stationRow(v, x[1])); });
    $("more").textContent = nearN > 8 ? t("less") : t("more");
    renderBest(v, ord); renderUsual(v);
  }
  function searchStations(q) {
    var v = view(), box = $("qres"); if (!v || !q.trim()) { box.hidden = true; return; }
    var ql = q.trim().toLowerCase(), hits = [];
    v.stations.forEach(function (s, i) { if (hits.length >= 8) return; var hay = (s.name + " " + (s.name_en || "") + " " + (SHORT[s.sno] ? SHORT[s.sno].join(" ") : "")).toLowerCase(); if (hay.indexOf(ql) >= 0) hits.push(i); });
    box.innerHTML = hits.length ? hits.map(function (i) { var s = v.stations[i]; return "<button type=\"button\" data-i=\"" + i + "\"><span>" + esc(nameOf(s)) + "<span class=\"alt\">" + esc(altName(s)) + "</span></span>" + badge(v, i) + "</button>"; }).join("") : "<div class=\"none\">" + t("noMatch") + "</div>";
    box.hidden = false;
    Array.prototype.forEach.call(box.querySelectorAll("button"), function (b) { b.addEventListener("click", function () { var i = parseInt(b.getAttribute("data-i"), 10); box.hidden = true; $("q").value = ""; $("q").blur(); select(i); focusStation(v.stations[i]); }); });
  }

  // ---------- station card ----------
  function sparkline(v, i) {
    var s = v.stations[i], hist = v.history(i);
    var W = 380, H = 88, padL = 24, padR = 8, padT = 8, padB = 18, n = hist.length, lo = 6 * 60, hi = 23 * 60;
    var X = function (mm) { return padL + (W - padL - padR) * (mm - lo) / (hi - lo); }, Y = function (b) { return padT + (H - padT - padB) * (1 - b / Math.max(s.cap, 1)); };
    var d = "", area = "", last = null, lastT = null, firstT = null;
    for (var k = 0; k < n; k++) { var b = hist[k][1], mm = hist[k][0]; if (b == null || mm < lo || mm > hi) continue; d += (last == null ? "M" : "L") + X(mm).toFixed(1) + " " + Y(Math.min(b, s.cap)).toFixed(1) + " "; if (firstT == null) firstT = mm; last = b; lastT = mm; }
    if (d) area = d + "L" + X(lastT).toFixed(1) + " " + Y(0).toFixed(1) + " L" + X(firstT).toFixed(1) + " " + Y(0).toFixed(1) + " Z";
    var bells = ""; v.meta.bells.forEach(function (bb) { var bm = mins(bb); if (bm < lo || bm > hi) return;
      bells += "<line x1=\"" + X(bm).toFixed(1) + "\" x2=\"" + X(bm).toFixed(1) + "\" y1=\"" + padT + "\" y2=\"" + (H - padB) + "\" stroke=\"" + tok(v.meta.major_bells.indexOf(bb) >= 0 ? "--ink-3" : "--line-2") + "\" stroke-width=\"1\" stroke-dasharray=\"2 3\"/>"; });
    var txt = function (xx, yy, anchor, s2) { return "<text x=\"" + xx + "\" y=\"" + yy + "\" font-size=\"10.5\" fill=\"" + tok("--ink-3") + "\" text-anchor=\"" + anchor + "\" font-family=\"Barlow Semi Condensed, sans-serif\">" + s2 + "</text>"; };
    var axis = ""; [6, 12, 18, 23].forEach(function (hh) { axis += txt(X(hh * 60).toFixed(1), H - 4, "middle", pad(hh)); });
    axis += txt(padL - 5, padT + 4, "end", s.cap) + txt(padL - 5, H - padB + 3, "end", "0");
    var fc = "", eb = aheadOf(v, i, "bikes");            // the chain's expected bikes for the next 90 minutes, dashed
    if (eb && last != null) { fc = "M" + X(lastT).toFixed(1) + " " + Y(Math.min(last, s.cap)).toFixed(1) + " "; for (var q = 0; q < eb.length; q++) { var fm = lastT + 10 * (q + 1); if (fm > hi) break; fc += "L" + X(fm).toFixed(1) + " " + Y(Math.min(A64.indexOf(eb.charAt(q)), s.cap)).toFixed(1) + " "; } }
    var dot = last != null ? "<circle cx=\"" + X(lastT).toFixed(1) + "\" cy=\"" + Y(Math.min(last, s.cap)).toFixed(1) + "\" r=\"4\" fill=\"" + tok("--accent") + "\" stroke=\"" + tok("--surface-2") + "\" stroke-width=\"2\"/>" : "";
    return "<svg viewBox=\"0 0 " + W + " " + H + "\" preserveAspectRatio=\"none\" aria-hidden=\"true\"><line x1=\"" + padL + "\" x2=\"" + (W - padR) + "\" y1=\"" + (H - padB) + "\" y2=\"" + (H - padB) + "\" stroke=\"" + tok("--line-2") + "\"/>" +
      "<line x1=\"" + padL + "\" x2=\"" + (W - padR) + "\" y1=\"" + padT + "\" y2=\"" + padT + "\" stroke=\"" + tok("--line-2") + "\" stroke-dasharray=\"1 3\"/>" + bells +
      (area ? "<path d=\"" + area + "\" fill=\"" + tok("--accent") + "\" fill-opacity=\"0.13\"/>" : "") + (d ? "<path d=\"" + d + "\" fill=\"none\" stroke=\"" + tok("--accent") + "\" stroke-width=\"2\" stroke-linejoin=\"round\" vector-effect=\"non-scaling-stroke\"/>" : "") +
      (fc ? "<path d=\"" + fc + "\" fill=\"none\" stroke=\"" + tok("--accent") + "\" stroke-width=\"2\" stroke-dasharray=\"3 4\" stroke-linecap=\"round\" vector-effect=\"non-scaling-stroke\"/>" : "") + dot + axis + "</svg>";
  }
  // the next 90 minutes in five cells: expected bikes (or free docks) and the colour of the answer at that time
  function aheadStrip(v, i, kind) {
    var a = aheadOf(v, i, kind), eb = aheadOf(v, i, "bikes"), s = v.stations[i], h = ""; if (!a || !eb) return "";
    for (var k = 0; k < a.length; k += 2) {
      var c = A64.indexOf(a.charAt(k)), n = A64.indexOf(eb.charAt(k)), val = kind === "bike" ? n : Math.max(0, s.cap - n);
      h += "<div class=\"cell " + (c >= SURE[kind] ? "g" : c >= MAYBE[kind] ? "y" : "r") + "\"><b>" + val + "</b><span>" + hm((v.t_min + 10 * (k + 1)) % 1440) + "</span></div>";
    }
    return "<div class=\"ahead\"><div class=\"cap\">" + t("aheadH") + sep() + t(kind === "bike" ? "aheadBike" : "aheadDock") + "</div><div class=\"cells\">" + h + "</div></div>";
  }
  function renderCard(v) {
    var wrap = $("cardWrap");
    if (selected == null) { wrap.hidden = true; return; }
    var i = selected, s = v.stations[i], observed = v.bikes[i] != null, kind = need(), o = look(v, i), isFav = favs.indexOf(s.sno) >= 0, turn = observed ? turnText(v, i, kind) : "";
    var foot = [];
    if (v.age && v.age[i] != null && v.age[i] > 20) foot.push(t("stale2", { m: v.age[i] }));
    if (s.excluded) foot.push(t("excluded"));
    var docks = v.docks && v.docks[i] != null ? v.docks[i] : null;
    $("card").innerHTML = "<div class=\"hd\">" + badge(v, i) + "<div><div class=\"nm\">" + esc(nameOf(s)) + "</div><div class=\"alt\">" + esc(altName(s)) + "</div></div><button class=\"x\" id=\"cardX\" type=\"button\" aria-label=\"" + t("close") + "\">" + ICON.close + "</button></div>" +
      "<div class=\"says\">" + (o.text ? "<span class=\"state " + o.cls + "\">" + (observed && o.cls !== "x" ? t("fArrive") + sep() : "") + o.text + "</span>" : "") + (turn ? "<span>" + turn + "</span>" : "") +
      (isCampus(s) ? "<span class=\"tag\">" + t("inCampus") + "</span>" : (s.group === "gateway" ? "<span class=\"tag\">" + t("nearCampus") + "</span>" : "")) + (isFav ? "<span class=\"tag\">★ " + t("fav") + "</span>" : "") + "</div>" +
      "<div class=\"facts two\"><div class=\"fact\"><div class=\"v\">" + (observed ? v.bikes[i] + "<small>/ " + s.cap + "</small>" : "–") + "</div><div class=\"k\">" + t("fBikes") + "</div></div>" +
      "<div class=\"fact\"><div class=\"v\">" + (docks != null ? docks : "–") + "</div><div class=\"k\">" + t("fDocks") + "</div></div></div>" + (observed ? aheadStrip(v, i, kind) : "") +
      "<div class=\"chart\"><div class=\"cap\">" + t("chartCap") + "</div>" + sparkline(v, i) + "</div>" + (foot.length ? "<div class=\"foot\">" + foot.join(lang === "zh" ? "；" : "; ") + "</div>" : "") +
      "<div class=\"actions\"><button class=\"btn\" id=\"favBtn\" type=\"button\" aria-pressed=\"" + (isFav ? "true" : "false") + "\">" + ICON.star.replace("FILL", isFav ? "currentColor" : "none") + (isFav ? t("rmFav") : t("addFav")) + "</button>" +
      "<a class=\"btn primary\" href=\"https://www.google.com/maps/dir/?api=1&destination=" + s.lat + "," + s.lng + "&travelmode=walking\" target=\"_blank\" rel=\"noopener\">" + ICON.walk + t("nav") + "</a></div>";
    $("cardX").addEventListener("click", function () { select(null); });
    $("favBtn").addEventListener("click", function () { var k = favs.indexOf(s.sno); if (k >= 0) { favs.splice(k, 1); toast(t("favRemoved")); } else { favs.unshift(s.sno); toast(t("favAdded")); } store("btb-favs", favs); render(); });
    wrap.hidden = false;
  }

  // ---------- dispatch ----------
  function renderKpis(v) {
    // one truck for the campus: the numbers are for the stations between campus and the metro, not the whole district
    var tt = v.totals, unit = function (k) { return "<small>" + t(k) + "</small>"; }, cor = [], empty = 0, soon = 0, unmet = 0;
    v.stations.forEach(function (s, i) { if (s.group !== "other") cor.push(i); });
    cor.forEach(function (i) { if (v.bikes[i] === 0) empty++; else if (v.bikes[i] > 0 && v.p30[i] != null && v.p30[i] >= 0.5) soon++; if (v.unmet && v.unmet[i] != null) unmet += v.unmet[i]; });
    if (tt.unmet_corridor != null) unmet = tt.unmet_corridor;
    $("hKpi").innerHTML = "<span>" + t("kpi") + "</span><span class=\"sub\">" + t("kpiSub", { n: cor.length }) + "</span>";
    $("tEmpty").innerHTML = fmt(empty) + unit("uSta"); $("kEmpty").textContent = t("kEmpty");
    $("tRisk").innerHTML = fmt(soon) + unit("uSta"); $("kRisk").textContent = t("kRisk");
    $("tUnmet").innerHTML = v.in_window ? fmt(unmet) + unit("uRide") : "–"; $("kUnmet").textContent = t("kUnmet", { h: v.meta.horizon_min });
    $("tSaved").innerHTML = v.in_window ? fmt(tt.plan_value) + unit("uRide") + (tt.plan_value > 0 && unmet >= 1 ? "<small>" + Math.min(100, Math.round(100 * tt.plan_value / unmet)) + "%</small>" : "") : "–";
    $("kSaved").textContent = t("kSaved");
  }
  function actText(st) { return st.d > 0 ? t("dropN", { n: st.d }) : t("pickN", { n: -st.d }); }
  function copyText(text, done) {
    var fallback = function () { var ta = document.createElement("textarea"); ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0"; document.body.appendChild(ta); ta.select(); try { document.execCommand("copy"); } catch (e) {} document.body.removeChild(ta); done(); };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, fallback); else fallback();
  }
  function renderPlans(v) {
    $("hPlan").textContent = t("plan");
    var el = $("plans"); el.innerHTML = "";
    var cb = $("copyAll"); cb.hidden = !(v.in_window && v.plans && v.plans.length); cb.textContent = t("copy");
    cb.onclick = function () {
      var text = v.snapshot_at + "\n" + v.plans.map(function (pl) { return t("truck", { k: pl.truck }) + "\n" + pl.stops.map(function (st, k) { var ss = v.stations[st.i]; return (k + 1) + ". " + actText(st) + " " + nameOf(ss) + " (" + t("nowAt", { b: v.bikes[st.i], c: ss.cap }) + sep() + fmt(st.eta) + " " + t("eta") + ")"; }).join("\n"); }).join("\n");
      copyText(text, function () { cb.textContent = t("copied"); setTimeout(function () { cb.textContent = t("copy"); }, 1600); });
    };
    if (!v.in_window) { el.innerHTML = "<div class=\"empty\">" + t("offWindow") + "</div>"; return; }
    if (!v.plans || !v.plans.length) { var worst = Math.max.apply(null, [0].concat((v.unmet || []).map(function (x, i) { return v.stations[i].group !== "other" ? (x || 0) : 0; }))); el.innerHTML = "<div class=\"empty\">" + t("noPlan", { m: Math.max(1, Math.round(worst)) }) + "</div>"; return; }
    v.plans.forEach(function (pl) {
      var box = document.createElement("div");
      box.innerHTML = "<p class=\"trip\"><b>" + t("truck", { k: pl.truck }) + "</b><span>" + t("nStops", { n: pl.stops.length }) + "</span><span>" + t("tripLen", { t: fmt(pl.minutes), k: fmt(pl.km, 1) }) + "</span><span>" + t("tripGain", { v: fmt(pl.value) }) + "</span></p>";
      var ol = document.createElement("ol"); ol.className = "stops";
      pl.stops.forEach(function (st, k) {
        var s = v.stations[st.i], li = document.createElement("li"); li.className = "stop"; li.tabIndex = 0;
        li.innerHTML = "<span class=\"n\">" + (k + 1) + "</span><span><div><span class=\"act\">" + actText(st) + "</span> <span class=\"nm\">" + esc(nameOf(s)) + "</span></div>" +
          "<div class=\"meta\">" + t("nowAt", { b: v.bikes[st.i], c: s.cap }) + sep() + t("onTruck", { n: st.load }) + "</div><div class=\"load\"><i style=\"width:" + Math.round(100 * st.load / v.meta.settings.Q) + "%\"></i></div></span>" +
          "<span class=\"eta\"><b>" + fmt(st.eta) + "</b> " + t("eta") + "</span>";
        var go = function () { select(st.i); focusStation(s); };
        li.addEventListener("click", go); li.addEventListener("keydown", function (e) { if (e.key === "Enter") go(); });
        ol.appendChild(li);
      });
      box.appendChild(ol); el.appendChild(box);
    });
  }
  function renderRisk(v) {
    var key = keyOf(), arr = key === "unmet" ? (v.unmet || []) : v[key], idx = [];
    v.stations.forEach(function (s, i) { if (arr[i] != null && s.group !== "other") idx.push(i); });     // the truck's own patch
    idx.sort(function (a, b) { return arr[b] - arr[a]; });
    $("hRisk").textContent = key === "unmet" ? t("unmetH") : t("riskH");
    $("h30").textContent = t("h30"); $("h60").textContent = t("h60"); $("hU").textContent = t("hU");
    var ol = $("risk"); ol.innerHTML = "";
    var top = key === "unmet" ? Math.max(1, arr[idx[0]] || 1) : 1;
    idx.slice(0, 10).forEach(function (i) {
      var s = v.stations[i], li = document.createElement("li"); li.tabIndex = 0; if (selected === i) li.className = "sel";
      var tag = isCampus(s) ? "<span class=\"tag in\">" + t("inCampus") + "</span>" : "";
      li.innerHTML = "<span class=\"nm\">" + esc(nameOf(s)) + tag + "</span><span class=\"bk\">" + v.bikes[i] + " / " + s.cap + "</span><span class=\"bar\"><i style=\"width:" + Math.round(100 * arr[i] / top) + "%\"></i></span><span class=\"pv\">" + (key === "unmet" ? arr[i].toFixed(1) : Math.round(100 * arr[i]) + "%") + "</span>";
      var go = function () { select(i); focusStation(s); };
      li.addEventListener("click", go); li.addEventListener("keydown", function (e) { if (e.key === "Enter") go(); });
      ol.appendChild(li);
    });
  }

  // ---------- about, legend, status ----------
  function renderAbout(v) {
    var s = v ? v.meta.settings : { Q: 20, speed_kmh: 15, stop_min: 3 };
    $("aboutWhat").innerHTML = t("aboutWhat") + t("aboutProof");
    $("aboutKeyH").textContent = t("keyH");
    var sw = function (cls, n) { return "<span class=\"sw\"><span class=\"badge " + cls + "\">" + n + "</span></span>"; };
    $("aboutKey").innerHTML = "<li>" + sw("g", 12) + "<span>" + t("keyYes") + "</span></li><li>" + sw("y", 4) + "<span>" + t("keyMaybe") + "</span></li><li>" + sw("r", 1) + "<span>" + t("keyNo") + "</span></li>" +
      "<li>" + sw("x", 0) + "<span>" + t("keyGone") + "</span></li><li>" + sw("n", "–") + "<span>" + t("keyNone") + "</span></li>" +
      "<li><span class=\"sw\"><svg width=\"30\" height=\"30\" viewBox=\"0 0 30 30\" aria-hidden=\"true\"><circle cx=\"15\" cy=\"15\" r=\"12\" fill=\"none\" stroke=\"var(--accent)\" stroke-width=\"2.5\"/><path d=\"M15 3 A12 12 0 0 1 25.4 21\" fill=\"none\" stroke=\"var(--ink-3)\" stroke-width=\"2.5\" stroke-linecap=\"round\"/><circle cx=\"15\" cy=\"15\" r=\"8\" fill=\"var(--ok-fill)\"/></svg></span><span>" + t("keyRing") + "</span></li>" +
      "<li><span class=\"sw\"><span class=\"ln\"></span></span><span>" + t("keyRoute") + "</span></li>";
    $("aboutHow").innerHTML = t("aboutHow", { n: v ? v.stations.length : 309, h: v ? v.meta.horizon_min : 90, q: s.Q, s: Math.round(s.speed_kmh), st: Math.round(s.stop_min) });
    $("langK").textContent = t("langK"); $("credit").innerHTML = t("credit");
  }
  function renderLegend(v) {
    var el = $("legend");
    if (tab === "ops") {
      var ends = horizon === 90 ? "<span>0</span><span>5</span><span>10+</span>" : "<span>0%</span><span>50%</span><span>100%</span>";
      el.innerHTML = "<div class=\"ttl\">" + (horizon === 90 ? t("legU", { h: v.meta.horizon_min }) : t("legP", { h: horizon })) + "</div><div class=\"ramp\"><i style=\"background:var(--r0)\"></i><i style=\"background:var(--r1)\"></i><i style=\"background:var(--r2)\"></i><i style=\"background:var(--r3)\"></i><i style=\"background:var(--r4)\"></i></div><div class=\"ends\">" + ends + "</div>" +
        "<div class=\"it\"><span class=\"ln\"></span>" + t("legRoute") + "</div><div class=\"it\">" + t("legCampus") + "</div>";
      return;
    }
    var it = function (c, k) { return "<div class=\"it\"><span class=\"sw\" style=\"background:var(" + c + ")\"></span>" + t(k) + "</div>"; };
    var bike = need() === "bike";
    el.innerHTML = "<div class=\"ttl\">" + t(bike ? "legBike" : "legDock") + "</div>" + it("--ok-fill", bike ? "cBikeYes" : "cDockYes") + it("--low-fill", bike ? "cBikeMaybe" : "cDockMaybe") + it("--out-fill", bike ? "cBikeNo" : "cDockNo") + it("--gone", bike ? "sGone" : "sFullNow") +
      "<div class=\"it gap\">" + t(bike ? "legNumBike" : "legNumDock") + "</div><div class=\"it\">" + t("legCampus") + "</div>";
  }
  function dayLabel(d) {
    var y = parseInt(d.slice(0, 4), 10), mo = parseInt(d.slice(5, 7), 10), da = parseInt(d.slice(8, 10), 10), wd = T[lang].weekdays[new Date(Date.UTC(y, mo - 1, da)).getUTCDay()];
    return lang === "zh" ? mo + "/" + da + "（" + wd + "）" : wd + " " + ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][mo - 1] + " " + da;
  }
  function showErr(kind, text) { var el = $("err"); errKind = kind; el.hidden = !kind; el.textContent = text || ""; }
  function renderStatus(v) {
    var st = $("status"), tx = $("statusText");
    st.className = "status";
    if (mode === "replay") { st.classList.add("replay"); tx.textContent = t("replayAt", { d: dayLabel(replay.date), t: v.snapshot_at.slice(11) }); if (errKind === "old") showErr(null); return; }
    var n = taipeiNow(), snap = v.snapshot_at, agoMin = Math.max(0, Math.round((n - new Date(snap.replace(" ", "T") + ":00")) / 60000));
    if (agoMin > 25) st.classList.add("stale");
    tx.textContent = t("liveAt", { t: snap.slice(11) }) + sep() + (agoMin < 1 ? t("justNow") : agoMin < 90 ? t("ago", { m: agoMin }) : t("agoH", { h: Math.round(agoMin / 60) }));
    if (agoMin > 60) { if (!errKind || errKind === "old") showErr("old", t("stalebig", { m: agoMin })); } else if (errKind === "old") showErr(null);
  }
  function renderChrome() {
    document.title = t("docTitle"); $("where").textContent = t("where");
    $("mLive").textContent = t("live"); $("mReplay").textContent = t("replay"); $("modeSeg").setAttribute("aria-label", t("modeLabel"));
    $("tabRiderT").textContent = t("tabRider"); $("tabDockT").textContent = t("tabDock"); $("tabOpsT").textContent = t("tabOps"); $("tabAboutT").textContent = t("tabAbout");
    $("grip").setAttribute("aria-label", t("gripLabel")); $("fab").setAttribute("aria-label", t("fabLabel")); $("fab").title = t("fabLabel");
    $("slider").setAttribute("aria-label", t("sliderLabel")); $("replayDay").setAttribute("aria-label", t("dayLabel")); $("horizonSeg").setAttribute("aria-label", t("horizonLabel"));
    $("map").setAttribute("aria-label", t("mapLabel")); $("langSeg").setAttribute("aria-label", t("langK"));
    $("play").innerHTML = playing ? ICON.pause : ICON.play; $("play").setAttribute("aria-label", playing ? t("pauseLabel") : t("playLabel"));
    if (!live && !replay) $("statusText").textContent = t("loading");
    fillDays();
  }
  function applyTab() {
    shell.setAttribute("data-tab", tab);
    [["rider", "tabRider"], ["dock", "tabDock"], ["ops", "tabOps"], ["about", "tabAbout"]].forEach(function (x) {
      $(x[1]).setAttribute("aria-selected", tab === x[0] ? "true" : "false"); $(x[1]).tabIndex = tab === x[0] ? 0 : -1; });
    $("paneRider").hidden = tab !== "rider" && tab !== "dock"; $("paneOps").hidden = tab !== "ops"; $("paneAbout").hidden = tab !== "about";
    $("paneRider").setAttribute("aria-labelledby", tab === "dock" ? "tabDock" : "tabRider");
  }
  function setTab(x) {
    var was = tab; tab = x; store("btb-tab", x); applyTab();
    if (picking) setPicking(false);
    if (x === "ops" && was !== "ops") { var v = view(); if (v && map.getZoom() >= 15 && selected == null) fitArea(v); }
    if (isPhone()) setSheet(sheetState === "peek" ? "half" : sheetState);
    scroller.scrollTop = 0; render();
  }
  function render() {
    var v = view(); renderChrome(); renderAbout(v); if (!v) return;
    renderStatus(v); renderBell(v); renderCard(v); renderLegend(v);
    if (tab === "rider" || tab === "dock") renderRider(v); else if (tab === "ops") { renderKpis(v); renderPlans(v); renderRisk(v); }
    drawStations(v); drawRoute(v); drawOrigin();
    if (mode === "replay") {
      var sl = $("slider"); sl.max = replay.slots.length - 1; sl.value = slot; $("sliderT").textContent = replay.slots[slot].snapshot_at.slice(11);
      var n = replay.slots.length, t0 = replay.slots[0].t_min, t1 = replay.slots[n - 1].t_min, hh = "";
      replay.bells.forEach(function (b) { var bm = mins(b); if (bm < t0 || bm > t1 || n < 2) return; hh += "<i class=\"" + (replay.major_bells.indexOf(b) >= 0 ? "major" : "") + "\" style=\"left:" + (100 * slotAt(bm) / (n - 1)).toFixed(2) + "%\"></i>"; });
      $("marks").innerHTML = hh;
    }
    if (pendingSno) { var k = -1; v.stations.forEach(function (s, i) { if (s.sno === pendingSno) k = i; }); pendingSno = null; if (k >= 0) { select(k); focusStation(v.stations[k]); } }
  }
  function select(i) {
    selected = i; var v = view(); if (!v) return;
    renderCard(v); if (tab === "rider" || tab === "dock") renderRider(v); else if (tab === "ops") renderRisk(v);
    drawStations(v);
    if (i != null) { if (isPhone()) setSheet("half"); scroller.scrollTop = 0; }
    try { history.replaceState(null, "", i != null ? "#" + v.stations[i].sno : location.pathname + location.search); } catch (e) {}
  }

  // ---------- data ----------
  function loadLive() {
    var url = /claude\.ai$/.test(location.hostname) || location.protocol === "file:" ? "state.json" : "state.json?t=" + Math.floor(Date.now() / 60000);
    return fetch(url, { cache: "no-store" }).then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
      .then(function (s) { live = s; if (errKind === "load") showErr(null); if (mode === "live") render(); })
      .catch(function (e) {
        if (live) { showErr("load", t("stale", { t: live.snapshot_at.slice(11) })); if (mode === "live") { render(); $("status").classList.add("stale"); } }
        else { showErr("load", t("loadFail", { e: e.message })); $("statusText").textContent = "–"; }
      });
  }
  function loadReplay(day) {
    if (replays[day]) { replay = replays[day]; return Promise.resolve(replay); }
    return fetch("replay_" + day + ".json").then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); }).then(function (s) { replays[day] = s; replay = s; return s; });
  }
  function fillDays() {
    var key = lang + "|" + replayDays.join(",");
    if (key !== daysKey) { daysKey = key; $("replayDay").innerHTML = replayDays.map(function (d) { return "<option value=\"" + d + "\">" + dayLabel(d) + "</option>"; }).join(""); }
    if (replayDay) $("replayDay").value = replayDay;
  }
  function loadDays() {
    return fetch("replays.json", { cache: "no-store" }).then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
      .then(function (j) { if (j.days && j.days.length) { replayDays = j.days; if (replayDays.indexOf(replayDay) < 0) replayDay = replayDays[0]; } }).catch(function () {}).then(function () { $("mReplay").disabled = !replayDays.length; fillDays(); });
  }
  function slotAt(tMin) { var i = -1; replay.slots.forEach(function (x, k) { if (i < 0 && x.t_min >= tMin) i = k; }); return i < 0 ? replay.slots.length - 1 : i; }
  function setMode(m) {
    if (m === "replay" && !replayDay) return;
    mode = m; shell.setAttribute("data-mode", m);
    $("mLive").setAttribute("aria-pressed", m === "live" ? "true" : "false"); $("mReplay").setAttribute("aria-pressed", m === "replay" ? "true" : "false");
    $("replaybar").hidden = m !== "replay"; stopPlay();
    if (m === "replay") loadReplay(replayDay).then(function () { slot = wantSlot != null ? slotAt(wantSlot) : slotAt(15 * 60 + 30); wantSlot = null; if (errKind === "replay") showErr(null); render(); })
      .catch(function (e) { showErr("replay", t("replayFail", { e: e.message })); mode = "live"; shell.setAttribute("data-mode", "live"); $("replaybar").hidden = true; $("mLive").setAttribute("aria-pressed", "true"); $("mReplay").setAttribute("aria-pressed", "false"); render(); });
    else render();
  }
  function stopPlay() { playing = false; $("play").innerHTML = ICON.play; $("play").setAttribute("aria-label", t("playLabel")); if (playTimer) { clearInterval(playTimer); playTimer = null; } }
  function togglePlay() {
    if (playing) { stopPlay(); return; }
    playing = true; $("play").innerHTML = ICON.pause; $("play").setAttribute("aria-label", t("pauseLabel"));
    playTimer = setInterval(function () { if (!replay) return; slot = (slot + 1) % replay.slots.length; render(); }, 700);
  }
  function setLang(l) {
    lang = l; $("lZh").setAttribute("aria-pressed", l === "zh" ? "true" : "false"); $("lEn").setAttribute("aria-pressed", l === "en" ? "true" : "false");
    root.lang = l === "zh" ? "zh-Hant" : "en"; store("btb-lang", l); render();
  }
  function setH(h) { horizon = h; $("h30").setAttribute("aria-pressed", h === 30 ? "true" : "false"); $("h60").setAttribute("aria-pressed", h === 60 ? "true" : "false"); $("hU").setAttribute("aria-pressed", h === 90 ? "true" : "false"); render(); }

  // ---------- events ----------
  $("mLive").addEventListener("click", function () { setMode("live"); });
  $("mReplay").addEventListener("click", function () { setMode("replay"); });
  $("replayDay").addEventListener("change", function (e) { replayDay = e.target.value; stopPlay(); var keep = replay ? replay.slots[slot].t_min : 15 * 60 + 30; loadReplay(replayDay).then(function () { slot = slotAt(keep); render(); }).catch(function (er) { showErr("replay", t("replayFail", { e: er.message })); }); });
  $("lZh").addEventListener("click", function () { setLang("zh"); });
  $("lEn").addEventListener("click", function () { setLang("en"); });
  $("tabRider").addEventListener("click", function () { setTab("rider"); });
  $("tabDock").addEventListener("click", function () { setTab("dock"); });
  $("tabOps").addEventListener("click", function () { setTab("ops"); });
  $("tabAbout").addEventListener("click", function () { setTab("about"); });
  $("tabs").addEventListener("keydown", function (e) {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    var order = ["rider", "dock", "ops", "about"], k = (order.indexOf(tab) + (e.key === "ArrowRight" ? 1 : 3)) % 4; setTab(order[k]); $({ rider: "tabRider", dock: "tabDock", ops: "tabOps", about: "tabAbout" }[order[k]]).focus();
  });
  $("h30").addEventListener("click", function () { setH(30); });
  $("h60").addEventListener("click", function () { setH(60); });
  $("hU").addEventListener("click", function () { setH(90); });
  $("play").addEventListener("click", togglePlay);
  $("slider").addEventListener("input", function (e) { stopPlay(); slot = parseInt(e.target.value, 10); render(); });
  $("q").addEventListener("input", function (e) { searchStations(e.target.value); });
  $("q").addEventListener("focus", function (e) { if (isPhone()) setSheet("full"); if (e.target.value) searchStations(e.target.value); });
  $("q").addEventListener("keydown", function (e) { if (e.key === "Escape") { $("qres").hidden = true; e.target.blur(); } if (e.key === "Enter") { var b = document.querySelector("#qres button"); if (b) b.click(); } });
  document.addEventListener("click", function (e) { if (!e.target.closest(".search")) $("qres").hidden = true; });
  $("oCampus").addEventListener("click", function () { if (picking) setPicking(false); setOrigin("campus", CAMPUS_CENTER[0], CAMPUS_CENTER[1]); var v = view(); if (v) fitCampus(v); });
  $("oKrt").addEventListener("click", function () { if (picking) setPicking(false); var v = view(); if (!v) return; v.stations.forEach(function (s) { if (s.sno === KRT) { setOrigin("krt", s.lat, s.lng); viewTo(s.lat, s.lng, Math.max(map.getZoom(), 16)); } }); });
  $("oMe").addEventListener("click", locate);
  $("fab").addEventListener("click", function () { if (tab !== "rider" && tab !== "dock") setTab("rider"); locate(); });
  $("oPick").addEventListener("click", function () { setPicking(!picking); });
  $("more").addEventListener("click", function () { nearN = nearN > 8 ? 8 : 16; var v = view(); if (v) renderRider(v); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") { if (picking) setPicking(false); else if (selected != null) select(null); } });

  // ---------- start ----------
  var qs = {}; location.search.replace(/^\?/, "").split("&").forEach(function (kv) { var p = kv.split("="); if (p[0]) qs[decodeURIComponent(p[0])] = decodeURIComponent(p[1] || ""); });
  var savedLang = qs.lang || load("btb-lang", null);
  if (savedLang === "en") { lang = "en"; $("lZh").setAttribute("aria-pressed", "false"); $("lEn").setAttribute("aria-pressed", "true"); root.lang = "en"; }
  var savedTab = qs.tab || load("btb-tab", "rider"); tab = savedTab === "ops" || savedTab === "about" || savedTab === "dock" ? savedTab : "rider"; applyTab();
  if (/^#\d{6,}$/.test(location.hash)) pendingSno = location.hash.slice(1);
  if (/^\d\d:\d\d$/.test(qs.t || "")) wantSlot = mins(qs.t);

  initSheet(); initMap(); renderChrome(); renderAbout(null);
  loadLive();
  fetch("outlook.json").then(function (r) { return r.ok ? r.json() : null; }).then(function (j) { usual = j; if (j && view()) render(); }).catch(function () {});
  loadDays().then(function () { if (/^\d{4}-\d\d-\d\d$/.test(qs.replay || "") && replayDays.indexOf(qs.replay) >= 0) { replayDay = qs.replay; fillDays(); setMode("replay"); } });
  setInterval(function () { if (mode === "live") loadLive(); }, 60000);
  setInterval(function () { var v = view(); if (v && mode === "live") { renderBell(v); renderStatus(v); } }, 15000);
})();
