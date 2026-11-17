// Every word the page shows, in both languages. {x} marks a value filled in by app.js.
var T = {
  zh: {
    docTitle: "Beat the Bell｜中山大學 YouBike", where: "中山大學 YouBike",
    live: "即時", replay: "重播", tabRider: "找車", tabOps: "調度", tabAbout: "說明",
    loading: "讀取資料中", liveAt: "{t} 更新", ago: "{m} 分鐘前", agoH: "{h} 小時前", justNow: "剛剛", replayAt: "重播 {d} {t}",
    stale: "讀不到新資料，先顯示 {t} 那一筆。",
    stalebig: "紀錄器已經 {m} 分鐘沒有新資料，畫面是最後一筆。",
    loadFail: "資料讀不進來（{e}）。請重新整理，或過幾分鐘再試。",
    replayFail: "這一天的重播讀不進來（{e}）。",

    bellNext: "下一次下課", bellIn: "還有 {m} 分", bellInH: "還有 {h} 小時 {m} 分", inMin: "{m} 分", inHour: "{h} 小時 {m} 分", nowIs: "現在 {t}",
    offdayBig: "今天沒課", offdayNote: "假日沒有下課人潮", overBig: "今天下課了", overNote: "最後一堂在 {t} 下課",

    search: "搜尋站名，例如 圖資", noMatch: "找不到這個站",
    originK: "起點", oCampus: "中山校園", oMe: "我的位置", oPick: "地圖選點",
    geoFail: "拿不到你的位置，改用地圖選點", tooFar: "你不在中山附近，起點先留在校園。", picking: "在地圖上點一下，設成起點", fabLabel: "用我的位置當起點",
    bestK: "建議", bestNearest: "最近的站就有車", bestFar: "近一點的站可能沒車，這站比較保險",
    bestNoneK: "附近可能都沒車", bestNone: "2 公里內的站都可能沒車。往外找地圖上綠色的站。",
    fav: "我的站", near: "附近的站", nearSub: "由近到遠", more: "再看 8 站", less: "收起來",
    walkK: "步行", walkMin: "{m} 分", farK: "直線", walkKm: "{k} 公里",
    sGood: "30 分內有車", sLow: "30 分內可能變少", sEmpty: "30 分內可能沒車", sVery: "30 分內很可能沒車", sGone: "現在沒車", sNone: "沒有資料", sOos: "暫停服務",
    lGood: "有車", lLow: "可能變少", lEmpty: "可能沒車", lVery: "很可能沒車", lGone: "現在沒車",
    noDock: "沒位子還車", ret: "可還 {d}", afterBell: "{at} 預估剩 {b} 台",

    fBikes: "可借", fDocks: "可還", fP30: "30 分內沒車機率", fP60: "60 分內沒車機率",
    afterWhen: "{t} 下課後 {a} 分，預估剩", afterEst: "{b} 台", afterEmpty: "沒車的機率 {p}%", afterFull: "沒位子還車的機率 {p}%",
    afterNone: "今天沒有下一次下課了，所以沒有下課後的預估。",
    chartCap: "今天的車數，虛線是下課鐘", addFav: "加入我的站", rmFav: "移出我的站", nav: "步行導航",
    stale2: "這站的資料是 {m} 分鐘前的", excluded: "旗津的站，卡車路線不會排到", inCampus: "校內", nearCampus: "校外鄰近",
    favAdded: "加進我的站了", favRemoved: "移出我的站了", close: "關閉",

    kpi: "現在的狀況", kpiSub: "{n} 站有資料", uSta: "站", uRide: "人次", kEmpty: "現在沒車", kRisk: "30 分內可能沒車", kUnmet: "未來 {h} 分預估借不到車", kSaved: "照建議路線可以少掉",
    plan: "下課前的卡車路線", copy: "複製路線", copied: "已複製",
    pickN: "載走 {n} 台", dropN: "補 {n} 台", nowAt: "現在 {b}/{c}", eta: "分後到", onTruck: "車上 {n} 台", truck: "卡車 {k}", nStops: "{n} 站",
    tripLen: "約 {t} 分鐘、{k} 公里", tripGain: "預估少 {v} 人次借不到車",
    noPlan: "現在不建議出車。借不到車的人次分散在很多站，最多的一站也只有 {m} 人次，跑一趟補到的抵不過花的時間。", offWindow: "路線只在 06:00 到 23:00 之間規劃。",
    riskH: "最可能沒車的站", unmetH: "未來 90 分缺最多車的站", h30: "30 分", h60: "60 分", hU: "90 分缺口",

    legOutlook: "30 分內的狀況", legP: "{h} 分內沒車的機率", legU: "未來 {h} 分借不到車的人次",
    legNum: "數字是現在可借的車", legCampus: "藍框是校內的站", legRoute: "卡車路線",
    keyH: "地圖和清單怎麼看",
    keyGood: "綠色是 30 分內有車。圓圈裡的數字是現在可借的車。", keyLow: "黃色是可能變少，沒車的機率在 25% 到 50% 之間。", keyEmpty: "橘色是可能沒車，機率 50% 到 75%。",
    keyVery: "紅色是很可能沒車，機率 75% 以上。", keyGone: "深紅是現在就沒車。", keyNone: "灰色是暫停服務或沒有資料。",
    keyRing: "地圖上圓圈外緣的弧線是車柱有車的比例，藍框是校內的站。", keyRoute: "虛線是建議的卡車路線，圓圈裡的數字是停靠順序。",
    aboutWhat: "<h3>這個頁面在做什麼</h3><p>下課那幾分鐘，中山校內的 YouBike 站很容易被借空。這個頁面每 10 分鐘更新一次。要借車的人可以看哪一站等一下還有車，調度的人可以看下課前卡車該先補哪幾站。</p>",
    aboutHow: "<h3>數字怎麼來的</h3>" +
      "<p>車數來自 YouBike 官方 API。紀錄器每 10 分鐘抓一次中山大學周邊 5 公里內的 {n} 個站，從 2026 年 10 月 1 日記到現在。</p>" +
      "<p>「30 分內沒車的機率」是一個 LightGBM 模型算的。模型用臺大周邊 10 個月的站點資料訓練，只看車數和時間，沒有拿中山的資料再調過。在臺大的測試月份 AUC 是 0.93，直接搬到中山也是 0.93。</p>" +
      "<p>「下課後預估剩幾台」把每一站當成一條生滅鏈：借走一台少一台，還進一台多一台。借還的速率用紀錄器的資料估，再從現在的車數往後推到下課後 20 分。</p>" +
      "<p>卡車路線先估每一站未來 {h} 分有幾個人借不到車，再搜尋一條路線，決定先去哪一站、載走或補上幾台。一台卡車最多載 {q} 台、時速 {s} 公里、每站停 {st} 分鐘。用臺大的真實騎乘紀錄重播，派 1、3、6 台卡車，借不到車的人次分別少 13%、30%、45%。</p>" +
      "<p>車程是用直線距離乘 1.3 估的，旗津的站不排進路線。「我的站」只存在這台裝置的瀏覽器裡，不會上傳。</p>",
    langK: "語言", credit: "人工智慧導論期末專案，第 54 組。程式和資料放在 <a href=\"https://github.com/alexlin8888/nsysu-youbike-log\" target=\"_blank\" rel=\"noopener\">GitHub</a>。",
    gripLabel: "拉高或收合清單", playLabel: "播放", pauseLabel: "暫停", sliderLabel: "時間", dayLabel: "日期", modeLabel: "即時或重播", horizonLabel: "排序依據", mapLabel: "站點地圖",
    weekdays: ["日", "一", "二", "三", "四", "五", "六"]
  },
  en: {
    docTitle: "Beat the Bell | NSYSU YouBike", where: "NSYSU YouBike",
    live: "Live", replay: "Replay", tabRider: "Find a bike", tabOps: "Dispatch", tabAbout: "About",
    loading: "Loading data", liveAt: "Updated {t}", ago: "{m} min ago", agoH: "{h} h ago", justNow: "just now", replayAt: "Replay {d} {t}",
    stale: "Can't reach new data. Showing the {t} snapshot.",
    stalebig: "The logger has sent nothing for {m} min. This is its last snapshot.",
    loadFail: "The data did not load ({e}). Reload the page, or try again in a few minutes.",
    replayFail: "This day's replay did not load ({e}).",

    bellNext: "Next class ends", bellIn: "in {m} min", bellInH: "in {h} h {m} min", inMin: "{m} min", inHour: "{h} h {m} min", nowIs: "now {t}",
    offdayBig: "No classes today", offdayNote: "No end-of-class rush on a day off", overBig: "Classes are over", overNote: "The last one ended at {t}",

    search: "Search stations, e.g. Library", noMatch: "No station by that name",
    originK: "From", oCampus: "Campus", oMe: "My location", oPick: "Pick on map",
    geoFail: "Couldn't get your location. Pick a point on the map instead.", tooFar: "You are far from NSYSU, so the start stays on campus.", picking: "Tap the map to set where you start", fabLabel: "Start from my location",
    bestK: "Suggested", bestNearest: "the nearest station has bikes", bestFar: "closer stations may run out, this one is safer",
    bestNoneK: "Nearby stations may all run out", bestNone: "Every station within 2 km may be empty. Look for a green one further out on the map.",
    fav: "My stations", near: "Nearby", nearSub: "nearest first", more: "Show 8 more", less: "Show fewer",
    walkK: "walk", walkMin: "{m} min", farK: "away", walkKm: "{k} km",
    sGood: "Bikes for the next 30 min", sLow: "May run low within 30 min", sEmpty: "May be empty within 30 min", sVery: "Likely empty within 30 min", sGone: "Empty now", sNone: "No data", sOos: "Out of service",
    lGood: "Bikes available", lLow: "May run low", lEmpty: "May be empty", lVery: "Likely empty", lGone: "Empty now",
    noDock: "No free dock", ret: "{d} docks free", afterBell: "about {b} left at {at}",

    fBikes: "Bikes", fDocks: "Free docks", fP30: "Empty within 30 min", fP60: "Empty within 60 min",
    afterWhen: "{a} min after the {t} bell, expected", afterEst: "{b} bikes", afterEmpty: "{p}% chance of no bikes", afterFull: "{p}% chance of no free dock",
    afterNone: "No more classes end today, so there is no after-class estimate.",
    chartCap: "Bikes today; dashed lines are class-end bells", addFav: "Save station", rmFav: "Remove station", nav: "Walking directions",
    stale2: "This station last reported {m} min ago", excluded: "A Qijin station; the truck route never includes it", inCampus: "on campus", nearCampus: "near campus",
    favAdded: "Saved to My stations", favRemoved: "Removed from My stations", close: "Close",

    kpi: "Right now", kpiSub: "{n} stations reporting", uSta: "stations", uRide: "riders", kEmpty: "empty now", kRisk: "may be empty within 30 min", kUnmet: "expected to find no bike in the next {h} min", kSaved: "spared if the truck follows the route",
    plan: "Truck route before the bell", copy: "Copy route", copied: "Copied",
    pickN: "Pick up {n}", dropN: "Drop off {n}", nowAt: "now {b}/{c}", eta: "min away", onTruck: "{n} on the truck", truck: "Truck {k}", nStops: "{n} stops",
    tripLen: "about {t} min, {k} km", tripGain: "about {v} fewer riders left without a bike",
    noPlan: "No trip is worth making now. The shortfall is spread over many stations, {m} riders at the worst one, so a run would save less than it costs in time.", offWindow: "Routes are planned between 06:00 and 23:00 only.",
    riskH: "Most likely to run out", unmetH: "Largest shortfall, next 90 min", h30: "30 min", h60: "60 min", hU: "90-min shortfall",

    legOutlook: "Next 30 minutes", legP: "Chance of no bikes within {h} min", legU: "Riders without a bike, next {h} min",
    legNum: "The number is bikes available now", legCampus: "A blue outline marks a campus station", legRoute: "Truck route",
    keyH: "Reading the map and the list",
    keyGood: "Green: bikes for the next 30 minutes. The number in the circle is bikes available now.", keyLow: "Yellow: may run low, a 25% to 50% chance of no bikes.", keyEmpty: "Orange: may be empty, 50% to 75%.",
    keyVery: "Red: likely empty, 75% or more.", keyGone: "Dark red: empty right now.", keyNone: "Grey: out of service or no data.",
    keyRing: "On the map, the arc around a circle is the share of docks holding a bike. A blue outline marks a campus station.", keyRoute: "The dotted line is the suggested truck route; the numbers are the order of its stops.",
    aboutWhat: "<h3>What this page does</h3><p>In the few minutes after a class ends, the YouBike stations on the NSYSU campus are often emptied. This page updates every 10 minutes. Riders can see which station will still have bikes; dispatchers can see which stations a truck should restock before the bell.</p>",
    aboutHow: "<h3>Where the numbers come from</h3>" +
      "<p>Bike counts come from the official YouBike API. A logger reads the {n} stations within 5 km of NSYSU every 10 minutes and has done so since 1 October 2026.</p>" +
      "<p>The chance of no bikes within 30 minutes comes from a LightGBM model. It was trained on 10 months of station data around NTU, uses only bike counts and time, and was never tuned on NSYSU data. Its AUC is 0.93 on the NTU test months and 0.93 at NSYSU.</p>" +
      "<p>The after-class estimate treats each station as a birth-death chain: a rental removes a bike, a return adds one. The rental and return rates are fitted to the logger's data, and the chain runs forward from the current count to 20 minutes after the bell.</p>" +
      "<p>The truck route starts from how many riders each station is expected to turn away over the next {h} minutes. A search then decides where the truck goes first and how many bikes it picks up or drops off. A truck carries {q} bikes, travels at {s} km/h and spends {st} minutes per stop. Replayed on real NTU trips, 1, 3 and 6 trucks cut the number of riders turned away by 13%, 30% and 45%.</p>" +
      "<p>Travel times are straight-line distance times 1.3, and Qijin stations are left out of the route. My stations are kept in this browser only and are never uploaded.</p>",
    langK: "Language", credit: "Final project for Introduction to Artificial Intelligence, Group 54. Code and data are on <a href=\"https://github.com/alexlin8888/nsysu-youbike-log\" target=\"_blank\" rel=\"noopener\">GitHub</a>.",
    gripLabel: "Expand or collapse the list", playLabel: "Play", pauseLabel: "Pause", sliderLabel: "Time", dayLabel: "Day", modeLabel: "Live or replay", horizonLabel: "Rank by", mapLabel: "Station map",
    weekdays: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
  }
};
