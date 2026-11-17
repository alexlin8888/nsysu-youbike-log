// Every word the page shows, in both languages. {x} marks a value filled in by app.js.
var T = {
  zh: {
    docTitle: "Beat the Bell｜中山大學 YouBike", where: "中山大學 YouBike",
    live: "即時", replay: "重播", tabRider: "借車", tabDock: "還車", tabOps: "調度", tabAbout: "說明",
    loading: "讀取資料中", liveAt: "{t} 更新", ago: "{m} 分鐘前", agoH: "{h} 小時前", justNow: "剛剛", replayAt: "重播 {d} {t}",
    stale: "讀不到新資料，先顯示 {t} 那一筆。",
    stalebig: "紀錄器已經 {m} 分鐘沒有新資料，畫面是最後一筆。",
    loadFail: "資料讀不進來（{e}）。請重新整理，或過幾分鐘再試。",
    replayFail: "這一天的重播讀不進來（{e}）。",

    bellNext: "下一次下課", bellIn: "還有 {m} 分", bellInH: "還有 {h} 小時 {m} 分", inMin: "{m} 分", inHour: "{h} 小時 {m} 分", nowIs: "現在 {t}",
    offdayBig: "今天沒課", offdayNote: "假日沒有下課人潮", overBig: "今天下課了", overNote: "最後一堂在 {t} 下課",
    stBikeOk: "校內現在好借", stBikeLow: "校內的車變少了", stBikeOut: "校內現在很難借到車",
    stDockOk: "校內現在好還", stDockLow: "校內的空位變少了", stDockOut: "校內現在很難還車",

    search: "搜尋站名，例如 圖資", noMatch: "找不到這個站",
    originK: "從哪裡", destK: "到哪裡", oCampus: "中山校園", oKrt: "哈瑪星站", oMe: "我的位置", oPick: "地圖選點",
    whenBikeK: "幾點走", whenDockK: "幾點到", wNow: "現在", wBell: "{t} 下課", wPlus: "{m} 分後",
    geoFail: "拿不到你的位置，改用地圖選點", tooFar: "你不在中山附近，位置先留在校園。", picking: "在地圖上點一下，設成起點", pickingDest: "在地圖上點一下，設成目的地", fabLabel: "用我的位置",
    bestBikeNow: "現在去這站借", bestBikeBell: "{t} 下課後去這站借", bestDock: "騎到這站還",
    skipBike: "{n}比較近，但你到的時候很可能沒車", skipDock: "{n}比較近，但你到的時候很可能停滿",
    weakBike: "附近都不一定有車，這站機會最大", weakDock: "附近都不一定有位子，這站機會最大",
    noneBike: "2 公里內沒有站回報資料", noneDock: "目的地附近沒有站回報資料",
    expect: "到時約剩 {b} 台", docksNow: "現在 {d} 個空位", bikesNow: "現在 {b} 台",
    tipSoon: "{t} 前出發，走 {a} 分鐘就借得到。再晚要走 {b} 分鐘。", tipLast: "{t} 前出發，走 {a} 分鐘就借得到。再晚附近都不一定有車。", tipCalm: "接下來一小時，走 {a} 分鐘內都借得到。",
    fav: "我的站", near: "附近的站", nearBike: "顏色是你走到時的狀況", nearDock: "顏色是你騎到時的狀況", more: "再看 8 站", less: "收起來",
    walkK: "步行", walkDest: "到目的地", walkMin: "{m} 分", farK: "直線", walkKm: "{k} 公里",
    cBikeYes: "應該有車", cBikeMaybe: "不一定有車", cBikeNo: "很可能沒車", sGone: "現在沒車",
    cDockYes: "應該有位子", cDockMaybe: "不一定有位子", cDockNo: "很可能停滿", sFullNow: "現在停滿", sNone: "沒有資料", sOos: "暫停服務",
    tGone: "預估 {t} 借光", tKeep: "到 {t} 都有車", tBack: "預估 {t} 有車還回來", tNoBack: "{t} 前大概都沒車",
    tFull: "預估 {t} 停滿", tFree: "到 {t} 都有位子", tOpen: "預估 {t} 有空位", tNoOpen: "{t} 前大概都沒位子",
    usualBikeCampus: "校內平常幾點難借", usualDockCampus: "校內平常幾點難還", usualBikeGate: "這一帶平常幾點難借", usualDockGate: "這一帶平常幾點難還",
    usualTeach: "上課日平均", usualOff: "假日平均", usualPeak: "最難的時段 {a} 到 {b}", usualEasy: "整天都不難",

    fBikes: "可借", fDocks: "可還", fArrive: "你到的時候", aheadH: "接下來 90 分鐘", aheadBike: "預估車數", aheadDock: "預估空位",
    chartCap: "今天的車數。直的虛線是下課鐘，橫的虛線是預估。", addFav: "加入我的站", rmFav: "移出我的站", nav: "步行導航",
    stale2: "這站的資料是 {m} 分鐘前的", excluded: "旗津的站，卡車路線不會排到", inCampus: "校內", nearCampus: "校外鄰近",
    favAdded: "加進我的站了", favRemoved: "移出我的站了", close: "關閉",

    kpi: "校園這一帶", kpiSub: "校園到捷運之間 {n} 站", uSta: "站", uRide: "人次", kEmpty: "現在沒車", kRisk: "30 分內可能被借光", kUnmet: "未來 {h} 分預估借不到車", kSaved: "這一趟可以少掉",
    plan: "校園專車的下一趟", copy: "複製路線", copied: "已複製",
    pickN: "載走 {n} 台", dropN: "補 {n} 台", nowAt: "現在 {b}/{c}", eta: "分後到", onTruck: "車上 {n} 台", truck: "卡車 {k}", nStops: "{n} 站",
    tripLen: "約 {t} 分鐘、{k} 公里", tripGain: "預估少 {v} 人次借不到車",
    noPlan: "現在不用出車。校園這一帶借不到車的人次很少，最多的一站也只有 {m} 人次。", offWindow: "路線只在 06:00 到 23:00 之間規劃。",
    riskH: "最可能沒車的站", unmetH: "未來 90 分缺最多車的站", h30: "30 分", h60: "60 分", hU: "90 分缺口",

    legBike: "你走到的時候", legDock: "你騎到的時候", legP: "{h} 分內沒車的機率", legU: "未來 {h} 分借不到車的人次",
    legNumBike: "數字是現在可借的車", legNumDock: "數字是現在的空位", legCampus: "藍框是校內的站", legRoute: "卡車路線",
    keyH: "地圖和清單怎麼看",
    keyYes: "綠色是你到的時候應該有車。還車那一頁是應該有位子。圓圈裡的數字是現在的數量。", keyMaybe: "黃色是不一定，十次裡大概有一到四次會撲空。", keyNo: "紅色是很可能沒有。",
    keyGone: "深紅是現在就沒有，短時間內也不太會有。", keyNone: "灰色是暫停服務或沒有資料。",
    keyRing: "地圖上圓圈外緣的弧線是車柱有車的比例，藍框是校內的站。", keyRoute: "虛線是建議的卡車路線，圓圈裡的數字是停靠順序。",
    aboutWhat: "<h3>這個頁面在做什麼</h3><p>中山的 YouBike 有三個時段特別難用。傍晚 5 點到 7 點半，校內借不到車。早上 9 點到 10 點半，校內沒位子還車。同一段時間，山下和捷運站的車也被借光。這個頁面每 10 分鐘更新一次，告訴你走到的時候哪一站還有車，騎到的時候哪一站還有位子。</p>",
    aboutProof: "<h3>照著走有沒有用</h3><p>我們拿 12 個沒有用來估模型的上課日來對：頁面建議的站，在人走到的那一刻，紀錄器上是不是真的有車。</p>" +
      "<p>傍晚在校內借車，走到最近的站有 64% 借得到，看現在的車數挑站是 73%，照這個頁面的建議是 93%，平均多走不到 5 分鐘。早上到校內還車，最近的站有 69% 還得進去，照建議是 95%，多走 1 分鐘。早上在山下借車，76% 變成 97%。</p>",
    aboutHow: "<h3>數字怎麼來的</h3>" +
      "<p>車數和空位來自 YouBike 官方 API。紀錄器每 10 分鐘抓一次中山大學周邊 5 公里內的 {n} 個站，從 2026 年 10 月 1 日記到現在。</p>" +
      "<p>「你到的時候有沒有車」把每一站當成一條生滅鏈：借走一台少一台，還進一台多一台。借還的速率用紀錄器的資料估，校園到捷運之間的 19 站在上課日每 10 分鐘估一組，因為下課那 10 分鐘借得特別快。從現在的車數往後推到你走到的那一刻，有車的機會九成以上才算「應該有車」。還車的門檻比較嚴，要九成五。「預估幾點借光」是有車的機會掉到一半以下的時間。</p>" +
      "<p>調度那一頁只排一台顧校園這一帶的卡車。先估每一站未來 {h} 分有幾個人借不到車，再搜尋路線，決定去哪一站載、送到哪一站。一台卡車最多載 {q} 台、時速 {s} 公里、每站停 {st} 分鐘。用估出來的借還速率模擬，這樣一台車讓傍晚校內借不到車的人次少 34%，讓早上山下借不到車的人次少 70%。在臺大用真實的騎乘紀錄重播，1、3、6 台卡車少 13%、30%、45%。</p>" +
      "<p>調度頁的「30 分內可能被借光」用的是另一個模型：LightGBM，先用臺大周邊 10 個月的資料訓練，再用中山的資料微調。</p>" +
      "<p>步行時間用直線距離乘 1.25、每分鐘 80 公尺估。車程用直線距離乘 1.3，旗津的站不排進路線。「我的站」只存在這台裝置的瀏覽器裡，不會上傳。</p>",
    langK: "語言", credit: "人工智慧導論期末專案，第 54 組。程式和資料放在 <a href=\"https://github.com/alexlin8888/nsysu-youbike-log\" target=\"_blank\" rel=\"noopener\">GitHub</a>。",
    gripLabel: "拉高或收合清單", playLabel: "播放", pauseLabel: "暫停", sliderLabel: "時間", dayLabel: "日期", modeLabel: "即時或重播", horizonLabel: "排序依據", mapLabel: "站點地圖",
    weekdays: ["日", "一", "二", "三", "四", "五", "六"]
  },
  en: {
    docTitle: "Beat the Bell | NSYSU YouBike", where: "NSYSU YouBike",
    live: "Live", replay: "Replay", tabRider: "Borrow", tabDock: "Return", tabOps: "Dispatch", tabAbout: "About",
    loading: "Loading data", liveAt: "Updated {t}", ago: "{m} min ago", agoH: "{h} h ago", justNow: "just now", replayAt: "Replay {d} {t}",
    stale: "Can't reach new data. Showing the {t} snapshot.",
    stalebig: "The logger has sent nothing for {m} min. This is its last snapshot.",
    loadFail: "The data did not load ({e}). Reload the page, or try again in a few minutes.",
    replayFail: "This day's replay did not load ({e}).",

    bellNext: "Next class ends", bellIn: "in {m} min", bellInH: "in {h} h {m} min", inMin: "{m} min", inHour: "{h} h {m} min", nowIs: "now {t}",
    offdayBig: "No classes today", offdayNote: "No end-of-class rush on a day off", overBig: "Classes are over", overNote: "The last one ended at {t}",
    stBikeOk: "Bikes are easy to find on campus", stBikeLow: "Campus is running low on bikes", stBikeOut: "Campus is nearly out of bikes",
    stDockOk: "Docks are easy to find on campus", stDockLow: "Campus docks are filling up", stDockOut: "Campus docks are nearly full",

    search: "Search stations, e.g. Library", noMatch: "No station by that name",
    originK: "From", destK: "To", oCampus: "Campus", oKrt: "KRT Sizihwan", oMe: "My location", oPick: "Pick on map",
    whenBikeK: "Leaving", whenDockK: "Arriving", wNow: "Now", wBell: "After {t} class", wPlus: "In {m} min",
    geoFail: "Couldn't get your location. Pick a point on the map instead.", tooFar: "You are far from NSYSU, so the place stays on campus.", picking: "Tap the map to set where you start", pickingDest: "Tap the map to set where you are going", fabLabel: "Use my location",
    bestBikeNow: "Borrow here now", bestBikeBell: "Borrow here after the {t} class", bestDock: "Return here",
    skipBike: "{n} is closer but will probably be out when you get there", skipDock: "{n} is closer but will probably be full when you get there",
    weakBike: "No sure bet nearby. This station has the best chance.", weakDock: "No sure bet nearby. This station has the best chance.",
    noneBike: "No station within 2 km is reporting", noneDock: "No station near the destination is reporting",
    expect: "about {b} left by then", docksNow: "{d} free docks now", bikesNow: "{b} bikes now",
    tipSoon: "Leave before {t} and a bike is {a} min away. Later it is {b} min.", tipLast: "Leave before {t} and a bike is {a} min away. Later nothing nearby is a sure bet.", tipCalm: "For the next hour a bike stays within {a} min.",
    fav: "My stations", near: "Nearby", nearBike: "colour: when you get there on foot", nearDock: "colour: when you ride in", more: "Show 8 more", less: "Show fewer",
    walkK: "walk", walkDest: "to destination", walkMin: "{m} min", farK: "away", walkKm: "{k} km",
    cBikeYes: "Should have a bike", cBikeMaybe: "May be out", cBikeNo: "Probably out", sGone: "No bikes now",
    cDockYes: "Should have a dock", cDockMaybe: "May be full", cDockNo: "Probably full", sFullNow: "Full now", sNone: "No data", sOos: "Out of service",
    tGone: "likely out by {t}", tKeep: "bikes until {t}", tBack: "a bike likely back by {t}", tNoBack: "probably none before {t}",
    tFull: "likely full by {t}", tFree: "docks until {t}", tOpen: "a dock likely free by {t}", tNoOpen: "probably full until {t}",
    usualBikeCampus: "When campus usually runs out", usualDockCampus: "When campus is usually full", usualBikeGate: "When this area usually runs out", usualDockGate: "When this area is usually full",
    usualTeach: "teaching-day average", usualOff: "day-off average", usualPeak: "hardest {a} to {b}", usualEasy: "easy all day",

    fBikes: "Bikes", fDocks: "Free docks", fArrive: "When you arrive", aheadH: "Next 90 minutes", aheadBike: "expected bikes", aheadDock: "expected free docks",
    chartCap: "Bikes today. Vertical dashes are class ends; the dashed line is the forecast.", addFav: "Save station", rmFav: "Remove station", nav: "Walking directions",
    stale2: "This station last reported {m} min ago", excluded: "A Qijin station; the truck route never includes it", inCampus: "on campus", nearCampus: "near campus",
    favAdded: "Saved to My stations", favRemoved: "Removed from My stations", close: "Close",

    kpi: "Around campus", kpiSub: "{n} stations between campus and the metro", uSta: "stations", uRide: "riders", kEmpty: "empty now", kRisk: "likely to run out within 30 min", kUnmet: "expected to find no bike in the next {h} min", kSaved: "spared by this trip",
    plan: "Next trip of the campus truck", copy: "Copy route", copied: "Copied",
    pickN: "Pick up {n}", dropN: "Drop off {n}", nowAt: "now {b}/{c}", eta: "min away", onTruck: "{n} on the truck", truck: "Truck {k}", nStops: "{n} stops",
    tripLen: "about {t} min, {k} km", tripGain: "about {v} fewer riders left without a bike",
    noPlan: "No trip is needed now. Few riders around campus are expected to find no bike, {m} at the worst station.", offWindow: "Routes are planned between 06:00 and 23:00 only.",
    riskH: "Most likely to run out", unmetH: "Largest shortfall, next 90 min", h30: "30 min", h60: "60 min", hU: "Shortfall",

    legBike: "When you get there on foot", legDock: "When you ride in", legP: "Chance of no bikes within {h} min", legU: "Riders without a bike, next {h} min",
    legNumBike: "The number is bikes available now", legNumDock: "The number is free docks now", legCampus: "A blue outline marks a campus station", legRoute: "Truck route",
    keyH: "Reading the map and the list",
    keyYes: "Green: there should be a bike when you get there. On the Return tab, a free dock. The number in the circle is the count right now.", keyMaybe: "Yellow: not certain. You would come up empty one to four times in ten.", keyNo: "Red: probably none.",
    keyGone: "Dark red: none right now, and little chance of one soon.", keyNone: "Grey: out of service or no data.",
    keyRing: "On the map, the arc around a circle is the share of docks holding a bike. A blue outline marks a campus station.", keyRoute: "The dotted line is the suggested truck route; the numbers are the order of its stops.",
    aboutWhat: "<h3>What this page does</h3><p>YouBike around NSYSU is hard to use at three times of day. From 17:00 to 19:30 the campus has no bikes. From 09:00 to 10:30 the campus has no free docks. Over the same morning hours the stations at the foot of the campus and at the metro run out of bikes. This page updates every 10 minutes and tells you which station will still have a bike when you get there on foot, and which will still have a dock when you ride in.</p>",
    aboutProof: "<h3>Does following it help</h3><p>We checked on 12 teaching days that were not used to fit the model: at the minute a rider would reach the suggested station, did the logger show a bike there?</p>" +
      "<p>Leaving campus in the evening, the nearest station had a bike 64% of the time, a station chosen from live counts 73%, and the station this page suggests 93%, for under 5 minutes of extra walking. Returning a bike on campus in the morning, the nearest station had a dock 69% of the time and the suggested one 95%, for 1 extra minute. Borrowing at the foot of the campus in the morning went from 76% to 97%.</p>",
    aboutHow: "<h3>Where the numbers come from</h3>" +
      "<p>Bike and dock counts come from the official YouBike API. A logger reads the {n} stations within 5 km of NSYSU every 10 minutes and has done so since 1 October 2026.</p>" +
      "<p>Whether a station will have a bike when you arrive comes from a birth-death chain: a rental removes a bike, a return adds one. The rental and return rates are fitted to the logger's data. The 19 stations between campus and the metro get one pair of rates per 10 minutes on teaching days, because rentals jump in the 10 minutes after a class ends. The chain runs forward from the current count to the minute you arrive, and a station counts as a sure bet at a 90% chance of a bike. For docks the bar is 95%. The time a station is likely out is when that chance falls below one half.</p>" +
      "<p>The Dispatch tab plans one truck that serves the stations around campus. It starts from how many riders each station is expected to turn away over the next {h} minutes; a search then decides where the truck picks up and where it delivers. A truck carries {q} bikes, travels at {s} km/h and spends {st} minutes per stop. In a simulation driven by the fitted rates, one such truck cuts the riders who find no bike on campus in the evening by 34%, and those who find none at the foot of the campus in the morning by 70%. Replayed on real NTU trips, 1, 3 and 6 trucks cut the number by 13%, 30% and 45%.</p>" +
      "<p>The list of stations likely to run out within 30 minutes on the Dispatch tab uses a second model: LightGBM, trained on 10 months of station data around NTU and then fine-tuned on NSYSU data.</p>" +
      "<p>Walking time is straight-line distance times 1.25 at 80 m per minute. Driving time is straight-line distance times 1.3, and Qijin stations are left out of the route. My stations are kept in this browser only and are never uploaded.</p>",
    langK: "Language", credit: "Final project for Introduction to Artificial Intelligence, Group 54. Code and data are on <a href=\"https://github.com/alexlin8888/nsysu-youbike-log\" target=\"_blank\" rel=\"noopener\">GitHub</a>.",
    gripLabel: "Expand or collapse the list", playLabel: "Play", pauseLabel: "Pause", sliderLabel: "Time", dayLabel: "Day", modeLabel: "Live or replay", horizonLabel: "Rank by", mapLabel: "Station map",
    weekdays: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
  }
};
