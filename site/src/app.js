// Beat the Bell: page logic. Reads docs/state.json (live) or docs/replay_YYYY-MM-DD.json and draws the same four
// tabs from either. Strings live in strings.js (T), the look in style.css. No framework; Leaflet draws the map.
(function () {
  "use strict";
  var SHORT = { "501209052": ["圖資", "Library"], "501209070": ["西灣藝廊", "Xiziwan Hall"], "501209051": ["工學院", "Engineering"], "501209054": ["材料", "Materials"],
                "501209039": ["社科院", "Social Sci."], "501209069": ["體育館", "Gym"], "501209040": ["海工館", "Marine Eng."], "501209071": ["海資館", "Marine Res."] };
  var CAMPUS_CENTER = [22.6273, 120.2658];
  var HOME = { kind: "place", id: "lib", lat: 22.62741, lng: 120.26586 };                     // the library, in the middle of the campus
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
  var origin = HOME, goal = null, dest = HOME, picking = null, favs = [];                     // borrow: from origin, optionally on to goal; return: at dest. picking: which of them the next map click sets
  var when = { rider: { kind: "now" }, dock: { kind: "plus", min: 10 } }, usual = null;      // when the rider leaves (borrow) or rides in (return)
  var policy = null, polSel = { er: 0, et: 0, es: 0, mr: 0, mt: 0 };                          // policy.json (final_policy.py); the what-if chosen on the Policy tab
  var PL = null, fresh = null, merged = null, track = null, placesKey = "";                   // places.json; counts read from the operator a minute ago; the live view with them; track.json
  var A64 = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-_";               // state.json packs a chance or a count into one character
  var SURE = { bike: 0.9, dock: 0.95 }, MAYBE = { bike: 0.6, dock: 0.7 }, G = 12, MARGIN = 0.5, RELAY = 0.6, RELAY_OFF = 0.5; // the chances behind "should" and "may"; G: minutes charged if the second station fails too; MARGIN: minutes given up for a surer station; RELAY(_OFF): the chance that turns a reward mark on (off)
  var SLOW = 8, THETA = 0.6;                                                                   // the dots: "over SLOW minutes" is a long search; THETA couples the stations' emptiness (analysis/code/final_spread.py)
  var REM_END = "2026-12-24", SITE = "https://alexlin8888.github.io/nsysu-youbike-log/";      // reminders repeat weekly to the last day of finals (NSYSU calendar, term 115-1)
  var relayMem = {}, relayOnly = false, colsMemo = null, remKey = "";
  var API = "https://apis.youbike.com.tw/tw2/parkingInfo";                                    // the operator's own counts for a list of stations
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
  function nameEn(s) { return (s.name_en || s.name).replace(/\(Exit \)(\d+)/, "(Exit $1)"); }     // the operator writes "(Exit )1" for one station
  function nameOf(s) { if (lang === "zh") return s.name; return isCampus(s) && SHORT[s.sno] ? "NSYSU " + SHORT[s.sno][1] : nameEn(s); }
  function altName(s) { return lang === "zh" ? (isCampus(s) && SHORT[s.sno] ? "NSYSU " + SHORT[s.sno][1] : (s.name_en ? nameEn(s) : "")) : s.name; }
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
  // Minutes on foot and by bike. places.json has path lengths for the campus buildings and the stations around them;
  // any other pair is a straight line (x 1.25 at 80 m/min on foot, x 1.3 at 200 m/min by bike). analysis/code/paths.py does the same.
  function nodeP(p) { return PL && p.kind === "place" && PL.pos[p.id] != null ? PL.pos[p.id] : null; }
  function nodeS(v, i) { var k = PL ? PL.pos[v.stations[i].sno] : null; return k == null ? null : k; }
  function tbl(name, a, b) { return A64.indexOf(PL[name][a].charAt(b)); }
  function lineRide(km) { return Math.max(1, Math.round(km * 1.3 * 1000 / 200)); }
  function walkPS(v, p, i) { var a = nodeP(p), b = nodeS(v, i), s = v.stations[i]; return a != null && b != null ? Math.max(1, tbl("walk", a, b)) : walkMin(distKm(s.lat, s.lng, p.lat, p.lng)); }
  function ridePS(v, p, i) { var a = nodeP(p), b = nodeS(v, i), s = v.stations[i]; return a != null && b != null ? Math.max(1, tbl("ride", a, b)) : lineRide(distKm(s.lat, s.lng, p.lat, p.lng)); }
  function walkSS(v, i, j) { if (i === j) return 0; var a = nodeS(v, i), b = nodeS(v, j), s = v.stations[i], u = v.stations[j]; return a != null && b != null ? tbl("walk", a, b) : walkMin(distKm(s.lat, s.lng, u.lat, u.lng)); }
  function rideSS(v, i, j) { if (i === j) return 0; var a = nodeS(v, i), b = nodeS(v, j), s = v.stations[i], u = v.stations[j]; return a != null && b != null ? tbl("ride", a, b) : lineRide(distKm(s.lat, s.lng, u.lat, u.lng)); }
  function walkPP(p, q) { var a = nodeP(p), b = nodeP(q); return a != null && b != null ? tbl("walk", a, b) : walkMin(distKm(p.lat, p.lng, q.lat, q.lng)); }
  function arriveMin(v, i) { return leaveMin(v) + (need() === "bike" ? walkPS(v, point(), i) : ridePS(v, point(), i)); }
  function aheadOf(v, i, key) { return v.ahead && v.ahead[key] && v.ahead[key][i] ? v.ahead[key][i] : ""; }
  function baseMin(v, i) { return v.base && v.base[i] != null ? v.base[i] : v.t_min; }       // the minute the count of station i was read
  // chance (0..1) that station i has a bike (a dock) at minute `at`: the count now, then the chain's 10-minute steps, linear in between
  function chance(v, i, kind, at) {
    var h = have(v, i, kind); if (v.bikes[i] == null || h == null) return null;
    var a = aheadOf(v, i, kind), p0 = h >= 1 ? 1 : 0;
    if (!a) return h >= 3 ? 1 : h >= 1 ? 0.63 : 0;                                            // a snapshot without the forecast: a guess from the count
    var x = Math.max(0, Math.min(a.length, (at - baseMin(v, i)) / 10)), k = Math.floor(x), f = x - k;
    var pa = k === 0 ? p0 : A64.indexOf(a.charAt(k - 1)) / 63, pb = k >= a.length ? pa : A64.indexOf(a.charAt(k)) / 63;
    return (1 - f) * pa + f * pb;
  }
  function expectAt(v, i, at) {
    var a = aheadOf(v, i, "bikes"); if (!a) return null;
    var x = Math.max(0, Math.min(a.length, (at - baseMin(v, i)) / 10)), k = Math.floor(x), f = x - k;
    var ea = k === 0 ? v.bikes[i] : A64.indexOf(a.charAt(k - 1)), eb = k >= a.length ? ea : A64.indexOf(a.charAt(k));
    return Math.round((1 - f) * ea + f * eb);
  }
  function verdict(v, i, kind, at) {
    if (v.bikes[i] == null) return { cls: "n", text: v.status && v.status[i] === 2 ? t("sOos") : t("sNone") };
    var c = chance(v, i, kind, at), h = have(v, i, kind), bike = kind === "bike";
    if (c == null) return { cls: "n", text: "" };
    // four plain states, as Bicing's app shows high / medium / low; how often each turned out right is on the About tab
    // (analysis/code/final_labels.py: 99% / 81% / 62% of riders found a bike, 22% where there was none at first)
    if (c >= SURE[kind]) return { cls: "g", text: t(h === 0 ? (bike ? "cBikeBack" : "cDockBack") : (bike ? "cBikeYes" : "cDockYes")) };
    if (c >= MAYBE[kind]) return { cls: "y", text: t(h === 0 ? (bike ? "sGone" : "sFullNow") : (bike ? "cBikeLow" : "cDockLow")) };
    return h === 0 ? { cls: "x", text: t(bike ? "sGone" : "sFullNow") } : { cls: "r", text: t(bike ? "cBikeNo" : "cDockNo") };
  }
  function look(v, i) { return verdict(v, i, need(), arriveMin(v, i)); }
  // The operator's reward ("friendship relay", in Kaohsiung since 1 July 2026): a NT$5 ride voucher for borrowing at a station
  // with no free dock, or for returning an ordinary bike to a station with no bike, between 06:00 and 24:00. The station's
  // state at that moment decides, so the page marks the stations likely to be in that state when the rider gets there
  // (a chance of RELAY or more; analysis/code/final_relay.py scores the mark). kind: what the rider needs there. A rider
  // who needs a dock is paid at an empty station, a rider who needs a bike at a full one.
  function relayP(v, i, kind, at) {
    if (!v.ahead || at < 360 || at >= 1440) return null;
    var c = chance(v, i, kind === "dock" ? "bike" : "dock", at); return c == null ? null : 1 - c;
  }
  function tenth(p) { return Math.max(1, Math.min(9, Math.round(p * 10))); }
  // A mark goes on at RELAY and stays until the chance falls below RELAY_OFF, so a count read a minute later does not
  // make it blink on and off while the rider is on the way.
  function relayOn(v, i, kind, at) {
    var p = relayP(v, i, kind, at), key = kind + v.stations[i].sno;
    if (p == null) { delete relayMem[key]; return false; }
    var on = relayMem[key] ? p >= RELAY_OFF : p >= RELAY;
    if (on) relayMem[key] = true; else delete relayMem[key];
    return on;
  }
  function relayTag(v, i, kind, at) { return relayOn(v, i, kind, at) ? "<span class=\"relay\">" + t("relayTag") + "</span>" : ""; }
  // How often this station was empty (full) in this half hour of a usual teaching day or day off (docs/outlook.json)
  function usualShare(v, s, kind, at) {
    var o = usual && usual.stations && usual.stations[s.sno], d = o && o[v.offday ? "off" : "teaching"], arr = d && d[kind === "bike" ? "no_bike" : "no_dock"];
    var b = Math.floor((at % 1440 - 360) / 30); if (!arr || b < 0 || b >= arr.length || arr.charAt(b) === " ") return null;
    return { p: A64.indexOf(arr.charAt(b)) / 63, a: 360 + 30 * b };
  }
  function usualNote(v, s, kind, at) {
    var u = usualShare(v, s, kind, at); if (!u) return "";
    var key = (kind === "bike" ? "usualNoteBike" : "usualNoteDock") + (u.p < 0.05 ? "Rare" : "");
    return t(key, { d: t(v.offday ? "dayOff" : "dayTeach"), a: hm(u.a), b: hm(u.a + 30), n: Math.round(100 * u.p) });
  }
  // when the answer changes: "likely out by 17:20", or for an empty station "a bike likely back by 18:10"
  function turnText(v, i, kind, cls) {
    var a = aheadOf(v, i, kind), h = have(v, i, kind), bike = kind === "bike", k; if (!a || h == null) return "";
    var b0 = baseMin(v, i), at = function (n) { return hm((b0 + 10 * (n + 1)) % 1440); };
    // the forecast ends here; "for the next 90 min" reads as that, while "until 23:13" reads as a change at 23:13
    var left = { m: Math.max(10, 10 * Math.floor((b0 + 10 * a.length - nowMin(v)) / 10)) };
    if (h > 0) { for (k = 0; k < a.length; k++) if (A64.indexOf(a.charAt(k)) < 32) return t(bike ? "tGone" : "tFull", { t: at(k) }); return cls === "g" ? t(bike ? "tKeep" : "tFree", left) : ""; }   // "bikes for the next hour" would contradict a "may be out"
    for (k = 0; k < a.length; k++) if (A64.indexOf(a.charAt(k)) >= 32) return t(bike ? "tBack" : "tOpen", { t: at(k) });
    return t(bike ? "tNoBack" : "tNoOpen", left);
  }
  function ramp(p) { if (p == null) return tok("--r0"); return tok(p < 0.1 ? "--r0" : p < 0.3 ? "--r1" : p < 0.5 ? "--r2" : p < 0.75 ? "--r3" : "--r4"); }
  function rampU(u) { if (u == null) return tok("--r0"); return tok(u < 0.5 ? "--r0" : u < 2 ? "--r1" : u < 5 ? "--r2" : u < 10 ? "--r3" : "--r4"); }
  function keyOf() { return horizon === 30 ? "p30" : horizon === 60 ? "p60" : "unmet"; }
  // The Policy tab: before noon the voucher for borrowing at a rack about to fill, after it the one for returning to a rack
  // about to run empty. polChance: the chance demo_state.py wrote for that, or null outside the campus corridor.
  function polMorning(v) { return v.t_min < 12 * 60; }
  function polChance(v, i) { var r = v.reward; if (!r || v.bikes[i] == null) return null; var x = (polMorning(v) ? r.full : r.empty)[i]; return x == null ? null : x; }
  function polPaysNow(v, i) { return polMorning(v) ? v.docks && v.docks[i] === 0 : v.bikes[i] === 0; }
  function polPays(v, i) { var c = polChance(v, i); return c != null && (polPaysNow(v, i) || c >= 0.5); }
  function fillOf(v, i) {
    if (v.bikes[i] == null) return tok("--r0");
    if (tab === "ops") return horizon === 90 ? rampU(v.unmet ? v.unmet[i] : null) : ramp(v[keyOf()][i]);
    if (tab === "policy") return ramp(polChance(v, i));
    return tok(FILL[look(v, i).cls]);
  }
  function inkOn(hex) {
    var c = hex.replace("#", ""); if (c.length === 3) c = c.replace(/(.)/g, "$1$1");
    var r = parseInt(c.slice(0, 2), 16), g = parseInt(c.slice(2, 4), 16), b = parseInt(c.slice(4, 6), 16);
    return 0.299 * r + 0.587 * g + 0.114 * b > 150 ? "#10202f" : "#ffffff";
  }
  function countOf(v, i) { var h = have(v, i, need()); return v.bikes[i] == null || h == null ? "–" : h; }
  function badge(v, i) { return "<span class=\"badge " + look(v, i).cls + "\">" + countOf(v, i) + "</span>"; }
  function badgeAt(v, i, kind, at) { var h = have(v, i, kind); return "<span class=\"badge " + verdict(v, i, kind, at).cls + "\">" + (v.bikes[i] == null || h == null ? "–" : h) + "</span>"; }

  // ---------- the Policy tab: why the voucher comes too late, the predictive voucher, what-ifs, what we suggest ----------
  // policy.json comes from analysis/code/final_reward.py and final_policy.py (12 held-out teaching days, the chain of the page)
  var REWARD_STEPS = [0, 0.25, 0.5, 1];
  function polRow(win, a, b, c) {
    var g = policy[win].grid, k;
    for (k = 0; k < g.length; k++) if (g[k][0] === REWARD_STEPS[a] && g[k][1] === b && (win === "morning" || g[k][2] === c)) return g[k];
    return null;
  }
  function polCut(win, a, b, c) { var r = polRow(win, a, b, c); return r ? 1 - r[win === "evening" ? 3 : 2] / policy[win].base : 0; }
  function pct(x) { return Math.round(100 * x); }
  function polChart(rows) {
    // bars: bikes returned to campus per half hour, split by what each voucher rule pays; under them, how often the racks are empty
    var W = 340, top = 20, bh = 90, gap = 3, n = rows.length, bw = (W - gap * (n - 1)) / n, max = 0, h = "", yH = top + bh + 13, yC = top + bh + 30, yS = top + bh + 36;
    rows.forEach(function (r) { max = Math.max(max, r[2]); });
    max = 25 * Math.ceil(max / 25);   // gridlines every 25 bikes, labelled at the right end where the evening bars are low
    var font = " font-family=\"Barlow Semi Condensed, sans-serif\"";
    for (var g = 25; g <= max; g += 25) {
      var gy = (top + bh - bh * g / max).toFixed(1);
      h += "<line x1=\"0\" x2=\"" + W + "\" y1=\"" + gy + "\" y2=\"" + gy + "\" stroke=\"" + tok("--line") + "\" stroke-width=\"1\"/>" +
        "<text x=\"" + W + "\" y=\"" + (gy - 3) + "\" text-anchor=\"end\" font-size=\"9.5\" fill=\"" + tok("--ink-3") + "\"" + font + ">" + g + "</text>";
    }
    rows.forEach(function (r, k) {
      var x = k * (bw + gap), y = top + bh;
      var part = function (val, fill) { if (val <= 0) return ""; var hh = bh * val / max; y -= hh; return "<rect x=\"" + x.toFixed(1) + "\" y=\"" + y.toFixed(1) + "\" width=\"" + bw.toFixed(1) + "\" height=\"" + Math.max(0.6, hh - 0.8).toFixed(1) + "\" rx=\"1.5\" fill=\"" + tok(fill) + "\"/>"; };
      h += part(r[3], "--ink-2") + part(Math.max(0, r[4] - r[3]), "--accent") + part(Math.max(0, r[2] - r[4]), "--line-2");
      var e = r[1], cell = e < 0.1 ? "--r0" : e < 0.3 ? "--r1" : e < 0.45 ? "--r2" : "--r3";
      h += "<rect x=\"" + x.toFixed(1) + "\" y=\"" + yS + "\" width=\"" + bw.toFixed(1) + "\" height=\"18\" rx=\"2\" fill=\"" + tok(cell) + "\"/>" +
        "<text x=\"" + (x + bw / 2).toFixed(1) + "\" y=\"" + (yS + 12.5) + "\" text-anchor=\"middle\" font-size=\"9.5\" fill=\"" + inkOn(tok(cell)) + "\"" + font + ">" + pct(e) + "</text>";
      if (r[0].slice(3) === "00") h += "<text x=\"" + x.toFixed(1) + "\" y=\"" + yH + "\" font-size=\"10\" fill=\"" + tok("--ink-3") + "\"" + font + ">" + r[0] + "</text>";
    });
    var bell = rows.map(function (r) { return r[0]; }).indexOf("17:00");
    if (bell > 0) { var bx = (bell * (bw + gap) - gap / 2).toFixed(1); h += "<line x1=\"" + bx + "\" x2=\"" + bx + "\" y1=\"" + (top - 2) + "\" y2=\"" + (yS + 18) + "\" stroke=\"" + tok("--ink") + "\" stroke-width=\"1.2\" stroke-dasharray=\"3 3\"/>"; }
    var cap = function (y, s2) { return "<text x=\"0\" y=\"" + y + "\" font-size=\"11\" fill=\"" + tok("--ink-2") + "\">" + esc(s2) + "</text>"; };
    var aria = rows.map(function (r) { return r[0] + " " + Math.round(r[2]) + ", " + pct(r[1]) + "%"; }).join("; ");
    return "<svg viewBox=\"0 0 " + W + " " + (yS + 20) + "\" role=\"img\" aria-label=\"" + esc(t("polChartRet") + " / " + t("polChartEmpty") + ": " + aria) + "\">" + cap(11, t("polChartRet")) + cap(yC, t("polChartEmpty") + " (%)") + h + "</svg>" +
      "<div class=\"dotkey\"><span><i style=\"background:var(--ink-2)\"></i>" + t("polKeyNow") + "</span><span><i style=\"background:var(--accent)\"></i>" + t("polKeyPred") + "</span><span><i style=\"background:var(--line-2)\"></i>" + t("polKeyNone") + "</span></div>";
  }
  function polNow(v) {
    var head = "<h3>" + t("polNowH", { t: v.snapshot_at.slice(11) }) + "</h3>";
    if (v.offday) return head + "<p class=\"note\">" + t("polNowOff") + "</p>";
    if (!v.reward) return head + "<p class=\"note\">" + t(v.t_min < 6 * 60 || v.t_min >= 23 * 60 ? "polNowNight" : "polNowOld") + "</p>";
    var morn = polMorning(v), rows = "", a = 0, b = 0, list = [];
    v.stations.forEach(function (s, i) { if (isCampus(s) && polChance(v, i) != null) list.push(i); });
    list.sort(function (x, y) { return polChance(v, y) - polChance(v, x); });
    list.forEach(function (i) {
      var now = polPaysNow(v, i), pays = polPays(v, i), ch = polChance(v, i); if (now) a++; if (pays) b++;
      // today's rule pays a NT$5 ride voucher; the proposal pays ride time
      var cell = function (on, key) { return "<td class=\"" + (on ? "pay" : "no") + "\">" + t(on ? key : "polNoPay") + "</td>"; };
      rows += "<tr data-i=\"" + i + "\"><th scope=\"row\">" + esc(shortName(v.stations[i])) + "</th><td class=\"n\">" + (morn ? v.docks[i] : v.bikes[i]) + "</td><td class=\"n\">" + pct(ch) + "%</td>" + cell(now, "polPay") + cell(pays, "polPayTime") + "</tr>";
    });
    var sum = b === 0 ? t(morn ? "polNowNoneM" : "polNowNone") : t("polNowSum", { a: a, b: b });
    return head + "<p class=\"sub\">" + t(morn ? "polNowMorn" : "polNowEve") + "</p><div class=\"tablewrap\"><table class=\"poltab\"><thead><tr><th scope=\"col\">" + t("polNowSt") + "</th><th scope=\"col\" class=\"n\">" + t(morn ? "polNowDocks" : "polNowBikes") + "</th><th scope=\"col\" class=\"n\">" + t(morn ? "polNowChF" : "polNowChE") +
      "</th><th scope=\"col\">" + t("polNowRule") + "</th><th scope=\"col\">" + t("polNowPred") + "</th></tr></thead><tbody>" + rows + "</tbody></table></div><p class=\"polsum\">" + sum + "</p>";
  }
  function simSeg(key, label, opts) {
    return "<div class=\"simrow\"><span class=\"k\">" + t(label) + "</span><span class=\"opts\" role=\"group\" aria-label=\"" + esc(t(label)) + "\" data-k=\"" + key + "\">" +
      opts.map(function (o, k) { return "<button class=\"opt chip\" type=\"button\" data-v=\"" + k + "\" aria-pressed=\"" + (polSel[key] === k ? "true" : "false") + "\">" + t(o) + "</button>"; }).join("") + "</span></div>";
  }
  function simOut(win) {
    var e = win === "evening", r = e ? polRow("evening", polSel.er, polSel.et, polSel.es) : polRow("morning", polSel.mr, polSel.mt), r0 = e ? polRow("evening", 0, 0, 0) : polRow("morning", 0, 0);
    if (!r || !r0) return "";
    var lost = r[e ? 3 : 2], base = policy[win].base, cut = 1 - lost / base, more = Math.round(r[e ? 4 : 3] - r0[e ? 4 : 3]), same = cut < 0.005;
    // rides the reward adds, and the extra ride time it hands out (policy.reward_min minutes per reward)
    var rides = Math.round(r[e ? 5 : 4] || 0), hours = Math.round((r[e ? 4 : 3] - r0[e ? 4 : 3]) * (policy.reward_min || 60) / 60);
    // today's count and the count with the chosen measures as two bars on one scale
    var bar = function (label, val, cls) {
      return "<div class=\"simbar " + cls + "\"><span class=\"k\">" + t(label) + "</span><span class=\"track\"><i style=\"width:" + (100 * val / base).toFixed(1) + "%\"></i></span><span class=\"v\">" + Math.round(val) + "</span></div>";
    };
    return "<div class=\"simout\" aria-live=\"polite\"><div class=\"big" + (same ? " asis" : "") + "\">" + (same ? t("simAsIs") : t("simCut", { p: pct(cut) })) + "</div>" +
      "<div class=\"unit\">" + t(e ? "simUnit" : "simUnitM") + "</div>" + bar("simNow", base, "now") + (same ? "" : bar("simTry", lost, "try")) +
      "<div class=\"meta\">" + (same ? t("simPick") : (e ? polSel.er : polSel.mr) > 0 ? t(e ? "simTime" : "simTimeM", { r: rides, h: hours }) : "") + "</div></div>";
  }
  function renderPolicy(v) {
    $("polKey").innerHTML = "<span class=\"rm\">" + t("rmPolicy") + "</span>" + t("polKey");
    $("hPolWhy").textContent = t("polWhyH"); $("hPolIdea").textContent = t("polIdeaH"); $("polIdeaTag").textContent = t("polIdeaTag");
    $("hPolSim").textContent = t("polSimH"); $("hPolAsk").textContent = t("polAskH"); $("polBrief").textContent = t("polBrief"); $("polIdea").textContent = t("polIdea"); $("polTime").textContent = t("polTime");
    if (!policy) { $("polWhy").textContent = t("loading"); return; }
    var P = policy, all = 0, pre = 0, prePaid = 0, peak = [];
    P.timing.forEach(function (r) { all += r[2]; if (mins(r[0]) < 17 * 60) { pre += r[2]; prePaid += r[3]; } if (r[0] === "17:30" || r[0] === "18:00") peak.push(r[1]); });
    $("hPolWhySub").textContent = t("polWhySub", { n: P.days }); $("hPolSimSub").textContent = t("polSimSub", { n: P.days });
    // the two half hours from 17:30 to 18:30, in which campus stations are empty more than half of the time
    $("polWhy").textContent = t("polWhy", { e: pct(peak.reduce(function (s2, x) { return s2 + x; }, 0) / Math.max(1, peak.length)), a: pct(pre / all), b: pct(prePaid / pre) });
    $("polChart").innerHTML = polChart(P.timing);
    var w = P.warning;
    $("polFacts").innerHTML = "<li>" + t("polFactCatch", { n: P.days, a: pct(w.flagged), m: w.lead_median }) + "</li><li>" + t("polFactRight", { p: pct(w.precision), b: pct(w.base) }) + "</li><li>" +
      t("polFactWorth", { v: Math.round(w.worth * 100), w: Math.round((w.worth_now != null ? w.worth_now : w.worth) * 100), u: Math.round((w.worth_unpaid != null ? w.worth_unpaid : 0) * 100) }) + "</li>";
    $("polNow").innerHTML = polNow(v);
    Array.prototype.forEach.call($("polNow").querySelectorAll("tr[data-i]"), function (tr) { tr.addEventListener("click", function () { var i = +tr.getAttribute("data-i"); select(i); focusStation(view().stations[i]); }); });
    $("simEve").innerHTML = "<h3>" + t("simEveH") + "</h3>" + simSeg("er", "simReward", ["simR0", "simR1", "simR2", "simR3"]) + simSeg("et", "simTruck", ["simT0", "simT1", "simT2"]) + simSeg("es", "simStag", ["simS0", "simS1"]) + simOut("evening") +
      "<p class=\"note\">" + t("simRef", { a: pct(P.sim.evening[0]), b: pct(P.sim.evening[1]) }) + "</p>";
    $("simMorn").innerHTML = "<h3>" + t("simMornH") + "</h3>" + simSeg("mr", "simRewardM", ["simR0", "simR1", "simR2", "simR3"]) + simSeg("mt", "simTruckM", ["simM0", "simM1"]) + simOut("morning");
    $("polSimNote").textContent = t("polSimNote");
    // a reward is policy.reward_min minutes of riding: an hour is two 30-minute blocks, NT$10 each at the full Kaohsiung fare
    var r2 = polRow("evening", 2, 0, 0), r0 = polRow("evening", 0, 0, 0), extra = Math.round(r2[4] - r0[4]), rmin = policy.reward_min || 60;
    $("polAsks").innerHTML = "<li>" + t("ask1", { a: pct(polCut("evening", 2, 0, 0)), r: Math.round(r2[5] || 0), h: Math.round((r2[4] - r0[4]) * rmin / 60), c: 10 * extra * rmin / 30 }) + "</li><li>" + t("ask2", { b: pct(polCut("evening", 0, 2, 0)), c: pct(polCut("morning", 0, 1)), d: pct(polCut("evening", 2, 2, 0)) }) + "</li><li>" + t("ask3", { e: pct(polCut("evening", 0, 0, 1)) }) + "</li>";
  }

  // ---------- current view: live state or one replay slot, in one shape ----------
  function view() {
    if (mode === "replay" && replay) {
      var sl = replay.slots[slot];
      return { meta: replay, stations: replay.stations, snapshot_at: sl.snapshot_at, t_min: sl.t_min, offday: replay.offday, in_window: true, next_bell: sl.next_bell, ahead: sl.ahead || null, reward: sl.reward || null,
               totals: sl.totals, plans: sl.plans, bikes: sl.bikes, docks: sl.docks || null, status: null, age: null, p30: sl.p30, p60: sl.p60, unmet: sl.unmet,
               history: function (i) { return replay.slots.slice(0, slot + 1).map(function (x) { return [x.t_min, x.bikes[i]]; }); } };
    }
    if (!live) return null;
    var key = live.snapshot_at + "|" + (fresh ? fresh.min : "");
    if (merged && merged.key === key) return merged.v;
    var v = { meta: live, stations: live.stations, snapshot_at: live.snapshot_at, t_min: live.t_min, offday: live.offday, in_window: live.in_window, next_bell: live.next_bell, ahead: live.ahead || null, reward: live.reward || null,
              totals: live.totals, plans: live.plans, bikes: live.bikes, docks: live.docks, status: live.status, age: live.age, p30: live.p30, p60: live.p60, unmet: live.unmet,
              history: function (i) { var t0 = mins(live.history.from), st = live.history.step; return (live.history.bikes[i] || []).map(function (b, k) { return [t0 + k * st, b]; }); } };
    // Counts read from the operator a moment ago replace the snapshot's for the stations around campus. state.json carries
    // the forecast for every stock such a station could have ("fresh"), so the new count picks its own row.
    var fr = live.fresh;
    if (fresh && fr && fr.sno && live.ahead && fresh.day === live.snapshot_at.slice(0, 10) && fresh.min >= live.t_min && fresh.min - live.t_min <= 25) {
      var pos = {}, bikes = live.bikes.slice(), docks = live.docks.slice(), base = [], used = 0;
      var ah = { step: live.ahead.step, bike: live.ahead.bike.slice(), dock: live.ahead.dock.slice(), bikes: live.ahead.bikes.slice() };
      live.stations.forEach(function (s, i) { pos[s.sno] = i; });
      fr.sno.forEach(function (sno, j) {
        var i = pos[sno], c = fresh.c[sno]; if (i == null || !c) return;
        var cap = live.stations[i].cap, w = fr.bike[j].length / (cap + 1), b = Math.max(0, Math.min(cap, c[0]));
        if (w !== Math.floor(w) || w < 1) return;
        bikes[i] = c[0]; docks[i] = c[1]; base[i] = fresh.min; used++;
        ah.bike[i] = fr.bike[j].substr(b * w, w); ah.dock[i] = fr.dock[j].substr(b * w, w); ah.bikes[i] = fr.bikes[j].substr(b * w, w);
      });
      if (used) { v.bikes = bikes; v.docks = docks; v.ahead = ah; v.base = base; v.freshMin = fresh.min; }
    }
    merged = { key: key, v: v };
    return v;
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
      if (picking) { var w = picking; setPicking(null); setPoint(w, { kind: "pick", lat: e.latlng.lat, lng: e.latlng.lng }); return; }
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
    var rl = (tab === "rider" || tab === "dock") ? observed && relayOn(v, i, need(), arriveMin(v, i)) : tab === "policy" && observed && polPays(v, i);
    var open = "<div class=\"glyph" + (sel ? " sel" : "") + (rl ? " paid" : "") + "\"><svg width=\"" + S + "\" height=\"" + S + "\" viewBox=\"0 0 " + S + " " + S + "\">";
    if (!big) {
      // zoomed out: a dot sized by the station; stations with nothing to report stay small and faint
      var calm = !observed || ((tab === "ops" || tab === "policy") && fill === tok("--r0")), r = calm ? R * 0.8 : R;
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
      "<circle cx=\"" + c + "\" cy=\"" + c + "\" r=\"" + rr + "\" fill=\"" + fill + "\" fill-opacity=\"" + (observed ? 1 : 0.7) + "\"/>" + num + "</svg>" + star + (rl ? "<span class=\"rmark\">" + (tab === "policy" ? t("rmPolicy") : "+5") + "</span>" : "") + label + "</div>";
  }
  function drawStations(v) {
    glyphLayer.clearLayers(); markers = {};
    $("map").classList.toggle("relayonly", relayOnly && (tab === "rider" || tab === "dock"));
    if (!fitted) { fitted = true; if (tab === "ops") fitArea(v); else fitCampus(v, false); }
    v.stations.forEach(function (s, i) {
      var S = 2 * glyphR(s.cap) + 6;
      var m = L.marker([s.lat, s.lng], { icon: L.divIcon({ className: "", html: glyphHtml(s, v, i, selected === i), iconSize: [S, S], iconAnchor: [S / 2, S / 2] }),
        zIndexOffset: selected === i ? 800 : (isCampus(s) ? 500 : 0), keyboard: false });
      m.on("click", function (e) { L.DomEvent.stopPropagation(e); if (picking) { var w = picking; setPicking(null); setPoint(w, { kind: "pick", lat: s.lat, lng: s.lng }); } select(i); });
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
    if (tab === "ops" || tab === "about") return;
    var mark = function (p, cls) { L.marker([p.lat, p.lng], { icon: L.divIcon({ className: "", html: "<div class=\"originicon" + cls + "\"></div>", iconSize: [18, 18], iconAnchor: [9, 9] }), zIndexOffset: 900, keyboard: false, interactive: false }).addTo(originLayer); };
    if (tab === "dock") { mark(dest, " to"); return; }
    mark(origin, ""); if (goal) mark(goal, " to");
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
    v.stations.forEach(function (s, i) { if (!isCampus(s) || v.bikes[i] == null) return; var c = chance(v, i, kind, at); if (c == null) return; n++; if (c >= SURE[kind]) sure++; });
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
      ml.textContent = st || (t("bellNext") + " " + nb.time); mleft.innerHTML = (st ? "<small class=\"bt\">" + t("bellUntil", { t: nb.time }) + "</small>" : "") + untilText(nb.minutes, false);
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
  function setPoint(which, p) {
    if (which === "origin") origin = p; else if (which === "goal") goal = p; else dest = p;
    store("btb-" + which, p && p.kind === "place" ? p.id : null); nearN = 8; if (view()) render();
  }
  function setPicking(which) {
    picking = which || null; $("hint").hidden = !picking; $("hint").textContent = picking ? t(picking === "origin" ? "picking" : "pickingDest") : ""; $("map").classList.toggle("picking", !!picking);
    if (isPhone()) setSheet(picking ? "peek" : "half");
    if (!picking) syncPlaces();
  }
  function locate(which) {
    var fab = $("fab"), fail = function () { fab.classList.remove("busy"); toast(t("geoFail"), 4000); syncPlaces(); };
    if (!navigator.geolocation) { fail(); return; }
    fab.classList.add("busy"); if (picking) setPicking(null);
    navigator.geolocation.getCurrentPosition(function (pos) {
      fab.classList.remove("busy");
      var lat = pos.coords.latitude, lng = pos.coords.longitude, v = view();
      var nearest = v ? Math.min.apply(null, v.stations.map(function (s) { return distKm(s.lat, s.lng, lat, lng); })) : 0;
      if (nearest > 5) { toast(t("tooFar"), 4500); syncPlaces(); return; }
      setPoint(which, { kind: "me", lat: lat, lng: lng }); viewTo(lat, lng, Math.max(map.getZoom(), 16));
    }, fail, { timeout: 8000, maximumAge: 60000, enableHighAccuracy: true });
  }
  // the two selectors: from (borrow tab) and to (borrow: optional; return: where the ride ends)
  function placeLabel(p) { return lang === "zh" ? p.name : p.name_en; }
  function valueOf(p) { return !p ? "" : p.kind === "place" ? p.id : p.kind; }
  function syncPlaces() {
    var dock = tab === "dock", key = lang + "|" + (dock ? "d" : "r") + "|" + (PL ? PL.places.length : 0);
    if (key !== placesKey) {
      placesKey = key;
      var list = PL ? PL.places : [{ id: "lib", name: "圖資大樓", name_en: "Library", group: "campus" }];
      var grp = function (g, label) { var o = list.filter(function (p) { return p.group === g; }).map(function (p) { return "<option value=\"" + p.id + "\">" + esc(placeLabel(p)) + "</option>"; }).join(""); return o ? "<optgroup label=\"" + t(label) + "\">" + o + "</optgroup>" : ""; };
      var rest = "<optgroup label=\"" + t("grpOther") + "\"><option value=\"me\">" + t("oMe") + "</option><option value=\"pick\">" + t("oPick") + "</option></optgroup>";
      $("fromSel").innerHTML = grp("campus", "grpCampus") + grp("town", "grpTown") + rest;
      $("toSel").innerHTML = (dock ? "" : "<option value=\"\">" + t("toNone") + "</option>") + grp("campus", "grpCampus") + grp("town", "grpTown") + rest;
    }
    $("fromWrap").hidden = dock; $("fromK").textContent = t("originK"); $("toK").textContent = t(dock ? "destK" : "goalK");
    $("fromSel").value = picking === "origin" ? "pick" : valueOf(origin);
    $("toSel").value = picking && picking !== "origin" ? "pick" : valueOf(dock ? dest : goal);
    $("fab").setAttribute("aria-pressed", point().kind === "me" ? "true" : "false");
  }
  function choosePlace(which, val) {
    if (picking) setPicking(null);
    if (val === "") { goal = null; store("btb-goal", null); render(); return; }
    if (val === "me") { locate(which); return; }
    if (val === "pick") { setPicking(which); return; }
    var p = PL && PL.byId[val]; if (!p) { syncPlaces(); return; }
    setPoint(which, { kind: "place", id: p.id, lat: p.lat, lng: p.lng });
    if (isPhone()) viewTo(p.lat, p.lng, Math.max(map.getZoom(), 16)); else viewTo(p.lat, p.lng, Math.max(map.getZoom(), 16));
  }
  function walkCell(m, label) { return "<span class=\"walk\">" + t("walkMin", { m: m }) + "<small>" + t(label || "walkK") + "</small></span>"; }
  function farCell(km) { return "<span class=\"walk\">" + t("walkKm", { k: km.toFixed(1) }) + "<small>" + t("farK") + "</small></span>"; }
  function shortName(s) { return isCampus(s) && SHORT[s.sno] ? SHORT[s.sno][lang === "zh" ? 0 : 1] : nameOf(s); }
  function subLine(v, i) {
    var o = look(v, i), turn = v.bikes[i] == null ? "" : turnText(v, i, need(), o.cls), h = "";
    if (o.text) h += "<span class=\"state " + o.cls + "\">" + o.text + "</span>";
    if (turn) h += "<span>" + turn + "</span>";
    return h;
  }
  function stationRow(v, i) {
    var s = v.stations[i], p = point(), li = document.createElement("li"); li.className = "row" + (selected === i ? " sel" : ""); li.tabIndex = 0;
    var km = distKm(s.lat, s.lng, p.lat, p.lng);
    li.innerHTML = badge(v, i) + "<span><span class=\"nm\">" + esc(nameOf(s)) + (favs.indexOf(s.sno) >= 0 ? "<span class=\"star\" aria-hidden=\"true\">★</span>" : "") + (v.bikes[i] == null ? "" : relayTag(v, i, need(), arriveMin(v, i))) + "</span><span class=\"sub\">" + subLine(v, i) + "</span></span>" + (km > 3 ? farCell(km) : walkCell(walkPS(v, p, i), tab === "dock" ? "walkDest" : "walkK"));
    var go = function () { select(i); focusStation(s); };
    li.addEventListener("click", go); li.addEventListener("keydown", function (e) { if (e.key === "Enter") go(); });
    return li;
  }
  function ordered(v) { var p = point(); return v.stations.map(function (s, i) { var km = distKm(s.lat, s.lng, p.lat, p.lng); return [km > 3 ? 1000 + km : walkPS(v, p, i), i, km]; }).sort(function (a, b) { return a[0] - b[0] || a[2] - b[2]; }); }

  // ---------- which station ----------
  // The rule checked against the logger (analysis/code/final_time.py "expectm", and day by day in demo_track.py): the
  // station with the fewest expected minutes until the rider has a bike, or is rid of one. A station that may fail is
  // charged the cost of going on to the next: x.e = minutes to reach it + chance of success x minutes left after it
  // + chance of failure x (the cheapest way on, itself charged G minutes if it fails too). Among the stations within
  // MARGIN minutes of the fewest, the one with the best chance is named, so nobody is sent past an empty rack to save seconds.
  function solve(v, c, kind, t0, hop) {
    if (!c.length) return null;
    var best = null, k;
    c.forEach(function (x) {
      x.at = t0 + x.leg; x.p = chance(v, x.i, kind, x.at);
      var on = null;
      c.forEach(function (y) { if (y === x) return; var h = hop(v, x.i, y.i), p2 = chance(v, y.i, kind, x.at + h), cost = h + y.tail + (1 - p2) * G; if (!on || cost < on.cost - 1e-9) on = { i: y.i, hop: h, p: p2, cost: cost }; });
      x.on = on; x.e = x.leg + x.p * x.tail + (1 - x.p) * (on ? on.cost : G);
      if (!best || x.e < best.e - 1e-9) best = x;
    });
    var least = best.e;
    c.forEach(function (x) { if (x.e <= least + MARGIN + 1e-9 && x.p > best.p + 1e-9) best = x; });
    var sure = null, skipped = null;
    for (k = 0; k < c.length; k++) if (c[k].p >= SURE[kind]) { sure = c[k]; break; }
    for (k = 0; k < c.length && c[k] !== best; k++) if (c[k].p < MAYBE[kind]) { skipped = c[k]; break; }
    return { best: best, sure: sure, skipped: skipped, cand: c };
  }
  function planBike(v, p, leave) {
    var c = [];
    v.stations.forEach(function (s, i) { if (v.bikes[i] == null) return; var km = distKm(s.lat, s.lng, p.lat, p.lng); if (km <= 2) c.push({ i: i, km: km, leg: walkPS(v, p, i), tail: 0 }); });
    c.sort(function (a, b) { return a.leg - b.leg || a.km - b.km; });
    return solve(v, c.slice(0, 12), "bike", leave, walkSS);
  }
  // p: where the rider is going; at: the minute the ride ends near p, or, with `from`, the minute it starts at station `from`
  function planDock(v, p, at, from) {
    var c = [], all = [];
    v.stations.forEach(function (s, i) {
      if (v.bikes[i] == null || have(v, i, "dock") == null || i === from) return;                                           // a ride does not end where it started
      var km = distKm(s.lat, s.lng, p.lat, p.lng), x = { i: i, km: km, leg: from == null ? ridePS(v, p, i) : rideSS(v, from, i), tail: walkPS(v, p, i) };
      if (km <= 0.6) c.push(x); else if (km <= 1.5) all.push(x);
    });
    if (c.length < 2) { all.sort(function (a, b) { return a.km - b.km; }); c = c.concat(all.slice(0, 3 - c.length)); }      // a destination with no station next to it
    c.sort(function (a, b) { return (a.leg + a.tail) - (b.leg + b.tail) || a.km - b.km; });
    return solve(v, c.slice(0, 12), "dock", at, rideSS);
  }
  // borrow, ride, return, against walking all the way
  function planTrip(v, from, to, leave) {
    var pb = planBike(v, from, leave); if (!pb) return null;
    var best = null, opts = [];
    pb.cand.slice().sort(function (a, b) { return a.e - b.e; }).slice(0, 3).forEach(function (x) {
      var pd = planDock(v, to, leave + x.e + 1, x.i); if (!pd) return;
      var o = { bike: x, dock: pd.best, dplan: pd, total: x.e + 1 + pd.best.e + 1 };     // a minute to take the bike, a minute to lock it
      opts.push(o); if (!best || o.total < best.total - 1e-9) best = o;
    });
    if (best) { var least = best.total; opts.forEach(function (o) { if (o.total <= least + MARGIN + 1e-9 && o.bike.p > best.bike.p + 1e-9) best = o; }); }
    if (!best) best = { bike: pb.best, dock: null, total: null };            // no other station near the destination: the trip is too short for a bike
    best.plan = pb; best.walk = walkPP(from, to); best.rideIt = best.dock != null && best.total + 1 < best.walk;
    return best;
  }
  // a chance as a percentage, rounded to tens (the forecast is not finer than that)
  function pickRow(v, x, kind, why, cellLabel, cell) {
    var s = v.stations[x.i], o = verdict(v, x.i, kind, x.at), el = document.createElement("button");
    el.type = "button"; el.className = "pick" + (x.p >= SURE[kind] ? "" : x.p >= MAYBE[kind] ? " weak" : " poor");
    var sub = "<span class=\"state " + o.cls + "\">" + o.text + "</span>";
    if (kind === "dock") sub += "<span>" + t(v.docks && v.docks[x.i] === 1 ? "docksNow1" : "docksNow", { d: v.docks && v.docks[x.i] != null ? v.docks[x.i] : "–" }) + "</span>";
    // a sure station gets the count to expect; "often empty at this time" beside "likely has bikes" would only confuse,
    // so the usual day is mentioned when the station is not sure
    var us = usualShare(v, s, kind, x.at), eb = expectAt(v, x.i, x.at), sure = x.p >= SURE[kind];
    if (sure && eb != null) sub += "<span>" + (kind === "dock" ? t("expectDock", { d: Math.max(0, s.cap - eb) }) : t("expect", { b: eb })) + "</span>";
    else if (!sure && us && us.p >= 0.4) sub += "<span>" + t(kind === "dock" ? "usualHotDock" : "usualHotBike") + "</span>";
    else if (kind !== "dock") sub += "<span>" + t("bikesNow", { b: v.bikes[x.i] }) + "</span>";
    el.innerHTML = badgeAt(v, x.i, kind, x.at) + "<span><span class=\"why\">" + why + "</span><span class=\"nm\">" + esc(nameOf(s)) + relayTag(v, x.i, kind, x.at) + "</span><span class=\"sub\">" + sub + "</span></span>" + walkCell(cell, cellLabel);
    el.addEventListener("click", function () { select(x.i); focusStation(s); });
    return el;
  }
  // what to say under the suggestion: the way on if it may fail, the safer station, the nearer one that was skipped
  function notes(v, pl, kind) {
    var b = pl.best, out = [], dock = kind === "dock";
    if (b.p < SURE[kind]) {
      if (b.p < MAYBE[kind] && !pl.sure) out.push(t(dock ? "weakDock" : "weakBike"));
      if (b.on) out.push(t(dock ? "tipOnDock" : "tipOn", { m: b.on.hop, n: shortName(v.stations[b.on.i]) }));
      if (pl.sure && pl.sure !== b) out.push(t(dock ? "tipSureDock" : "tipSure", { n: shortName(v.stations[pl.sure.i]), m: dock ? pl.sure.tail : pl.sure.leg }));
    } else if (pl.skipped) {
      var sk = pl.skipped, skn = shortName(v.stations[sk.i]), gone = have(v, sk.i, kind) === 0;
      out.push(t(dock ? (gone ? "skipDockGone" : "skipDock") : (gone ? "skipBikeGone" : "skipBike"), { n: skn }));
    }
    return out;
  }
  // one line about the reward: the suggested station if it is likely to pay, else the likeliest station that costs at most three minutes more
  function relayLine(v, pl, kind, best) {
    var dock = kind === "dock", top = null;
    if (relayOn(v, best.i, kind, best.at)) return t(dock ? "relayRetHere" : "relayBorHere", { p: 10 * tenth(relayP(v, best.i, kind, best.at)) });
    pl.cand.forEach(function (x) { if (x === best || x.e > best.e + 3 || !relayOn(v, x.i, kind, x.at)) return; var p = relayP(v, x.i, kind, x.at); if (!top || p > top.p) top = { x: x, p: p }; });
    return top ? t(dock ? "relayRetAlt" : "relayBorAlt", { n: shortName(v.stations[top.x.i]), m: Math.max(1, Math.round(top.x.e - best.e)), p: 10 * tenth(top.p) }) : "";
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
  function renderBest(v) {
    var pk = $("best"), tip = $("tip"), dock = tab === "dock", w = when[dock ? "dock" : "rider"], leave = leaveMin(v), lines = [], relay = "";
    pk.hidden = false; pk.innerHTML = ""; tip.hidden = true;
    if (dock) {
      var pd = planDock(v, dest, leave);
      if (!pd) { pk.innerHTML = "<div class=\"pick none\"><span><span class=\"sub\">" + t("noneDock") + "</span></span></div>"; return; }
      pk.appendChild(pickRow(v, pd.best, "dock", t("bestDock"), "walkDest", pd.best.tail));
      lines = notes(v, pd, "dock"); relay = relayLine(v, pd, "dock", pd.best);
    } else {
      var why = w.kind === "bell" ? t("bestBikeBell", { t: hm(w.time) }) : t("bestBikeNow");
      var trip = goal ? planTrip(v, origin, goal, leave) : null, pb = trip ? trip.plan : planBike(v, origin, leave);
      if (!pb) { pk.innerHTML = "<div class=\"pick none\"><span><span class=\"sub\">" + t("noneBike") + "</span></span></div>"; return; }
      var bx = trip ? trip.bike : pb.best;
      if (trip && !trip.rideIt) {
        var wk = document.createElement("div"); wk.className = "pick walkit";
        wk.innerHTML = "<span class=\"badge n\">" + ICON.walk + "</span><span><span class=\"why\">" + t("walkWins") + "</span><span class=\"nm\">" + t("walkAll", { m: trip.walk }) + "</span>" + (trip.dock ? "<span class=\"sub\"><span>" + t("walkVs", { m: Math.round(trip.total) }) + "</span></span>" : "") + "</span>";
        pk.appendChild(wk);
      }
      pk.appendChild(pickRow(v, bx, "bike", why, "walkK", bx.leg));
      if (trip && trip.dock) {
        pk.appendChild(pickRow(v, trip.dock, "dock", t("bestDock"), "walkDest", trip.dock.tail));
        if (trip.rideIt) lines.push(t("tripRide", { a: Math.round(trip.total), b: trip.walk }));
      }
      lines = lines.concat(notes(v, { best: bx, sure: pb.sure, skipped: bx === pb.best ? pb.skipped : null }, "bike"));
      if (!lines.length && w.kind === "now" && !(trip && !trip.rideIt)) { var lt = leaveTip(v); if (lt) lines.push(lt); }
      relay = (trip && trip.dock ? relayLine(v, trip.dplan, "dock", trip.dock) : "") || relayLine(v, pb, "bike", bx);
    }
    if (lines.length || relay) { tip.innerHTML = lines.map(esc).join("<br>") + (relay ? (lines.length ? "<br>" : "") + "<span class=\"relayline\">" + esc(relay) + "</span>" : ""); tip.hidden = false; }
  }
  // How the search for a bike goes when leaving at `leave`, in three shares: the first station has a bike, another
  // station is needed but the rider is on a bike within SLOW minutes, or it takes longer. Leaving now, the rider follows
  // the suggestion: its chance, then the station the rule would go on to, then one more. Leaving later, the rider will
  // look again before going: the nearest station that shows a bike then, with the chance that the first n stations are
  // all empty taken as (product of their chances of being empty) ^ THETA, because campus stations empty together.
  // analysis/code/final_spread.py checks both against the held-out days.
  function spread(v, from, leave) {
    var pl = planBike(v, from, leave); if (!pl) return null;
    var green = 0, yellow = 0, c = pl.cand;
    if (leave <= nowMin(v)) {
      var b = pl.best, m1 = b.leg;
      if (m1 <= SLOW) green = b.p;
      if (b.on) {
        var m2 = m1 + b.on.hop, t2 = b.at + b.on.hop, third = null;
        if (m2 <= SLOW) yellow += (1 - b.p) * b.on.p;
        c.forEach(function (y) { if (y === b || y.i === b.on.i) return; var h = walkSS(v, b.on.i, y.i), p3 = chance(v, y.i, "bike", t2 + h), cost = h + (1 - p3) * G; if (!third || cost < third.cost - 1e-9) third = { hop: h, p: p3, cost: cost }; });
        if (third && m2 + third.hop <= SLOW) yellow += (1 - b.p) * (1 - b.on.p) * third.p;
      }
    } else {
      var order = c.slice().sort(function (x, y) { return x.leg - y.leg || x.km - y.km; }), prod = 1, before = 1;
      order.forEach(function (x) {
        var s0 = chance(v, x.i, "bike", leave); if (s0 == null) return;
        prod *= 1 - s0; var after = Math.pow(prod, THETA), pick = before - after; before = after;
        if (s0 <= 0 || pick <= 0 || x.leg > SLOW) return;
        var r = Math.min(1, chance(v, x.i, "bike", leave + x.leg) / s0), k2 = null;
        green += pick * r;
        order.forEach(function (y) { if (y !== x && (!k2 || walkSS(v, x.i, y.i) < walkSS(v, x.i, k2.i))) k2 = y; });
        if (k2) { var h2 = walkSS(v, x.i, k2.i); if (x.leg + h2 <= SLOW) yellow += pick * (1 - r) * chance(v, k2.i, "bike", leave + x.leg + h2); }
      });
    }
    green = Math.max(0, Math.min(1, green)); yellow = Math.max(0, Math.min(1 - green, yellow));
    return { g: green, y: yellow, r: 1 - green - yellow, e: pl.best.e };
  }
  function dotsOf(sp) { var r = Math.round(10 * sp.r), g = Math.min(10 - r, Math.round(10 * sp.g)); return { g: g, y: 10 - r - g, r: r }; }
  // the seven departures of the chart (now and every 10 minutes for an hour), computed once per view
  function columns(v) {
    if (!v.ahead || !v.in_window) return null;
    var n = nowMin(v), key = v.snapshot_at + "|" + (v.freshMin || "") + "|" + n + "|" + origin.lat + "," + origin.lng + "|" + (PL ? 1 : 0);
    if (colsMemo && colsMemo.key === key) return colsMemo.cols;
    var cols = [];
    for (var d = 0; d <= 60; d += 10) { var sp = spread(v, origin, n + d); if (!sp) { cols = null; break; } cols.push({ at: n + d, sp: sp, k: dotsOf(sp) }); }
    colsMemo = { key: key, cols: cols };
    return cols;
  }
  // one line that says what the dots say: minutes for leaving now, and the first departure with a long search
  function leaveTip(v) {
    var cols = columns(v); if (!cols) return "";
    var a = Math.max(1, Math.round(cols[0].sp.e)), first = -1, k, best = 0;
    for (k = 0; k < cols.length; k++) if (cols[k].k.r >= 1) { first = k; break; }
    // advice, not odds: the latest departure before the dots show a long search ("leave by", as route planners say)
    if (first < 0) return t("tipCalm", { a: a });
    if (first === 1) return t("tipSoon1", { a: a, u: hm(cols[1].at % 1440) });
    if (first > 1) return t("tipSoon", { a: a, u: hm(cols[first].at % 1440), v: hm(cols[first - 1].at % 1440) });
    for (k = 1; k < cols.length; k++) if (cols[k].k.r < cols[best].k.r) best = k;
    return t("tipNowSlow") + (best && cols[best].k.r <= cols[0].k.r - 2 ? t("tipLater", { u: hm(cols[best].at % 1440) }) : "");
  }
  // ten dots per departure (Kay et al. 2016; Fernandes et al. 2018): green, yellow and red stacked from the bottom
  function renderLater(v) {
    var sec = $("laterSec"), cols = tab === "rider" ? columns(v) : null;
    if (!cols) { sec.hidden = true; return; }
    sec.hidden = false;
    $("hLater").textContent = t("laterH"); $("hLaterSub").textContent = t("laterSub");
    var W = 340, H = 94, bw = W / cols.length, R = 4.3, gap = 10.6, h = "", aria = [];
    var label = function (x, y, s2, bold) { return "<text class=\"" + (bold ? "nred" : "tick") + "\" x=\"" + x.toFixed(1) + "\" y=\"" + y + "\" text-anchor=\"middle\" font-size=\"" + (bold ? 11.5 : 10.5) + "\"" + (bold ? " font-weight=\"600\"" : "") + " fill=\"" + tok(bold ? "--ink" : "--ink-3") + "\" font-family=\"Barlow Semi Condensed, sans-serif\">" + s2 + "</text>"; };
    cols.forEach(function (col, k) {
      var seq = [], q, cx = k * bw + bw / 2, when = k === 0 ? t("wNow") : hm(col.at % 1440);
      for (q = 0; q < col.k.g; q++) seq.push("g");
      for (q = 0; q < col.k.y; q++) seq.push("y");
      for (q = 0; q < col.k.r; q++) seq.push("r");
      seq.forEach(function (c2, q2) { var fill = { g: "--ok-fill", y: "--low-fill", r: "--out-fill" }[c2]; h += "<circle class=\"d " + c2 + "\" cx=\"" + (cx + (q2 % 2 ? gap / 2 : -gap / 2)).toFixed(1) + "\" cy=\"" + (70 - Math.floor(q2 / 2) * gap).toFixed(1) + "\" r=\"" + R + "\" fill=\"" + tok(fill) + "\" stroke=\"" + tok("--surface") + "\" stroke-width=\"1\"/>"; });
      if (col.k.r) h += label(cx, 13, t("dotsRed", { p: 10 * col.k.r }), true);
      h += label(cx, 90, when, false);
      aria.push(t("dotsAria", { t: when, g: 10 * col.k.g, y: 10 * col.k.y, r: 10 * col.k.r }));
    });
    var key = function (cls, k2) { return "<span><i class=\"" + cls + "\"></i>" + t(k2) + "</span>"; };
    $("later").innerHTML = "<svg viewBox=\"0 0 " + W + " " + H + "\" role=\"img\" aria-label=\"" + esc(t("laterH") + (lang === "zh" ? "：" : ": ") + aria.join(lang === "zh" ? "；" : "; ")) + "\">" + h + "</svg>" +
      "<div class=\"dotkey\">" + key("ok", "dotKeyG") + key("low", "dotKeyY") + key("out", "dotKeyR") + "</div>";
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
    $("hUsualSub").textContent = t(v.offday ? "usualOff" : "usualTeach") + sep() + (a < 0 ? t(bike ? "usualEasyBike" : "usualEasyDock") : t("usualPeak", { a: hm(360 + 30 * a), b: hm(360 + 30 * (b + 1)) }));
    var W = 340, H = 56, bw = W / arr.length, m = nowMin(v), h = "";
    arr.forEach(function (x, k) { var hh = Math.max(2, Math.min(1, x / 0.6) * 38); h += "<rect x=\"" + (k * bw + 1).toFixed(1) + "\" y=\"" + (40 - hh).toFixed(1) + "\" width=\"" + (bw - 2).toFixed(1) + "\" height=\"" + hh.toFixed(1) + "\" rx=\"2\" fill=\"" + tok(x >= 0.4 ? "--out-fill" : x >= 0.2 ? "--low-fill" : "--line-2") + "\"/>"; });
    [6, 9, 12, 15, 18, 21].forEach(function (hr) { h += "<text x=\"" + ((hr * 60 - 360) / 30 * bw + 1).toFixed(1) + "\" y=\"53\" font-size=\"10.5\" fill=\"" + tok("--ink-3") + "\" font-family=\"Barlow Semi Condensed, sans-serif\">" + pad(hr) + "</text>"; });
    if (m >= 360 && m <= 1380) { var x = ((m - 360) / 30 * bw).toFixed(1); h += "<line x1=\"" + x + "\" x2=\"" + x + "\" y1=\"0\" y2=\"42\" stroke=\"" + tok("--accent") + "\" stroke-width=\"2\"/>"; }
    $("usual").innerHTML = "<svg viewBox=\"0 0 " + W + " " + H + "\" aria-hidden=\"true\">" + h + "</svg>";
  }
  // ---------- class-end reminders ----------
  // A weekly calendar event five minutes before a class ends, with a link that opens the page set to that building. The
  // page has no server, so the phone's own calendar does the reminding.
  function remState(v) {
    var r = load("btb-remind", null) || {}, n = taipeiNow(), wd = n.getDay(), nb = null, m = n.getHours() * 60 + n.getMinutes();
    v.meta.bells.forEach(function (b) { if (!nb && mins(b) > m) nb = mins(b); });
    var campus = function (id) { var p = id && PL && PL.byId[id]; return !!p && p.group === "campus"; };      // classes are on campus
    if (!campus(r.place)) r.place = origin.kind === "place" && campus(origin.id) ? origin.id : "lib";
    if (!Array.isArray(r.days)) r.days = wd >= 1 && wd <= 5 ? [wd] : [1];
    if (typeof r.end !== "number" || v.meta.bells.map(mins).indexOf(r.end) < 0) r.end = nb || mins(v.meta.bells[v.meta.bells.length - 1]);
    return r;
  }
  function renderRemind(v) {
    var box = $("remindBox");
    box.hidden = tab !== "rider" || !PL || !v.meta.bells || !v.meta.bells.length; if (box.hidden) return;
    var r = remState(v), key = lang + "|" + v.meta.bells.join(",") + "|" + PL.places.length;
    $("remindOpen").textContent = t("remindOpen");
    if (key !== remKey) {
      remKey = key;
      $("remPlaceK").textContent = t("remindPlace"); $("remEndK").textContent = t("remindEnd"); $("remDaysK").textContent = t("remindDays"); $("remIcs").textContent = t("remindIcs");
      $("remPlace").innerHTML = PL.places.filter(function (p) { return p.group === "campus"; }).map(function (p) { return "<option value=\"" + p.id + "\">" + esc(placeLabel(p)) + "</option>"; }).join("");
      $("remEnd").innerHTML = v.meta.bells.map(function (b) { return "<option value=\"" + mins(b) + "\">" + b + "</option>"; }).join("");
      $("remDays").innerHTML = [1, 2, 3, 4, 5].map(function (d) { return "<button type=\"button\" class=\"opt\" data-d=\"" + d + "\" aria-pressed=\"false\">" + T[lang].weekdays[d] + "</button>"; }).join("");
    }
    $("remPlace").value = r.place; $("remEnd").value = String(r.end);
    Array.prototype.forEach.call($("remDays").querySelectorAll("button"), function (b) { b.setAttribute("aria-pressed", r.days.indexOf(parseInt(b.getAttribute("data-d"), 10)) >= 0 ? "true" : "false"); });
    var g = $("remGcal"), on = r.days.length > 0;
    $("remIcs").disabled = !on; g.hidden = !on; g.textContent = t("remindGcal"); if (on) g.href = gcalLink(r);
    $("remNote").textContent = on ? t("remindNote", { d: parseInt(REM_END.slice(5, 7), 10) + "/" + parseInt(REM_END.slice(8, 10), 10) }) : t("remindPick");
  }
  function remLink(r) { var base = /^https:/.test(location.protocol) && !/claude\.ai$/.test(location.hostname) ? location.origin + location.pathname.replace(/index\.html$/, "") : SITE; return base + "?from=" + encodeURIComponent(r.place); }
  function ymd(d) { return d.getFullYear() + pad(d.getMonth() + 1) + pad(d.getDate()); }
  function hhmm(m) { return pad(Math.floor(m / 60)) + pad(m % 60); }
  // the first date on one of the chosen weekdays on which the reminder is still ahead
  function firstDay(days, startMin) {
    var n = taipeiNow(), best = null;
    days.forEach(function (d) { var x = new Date(n.getFullYear(), n.getMonth(), n.getDate()), k = (d - x.getDay() + 7) % 7; if (k === 0 && n.getHours() * 60 + n.getMinutes() >= startMin) k = 7; x.setDate(x.getDate() + k); if (!best || x < best) best = x; });
    return best;
  }
  function byDay(days) { return days.slice().sort().map(function (d) { return ["SU", "MO", "TU", "WE", "TH", "FR", "SA"][d]; }).join(","); }
  function untilUtc() {
    var end = new Date(parseInt(REM_END.slice(0, 4), 10), parseInt(REM_END.slice(5, 7), 10) - 1, parseInt(REM_END.slice(8, 10), 10)), n = taipeiNow();
    if (end < n) { end = new Date(n.getFullYear(), n.getMonth(), n.getDate() + 18 * 7); }             // after this term: eighteen weeks from today
    return ymd(end) + "T155959Z";                                                                       // 23:59:59 in Taipei
  }
  function gcalLink(r) {
    var st = r.end - 5, day = ymd(firstDay(r.days, st));
    return "https://calendar.google.com/calendar/render?action=TEMPLATE&text=" + encodeURIComponent(t("remindTitle")) + "&dates=" + day + "T" + hhmm(st) + "00/" + day + "T" + hhmm(r.end) + "00&ctz=Asia/Taipei" +
      "&recur=" + encodeURIComponent("RRULE:FREQ=WEEKLY;BYDAY=" + byDay(r.days) + ";UNTIL=" + untilUtc()) + "&details=" + encodeURIComponent(t("remindDesc", { u: remLink(r) }));
  }
  function icsEsc(s) { return String(s).replace(/\\/g, "\\\\").replace(/;/g, "\\;").replace(/,/g, "\\,").replace(/\n/g, "\\n"); }
  // lines longer than 75 bytes are folded, never inside a character
  function icsFold(line) {
    var enc = window.TextEncoder ? new TextEncoder() : null, out = "", n = 0;
    Array.from(line).forEach(function (ch) { var b = enc ? enc.encode(ch).length : (ch.charCodeAt(0) > 127 ? 3 : 1); if (n + b > 75) { out += "\r\n "; n = 1; } out += ch; n += b; });
    return out;
  }
  function icsText(r) {
    var now = new Date(), stamp = now.getUTCFullYear() + pad(now.getUTCMonth() + 1) + pad(now.getUTCDate()) + "T" + pad(now.getUTCHours()) + pad(now.getUTCMinutes()) + pad(now.getUTCSeconds()) + "Z", link = remLink(r);
    var L = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Beat the Bell//NSYSU YouBike//EN", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
      "BEGIN:VTIMEZONE", "TZID:Asia/Taipei", "BEGIN:STANDARD", "DTSTART:19700101T000000", "TZOFFSETFROM:+0800", "TZOFFSETTO:+0800", "TZNAME:CST", "END:STANDARD", "END:VTIMEZONE"];
    var st = r.end - 5, day = ymd(firstDay(r.days, st)), bd = byDay(r.days);
    L.push("BEGIN:VEVENT", "UID:btb-" + bd.replace(/,/g, "") + "-" + hhmm(r.end) + "-" + r.place + "@alexlin8888.github.io", "DTSTAMP:" + stamp,
      "DTSTART;TZID=Asia/Taipei:" + day + "T" + hhmm(st) + "00", "DTEND;TZID=Asia/Taipei:" + day + "T" + hhmm(r.end) + "00",
      "RRULE:FREQ=WEEKLY;BYDAY=" + bd + ";UNTIL=" + untilUtc(),
      "SUMMARY:" + icsEsc(t("remindTitle")), "DESCRIPTION:" + icsEsc(t("remindDesc", { u: link })), "URL:" + link,
      "BEGIN:VALARM", "ACTION:DISPLAY", "DESCRIPTION:" + icsEsc(t("remindTitle")), "TRIGGER:PT0M", "END:VALARM", "END:VEVENT", "END:VCALENDAR");
    return L.map(icsFold).join("\r\n") + "\r\n";
  }
  function remSave(change) { var v = view(); if (!v) return; var r = remState(v); change(r); store("btb-remind", r); renderRemind(v); }
  function renderRider(v) {
    var dock = tab === "dock";
    $("q").placeholder = t("search"); $("q").setAttribute("aria-label", t("search"));
    syncPlaces(); renderWhen(v);
    $("hFav").textContent = t("fav"); $("hNear").textContent = t("near"); $("hNearSub").textContent = v.freshMin != null ? t("nearFresh", { t: hm(v.freshMin) }) : t(dock ? "nearDock" : "nearBike");
    var idx = {}; v.stations.forEach(function (s, i) { idx[s.sno] = i; });
    var fl = $("favs"); fl.innerHTML = "";
    var fi = favs.map(function (sno) { return idx[sno]; }).filter(function (i) { return i != null; });
    $("favSec").hidden = !fi.length;
    fi.forEach(function (i) { fl.appendChild(stationRow(v, i)); });
    $("hFavSub").textContent = fi.length ? String(fi.length) : "";
    var ord = ordered(v), nl = $("near"); nl.innerHTML = "";
    var paid = ord.filter(function (x) { return x[2] <= 1.5 && v.bikes[x[1]] != null && relayOn(v, x[1], need(), arriveMin(v, x[1])); }), ro = $("relayOnly");
    if (relayOnly && !paid.length) relayOnly = false;
    ro.hidden = !paid.length; ro.textContent = t("relayOnly"); ro.setAttribute("aria-pressed", relayOnly ? "true" : "false");
    (relayOnly ? paid : ord.slice(0, nearN)).forEach(function (x) { nl.appendChild(stationRow(v, x[1])); });
    $("map").classList.toggle("relayonly", relayOnly);
    $("more").hidden = relayOnly; $("more").textContent = nearN > 8 ? t("less") : t("more");
    renderBest(v); renderLater(v); renderUsual(v); renderRemind(v);
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
      h += "<div class=\"cell " + (c / 63 >= SURE[kind] ? "g" : c / 63 >= MAYBE[kind] ? "y" : "r") + "\"><b>" + val + "</b><span>" + hm((baseMin(v, i) + 10 * (k + 1)) % 1440) + "</span></div>";
    }
    return "<div class=\"ahead\"><div class=\"cap\">" + t("aheadH") + sep() + t(kind === "bike" ? "aheadBike" : "aheadDock") + "</div><div class=\"cells\">" + h + "</div></div>";
  }
  function renderCard(v) {
    var wrap = $("cardWrap");
    if (selected == null) { wrap.hidden = true; return; }
    var i = selected, s = v.stations[i], observed = v.bikes[i] != null, kind = need(), o = look(v, i), isFav = favs.indexOf(s.sno) >= 0, turn = observed ? turnText(v, i, kind, o.cls) : "";
    var foot = [];
    if (v.age && v.age[i] != null && v.age[i] > 20) foot.push(t("stale2", { m: v.age[i] }));
    if (s.excluded) foot.push(t("excluded"));
    var docks = v.docks && v.docks[i] != null ? v.docks[i] : null, rp = observed && relayOn(v, i, kind, arriveMin(v, i)) ? relayP(v, i, kind, arriveMin(v, i)) : null, un = observed ? usualNote(v, s, kind, arriveMin(v, i)) : "";
    $("card").innerHTML = "<div class=\"hd\">" + badge(v, i) + "<div><div class=\"nm\">" + esc(nameOf(s)) + "</div><div class=\"alt\">" + esc(altName(s)) + "</div></div><button class=\"x\" id=\"cardX\" type=\"button\" aria-label=\"" + t("close") + "\">" + ICON.close + "</button></div>" +
      "<div class=\"says\">" + (o.text ? "<span class=\"state " + o.cls + "\">" + (observed && o.cls !== "x" ? t(kind === "dock" ? "fArriveDock" : "fArriveBike") + sep() : "") + o.text + "</span>" : "") + (turn ? "<span>" + turn + "</span>" : "") +
      (isCampus(s) ? "<span class=\"tag\">" + t("inCampus") + "</span>" : (s.group === "gateway" ? "<span class=\"tag\">" + t("nearCampus") + "</span>" : "")) + (isFav ? "<span class=\"tag\">★ " + t("fav") + "</span>" : "") + "</div>" +
      (rp != null ? "<div class=\"relaynote\"><span class=\"relay\">" + t("relayTag") + "</span>" + t(kind === "dock" ? "relayCardRet" : "relayCardBor", { p: 10 * tenth(rp) }) + "</div>" : "") +
      (un ? "<div class=\"usualnote\">" + un + "</div>" : "") +
      "<div class=\"facts two\"><div class=\"fact\"><div class=\"v\">" + (observed ? v.bikes[i] : "–") + "</div><div class=\"k\">" + t("fBikes", { c: s.cap }) + "</div></div>" +
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
    // the share goes into the words ("cuts it by 34%"): a bare "34%" beside "19 riders" said nothing
    var share = v.in_window && tt.plan_value > 0 && unmet >= 1 ? Math.min(100, Math.round(100 * tt.plan_value / unmet)) : null;
    $("tSaved").innerHTML = v.in_window ? fmt(tt.plan_value) + unit("uRide") : "–";
    $("kSaved").textContent = share != null ? t("kSavedP", { p: share }) : t("kSaved");
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
    // column names, so that "0 / 20" and "78%" say what they are
    $("riskHead").innerHTML = "<span></span><span class=\"bk\">" + t("riskColBk") + "</span><span class=\"pv\">" + (key === "unmet" ? t("riskColU") : t("riskColP", { h: horizon })) + "</span>";
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
    $("aboutWhat").innerHTML = t("aboutWhat"); $("aboutMore").innerHTML = t("aboutProof") + t("aboutRelay"); $("aboutHowS").textContent = t("aboutHowS");
    $("aboutKeyH").textContent = t("keyH");
    var sw = function (cls, n) { return "<span class=\"sw\"><span class=\"badge " + cls + "\">" + n + "</span></span>"; };
    $("aboutKey").innerHTML = "<li>" + sw("g", 12) + "<span>" + t("keyYes") + "</span></li><li>" + sw("y", 4) + "<span>" + t("keyMaybe") + "</span></li><li>" + sw("r", 1) + "<span>" + t("keyNo") + "</span></li>" +
      "<li>" + sw("x", 0) + "<span>" + t("keyGone") + "</span></li><li>" + sw("n", "–") + "<span>" + t("keyNone") + "</span></li>" +
      "<li><span class=\"sw\"><svg width=\"30\" height=\"30\" viewBox=\"0 0 30 30\" aria-hidden=\"true\"><circle cx=\"15\" cy=\"15\" r=\"12\" fill=\"none\" stroke=\"var(--accent)\" stroke-width=\"2.5\"/><path d=\"M15 3 A12 12 0 0 1 25.4 21\" fill=\"none\" stroke=\"var(--ink-3)\" stroke-width=\"2.5\" stroke-linecap=\"round\"/><circle cx=\"15\" cy=\"15\" r=\"8\" fill=\"var(--ok-fill)\"/></svg></span><span>" + t("keyRing") + "</span></li>" +
      "<li><span class=\"sw\"><span class=\"ln\"></span></span><span>" + t("keyRoute") + "</span></li>";
    $("aboutHow").innerHTML = t("aboutHow", { n: v ? v.stations.length : 309, h: v ? v.meta.horizon_min : 90, q: s.Q, s: Math.round(s.speed_kmh), st: Math.round(s.stop_min) });
    $("langK").textContent = t("langK"); $("credit").innerHTML = t("credit");
    renderTrack();
  }
  // track.json: what the page advised, written down before the outcome, and what then happened (analysis/code/demo_track.py)
  function renderTrack() {
    var el = $("aboutTrack"); if (!track || !track.days || !track.fields) { el.hidden = true; return; }
    var F = {}; track.fields.forEach(function (k, n) { F[k] = n; });
    var sum = {}, days = 0;
    Object.keys(track.days).forEach(function (d) { var x = track.days[d]; if (!x.teaching) return; days++; Object.keys(x.w).forEach(function (w) { if (!sum[w]) sum[w] = x.w[w].slice(); else x.w[w].forEach(function (val, n) { sum[w][n] += val; }); }); });
    var md = function (d) { return parseInt(d.slice(5, 7), 10) + "/" + parseInt(d.slice(8, 10), 10); };
    var h = "<h3>" + t("trackH") + "</h3><p>" + t("trackSub", { d: md(track.since || ""), n: days }) + "</p>", any = false;
    [["leave", "trackLeave"], ["arrive", "trackArrive"], ["dock", "trackDock"]].forEach(function (x) {
      var a = sum[x[0]]; if (!a || a[F.cases] < 20) return; any = true;
      var n = a[F.cases], f1 = function (k) { return (a[F[k]] / n).toFixed(1); }, m = { n: Math.round(n), a: f1("min_pick"), b: f1("min_alt"), c: f1("min_near") };
      // three equal numbers in a row look like a fault, so equal ones are said once
      var same = m.a === m.b && m.b === m.c, key = x[0] === "dock" ? "trackLineDock" : "trackLine";
      h += "<p><b>" + t(x[1]) + "</b>" + sep() + t(same ? key + "Same" : key, m);
      if (x[0] !== "dock" && a[F.n20] >= 20) h += t("trackSee", { x: (a[F.err20] / a[F.n20]).toFixed(1) });
      h += "</p>";
    });
    if (!any) h += "<p>" + t("trackNone") + "</p>";
    el.innerHTML = h; el.hidden = false;
  }
  function renderLegend(v) {
    var el = $("legend");
    if (tab === "policy") {
      el.innerHTML = "<div class=\"ttl\">" + t(polMorning(v) ? "legPolF" : "legPolE") + "</div><div class=\"ramp\"><i style=\"background:var(--r0)\"></i><i style=\"background:var(--r1)\"></i><i style=\"background:var(--r2)\"></i><i style=\"background:var(--r3)\"></i><i style=\"background:var(--r4)\"></i></div><div class=\"ends\"><span>0%</span><span>50%</span><span>100%</span></div>" +
        "<div class=\"it\"><span class=\"rm\">" + t("rmPolicy") + "</span>" + t("legPolPaid") + "</div><div class=\"it\">" + t("legCampus") + "</div>";
      return;
    }
    if (tab === "ops") {
      var ends = horizon === 90 ? "<span>0</span><span>5</span><span>10+</span>" : "<span>0%</span><span>50%</span><span>100%</span>";
      el.innerHTML = "<div class=\"ttl\">" + (horizon === 90 ? t("legU", { h: v.meta.horizon_min }) : t("legP", { h: horizon })) + "</div><div class=\"ramp\"><i style=\"background:var(--r0)\"></i><i style=\"background:var(--r1)\"></i><i style=\"background:var(--r2)\"></i><i style=\"background:var(--r3)\"></i><i style=\"background:var(--r4)\"></i></div><div class=\"ends\">" + ends + "</div>" +
        "<div class=\"it\"><span class=\"ln\"></span>" + t("legRoute") + "</div><div class=\"it\">" + t("legCampus") + "</div>";
      return;
    }
    var it = function (c, k) { return "<div class=\"it\"><span class=\"sw\" style=\"background:var(" + c + ")\"></span>" + t(k) + "</div>"; };
    var bike = need() === "bike";
    el.innerHTML = "<div class=\"ttl\">" + t(bike ? "legBike" : "legDock") + "</div>" + it("--ok-fill", bike ? "cBikeYes" : "cDockYes") + it("--low-fill", bike ? "cBikeLow" : "cDockLow") + it("--out-fill", bike ? "cBikeNo" : "cDockNo") + it("--gone", bike ? "sGone" : "sFullNow") +
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
    if (v.freshMin != null && agoMin <= 30) { var fm = Math.max(0, n.getHours() * 60 + n.getMinutes() - v.freshMin); tx.textContent = t("liveAt", { t: hm(v.freshMin) }) + sep() + (fm < 1 ? t("justNow") : t("ago", { m: fm })); if (errKind === "old") showErr(null); return; }
    if (agoMin > 25) st.classList.add("stale");
    tx.textContent = t("liveAt", { t: snap.slice(11) }) + sep() + (agoMin < 1 ? t("justNow") : agoMin < 90 ? t("ago", { m: agoMin }) : t("agoH", { h: Math.round(agoMin / 60) }));
    if (agoMin > 60) { if (!errKind || errKind === "old") showErr("old", t("stalebig", { m: agoMin })); } else if (errKind === "old") showErr(null);
  }
  function renderChrome() {
    document.title = t("docTitle"); $("where").textContent = t("where");
    $("mLive").textContent = t("live"); $("mReplay").textContent = t("replay"); $("modeSeg").setAttribute("aria-label", t("modeLabel"));
    $("tabRiderT").textContent = t("tabRider"); $("tabDockT").textContent = t("tabDock"); $("tabPolicyT").textContent = t("tabPolicy"); $("tabOpsT").textContent = t("tabOps"); $("tabAboutT").textContent = t("tabAbout");
    $("grip").setAttribute("aria-label", t("gripLabel")); $("fab").setAttribute("aria-label", t("fabLabel")); $("fab").title = t("fabLabel");
    $("slider").setAttribute("aria-label", t("sliderLabel")); $("replayDay").setAttribute("aria-label", t("dayLabel")); $("horizonSeg").setAttribute("aria-label", t("horizonLabel"));
    $("map").setAttribute("aria-label", t("mapLabel")); $("langSeg").setAttribute("aria-label", t("langK"));
    $("play").innerHTML = playing ? ICON.pause : ICON.play; $("play").setAttribute("aria-label", playing ? t("pauseLabel") : t("playLabel"));
    if (!live && !replay) $("statusText").textContent = t("loading");
    fillDays();
  }
  function applyTab() {
    shell.setAttribute("data-tab", tab);
    [["rider", "tabRider"], ["dock", "tabDock"], ["policy", "tabPolicy"], ["ops", "tabOps"], ["about", "tabAbout"]].forEach(function (x) {
      $(x[1]).setAttribute("aria-selected", tab === x[0] ? "true" : "false"); $(x[1]).tabIndex = tab === x[0] ? 0 : -1; });
    $("paneRider").hidden = tab !== "rider" && tab !== "dock"; $("panePolicy").hidden = tab !== "policy"; $("paneOps").hidden = tab !== "ops"; $("paneAbout").hidden = tab !== "about";
    $("paneRider").setAttribute("aria-labelledby", tab === "dock" ? "tabDock" : "tabRider");
  }
  function setTab(x) {
    var was = tab; tab = x; store("btb-tab", x); applyTab();
    if (picking) setPicking(null);
    if (x === "ops" && was !== "ops") { var v = view(); if (v && map.getZoom() >= 15 && selected == null) fitArea(v); }
    if (x === "policy" && was === "ops") { var w = view(); if (w && selected == null) fitCampus(w, true); }
    if (isPhone()) setSheet(sheetState === "peek" ? "half" : sheetState);
    scroller.scrollTop = 0; render();
  }
  function render() {
    var v = view(); renderChrome(); renderAbout(v); if (!v) return;
    renderStatus(v); renderBell(v); renderCard(v); renderLegend(v);
    if (tab === "rider" || tab === "dock") renderRider(v); else if (tab === "ops") { renderKpis(v); renderPlans(v); renderRisk(v); } else if (tab === "policy") renderPolicy(v);
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
    var cached = false;                                                                        // served by sw.js from its last copy
    return fetch(url, { cache: "no-store" }).then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); cached = !!r.headers.get("X-BTB-Cache"); return r.json(); })
      .then(function (s) {
        live = s; merged = null;
        if (cached) showErr("load", t("stale", { t: s.snapshot_at.slice(11) })); else if (errKind === "load") showErr(null);
        if (mode === "live") { render(); if (cached) $("status").classList.add("stale"); }
        loadFresh();
      })
      .catch(function (e) {
        if (live) { showErr("load", t("stale", { t: live.snapshot_at.slice(11) })); if (mode === "live") { render(); $("status").classList.add("stale"); } }
        else { showErr("load", t("loadFail", { e: e.message })); $("statusText").textContent = "–"; }
      });
  }
  // the operator's counts for the stations around campus, read by the browser itself: up to a minute old instead of up to ten
  function loadFresh() {
    if (qs.fresh === "0" || mode !== "live" || !live || !live.fresh || !live.fresh.sno || !live.fresh.sno.length || document.hidden) return;
    fetch(API, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ station_no: live.fresh.sno }) })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) {
        var d = j && j.retVal && j.retVal.data; if (!Array.isArray(d) || !d.length) return;
        var c = {}; d.forEach(function (x) { if (x.status === 1 && typeof x.available_spaces === "number" && typeof x.empty_spaces === "number") c[x.station_no] = [x.available_spaces, x.empty_spaces]; });
        var n = taipeiNow(); fresh = { min: n.getHours() * 60 + n.getMinutes(), day: n.getFullYear() + "-" + pad(n.getMonth() + 1) + "-" + pad(n.getDate()), c: c }; merged = null;
        if (mode === "live") render();
      }).catch(function () {});
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
  $("tabPolicy").addEventListener("click", function () { setTab("policy"); });
  $("tabOps").addEventListener("click", function () { setTab("ops"); });
  $("tabAbout").addEventListener("click", function () { setTab("about"); });
  $("tabs").addEventListener("keydown", function (e) {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    var order = ["rider", "dock", "policy", "ops", "about"], k = (order.indexOf(tab) + (e.key === "ArrowRight" ? 1 : order.length - 1)) % order.length; setTab(order[k]);
    $({ rider: "tabRider", dock: "tabDock", policy: "tabPolicy", ops: "tabOps", about: "tabAbout" }[order[k]]).focus();
  });
  $("panePolicy").addEventListener("click", function (e) {
    var b = e.target.closest("button[data-v]"), g = b && b.closest("[data-k]"); if (!g) return;
    polSel[g.getAttribute("data-k")] = parseInt(b.getAttribute("data-v"), 10); var v = view(); if (v) renderPolicy(v);
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
  $("fromSel").addEventListener("change", function (e) { choosePlace("origin", e.target.value); });
  $("toSel").addEventListener("change", function (e) { choosePlace(tab === "dock" ? "dest" : "goal", e.target.value); });
  $("fab").addEventListener("click", function () { if (tab !== "rider" && tab !== "dock") setTab("rider"); locate(tab === "dock" ? "dest" : "origin"); });
  $("more").addEventListener("click", function () { nearN = nearN > 8 ? 8 : 16; var v = view(); if (v) renderRider(v); });
  $("relayOnly").addEventListener("click", function () { relayOnly = !relayOnly; var v = view(); if (v) { renderRider(v); drawStations(v); } });
  $("remPlace").addEventListener("change", function (e) { remSave(function (r) { r.place = e.target.value; }); });
  $("remEnd").addEventListener("change", function (e) { remSave(function (r) { r.end = parseInt(e.target.value, 10); }); });
  $("remDays").addEventListener("click", function (e) { var b = e.target.closest("button"); if (!b) return; var d = parseInt(b.getAttribute("data-d"), 10); remSave(function (r) { var k = r.days.indexOf(d); if (k >= 0) r.days.splice(k, 1); else r.days.push(d); }); });
  $("remIcs").addEventListener("click", function () {
    var v = view(); if (!v) return; var r = remState(v); if (!r.days.length) return;
    var url = URL.createObjectURL(new Blob([icsText(r)], { type: "text/calendar;charset=utf-8" })), a = document.createElement("a");
    a.href = url; a.download = "beat-the-bell-reminders.ics"; document.body.appendChild(a); a.click();
    setTimeout(function () { URL.revokeObjectURL(url); a.remove(); }, 1500); toast(t("remindDone"));
  });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") { if (picking) setPicking(null); else if (selected != null) select(null); } });

  // ---------- start ----------
  var qs = {}; location.search.replace(/^\?/, "").split("&").forEach(function (kv) { var p = kv.split("="); if (p[0]) qs[decodeURIComponent(p[0])] = decodeURIComponent(p[1] || ""); });
  var savedLang = qs.lang || load("btb-lang", null);
  if (savedLang === "en") { lang = "en"; $("lZh").setAttribute("aria-pressed", "false"); $("lEn").setAttribute("aria-pressed", "true"); root.lang = "en"; }
  var savedTab = qs.tab || load("btb-tab", "rider"); tab = ["ops", "about", "dock", "policy"].indexOf(savedTab) >= 0 ? savedTab : "rider"; applyTab();
  if (/^#\d{6,}$/.test(location.hash)) pendingSno = location.hash.slice(1);
  if (/^\d\d:\d\d$/.test(qs.t || "")) wantSlot = mins(qs.t);

  initSheet(); initMap(); renderChrome(); renderAbout(null);
  loadLive();
  fetch("outlook.json").then(function (r) { return r.ok ? r.json() : null; }).then(function (j) { usual = j; if (j && view()) render(); }).catch(function () {});
  fetch("places.json").then(function (r) { return r.ok ? r.json() : null; }).then(function (j) {
    if (!j || !j.places || !j.walk) return;
    j.pos = {}; j.byId = {}; j.places.forEach(function (p, k) { j.pos[p.id] = k; j.byId[p.id] = p; }); j.stations.forEach(function (sno, k) { j.pos[sno] = j.places.length + k; });
    PL = j;
    var at = function (id) { var p = id && j.byId[id]; return p ? { kind: "place", id: p.id, lat: p.lat, lng: p.lng } : null; };
    origin = at(qs.from) || at(load("btb-origin", null)) || origin; goal = at(qs.to) || (qs.to === "" ? null : at(load("btb-goal", null))); dest = at(qs.to) || at(load("btb-dest", null)) || dest;
    if (view()) render(); else syncPlaces();
  }).catch(function () {});
  fetch("policy.json", { cache: "no-store" }).then(function (r) { return r.ok ? r.json() : null; }).then(function (j) { policy = j; if (tab === "policy") render(); }).catch(function () {});
  fetch("track.json", { cache: "no-store" }).then(function (r) { return r.ok ? r.json() : null; }).then(function (j) { track = j; renderTrack(); }).catch(function () {});
  loadDays().then(function () { if (/^\d{4}-\d\d-\d\d$/.test(qs.replay || "") && replayDays.indexOf(qs.replay) >= 0) { replayDay = qs.replay; fillDays(); setMode("replay"); } });
  setInterval(function () { if (mode === "live") loadLive(); }, 60000);
  document.addEventListener("visibilitychange", function () { if (!document.hidden && mode === "live") loadFresh(); });
  setInterval(function () { var v = view(); if (v && mode === "live") { renderBell(v); renderStatus(v); } }, 15000);
  // the installed app opens from its own copy and shows the last data it had when the network is gone (sw.js)
  // (a preview without its own origin refuses service workers; ?sw=1 turns it on over http for the checks, ?sw=0 off)
  if ("serviceWorker" in navigator && qs.sw !== "0" && (location.protocol === "https:" || qs.sw === "1")) { try { navigator.serviceWorker.register("sw.js").catch(function () {}); } catch (e) {} }
})();
